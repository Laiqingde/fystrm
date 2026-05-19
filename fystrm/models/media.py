from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from fystrm.db import Base
from fystrm.models.base import TimestampMixin


class MediaItem(Base, TimestampMixin):
    """已入库的媒体条目。"""

    __tablename__ = "media_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    library_id: Mapped[int] = mapped_column(ForeignKey("libraries.id", ondelete="CASCADE"), index=True)

    # 识别结果
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    original_title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tmdb_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    media_type: Mapped[str] = mapped_column(String(16), nullable=False, default="movie")

    # 源文件
    source_file_path: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    source_file_size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    source_file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # 产物
    strm_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    nfo_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    poster_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    fanart_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # 刮削状态
    scrape_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")  # pending/done/failed/skipped
    scrape_error: Mapped[str | None] = mapped_column(Text, nullable=True)
