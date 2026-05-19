"""下载 TMDB poster + fanart 到本地。"""

from __future__ import annotations

from pathlib import Path

import httpx
from loguru import logger


async def download_image(url: str, dest: Path) -> bool:
    """下载图片到 dest。成功返回 True，失败 False（不抛异常）。"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
            return True
    except Exception as e:
        logger.warning("download image failed: {} -> {} : {}", url, dest, e)
        return False
