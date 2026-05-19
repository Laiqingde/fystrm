"""刮削编排：识别结果 → MetaPlugin 找匹配。

v0.1 movie, v0.2 加 tv + episode 编排.
"""

from __future__ import annotations

from loguru import logger

from fystrm.engines.identifier import IdentifyResult
from fystrm.plugins.meta.base import MediaMeta, MetaPlugin


async def scrape_movie(meta_plugin: MetaPlugin, identified: IdentifyResult) -> MediaMeta | None:
    if identified.year:
        results = await meta_plugin.search(identified.title, year=identified.year, media_type="movie")
        if results:
            return await meta_plugin.fetch(results[0].source_id, media_type="movie")

    results = await meta_plugin.search(identified.title, media_type="movie")
    if results:
        target = results[0]
        if identified.year:
            matched = [r for r in results if r.year and abs(r.year - identified.year) <= 1]
            target = matched[0] if matched else results[0]
        return await meta_plugin.fetch(target.source_id, media_type="movie")

    logger.info("No TMDB movie match for {!r} ({})", identified.title, identified.year)
    return None


async def scrape_tv(meta_plugin: MetaPlugin, identified: IdentifyResult) -> MediaMeta | None:
    """搜剧集 + 拿到 tv 详情. 不查 episode."""
    if identified.year:
        results = await meta_plugin.search(identified.title, year=identified.year, media_type="tv")
        if results:
            return await meta_plugin.fetch(results[0].source_id, media_type="tv")

    results = await meta_plugin.search(identified.title, media_type="tv")
    if results:
        return await meta_plugin.fetch(results[0].source_id, media_type="tv")

    logger.info("No TMDB tv match for {!r}", identified.title)
    return None


async def scrape_episode(
    meta_plugin: MetaPlugin, tv_meta: MediaMeta, season: int, episode: int
) -> MediaMeta | None:
    """单集详情."""
    try:
        return await meta_plugin.fetch_episode(tv_meta.source_id, season, episode)
    except LookupError as e:
        logger.warning("episode lookup failed: {}", e)
        return None
