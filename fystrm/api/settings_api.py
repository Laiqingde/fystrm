"""动态配置 API + 修改密码."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from fystrm.api.auth import get_current_user
from fystrm.config import settings as env_settings
from fystrm.core import dynamic_settings
from fystrm.core.auth import hash_password, verify_password
from fystrm.db import get_session
from fystrm.models.user import User

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/")
async def get_settings(reveal: bool = False) -> dict:
    """所有动态配置 (默认 secret 字段打码; ?reveal=true 显示明文)."""
    return {
        "fields": dynamic_settings.all_for_api(reveal_secrets=reveal),
        "static": {
            "tmdb_language_default": "zh-CN",
            "log_level_default": "INFO",
            "host": env_settings.host,
            "port": env_settings.port,
        },
    }


class UpdateSettingsRequest(BaseModel):
    values: dict[str, str] = Field(default_factory=dict)


@router.put("/")
async def update_settings(req: UpdateSettingsRequest) -> dict:
    """批量更新配置 (web UI 保存按钮调). 未在白名单的 key 会报 400."""
    try:
        await dynamic_settings.set_many(req.values)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True, "updated": list(req.values.keys())}


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6, max_length=128)


@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_session),
) -> dict:
    if not verify_password(req.old_password, user.password_hash):
        raise HTTPException(400, "原密码错误")
    user.password_hash = hash_password(req.new_password)
    await db.commit()
    return {"ok": True}
