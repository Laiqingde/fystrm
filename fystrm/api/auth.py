"""认证 API: login / me."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fystrm.core.auth import create_token, decode_token, verify_password
from fystrm.db import get_session
from fystrm.models.user import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_session)) -> LoginResponse:
    res = await db.execute(select(User).where(User.username == req.username))
    user = res.scalar_one_or_none()
    if user is None or not user.enabled:
        raise HTTPException(401, "用户名或密码错误")
    if not verify_password(req.password, user.password_hash):
        raise HTTPException(401, "用户名或密码错误")
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    token = create_token(subject=user.username, extra={"uid": user.id, "is_admin": user.is_admin})
    return LoginResponse(
        access_token=token,
        user={"id": user.id, "username": user.username, "is_admin": user.is_admin},
    )


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_session),
) -> User:
    if not authorization:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "缺少 Authorization")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authorization 格式错误 (应 Bearer <token>)")
    payload = decode_token(token.strip())
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token 无效或过期")
    username = payload.get("sub")
    if not username:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token 缺少 sub")
    res = await db.execute(select(User).where(User.username == username))
    user = res.scalar_one_or_none()
    if user is None or not user.enabled:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户不存在或已禁用")
    return user


@router.get("/me")
async def me(user: User = Depends(get_current_user)) -> dict:
    return {
        "id": user.id, "username": user.username, "is_admin": user.is_admin,
        "last_login_at": user.last_login_at,
    }
