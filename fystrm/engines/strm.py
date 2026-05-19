"""strm + nfo + poster 输出。

布局:
  电影: {target_root}/{title} ({year})/{title}.strm + movie.nfo + poster + fanart
  剧集: {target_root}/{title} ({year})/                ← tvshow.nfo + poster + fanart 在根
                                  /Season 01/        ← 季海报 poster.jpg (可选)
                                            /{title} - S01E01.strm
                                            /{title} - S01E01.nfo
                                            /{title} - S01E01-thumb.jpg (still)
                                            /{title} - S01E01.zh.ass (字幕由 subtitle 引擎补)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger

from fystrm.engines.nfo import build_episode_nfo, build_movie_nfo, build_tvshow_nfo
from fystrm.engines.poster import download_image
from fystrm.plugins.meta.base import MediaMeta
from fystrm.plugins.strm_path.base import StrmContext, StrmPathPlugin


@dataclass(slots=True, frozen=True)
class StrmArtifacts:
    out_dir: Path
    strm_path: Path
    nfo_path: Path
    poster_path: Path | None = None
    fanart_path: Path | None = None
    still_path: Path | None = None
    season_dir: Path | None = None         # episode 模式
    tvshow_nfo_path: Path | None = None    # episode 模式


_INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize_dirname(name: str) -> str:
    name = _INVALID_CHARS.sub(" ", name)
    name = re.sub(r"\s+", " ", name).strip().rstrip(".")
    return name or "unknown"


def movie_root_dir(target_root: Path, meta: MediaMeta) -> Path:
    folder = sanitize_dirname(meta.title)
    if meta.year:
        folder = f"{folder} ({meta.year})"
    return target_root / folder


async def generate_movie_strm(
    meta: MediaMeta,
    target_root: Path,
    strm_path_plugin: StrmPathPlugin,
    strm_ctx: StrmContext,
    *,
    download_artwork: bool = True,
) -> StrmArtifacts:
    out_dir = movie_root_dir(target_root, meta)
    out_dir.mkdir(parents=True, exist_ok=True)
    base = sanitize_dirname(meta.title)

    strm_content = strm_path_plugin.render(strm_ctx)
    strm_path = out_dir / f"{base}.strm"
    strm_path.write_text(strm_content, encoding="utf-8")
    logger.info("movie strm -> {}", strm_path)

    nfo_path = out_dir / "movie.nfo"
    nfo_path.write_text(build_movie_nfo(meta), encoding="utf-8")

    poster_path = fanart_path = None
    if download_artwork:
        if meta.poster_url:
            t = out_dir / "poster.jpg"
            if await download_image(meta.poster_url, t):
                poster_path = t
        if meta.fanart_url:
            t = out_dir / "fanart.jpg"
            if await download_image(meta.fanart_url, t):
                fanart_path = t

    return StrmArtifacts(
        out_dir=out_dir, strm_path=strm_path, nfo_path=nfo_path,
        poster_path=poster_path, fanart_path=fanart_path,
    )


async def generate_episode_strm(
    tv_meta: MediaMeta,
    episode_meta: MediaMeta,
    target_root: Path,
    strm_path_plugin: StrmPathPlugin,
    strm_ctx: StrmContext,
    *,
    download_artwork: bool = True,
    tvshow_lock_set: set | None = None,
) -> StrmArtifacts:
    """生成单集 strm + episode nfo + 集截图，并按需写 tvshow.nfo / 剧集根海报。

    tvshow_lock_set: set of tmdb_id; 同一 set 内只在第一次见到时写 tvshow.nfo。
                     一个 ScanTask 共用一个 set。
    """
    show_dir = movie_root_dir(target_root, tv_meta)  # 复用同样的 {title} ({year}) 布局
    show_dir.mkdir(parents=True, exist_ok=True)

    season = episode_meta.season_number or 0
    episode = episode_meta.episode_number or 0
    season_dir = show_dir / f"Season {season:02d}"
    season_dir.mkdir(parents=True, exist_ok=True)

    show_base = sanitize_dirname(tv_meta.title)
    ep_base = f"{show_base} - S{season:02d}E{episode:02d}"

    # strm
    strm_content = strm_path_plugin.render(strm_ctx)
    strm_path = season_dir / f"{ep_base}.strm"
    strm_path.write_text(strm_content, encoding="utf-8")
    logger.info("episode strm -> {}", strm_path)

    # nfo
    nfo_path = season_dir / f"{ep_base}.nfo"
    nfo_path.write_text(build_episode_nfo(episode_meta, parent_meta=tv_meta), encoding="utf-8")

    still_path = None
    if download_artwork and episode_meta.still_url:
        t = season_dir / f"{ep_base}-thumb.jpg"
        if await download_image(episode_meta.still_url, t):
            still_path = t

    # 一次性写 tvshow.nfo + 剧集根海报（仅第一次见到该剧时）
    tvshow_nfo_path = None
    if tvshow_lock_set is None or tv_meta.source_id not in tvshow_lock_set:
        tvshow_nfo_path = show_dir / "tvshow.nfo"
        tvshow_nfo_path.write_text(build_tvshow_nfo(tv_meta), encoding="utf-8")
        if download_artwork:
            if tv_meta.poster_url:
                await download_image(tv_meta.poster_url, show_dir / "poster.jpg")
            if tv_meta.fanart_url:
                await download_image(tv_meta.fanart_url, show_dir / "fanart.jpg")
        if tvshow_lock_set is not None:
            tvshow_lock_set.add(tv_meta.source_id)

    return StrmArtifacts(
        out_dir=season_dir, strm_path=strm_path, nfo_path=nfo_path,
        still_path=still_path, season_dir=season_dir,
        tvshow_nfo_path=tvshow_nfo_path,
        poster_path=(show_dir / "poster.jpg") if (show_dir / "poster.jpg").exists() else None,
        fanart_path=(show_dir / "fanart.jpg") if (show_dir / "fanart.jpg").exists() else None,
    )
