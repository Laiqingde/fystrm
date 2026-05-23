from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from fystrm.db import Base
from fystrm.models.base import TimestampMixin


class ScanTask(Base, TimestampMixin):
    """扫描任务（v0.1 核心）。"""

    __tablename__ = "scan_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    library_id: Mapped[int] = mapped_column(ForeignKey("libraries.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")  # pending/running/done/failed
    total_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processed_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # v0.3: 阶段细分 (pending/discovering/processing/syncing_metadata/done)
    stage: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    stage_message: Mapped[str | None] = mapped_column(String(256), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TransferTask(Base, TimestampMixin):
    """转存任务（v0.1 表先建，接口 stub，不写入数据）。"""

    __tablename__ = "transfer_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    share_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    share_password: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_drive_account_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
