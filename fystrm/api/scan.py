from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from fystrm.core.queue import get_arq_pool
from fystrm.core.ws_hub import hub
from fystrm.db import get_session
from fystrm.models.library import Library
from fystrm.models.task import ScanTask

router = APIRouter(tags=["scan"])


class ScanRequest(BaseModel):
    library_id: int


class ScanTaskOut(BaseModel):
    id: int
    library_id: int
    status: str
    total_files: int
    processed_files: int
    success_count: int
    failed_count: int
    error: Optional[str] = None
    stage: str = "pending"
    stage_message: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


@router.post("/api/scan", response_model=ScanTaskOut, status_code=202)
async def start_scan(req: ScanRequest, db: AsyncSession = Depends(get_session)) -> ScanTaskOut:
    lib = await db.get(Library, req.library_id)
    if not lib:
        raise HTTPException(404, "Library not found")
    if not lib.enabled:
        raise HTTPException(400, "Library is disabled")
    task = ScanTask(library_id=req.library_id, status="pending")
    db.add(task)
    await db.commit()
    await db.refresh(task)

    pool = await get_arq_pool()
    await pool.enqueue_job("scan_library_task", task.id, _job_id=f"scan:{task.id}")

    return ScanTaskOut.model_validate(_serialize(task))


@router.get("/api/tasks", response_model=list[ScanTaskOut])
async def list_tasks(limit: int = 50, db: AsyncSession = Depends(get_session)) -> list[ScanTaskOut]:
    res = await db.execute(select(ScanTask).order_by(desc(ScanTask.id)).limit(limit))
    return [ScanTaskOut.model_validate(_serialize(t)) for t in res.scalars().all()]


@router.get("/api/tasks/{task_id}", response_model=ScanTaskOut)
async def get_task(task_id: int, db: AsyncSession = Depends(get_session)) -> ScanTaskOut:
    t = await db.get(ScanTask, task_id)
    if not t:
        raise HTTPException(404, "Task not found")
    return ScanTaskOut.model_validate(_serialize(t))


def _serialize(t: ScanTask) -> dict:
    return {
        "id": t.id, "library_id": t.library_id, "status": t.status,
        "total_files": t.total_files, "processed_files": t.processed_files,
        "success_count": t.success_count, "failed_count": t.failed_count,
        "error": t.error, "stage": t.stage, "stage_message": t.stage_message,
        "started_at": t.started_at, "finished_at": t.finished_at,
        "created_at": t.created_at, "updated_at": t.updated_at,
    }
