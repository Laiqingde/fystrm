"""扫描任务进度的 WebSocket 推送 hub。

每个 task_id 维护一个 websocket 订阅集合。
arq worker 通过 Redis pub/sub 通道发布进度，FastAPI app 这边订阅并推到 ws。
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import WebSocket
from loguru import logger

from fystrm.utils.cache import get_redis

CHANNEL_PREFIX = "fystrm:task:"


def channel_for(task_id: int) -> str:
    return f"{CHANNEL_PREFIX}{task_id}"


async def publish(task_id: int, payload: dict[str, Any]) -> None:
    r = get_redis()
    await r.publish(channel_for(task_id), json.dumps(payload, ensure_ascii=False, default=str))


class WSHub:
    """连接 WebSocket <-> Redis pubsub。每个 ws 连接 spawn 一个 subscriber 协程。"""

    async def serve(self, ws: WebSocket, task_id: int) -> None:
        await ws.accept()
        r = get_redis()
        pubsub = r.pubsub()
        await pubsub.subscribe(channel_for(task_id))
        try:
            async for msg in pubsub.listen():
                if msg["type"] != "message":
                    continue
                data = msg["data"]
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                try:
                    await ws.send_text(data)
                except Exception as e:
                    logger.debug("ws send failed: {}", e)
                    break
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning("ws hub error for task {}: {}", task_id, e)
        finally:
            try:
                await pubsub.unsubscribe(channel_for(task_id))
                await pubsub.close()
            except Exception:
                pass


hub = WSHub()
