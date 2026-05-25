"""下载 TMDB poster + fanart + 集截图到本地. 带重试 + 已存在跳过."""

from __future__ import annotations

from pathlib import Path

import httpx
from loguru import logger
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

_TRANSIENT = (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, httpx.RemoteProtocolError, httpx.PoolTimeout)


@retry(
    retry=retry_if_exception_type(_TRANSIENT),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
async def _fetch(url: str) -> bytes:
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.content


async def download_image(url: str, dest: Path, *, skip_existing: bool = True) -> bool:
    """下载图片到 dest. 成功 True / 失败 False (不抛异常).

    skip_existing: dest 已存在且 size>0 直接跳过 (避免重复下载).
    瞬时网络错误自动重试 3 次 (指数退避 1-8s).
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    if skip_existing and dest.exists() and dest.stat().st_size > 0:
        return True
    try:
        content = await _fetch(url)
        dest.write_bytes(content)
        return True
    except Exception as e:
        # {e!r} 显示异常类型 (ConnectTimeout 等 str 为空)
        logger.warning("download image failed (重试 3 次后): {} -> {} : {!r}", url, dest, e)
        return False
