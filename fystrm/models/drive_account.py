from __future__ import annotations

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from fystrm.db import Base
from fystrm.models.base import TimestampMixin


class DriveAccount(Base, TimestampMixin):
    """网盘账号凭证（v0.1 表先建，预留 v0.2+ 转存功能用）。"""

    __tablename__ = "drive_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    drive_type: Mapped[str] = mapped_column(String(32), nullable=False)  # local/pan123/pan115/baidu/onedrive/gdrive
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    credentials_enc: Mapped[str | None] = mapped_column(String(2048), nullable=True)  # 加密后的凭证 JSON
    extra: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    token_expires_at: Mapped["DateTime | None"] = mapped_column(DateTime(timezone=True), nullable=True)
