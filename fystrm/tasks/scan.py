"""扫描任务: scanner -> identifier -> scraper -> strm/nfo/poster -> DB

通过 WSHub 实时推进度。
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger
from sqlalchemy import select

from fystrm.core.ws_hub import publish
from fystrm.db import SessionLocal
from fystrm.engines.emby import refresh_library
from fystrm.engines.identifier import identify
from fystrm.engines.scanner import scan_directory
from fystrm.engines.scraper import scrape_movie
from fystrm.engines.strm import generate_strm
from fystrm.models.library import Library
from fystrm.models.media import MediaItem
from fystrm.models.task import ScanTask
from fystrm.plugins.drives.local import LocalDrivePlugin
from fystrm.plugins.meta.tmdb import TMDBPlugin
from fystrm.plugins.strm_path.base import StrmContext
from fystrm.plugins.strm_path.cd2_local import CD2LocalStrmPathPlugin


async def scan_library_task(ctx: dict, task_id: int) -> dict[str, Any]:
    """arq 任务: 扫描整个 library。

    Args:
        task_id: ScanTask.id
    """
    logger.info("scan_library_task start, task_id={}", task_id)
    async with SessionLocal() as db:
        task = await db.get(ScanTask, task_id)
        if not task:
            raise ValueError(f"ScanTask {task_id} not found")
        lib = await db.get(Library, task.library_id)
        if not lib:
            task.status = "failed"
            task.error = f"Library {task.library_id} not found"
            task.finished_at = _now()
            await db.commit()
            return {"status": "failed"}

        task.status = "running"
        task.started_at = _now()
        await db.commit()

    await publish(task_id, {"event": "start", "task_id": task_id, "library_id": lib.id})

    drive = LocalDrivePlugin()
    meta_plugin = TMDBPlugin()
    strm_plugin = CD2LocalStrmPathPlugin()
    target_root = Path(lib.target_strm_path)
    target_root.mkdir(parents=True, exist_ok=True)

    # 先收集全部文件计算 total
    files = []
    async for sf in scan_directory(drive, lib.source_path):
        files.append(sf)

    total = len(files)
    async with SessionLocal() as db:
        task = await db.get(ScanTask, task_id)
        task.total_files = total
        await db.commit()
    await publish(task_id, {"event": "discovered", "total": total})

    processed = 0
    success = 0
    failed = 0
    for sf in files:
        processed += 1
        try:
            await _process_one(
                db_lib=lib,
                sf=sf,
                meta_plugin=meta_plugin,
                strm_plugin=strm_plugin,
                target_root=target_root,
            )
            success += 1
            event = "file_done"
        except Exception as e:
            logger.exception("file failed: {}", sf.rel_path)
            failed += 1
            event = "file_failed"
            error_msg = str(e)[:200]
        else:
            error_msg = None

        async with SessionLocal() as db:
            task = await db.get(ScanTask, task_id)
            task.processed_files = processed
            task.success_count = success
            task.failed_count = failed
            await db.commit()

        await publish(task_id, {
            "event": event,
            "processed": processed,
            "total": total,
            "success": success,
            "failed": failed,
            "file": sf.rel_path,
            "error": error_msg,
        })

    # 触发 Emby refresh
    emby_ok = await refresh_library()
    await publish(task_id, {"event": "emby_refresh", "ok": emby_ok})

    async with SessionLocal() as db:
        task = await db.get(ScanTask, task_id)
        task.status = "done"
        task.finished_at = _now()
        await db.commit()
        lib_obj = await db.get(Library, lib.id)
        lib_obj.last_scan_at = _now()
        await db.commit()

    await publish(task_id, {
        "event": "done",
        "processed": processed,
        "total": total,
        "success": success,
        "failed": failed,
    })
    logger.info("scan_library_task done, task_id={} success={} failed={}", task_id, success, failed)
    return {"status": "done", "success": success, "failed": failed}


async def _process_one(*, db_lib, sf, meta_plugin, strm_plugin, target_root) -> None:
    """处理单个文件: 识别 -> 刮削 -> 生成 strm/nfo/poster -> 入库 MediaItem"""
    info = identify(sf.drive_file.name)
    # v0.1 仅做电影
    if info.media_type != "movie":
        logger.info("skip non-movie {} (type={})", sf.drive_file.name, info.media_type)
        await _upsert(
            source_file_path=sf.drive_file.path,
            library_id=db_lib.id,
            title=info.title,
            year=info.year,
            media_type=info.media_type,
            source_file_size=sf.drive_file.size,
            scrape_status="skipped",
            scrape_error=f"v0.1 only supports movie, got {info.media_type}",
        )
        return

    meta = await scrape_movie(meta_plugin, info)
    if not meta:
        await _upsert(
            source_file_path=sf.drive_file.path,
            library_id=db_lib.id,
            title=info.title,
            year=info.year,
            media_type="movie",
            source_file_size=sf.drive_file.size,
            scrape_status="failed",
            scrape_error="no TMDB match",
        )
        return

    strm_ctx = StrmContext(
        source_path=sf.drive_file.path,
        source_root=db_lib.source_path,
        cd2_mount_prefix=db_lib.cd2_mount_prefix,
    )
    artifacts = await generate_strm(meta, target_root, strm_plugin, strm_ctx)

    await _upsert(
        source_file_path=sf.drive_file.path,
        library_id=db_lib.id,
        title=meta.title,
        original_title=meta.original_title,
        year=meta.year,
        tmdb_id=meta.source_id,
        media_type="movie",
        source_file_size=sf.drive_file.size,
        strm_path=str(artifacts.strm_path),
        nfo_path=str(artifacts.nfo_path),
        poster_path=str(artifacts.poster_path) if artifacts.poster_path else None,
        fanart_path=str(artifacts.fanart_path) if artifacts.fanart_path else None,
        scrape_status="done",
        scrape_error=None,
    )



async def _upsert(*, source_file_path: str, **fields) -> None:
    """Insert or update MediaItem by source_file_path."""
    async with SessionLocal() as db:
        res = await db.execute(
            select(MediaItem).where(MediaItem.source_file_path == source_file_path)
        )
        item = res.scalar_one_or_none()
        if item is None:
            item = MediaItem(source_file_path=source_file_path, **fields)
            db.add(item)
        else:
            for k, v in fields.items():
                setattr(item, k, v)
        await db.commit()


def _now() -> datetime:
    return datetime.now(timezone.utc)
