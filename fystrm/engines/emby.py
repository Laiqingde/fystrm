"""Emby Library Refresh 触发。"""

from __future__ import annotations

import httpx
from loguru import logger

from fystrm.config import settings
from fystrm.core import dynamic_settings


async def refresh_library() -> bool:
    """触发 Emby 全库扫描刷新。

    返回 True = 调用成功；False = 未配置或失败。
    """
    emby_url = dynamic_settings.get("EMBY_URL") or settings.emby_url
    emby_api_key = dynamic_settings.get("EMBY_API_KEY") or settings.emby_api_key
    if not emby_url or not emby_api_key:
        logger.info("Emby 未配置, skip refresh")
        return False
    url = emby_url.rstrip("/") + "/Library/Refresh"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                url,
                headers={"X-Emby-Token": emby_api_key},
            )
            r.raise_for_status()
            logger.info("Emby /Library/Refresh -> {}", r.status_code)
            return True
    except Exception as e:
        logger.warning("Emby refresh failed: {}", e)
        return False
