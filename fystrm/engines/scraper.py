"""刮削引擎：根据识别结果调 MetaPlugin 找匹配。

策略:
1. 先按 (title, year) 搜索
2. 没结果就退一步按 title 搜
3. 取第一个匹配作为最终结果（v0.1 简化策略，未来加打分匹配）
"""

from __future__ import annotations

from loguru import logger

from fystrm.engines.identifier import IdentifyResult
from fystrm.plugins.meta.base import MediaMeta, MetaPlugin


async def scrape_movie(meta_plugin: MetaPlugin, identified: IdentifyResult) -> MediaMeta | None:
    """根据识别结果刮削元数据。"""
    # 第一轮：带 year
    if identified.year:
        results = await meta_plugin.search(identified.title, year=identified.year, media_type="movie")
        if results:
            return await meta_plugin.fetch(results[0].source_id, media_type="movie")

    # 第二轮：去掉 year
    results = await meta_plugin.search(identified.title, media_type="movie")
    if results:
        if identified.year:
            # 用 year ±1 容差挑最近的
            matched = [r for r in results if r.year and abs(r.year - identified.year) <= 1]
            target = matched[0] if matched else results[0]
        else:
            target = results[0]
        return await meta_plugin.fetch(target.source_id, media_type="movie")

    logger.info("No TMDB match for {!r} ({})", identified.title, identified.year)
    return None
