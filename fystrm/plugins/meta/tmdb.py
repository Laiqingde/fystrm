"""TMDB 元数据插件（async, 走 httpx，带 Redis 缓存）。

不用 tmdbsimple（同步阻塞），直接调用 TMDB v3 API。
v0.1 仅实现电影。
"""

from __future__ import annotations

from typing import Any, ClassVar

import httpx
from loguru import logger

from fystrm.config import settings
from fystrm.plugins.meta.base import MediaMeta, MetaPlugin
from fystrm.utils.cache import cache_get, cache_set

TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG_BASE = "https://image.tmdb.org/t/p"

CACHE_TTL_SEARCH = 7 * 86400
CACHE_TTL_DETAIL = 7 * 86400


class TMDBPlugin(MetaPlugin):
    source_name: ClassVar[str] = "tmdb"

    def __init__(self, api_key: str | None = None, language: str | None = None) -> None:
        self.api_key = api_key or settings.tmdb_api_key
        self.language = language or settings.tmdb_language
        if not self.api_key:
            logger.warning("TMDB_API_KEY 未配置，刮削会失败")

    async def search(self, title: str, year: int | None = None, media_type: str = "movie") -> list[MediaMeta]:
        if media_type != "movie":
            logger.warning("v0.1 TMDB plugin only supports movie, got {}", media_type)
            return []
        if not self.api_key:
            return []

        cache_key = f"tmdb:search:{self.language}:{media_type}:{title}:{year or ""}"
        cached = await cache_get(cache_key)
        if cached is not None:
            return [self._meta_from_movie_search(r) for r in cached]

        params: dict[str, Any] = {
            "api_key": self.api_key,
            "language": self.language,
            "query": title,
            "include_adult": "false",
        }
        if year:
            params["year"] = year

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(f"{TMDB_BASE}/search/movie", params=params)
            resp.raise_for_status()
            data = resp.json()
        results: list[dict] = data.get("results", [])[:10]
        await cache_set(cache_key, results, ttl=CACHE_TTL_SEARCH)
        return [self._meta_from_movie_search(r) for r in results]

    async def fetch(self, source_id: str, media_type: str = "movie") -> MediaMeta:
        if media_type != "movie":
            raise NotImplementedError("v0.1 TMDB only supports movie")
        if not self.api_key:
            raise RuntimeError("TMDB_API_KEY 未配置")

        cache_key = f"tmdb:movie:{self.language}:{source_id}"
        cached = await cache_get(cache_key)
        if cached is not None:
            return self._meta_from_movie_detail(cached)

        params = {"api_key": self.api_key, "language": self.language, "append_to_response": "credits,images,release_dates"}
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(f"{TMDB_BASE}/movie/{source_id}", params=params)
            resp.raise_for_status()
            data = resp.json()
        await cache_set(cache_key, data, ttl=CACHE_TTL_DETAIL)
        return self._meta_from_movie_detail(data)

    @staticmethod
    def _img_url(path: str | None, size: str = "original") -> str | None:
        if not path:
            return None
        return f"{TMDB_IMG_BASE}/{size}{path}"

    @classmethod
    def _meta_from_movie_search(cls, r: dict) -> MediaMeta:
        date = r.get("release_date") or ""
        year = int(date[:4]) if len(date) >= 4 and date[:4].isdigit() else None
        return MediaMeta(
            source="tmdb",
            source_id=str(r.get("id")),
            media_type="movie",
            title=r.get("title") or "",
            original_title=r.get("original_title"),
            year=year,
            overview=r.get("overview"),
            poster_url=cls._img_url(r.get("poster_path"), "w500"),
            fanart_url=cls._img_url(r.get("backdrop_path"), "original"),
            rating=r.get("vote_average"),
            release_date=date or None,
            raw=r,
        )

    @classmethod
    def _meta_from_movie_detail(cls, r: dict) -> MediaMeta:
        date = r.get("release_date") or ""
        year = int(date[:4]) if len(date) >= 4 and date[:4].isdigit() else None
        genres = [g["name"] for g in r.get("genres", []) if g.get("name")]
        return MediaMeta(
            source="tmdb",
            source_id=str(r.get("id")),
            media_type="movie",
            title=r.get("title") or "",
            original_title=r.get("original_title"),
            year=year,
            overview=r.get("overview"),
            poster_url=cls._img_url(r.get("poster_path"), "original"),
            fanart_url=cls._img_url(r.get("backdrop_path"), "original"),
            rating=r.get("vote_average"),
            genres=genres,
            runtime=r.get("runtime"),
            release_date=date or None,
            raw=r,
        )
