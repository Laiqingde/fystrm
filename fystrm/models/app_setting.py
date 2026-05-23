from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from fystrm.db import Base
from fystrm.models.base import TimestampMixin


class AppSetting(Base, TimestampMixin):
    """运行时配置 (web UI 可改). 启动时 seed .env 当前值."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False, default="")
