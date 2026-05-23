"""WebSocket 端点 (token 走 query string, 不挂 router-level Depends)."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket
from loguru import logger

from fystrm.core.auth import decode_token
from fystrm.core.log_stream import LOG_CHANNEL
from fystrm.core.ws_hub import hub
from fystrm.utils.cache import get_redis

router = APIRouter()


def _check_token(token: str) -> bool:
    return bool(token) and decode_token(token) is not None


@router.websocket("/ws/tasks/{task_id}")
async def ws_task(ws: WebSocket, task_id: int, token: str = "") -> None:
    if not _check_token(token):
        await ws.close(code=4401, reason="unauthorized")
        return
    await hub.serve(ws, task_id)


@router.websocket("/ws/logs")
async def ws_logs(ws: WebSocket, token: str = "") -> None:
    if not _check_token(token):
        await ws.close(code=4401, reason="unauthorized")
        return
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
