"""仪表盘聚合 API."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from fystrm.db import get_session
from fystrm.models.library import Library
from fystrm.models.media import MediaItem
from fystrm.models.task import ScanTask

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
async def dashboard_stats(db: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    # 总数
    media_count = (await db.execute(select(func.count(MediaItem.id)))).scalar_one()
    library_count = (await db.execute(select(func.count(Library.id)))).scalar_one()
    task_count = (await db.execute(select(func.count(ScanTask.id)))).scalar_one()
    total_size = (await db.execute(select(func.coalesce(func.sum(MediaItem.source_file_size), 0)))).scalar_one()

    # by status
    by_status_rows = (await db.execute(
        select(MediaItem.scrape_status, func.count(MediaItem.id))
        .group_by(MediaItem.scrape_status)
    )).all()
    by_status = {r[0]: r[1] for r in by_status_rows}

    # by media_type
    by_type_rows = (await db.execute(
        select(MediaItem.media_type, func.count(MediaItem.id))
        .group_by(MediaItem.media_type)
    )).all()
    by_type = {r[0]: r[1] for r in by_type_rows}

    # 最近 7 天扫描任务趋势 (按完成日聚合 success/failed)
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=7)
    trend_rows = (await db.execute(
        select(
            func.date(ScanTask.created_at).label("d"),
            func.coalesce(func.sum(ScanTask.success_count), 0),
            func.coalesce(func.sum(ScanTask.failed_count), 0),
            func.count(ScanTask.id),
        )
        .where(ScanTask.created_at >= since)
        .group_by("d")
        .order_by("d")
    )).all()
    trend = [
        {"date": str(r[0]), "success": int(r[1]), "failed": int(r[2]), "tasks": int(r[3])}
        for r in trend_rows
    ]

    # 最近 5 个任务
    recent_tasks_rows = (await db.execute(
        select(ScanTask).order_by(desc(ScanTask.id)).limit(5)
    )).scalars().all()
    recent_tasks = [
        {
            "id": t.id, "library_id": t.library_id, "status": t.status,
            "total_files": t.total_files, "processed_files": t.processed_files,
            "success_count": t.success_count, "failed_count": t.failed_count,
            "started_at": t.started_at, "finished_at": t.finished_at,
        }
        for t in recent_tasks_rows
    ]

    # 最近 5 个 MediaItem
    recent_media_rows = (await db.execute(
        select(MediaItem).order_by(desc(MediaItem.id)).limit(5)
    )).scalars().all()
    recent_media = [
        {
            "id": m.id, "title": m.title, "year": m.year, "media_type": m.media_type,
            "season": m.season, "episode": m.episode, "episode_title": m.episode_title,
            "tmdb_id": m.tmdb_id, "scrape_status": m.scrape_status,
            "poster_path": m.poster_path,
        }
        for m in recent_media_rows
    ]

    return {
        "media_count": media_count,
        "library_count": library_count,
        "task_count": task_count,
        "total_size": int(total_size or 0),
        "by_status": by_status,
        "by_type": by_type,
        "trend_7d": trend,
        "recent_tasks": recent_tasks,
        "recent_media": recent_media,
    }
