"""CD2 webhook 事件处理 task.

处理三种 action:
- create: 找匹配 library + 增量入库一个文件
- delete: 删 MediaItem + 清理 strm/nfo/poster/字幕/集截图 + 删空目录
- rename: source_file 改为 destination_file, 重写 strm 内容
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger
from sqlalchemy import select

from fystrm.db import SessionLocal
from fystrm.engines.identifier import identify
from fystrm.engines.scanner import VIDEO_EXTENSIONS, is_video
from fystrm.engines.scraper import scrape_episode, scrape_movie, scrape_tv
from fystrm.engines.strm import generate_episode_strm, generate_movie_strm
from fystrm.engines.subtitle import copy_subtitles, find_subtitles
from fystrm.models.library import Library
from fystrm.models.media import MediaItem
from fystrm.plugins.drives.local import LocalDrivePlugin
from fystrm.plugins.drives.base import DriveFile
from fystrm.plugins.meta.tmdb import TMDBPlugin
from fystrm.plugins.strm_path.base import StrmContext, StrmPathPlugin
from fystrm.plugins.strm_path.cd2_local import CD2LocalStrmPathPlugin
from fystrm.plugins.strm_path.webdav import WebDAVStrmPathPlugin


def _normalize_cd2_path(path: str) -> str:
    """把 CD2 推过来的网盘相对路径转换成 fystrm 容器内的 FUSE 挂载路径.

    CD2 通常推: /WebDAV/me/media/电影/华语电影/foo.mkv  (网盘根下)
    fystrm 看: /mnt/CloudNAS/WebDAV/me/media/电影/华语电影/foo.mkv

    转换规则: 如果 path 不以 cd2_mount_root 开头, 自动拼接前缀.
    """
    from fystrm.config import settings
    from fystrm.core import dynamic_settings
    root = (settings.cd2_mount_root or "").rstrip("/")
    if not root or not path:
        return path
    if path.startswith(root + "/") or path == root:
        return path
    if not path.startswith("/"):
        path = "/" + path
    return root + path


async def handle_file_event(
    ctx: dict, *, action: str, source_file: str, destination_file: str | None = None
) -> dict[str, Any]:
    """webhook 入队任务."""
    # 路径映射: CD2 给的网盘相对路径 -> fystrm 容器内的 FUSE 挂载路径
    src_orig = source_file
    source_file = _normalize_cd2_path(source_file)
    if destination_file:
        destination_file = _normalize_cd2_path(destination_file)
    if src_orig != source_file:
        logger.info("path mapped: {!r} -> {!r}", src_orig, source_file)
    logger.info("file webhook action={} src={!r} dst={!r}", action, source_file, destination_file)

    if action == "create":
        return await _handle_create(source_file)
    if action == "delete":
        return await _handle_delete(source_file)
    if action == "rename":
        return await _handle_rename(source_file, destination_file)

    logger.warning("unknown webhook action: {}", action)
    return {"status": "ignored", "reason": f"unknown action {action}"}


# ---------- create ----------

async def _handle_create(source_file: str) -> dict[str, Any]:
    if not is_video(source_file):
        return {"status": "skipped", "reason": "not a video extension"}

    src = Path(source_file)
    if not src.exists():
        # CD2 推过来时文件可能还没完全同步, 等等再说
        logger.warning("create event but file not yet present: {}", source_file)
        return {"status": "deferred", "reason": "file not yet present"}

    lib = await _find_library_for(source_file)
    if lib is None:
        return {"status": "skipped", "reason": "no matching library"}

    # 用同一份 process_one 逻辑（从 scan task 抽出）
    meta_plugin = TMDBPlugin()
    strm_plugin = _make_strm_plugin(lib)
    target_root = Path(lib.target_strm_path)
    target_root.mkdir(parents=True, exist_ok=True)

    drive = LocalDrivePlugin()
    df = await drive.get_info(source_file)
    info = identify(src.name)
    subs = find_subtitles(src)

    if info.media_type == "movie":
        outcome = await _process_one_movie(lib, df, info, subs, meta_plugin, strm_plugin, target_root)
    elif info.media_type in {"tv", "anime"}:
        outcome = await _process_one_episode(lib, df, info, subs, meta_plugin, strm_plugin, target_root)
    else:
        outcome = "skipped"
    return {"status": outcome, "source_file": source_file}


# ---------- delete ----------

async def _handle_delete(source_file: str) -> dict[str, Any]:
    async with SessionLocal() as db:
        res = await db.execute(
            select(MediaItem).where(MediaItem.source_file_path == source_file)
        )
        item = res.scalar_one_or_none()
        if item is None:
            return {"status": "skipped", "reason": "no MediaItem for source"}
        artifacts_removed = _remove_artifacts(item)
        await db.delete(item)
        await db.commit()
    return {"status": "deleted", "artifacts_removed": artifacts_removed}


def _remove_artifacts(item: MediaItem) -> list[str]:
    removed: list[str] = []
    for attr in ("strm_path", "nfo_path", "poster_path", "fanart_path"):
        p = getattr(item, attr, None)
        if p:
            _try_unlink(Path(p), removed)
    if item.subtitle_paths:
        for p in item.subtitle_paths:
            _try_unlink(Path(p), removed)
    # 集截图 (按惯例命名)
    if item.strm_path:
        thumb = Path(item.strm_path).with_name(Path(item.strm_path).stem + "-thumb.jpg")
        _try_unlink(thumb, removed)
        # 尝试清理空 season 目录
        season_dir = Path(item.strm_path).parent
        _try_rmdir(season_dir, removed)
        # 再清空 tvshow 根 (仅当无 episode 子目录)
        if item.media_type in {"tv", "anime"}:
            _try_rmdir(season_dir.parent, removed)
    return removed


def _try_unlink(path: Path, removed: list[str]) -> None:
    try:
        if path.exists():
            path.unlink()
            removed.append(str(path))
            logger.info("removed {}", path)
    except Exception as e:
        logger.warning("unlink failed {}: {}", path, e)


def _try_rmdir(path: Path, removed: list[str]) -> None:
    try:
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()
            removed.append(str(path))
            logger.info("removed empty dir {}", path)
    except Exception as e:
        logger.debug("rmdir skip {}: {}", path, e)


# ---------- rename ----------

async def _handle_rename(source_file: str, destination_file: str | None) -> dict[str, Any]:
    if not destination_file:
        return {"status": "skipped", "reason": "no destination_file"}

    async with SessionLocal() as db:
        res = await db.execute(
            select(MediaItem).where(MediaItem.source_file_path == source_file)
        )
        item = res.scalar_one_or_none()

        if item is None:
            # 旧路径不在库里 -> 当 create 处理新路径
            logger.info("rename src not in DB, treating as create on dst: {}", destination_file)
            return await _handle_create(destination_file)

        # 更新 source_file_path
        item.source_file_path = destination_file
        # 更新 strm 文件内容 (路径会因为 source 变化而变)
        lib = await db.get(Library, item.library_id)
        if lib and item.strm_path:
            strm_plugin = _make_strm_plugin(lib)
            try:
                ctx = StrmContext(
                    source_path=destination_file,
                    source_root=lib.source_path,
                    cd2_mount_prefix=lib.cd2_mount_prefix or "",
                    webdav_base_url=lib.webdav_base_url,
                    webdav_path_prefix=lib.webdav_path_prefix,
                )
                new_content = strm_plugin.render(ctx)
                Path(item.strm_path).write_text(new_content, encoding="utf-8")
                logger.info("rewrote strm {} -> {}", item.strm_path, new_content)
            except Exception as e:
                logger.warning("rewrite strm failed: {}", e)
        await db.commit()
    return {"status": "renamed", "old": source_file, "new": destination_file}


# ---------- helpers ----------

async def _find_library_for(path: str) -> Library | None:
    """找路径所属的 library (longest source_path prefix match)."""
    async with SessionLocal() as db:
        res = await db.execute(select(Library).where(Library.enabled == True))
        candidates = [
            lib for lib in res.scalars().all()
            if path.startswith(lib.source_path.rstrip("/") + "/") or path == lib.source_path
        ]
        if not candidates:
            return None
        # 最长前缀优先
        return max(candidates, key=lambda l: len(l.source_path))


def _make_strm_plugin(lib: Library) -> StrmPathPlugin:
    if lib.strm_mode == "webdav":
        return WebDAVStrmPathPlugin()
    return CD2LocalStrmPathPlugin()


def _make_ctx(lib: Library, source_path: str) -> StrmContext:
    return StrmContext(
        source_path=source_path,
        source_root=lib.source_path,
        cd2_mount_prefix=lib.cd2_mount_prefix or "",
        webdav_base_url=lib.webdav_base_url,
        webdav_path_prefix=lib.webdav_path_prefix,
    )


# ---------- 单文件处理 (复用 scan task 思路, 但不依赖 ScanTask) ----------

async def _process_one_movie(lib, df: DriveFile, info, subs, meta_plugin, strm_plugin, target_root) -> str:
    meta = await scrape_movie(meta_plugin, info)
    if not meta:
        await _upsert(
            source_file_path=df.path, library_id=lib.id,
            title=info.title, year=info.year, media_type="movie",
            source_file_size=df.size, scrape_status="failed",
            scrape_error="no TMDB match (webhook)",
        )
        return "failed"
    ctx = _make_ctx(lib, df.path)
    artifacts = await generate_movie_strm(meta, target_root, strm_plugin, ctx)
    sub_paths = [str(p) for p in copy_subtitles(list(subs), artifacts.out_dir, artifacts.strm_path.stem)] if subs else []
    await _upsert(
        source_file_path=df.path, library_id=lib.id,
        title=meta.title, original_title=meta.original_title,
        year=meta.year, tmdb_id=meta.source_id, media_type="movie",
        source_file_size=df.size,
        strm_path=str(artifacts.strm_path), nfo_path=str(artifacts.nfo_path),
        poster_path=str(artifacts.poster_path) if artifacts.poster_path else None,
        fanart_path=str(artifacts.fanart_path) if artifacts.fanart_path else None,
        subtitle_paths=sub_paths or None,
        scrape_status="done", scrape_error=None,
    )
    return "done"


async def _process_one_episode(lib, df: DriveFile, info, subs, meta_plugin, strm_plugin, target_root) -> str:
    if info.season is None or info.episode is None:
        return "skipped"
    tv_meta = await scrape_tv(meta_plugin, info)
    if tv_meta is None:
        return "failed"
    ep_meta = await scrape_episode(meta_plugin, tv_meta, info.season, info.episode)
    if ep_meta is None:
        from fystrm.plugins.meta.base import MediaMeta
        ep_meta = MediaMeta(
            source="tmdb",
            source_id=f"{tv_meta.source_id}/{info.season}/{info.episode}",
            media_type="episode", title=f"S{info.season:02d}E{info.episode:02d}",
            parent_id=tv_meta.source_id, season_number=info.season, episode_number=info.episode,
        )
    ctx = _make_ctx(lib, df.path)
    artifacts = await generate_episode_strm(
        tv_meta, ep_meta, target_root, strm_plugin, ctx,
        tvshow_lock_set=None,  # webhook 单次, 总是写 tvshow.nfo (idempotent overwrite OK)
    )
    sub_paths = [str(p) for p in copy_subtitles(list(subs), artifacts.out_dir, artifacts.strm_path.stem)] if subs else []
    await _upsert(
        source_file_path=df.path, library_id=lib.id,
        title=tv_meta.title, original_title=tv_meta.original_title,
        year=tv_meta.year, tmdb_id=tv_meta.source_id, media_type=info.media_type,
        season=info.season, episode=info.episode,
        episode_title=ep_meta.episode_title or ep_meta.title,
        parent_tmdb_id=tv_meta.source_id,
        source_file_size=df.size,
        strm_path=str(artifacts.strm_path), nfo_path=str(artifacts.nfo_path),
        poster_path=str(artifacts.poster_path) if artifacts.poster_path else None,
        fanart_path=str(artifacts.fanart_path) if artifacts.fanart_path else None,
        subtitle_paths=sub_paths or None,
        scrape_status="done", scrape_error=None,
    )
    return "done"


async def _upsert(*, source_file_path: str, **fields) -> None:
    async with SessionLocal() as db:
        res = await db.execute(
            select(MediaItem).where(MediaItem.source_file_path == source_file_path)
        )
        item = res.scalar_one_or_none()
        if item is None:
            db.add(MediaItem(source_file_path=source_file_path, **fields))
        else:
            for k, v in fields.items():
                setattr(item, k, v)
        await db.commit()
