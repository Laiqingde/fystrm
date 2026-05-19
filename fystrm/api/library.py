from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fystrm.db import get_session
from fystrm.models.library import Library

router = APIRouter(prefix="/api/libraries", tags=["library"])


class LibraryIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    source_path: str = Field(..., min_length=1)
    target_strm_path: str = Field(..., min_length=1)
    cd2_mount_prefix: str = Field(default="", description="cd2_local 模式下的 CD2 路径前缀")
    media_type: str = Field("movie", pattern="^(movie|tv|mixed)$")
    enabled: bool = True
    # v0.2 新字段
    strm_mode: str = Field("cd2_local", pattern="^(cd2_local|webdav)$")
    webdav_base_url: str | None = None
    webdav_path_prefix: str | None = None


class LibraryOut(LibraryIn):
    id: int
    last_scan_at: datetime | None
    created_at: datetime
    updated_at: datetime


@router.get("/", response_model=list[LibraryOut])
async def list_libraries(db: AsyncSession = Depends(get_session)) -> list[LibraryOut]:
    res = await db.execute(select(Library).order_by(Library.id))
    return [LibraryOut.model_validate(_serialize(row)) for row in res.scalars().all()]


@router.post("/", response_model=LibraryOut, status_code=201)
async def create_library(payload: LibraryIn, db: AsyncSession = Depends(get_session)) -> LibraryOut:
    lib = Library(**payload.model_dump())
    db.add(lib)
    await db.commit()
    await db.refresh(lib)
    return LibraryOut.model_validate(_serialize(lib))


@router.get("/{lib_id}", response_model=LibraryOut)
async def get_library(lib_id: int, db: AsyncSession = Depends(get_session)) -> LibraryOut:
    lib = await db.get(Library, lib_id)
    if not lib:
        raise HTTPException(404, "Library not found")
    return LibraryOut.model_validate(_serialize(lib))


@router.put("/{lib_id}", response_model=LibraryOut)
async def update_library(lib_id: int, payload: LibraryIn, db: AsyncSession = Depends(get_session)) -> LibraryOut:
    lib = await db.get(Library, lib_id)
    if not lib:
        raise HTTPException(404, "Library not found")
    for k, v in payload.model_dump().items():
        setattr(lib, k, v)
    await db.commit()
    await db.refresh(lib)
    return LibraryOut.model_validate(_serialize(lib))


@router.delete("/{lib_id}", status_code=204)
async def delete_library(lib_id: int, db: AsyncSession = Depends(get_session)) -> None:
    lib = await db.get(Library, lib_id)
    if not lib:
        raise HTTPException(404, "Library not found")
    await db.delete(lib)
    await db.commit()


def _serialize(lib: Library) -> dict:
    return {
        "id": lib.id,
        "name": lib.name,
        "source_path": lib.source_path,
        "target_strm_path": lib.target_strm_path,
        "cd2_mount_prefix": lib.cd2_mount_prefix,
        "media_type": lib.media_type,
        "enabled": lib.enabled,
        "strm_mode": lib.strm_mode,
        "webdav_base_url": lib.webdav_base_url,
        "webdav_path_prefix": lib.webdav_path_prefix,
        "last_scan_at": lib.last_scan_at,
        "created_at": lib.created_at,
        "updated_at": lib.updated_at,
    }
