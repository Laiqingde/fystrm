"""启动时若 users 表为空, 自动创建 admin (密码从 .env 或随机生成)."""

from __future__ import annotations

import secrets

from loguru import logger
from sqlalchemy import select

from fystrm.config import settings
from fystrm.core.auth import hash_password
from fystrm.db import SessionLocal
from fystrm.models.user import User


async def ensure_admin() -> None:
    async with SessionLocal() as db:
        res = await db.execute(select(User).where(User.username == settings.admin_username))
        existing = res.scalar_one_or_none()
        if existing is not None:
            return

        pwd = settings.admin_password.strip()
        random_generated = False
        if not pwd:
            pwd = secrets.token_urlsafe(12)
            random_generated = True

        admin = User(
            username=settings.admin_username,
            password_hash=hash_password(pwd),
            is_admin=True,
            enabled=True,
        )
        db.add(admin)
        await db.commit()

        if random_generated:
            # 把临时密码大字打到日志 (用户首次登录后该自己改 .env)
            border = "=" * 60
            logger.warning("\n{}\n  ⚠️ 已生成 admin 默认密码 (请妥善记录):\n  username: {}\n  password: {}\n{}",
                           border, settings.admin_username, pwd, border)
        else:
            logger.info("admin 用户创建 ({})", settings.admin_username)
