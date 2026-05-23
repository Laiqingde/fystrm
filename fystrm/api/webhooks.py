"""CD2 webhook 接收端。

CD2 配置中 base_url=http://<fystrm>:8095, file_system_watcher.url
指向 /api/webhooks/cd2/file, mount_point_watcher.url 指向 /api/webhooks/cd2/mount。
"""

from __future__ import annotations

import secrets
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from loguru import logger
from pydantic import BaseModel

from fystrm.config import settings
from fystrm.core import dynamic_settings
from fystrm.core.queue import get_arq_pool

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


def verify_token(authorization: str | None = Header(default=None)) -> None:
    """校验 Bearer token == settings.cd2_webhook_token. 没配 token 则拒绝全部。"""
    expected = dynamic_settings.get("CD2_WEBHOOK_TOKEN") or settings.cd2_webhook_token
    if not expected:
        raise HTTPException(503, "CD2_WEBHOOK_TOKEN not configured")
    if not authorization:
        raise HTTPException(401, "missing Authorization header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        raise HTTPException(401, "expected Bearer scheme")
    if not secrets.compare_digest(token.strip(), expected):
        raise HTTPException(403, "invalid token")


class FileEvent(BaseModel):
    """单条文件变更事件（CD2 data[] 数组里的一项）。"""
    action: str          # create / delete / rename
    is_dir: str | bool   # CD2 发的是字符串 "true"/"false"
    source_file: str
    destination_file: str = ""


class CD2FileWebhook(BaseModel):
    device_name: str | None = None
    user_name: str | None = None
    version: str | None = None
    event_category: str | None = None
    event_name: str | None = None
    event_time: str | None = None
    send_time: str | None = None
    data: list[FileEvent] = []


class MountEvent(BaseModel):
    action: str           # mount / unmount
    mount_point: str
    status: str | bool
    reason: str = ""


class CD2MountWebhook(BaseModel):
    device_name: str | None = None
    user_name: str | None = None
    version: str | None = None
    event_category: str | None = None
    event_name: str | None = None
    event_time: str | None = None
    send_time: str | None = None
    data: list[MountEvent] = []


@router.post("/cd2/file", dependencies=[Depends(verify_token)])
async def cd2_file(payload: CD2FileWebhook, request: Request) -> dict[str, Any]:
    """接收 CD2 文件变更, 入队 handle_file_event."""
    logger.info(
        "CD2 file webhook from {} device={} user={} events={}",
        request.client.host if request.client else "-",
        payload.device_name, payload.user_name, len(payload.data),
    )
    pool = await get_arq_pool()
    queued = 0
    for ev in payload.data:
        # is_dir 字段 CD2 给的是字符串，归一化
        is_dir = _truthy(ev.is_dir)
        if is_dir:
            # 目录变更暂时忽略（v0.3 后再扩展，避免误删一整批 MediaItem）
            logger.debug("skip dir event {} on {}", ev.action, ev.source_file)
            continue
        await pool.enqueue_job(
            "handle_file_event",
            action=ev.action,
            source_file=ev.source_file,
            destination_file=ev.destination_file or None,
        )
        queued += 1
    return {"accepted": len(payload.data), "queued": queued}


@router.post("/cd2/mount", dependencies=[Depends(verify_token)])
async def cd2_mount(payload: CD2MountWebhook, request: Request) -> dict[str, Any]:
    """接收 CD2 挂载点变更, v0.3 简单记日志."""
    for ev in payload.data:
        ok = _truthy(ev.status)
        if ok:
            logger.info("CD2 mount event {} on {} OK", ev.action, ev.mount_point)
        else:
            logger.warning("CD2 mount event {} on {} FAILED: {}", ev.action, ev.mount_point, ev.reason)
    return {"accepted": len(payload.data)}


def _truthy(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in {"true", "1", "yes"}
    return bool(v)
