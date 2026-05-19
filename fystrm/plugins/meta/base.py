"""元数据/刮削插件抽象基类（TMDB / 豆瓣等）。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar


@dataclass(slots=True)
class MediaMeta:
    """统一的媒体元数据结构。"""
    source: str                       # "tmdb" | "douban"
    source_id: str                    # TMDB ID 或 豆瓣 ID
    media_type: str                   # "movie" | "tv"
    title: str                        # 主语言标题（默认中文）
    original_title: str | None = None
    year: int | None = None
    overview: str | None = None
    poster_url: str | None = None
    fanart_url: str | None = None
    rating: float | None = None
    genres: list[str] = field(default_factory=list)
    runtime: int | None = None        # 分钟
    release_date: str | None = None   # YYYY-MM-DD
    raw: dict = field(default_factory=dict)


class MetaPlugin(ABC):
    source_name: ClassVar[str] = ""

    @abstractmethod
    async def search(self, title: str, year: int | None = None, media_type: str = "movie") -> list[MediaMeta]:
        """搜索匹配，按相关度返回候选列表。"""

    @abstractmethod
    async def fetch(self, source_id: str, media_type: str = "movie") -> MediaMeta:
        """按 ID 拉取完整元数据。"""
