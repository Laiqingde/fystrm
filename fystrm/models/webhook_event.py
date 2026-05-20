from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from fystrm.db import Base
from fystrm.models.base import TimestampMixin


class WebhookEvent(Base, TimestampMixin):
    """CD2 webhook 收到的每个事件 (file create/delete/rename) 处理记录."""

    __tablename__ = "webhook_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    action: Mapped[str] = mapped_column(String(16), nullable=False)   # create/delete/rename
    source_file: Mapped[str] = mapped_column(String(1024), nullable=False)
    destination_file: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    library_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    # queued | done | skipped | failed | no_scrape
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
