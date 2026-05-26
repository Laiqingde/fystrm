"""扫描任务: scanner -> identifier -> scraper -> strm/nfo/poster/subtitles -> DB"""

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
from fystrm.engines.metadata_sync import sync_metadata
from fystrm.engines.scanner import parse_extensions, scan_directory
from fystrm.engines.scraper import scrape_episode, scrape_movie, scrape_tv
from fystrm.engines.strm import generate_episode_strm, generate_movie_strm
from fystrm.engines.subtitle import copy_subtitles
from fystrm.models.library import Library
from fystrm.models.media import MediaItem
from fystrm.models.task import ScanTask
from fystrm.plugins.drives.local import LocalDrivePlugin
from fystrm.plugins.meta.tmdb import TMDBPlugin
from fystrm.plugins.strm_path.base import StrmContext, StrmPathPlugin
from fystrm.plugins.strm_path.cd2_local import CD2LocalStrmPathPlugin
from fystrm.plugins.strm_path.webdav import WebDAVStrmPathPlugin


def _make_strm_plugin(library: Library) -> StrmPathPlugin:
    if library.strm_mode == "webdav":
        return WebDAVStrmPathPlugin()
    return CD2LocalStrmPathPlugin()


def _make_strm_ctx(library: Library, source_path: str) -> StrmContext:
    return StrmContext(
        source_path=source_path,
        source_root=library.source_path,
        cd2_mount_prefix=library.cd2_mount_prefix or "",
        webdav_base_url=library.webdav_base_url,
        webdav_path_prefix=library.webdav_path_prefix,
    )


async def scan_library_task(ctx: dict, task_id: int, mode: str = "full") -> dict[str, Any]:
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
    strm_plugin = _make_strm_plugin(lib)
    target_root = Path(lib.target_strm_path)
    target_root.mkdir(parents=True, exist_ok=True)

    # === stage 1: discovering ===
    await _update_stage(task_id, "discovering", "扫描视频文件中...")
    video_exts = parse_extensions(lib.strm_extensions) or None
    files = []
    async for sf in scan_directory(drive, lib.source_path, video_extensions=video_exts):
        files.append(sf)
        if len(files) % 100 == 0:
            await _update_stage(task_id, "discovering", f"已发现 {len(files)} 个视频...")

    total = len(files)
    async with SessionLocal() as db:
        task = await db.get(ScanTask, task_id)
        task.total_files = total
        await db.commit()
    await publish(task_id, {"event": "discovered", "total": total})
    await _update_stage(task_id, "processing", f"{'增量' if mode == 'incremental' else '全量'}处理 0/{total}")

    # Per-task cache: 同剧集只写一次 tvshow.nfo
    tvshow_lock: set[str] = set()
    # 跨文件复用 tv 详情
    tv_meta_cache: dict[str, Any] = {}

    processed = 0
    success = 0
    failed = 0
    skipped = 0
    for sf in files:
        processed += 1
        try:
            outcome = await _process_one(
                lib=lib,
                sf=sf,
                meta_plugin=meta_plugin,
                strm_plugin=strm_plugin,
                target_root=target_root,
                tvshow_lock=tvshow_lock,
                tv_meta_cache=tv_meta_cache,
                mode=mode,
            )
            if outcome in ("done", "no_scrape"):
                success += 1; event = "file_done"
            elif outcome == "skipped":
                skipped += 1; event = "file_skipped"
            else:
                failed += 1; event = "file_failed"
            error_msg = None
        except Exception as e:
            logger.exception("file failed: {}", sf.rel_path)
            failed += 1
            event = "file_failed"
            error_msg = str(e)[:200]

        async with SessionLocal() as db:
            task = await db.get(ScanTask, task_id)
            task.processed_files = processed
            task.success_count = success
            task.failed_count = failed
            await db.commit()

        await publish(task_id, {
            "event": event,
            "processed": processed, "total": total,
            "success": success, "failed": failed, "skipped": skipped,
            "file": sf.rel_path, "error": error_msg,
        })

    # === stage 3: syncing_metadata (后置, 已经把视频处理完用户看到 100%) ===
    metadata_exts = parse_extensions(lib.metadata_extensions)
    if metadata_exts:
        await _update_stage(task_id, "syncing_metadata", "同步元数据中...")

        def _progress(scanned, copied, skipped):
            msg = f"同步元数据 {scanned} (copy {copied} / 跳过 {skipped})"
            # 这是从同步函数回调, 不能 await, 用 asyncio.run_coroutine_threadsafe 或直接同步写
            # 但 publish 是 async, 简化用 logger 输出, stage 通过外层定期更新
            logger.info(msg)
        result = sync_metadata(lib.source_path, lib.target_strm_path, metadata_exts, progress_cb=_progress)
        await _update_stage(task_id, "syncing_metadata",
                            f"元数据同步完成: copy {result["copied"]} / 跳过 {result["skipped"]} / 共 {result["total"]}")
        logger.info("metadata 同步 copy={} skipped={} total={}",
                    result["copied"], result["skipped"], result["total"])

    emby_ok = await refresh_library()
    await publish(task_id, {"event": "emby_refresh", "ok": emby_ok})

    async with SessionLocal() as db:
        task = await db.get(ScanTask, task_id)
        task.status = "done"
        task.stage = "done"
        task.stage_message = None
        task.finished_at = _now()
        await db.commit()
        lib_obj = await db.get(Library, lib.id)
        lib_obj.last_scan_at = _now()
        await db.commit()

    await publish(task_id, {
        "event": "done",
        "processed": processed, "total": total,
        "success": success, "failed": failed, "skipped": skipped,
    })
    logger.info("scan task done task_id={} success={} failed={} skipped={}",
                task_id, success, failed, skipped)
    return {"status": "done", "success": success, "failed": failed, "skipped": skipped}


async def _process_one(*, lib, sf, meta_plugin, strm_plugin, target_root, tvshow_lock, tv_meta_cache, mode: str = "full") -> str:
    """Returns: "done" | "skipped" | "failed" | "no_scrape"."""
    # 增量模式: 已入库 (done/no_scrape/skipped) 的文件直接跳过, 只处理新增
    if mode == "incremental":
        async with SessionLocal() as db:
            res = await db.execute(
                select(MediaItem).where(MediaItem.source_file_path == sf.drive_file.path)
            )
            existing = res.scalar_one_or_none()
        if existing is not None and existing.scrape_status in ("done", "no_scrape", "skipped"):
            return "skipped"

    # 刮削开关关闭 -> 只生成 strm, 不调 TMDB, 不写 movie.nfo, 不下载海报
    if not lib.scrape_enabled:
        return await _process_no_scrape(lib, sf, strm_plugin, target_root)

    info = identify(sf.drive_file.name)

    if info.media_type == "movie":
        return await _process_movie(lib, sf, info, meta_plugin, strm_plugin, target_root)

    if info.media_type in {"tv", "anime"}:
        return await _process_episode(
            lib, sf, info, meta_plugin, strm_plugin, target_root, tvshow_lock, tv_meta_cache
        )

    # 未知类型 → 跳过
    await _upsert(
        source_file_path=sf.drive_file.path, library_id=lib.id,
        title=info.title, year=info.year, media_type=info.media_type,
        source_file_size=sf.drive_file.size, scrape_status="skipped",
        scrape_error=f"unknown media_type {info.media_type}",
    )
    return "skipped"


async def _process_movie(lib, sf, info, meta_plugin, strm_plugin, target_root) -> str:
    meta = await scrape_movie(meta_plugin, info)
    if not meta:
        await _upsert(
            source_file_path=sf.drive_file.path, library_id=lib.id,
            title=info.title, year=info.year, media_type="movie",
            source_file_size=sf.drive_file.size, scrape_status="failed",
            scrape_error="no TMDB match",
        )
        return "failed"

    ctx = _make_strm_ctx(lib, sf.drive_file.path)
    artifacts = await generate_movie_strm(meta, target_root, strm_plugin, ctx)

    sub_paths = []
    if sf.sidecar_subtitles:
        sub_paths = [str(p) for p in copy_subtitles(
            list(sf.sidecar_subtitles), artifacts.out_dir,
            artifacts.strm_path.stem,
        )]

    await _upsert(
        source_file_path=sf.drive_file.path, library_id=lib.id,
        title=meta.title, original_title=meta.original_title,
        year=meta.year, tmdb_id=meta.source_id, media_type="movie",
        source_file_size=sf.drive_file.size,
        strm_path=str(artifacts.strm_path), nfo_path=str(artifacts.nfo_path),
        poster_path=str(artifacts.poster_path) if artifacts.poster_path else None,
        fanart_path=str(artifacts.fanart_path) if artifacts.fanart_path else None,
        subtitle_paths=sub_paths or None,
        scrape_status="done", scrape_error=None,
    )
    return "done"


async def _process_episode(lib, sf, info, meta_plugin, strm_plugin, target_root, tvshow_lock, tv_meta_cache) -> str:
    if info.season is None or info.episode is None:
        await _upsert(
            source_file_path=sf.drive_file.path, library_id=lib.id,
            title=info.title, year=info.year, media_type=info.media_type,
            source_file_size=sf.drive_file.size, scrape_status="skipped",
            scrape_error="missing season/episode",
        )
        return "skipped"

    # 取 tv 详情 (按 identified.title cache)
    cache_key = f"{info.title}:{info.year or ''}"
    tv_meta = tv_meta_cache.get(cache_key)
    if tv_meta is None:
        tv_meta = await scrape_tv(meta_plugin, info)
        if tv_meta is None:
            await _upsert(
                source_file_path=sf.drive_file.path, library_id=lib.id,
                title=info.title, year=info.year, media_type=info.media_type,
                season=info.season, episode=info.episode,
                source_file_size=sf.drive_file.size, scrape_status="failed",
                scrape_error="no TMDB tv match",
            )
            return "failed"
        tv_meta_cache[cache_key] = tv_meta

    # episode 详情
    ep_meta = await scrape_episode(meta_plugin, tv_meta, info.season, info.episode)
    if ep_meta is None:
        # episode 拿不到也继续，仅基础信息
        from fystrm.plugins.meta.base import MediaMeta
        ep_meta = MediaMeta(
            source="tmdb",
            source_id=f"{tv_meta.source_id}/{info.season}/{info.episode}",
            media_type="episode",
            title=f"S{info.season:02d}E{info.episode:02d}",
            parent_id=tv_meta.source_id,
            season_number=info.season,
            episode_number=info.episode,
        )

    ctx = _make_strm_ctx(lib, sf.drive_file.path)
    artifacts = await generate_episode_strm(
        tv_meta, ep_meta, target_root, strm_plugin, ctx,
        tvshow_lock_set=tvshow_lock,
    )

    sub_paths = []
    if sf.sidecar_subtitles:
        sub_paths = [str(p) for p in copy_subtitles(
            list(sf.sidecar_subtitles), artifacts.out_dir,
            artifacts.strm_path.stem,
        )]

    await _upsert(
        source_file_path=sf.drive_file.path, library_id=lib.id,
        title=tv_meta.title, original_title=tv_meta.original_title,
        year=tv_meta.year, tmdb_id=tv_meta.source_id, media_type=info.media_type,
        season=info.season, episode=info.episode,
        episode_title=ep_meta.episode_title or ep_meta.title,
        parent_tmdb_id=tv_meta.source_id,
        source_file_size=sf.drive_file.size,
        strm_path=str(artifacts.strm_path), nfo_path=str(artifacts.nfo_path),
        poster_path=str(artifacts.poster_path) if artifacts.poster_path else None,
        fanart_path=str(artifacts.fanart_path) if artifacts.fanart_path else None,
        subtitle_paths=sub_paths or None,
        scrape_status="done", scrape_error=None,
    )
    return "done"


async def _process_no_scrape(lib, sf, strm_plugin, target_root) -> str:
    """关闭刮削模式: 按源目录镜像生成 strm, 文件名跟随源 stem.

    target/<rel_dir>/<source_stem>.strm
    不调 TMDB, 不生 movie.nfo, 不下载 poster/fanart.
    源 nfo/jpg/png 通过 metadata_sync 已经镜像 (调 task 主流程那里).
    """
    from pathlib import PurePosixPath
    from fystrm.engines.strm import sanitize_dirname
    from fystrm.plugins.strm_path.base import StrmContext

    src = PurePosixPath(sf.drive_file.path)
    root = PurePosixPath(lib.source_path)
    try:
        rel = src.relative_to(root)
    except ValueError:
        rel = PurePosixPath(src.name)
    rel_dir = rel.parent
    stem = src.stem

    out_dir = Path(lib.target_strm_path) / str(rel_dir) if str(rel_dir) and str(rel_dir) != "." else Path(lib.target_strm_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    strm_path = out_dir / f"{stem}.strm"

    ctx = StrmContext(
        source_path=sf.drive_file.path,
        source_root=lib.source_path,
        cd2_mount_prefix=lib.cd2_mount_prefix or "",
        webdav_base_url=lib.webdav_base_url,
        webdav_path_prefix=lib.webdav_path_prefix,
    )
    strm_content = strm_plugin.render(ctx)
    strm_path.write_text(strm_content, encoding="utf-8")
    logger.info("no-scrape strm -> {}", strm_path)

    # MediaItem 仅记最小信息
    await _upsert(
        source_file_path=sf.drive_file.path, library_id=lib.id,
        title=stem,
        source_file_size=sf.drive_file.size,
        strm_path=str(strm_path),
        media_type="unknown",
        scrape_status="no_scrape", scrape_error=None,
    )
    return "no_scrape"


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


async def _update_stage(task_id: int, stage: str, message: str | None = None) -> None:
    """更新 ScanTask.stage + stage_message + WS 推 stage 事件."""
    async with SessionLocal() as db:
        t = await db.get(ScanTask, task_id)
        if t:
            t.stage = stage
            t.stage_message = message
            await db.commit()
    await publish(task_id, {"event": "stage", "stage": stage, "message": message})


def _now() -> datetime:
    return datetime.now(timezone.utc)
