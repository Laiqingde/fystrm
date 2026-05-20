"""把 loguru 日志写到 Redis (pub/sub + LIST), 供 UI 实时展示."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import redis as redis_sync
from loguru import logger

from fystrm.config import settings

LOG_CHANNEL = "fystrm:logs"
LOG_HISTORY_KEY = "fystrm:log:history"
LOG_HISTORY_MAX = 500

_redis_client: redis_sync.Redis | None = None


def _redis() -> redis_sync.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis_sync.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=True,
        )
    return _redis_client


def _categorize(module: str) -> str:
    """按 module 路径自动归类 (去掉 fystrm. 前缀避免 "strm" 误命中所有模块)."""
    m = module.lower().replace("fystrm.", "")
    if "webhook" in m:
        return "webhook"
    if "metadata_sync" in m or "subtitle" in m or "poster" in m:
        return "metadata"
    if "scraper" in m or "tmdb" in m or "engines.meta" in m or "plugins.meta" in m:
        return "scrape"
    if "emby" in m:
        return "emby"
    if "engines.strm" in m or "engines.nfo" in m:
        return "strm"
    if "scan" in m or "task" in m:
        return "scan"
    return "general"


def redis_sink(message: Any) -> None:
    """Loguru sink: 把日志 publish + 追加 LIST."""
    try:
        rec = message.record
        payload = {
            "ts": datetime.fromtimestamp(rec["time"].timestamp(), tz=timezone.utc).isoformat(),
            "level": rec["level"].name,
            "module": rec["name"],
            "function": rec["function"],
            "line": rec["line"],
            "msg": rec["message"],
            "category": _categorize(rec["name"]),
        }
        line = json.dumps(payload, ensure_ascii=False)
        r = _redis()
        # 用 pipeline 减少往返
        pipe = r.pipeline(transaction=False)
        pipe.publish(LOG_CHANNEL, line)
        pipe.lpush(LOG_HISTORY_KEY, line)
        pipe.ltrim(LOG_HISTORY_KEY, 0, LOG_HISTORY_MAX - 1)
        pipe.execute()
    except Exception:
        # 不要让日志失败影响主流程
        pass


def setup_log_stream() -> None:
    """注册 sink (在 setup_logging 之后调用)."""
    logger.add(redis_sink, level="INFO", format="{message}")
