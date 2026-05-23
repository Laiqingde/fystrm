"""运行时可改的配置 (DB key-value). 启动 seed .env 当前值.

哪些键属于运行时:
  TMDB_API_KEY, TMDB_LANGUAGE
  EMBY_URL, EMBY_API_KEY
  CD2_WEBHOOK_TOKEN, CD2_MOUNT_ROOT
  LOG_LEVEL

其他启动级配置 (DB/Redis/SECRET_KEY/JWT_*) 仍走 .env, 不动态.
"""

from __future__ import annotations

import asyncio
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from fystrm.config import settings as env_settings
from fystrm.db import SessionLocal
from fystrm.models.app_setting import AppSetting

# 在 DB 里维护的 key 白名单 -> .env 默认值
DYNAMIC_KEYS: dict[str, str] = {
    "TMDB_API_KEY": env_settings.tmdb_api_key,
    "TMDB_LANGUAGE": env_settings.tmdb_language,
    "EMBY_URL": env_settings.emby_url,
    "EMBY_API_KEY": env_settings.emby_api_key,
    "CD2_WEBHOOK_TOKEN": env_settings.cd2_webhook_token,
    "CD2_MOUNT_ROOT": env_settings.cd2_mount_root,
    "LOG_LEVEL": env_settings.log_level,
}

# secret 字段: API 输出时打码
SECRET_KEYS: set[str] = {"TMDB_API_KEY", "EMBY_API_KEY", "CD2_WEBHOOK_TOKEN"}

# 内存缓存 (启动加载, set 时刷新)
_cache: dict[str, str] = {}
_lock = asyncio.Lock()


async def seed_defaults() -> None:
    """启动时把 .env 当前值灌入 DB 缺失的 key. 已存在的不动."""
    async with SessionLocal() as db:
        for k, default in DYNAMIC_KEYS.items():
            stmt = pg_insert(AppSetting).values(key=k, value=default or "")
            stmt = stmt.on_conflict_do_nothing(index_elements=["key"])
            await db.execute(stmt)
        await db.commit()


async def load_all() -> None:
    """加载所有 DB 配置到内存缓存."""
    async with SessionLocal() as db:
        res = await db.execute(select(AppSetting))
        rows = res.scalars().all()
    async with _lock:
        _cache.clear()
        for r in rows:
            _cache[r.key] = r.value
        # .env fallback (DB 没有的 key 走 env)
        for k, v in DYNAMIC_KEYS.items():
            _cache.setdefault(k, v or "")
    logger.info("dynamic settings 加载 {} 项", len(_cache))


def get(key: str, default: str = "") -> str:
    """同步读取 (热路径). 必须在 load_all 之后调用."""
    return _cache.get(key, default)


async def set_value(key: str, value: str) -> None:
    """写入 DB + 刷新缓存. 只允许白名单 key."""
    if key not in DYNAMIC_KEYS:
        raise ValueError(f"key '{key}' not in DYNAMIC_KEYS whitelist")
    async with SessionLocal() as db:
        stmt = pg_insert(AppSetting).values(key=key, value=value)
        stmt = stmt.on_conflict_do_update(index_elements=["key"], set_={"value": stmt.excluded.value})
        await db.execute(stmt)
        await db.commit()
    async with _lock:
        _cache[key] = value
    logger.info("dynamic setting {}={}", key, "***" if key in SECRET_KEYS else value)


async def set_many(items: dict[str, str]) -> None:
    for k, v in items.items():
        await set_value(k, v)


def all_for_api(reveal_secrets: bool = False) -> dict[str, Any]:
    """API 输出格式: 含字段定义 + 是否 secret + 当前值 (secret 默认打码)."""
    out = {}
    for k in DYNAMIC_KEYS:
        v = _cache.get(k, "")
        is_secret = k in SECRET_KEYS
        out[k] = {
            "value": v if (reveal_secrets or not is_secret) else _mask(v),
            "is_secret": is_secret,
            "configured": bool(v),
        }
    return out


def _mask(v: str) -> str:
    if not v:
        return ""
    if len(v) <= 8:
        return "•" * len(v)
    return v[:4] + "•" * 6 + v[-4:]
