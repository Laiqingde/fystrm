from __future__ import annotations

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from fystrm.db import Base
from fystrm.models.base import TimestampMixin


class Library(Base, TimestampMixin):
    """媒体库配置：扫描源 + strm 输出 + CD2 路径映射。"""

    __tablename__ = "libraries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    source_path: Mapped[str] = mapped_column(String(512), nullable=False)
    target_strm_path: Mapped[str] = mapped_column(String(512), nullable=False)
    cd2_mount_prefix: Mapped[str] = mapped_column(String(512), nullable=False)
    media_type: Mapped[str] = mapped_column(String(16), nullable=False, default="movie")  # movie/tv/mixed
    drive_account_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # FK 到 drive_accounts，v0.1 留空
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_scan_at: Mapped["DateTime | None"] = mapped_column(DateTime(timezone=True), nullable=True)

    # v0.2: strm 输出模式
    strm_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="cd2_local")  # cd2_local | webdav
    webdav_base_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    webdav_path_prefix: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # v0.3: 自定义文件后缀 (分号分隔, 小写带点)
    strm_extensions: Mapped[str] = mapped_column(
        String(1024), nullable=False,
        default=".mp4;.mkv;.ts;.iso;.rmvb;.avi;.mov;.mpeg;.mpg;.wmv;.3gp;.asf;.m4v;.flv;.m2ts;.tp;.f4v",
    )
    metadata_extensions: Mapped[str] = mapped_column(
        String(1024), nullable=False, default="",
    )

    # v0.3: 刮削开关 (False = 只生成 strm + 同步源元数据, 不调 TMDB / 不生 movie.nfo / 不下载海报)
    scrape_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
