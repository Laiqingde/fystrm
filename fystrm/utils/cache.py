"""轻量 Redis JSON 缓存（直接用 redis-py async）。"""

from __future__ import annotations

import json
from typing import Any

import redis.asyncio as redis_async

from fystrm.config import settings

_pool: redis_async.ConnectionPool | None = None


def _get_pool() -> redis_async.ConnectionPool:
    global _pool
    if _pool is None:
        _pool = redis_async.ConnectionPool.from_url(settings.redis_url, decode_responses=True)
    return _pool


def get_redis() -> redis_async.Redis:
    return redis_async.Redis(connection_pool=_get_pool())


async def cache_get(key: str) -> Any | None:
    r = get_redis()
    raw = await r.get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


async def cache_set(key: str, value: Any, ttl: int = 7 * 86400) -> None:
    r = get_redis()
    await r.setex(key, ttl, json.dumps(value, ensure_ascii=False))
