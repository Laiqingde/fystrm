"""实时日志 API."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Query

from fystrm.core.log_stream import LOG_HISTORY_KEY
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



