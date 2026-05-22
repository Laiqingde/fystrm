"""密码哈希 (bcrypt) + JWT 签发/校验."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from fystrm.config import settings

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_ctx.verify(plain, hashed)
    except Exception:
        return False


def _secret() -> str:
    return settings.jwt_secret or settings.secret_key


def create_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours)
    payload: dict[str, Any] = {"sub": subject, "exp": exp}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, _secret(), algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, _secret(), algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
