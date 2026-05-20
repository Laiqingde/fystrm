"""实时日志 API."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, Query, WebSocket
from loguru import logger

from fystrm.core.log_stream import LOG_CHANNEL, LOG_HISTORY_KEY
from fystrm.utils.cache import get_redis

router = APIRouter(tags=["logs"])


@router.get("/api/logs/recent")
async def recent_logs(limit: int = Query(200, ge=1, le=500)) -> list[dict]:
    """拿历史日志 (按时间倒序, 最新在前)."""
    r = get_redis()
    raw = await r.lrange(LOG_HISTORY_KEY, 0, limit - 1)
    out = []
    for line in raw:
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    return out


@router.websocket("/ws/logs")
async def ws_logs(ws: WebSocket) -> None:
    """订阅实时日志 (pub/sub)."""
    await ws.accept()
    r = get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe(LOG_CHANNEL)
    try:
        async for msg in pubsub.listen():
            if msg["type"] != "message":
                continue
            data = msg["data"]
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            try:
                await ws.send_text(data)
            except Exception:
                break
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.debug("ws logs error: {}", e)
    finally:
        try:
            await pubsub.unsubscribe(LOG_CHANNEL)
            await pubsub.close()
        except Exception:
            pass
