"""TMDB 元数据插件（async, httpx, Redis 缓存）。

v0.2 加: search_tv / fetch_tv / fetch_episode + 多语言 fallback + 未匹配缓存
"""

from __future__ import annotations

from typing import Any, ClassVar

import httpx
from loguru import logger

from fystrm.config import settings
from fystrm.core import dynamic_settings
from fystrm.plugins.meta.base import MediaMeta, MetaPlugin
from fystrm.utils.cache import cache_get, cache_set, get_redis

TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG_BASE = "https://image.tmdb.org/t/p"

CACHE_TTL_SEARCH = 7 * 86400
CACHE_TTL_DETAIL = 7 * 86400
CACHE_TTL_NOMATCH = 7 * 86400


class TMDBPlugin(MetaPlugin):
    source_name: ClassVar[str] = "tmdb"

    def __init__(self, api_key: str | None = None, language: str | None = None) -> None:
        self.api_key = api_key or dynamic_settings.get("TMDB_API_KEY") or settings.tmdb_api_key
        self.language = language or dynamic_settings.get("TMDB_LANGUAGE") or settings.tmdb_language
        if not self.api_key:
            logger.warning("TMDB_API_KEY 未配置，刮削会失败")

    # ---------- 公共接口 ----------

    async def search(self, title: str, year: int | None = None, media_type: str = "movie") -> list[MediaMeta]:
        if media_type == "movie":
            return await self._search_with_fallback(title, year, "movie")
        if media_type in {"tv", "anime"}:
            return await self._search_with_fallback(title, year, "tv")
        logger.warning("Unknown media_type {}", media_type)
        return []

    async def fetch(self, source_id: str, media_type: str = "movie") -> MediaMeta:
        if media_type == "movie":
            return await self._fetch_movie(source_id)
        if media_type in {"tv", "anime"}:
            return await self._fetch_tv(source_id)
        raise NotImplementedError(media_type)

    async def fetch_episode(self, tv_id: str, season: int, episode: int) -> MediaMeta:
        if not self.api_key:
            raise RuntimeError("TMDB_API_KEY 未配置")
        cache_key = f"tmdb:episode:{self.language}:{tv_id}:{season}:{episode}"
        cached = await cache_get(cache_key)
        if cached is not None:
            return self._meta_from_episode(tv_id, cached)

        params = {"api_key": self.api_key, "language": self.language}
        url = f"{TMDB_BASE}/tv/{tv_id}/season/{season}/episode/{episode}"
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 404:
                    raise LookupError(f"episode not found: tv={tv_id} S{season:02d}E{episode:02d}")
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as e:
            raise LookupError(f"episode HTTP error: {e}") from e
        await cache_set(cache_key, data, ttl=CACHE_TTL_DETAIL)
        return self._meta_from_episode(tv_id, data)

    # ---------- 多语言 fallback + 未匹配缓存 ----------

    async def _search_with_fallback(self, title: str, year: int | None, kind: str) -> list[MediaMeta]:
        """先按主语言搜，搜不到回退英文，再用 ID 反查主语言详情避免乱码。

        kind: "movie" | "tv"
        """
        if not self.api_key:
            return []

        nomatch_key = f"tmdb:nomatch:{kind}:{self.language}:{title}:{year or ''}"
        if await cache_get(nomatch_key) is not None:
            logger.debug("nomatch cached: {}", nomatch_key)
            return []

        # round 1: 主语言搜
        results = await self._raw_search(title, year, kind, self.language)
        if results:
            return [self._convert(r, kind) for r in results]

        # round 2: 英文 fallback
        if self.language != "en-US":
            results = await self._raw_search(title, year, kind, "en-US")
            if results:
                # 拿到 id 后反查主语言详情
                output: list[MediaMeta] = []
                for r in results[:5]:
                    try:
                        if kind == "movie":
                            output.append(await self._fetch_movie(str(r["id"])))
                        else:
                            output.append(await self._fetch_tv(str(r["id"])))
                    except Exception as e:
                        logger.debug("fallback fetch failed: {}", e)
                if output:
                    return output

        # 都搜不到 → 缓存 nomatch
        await cache_set(nomatch_key, {"ts": "nomatch"}, ttl=CACHE_TTL_NOMATCH)
        return []

    async def _raw_search(self, title: str, year: int | None, kind: str, lang: str) -> list[dict]:
        endpoint = "search/movie" if kind == "movie" else "search/tv"
        params: dict[str, Any] = {
            "api_key": self.api_key,
            "language": lang,
            "query": title,
            "include_adult": "false",
        }
        if year:
            if kind == "movie":
                params["year"] = year
            else:
                params["first_air_date_year"] = year

        cache_key = f"tmdb:search:{lang}:{kind}:{title}:{year or ''}"
        cached = await cache_get(cache_key)
        if cached is not None:
            return cached

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(f"{TMDB_BASE}/{endpoint}", params=params)
            resp.raise_for_status()
            data = resp.json()
        results = data.get("results", [])[:10]
        await cache_set(cache_key, results, ttl=CACHE_TTL_SEARCH)
        return results

    # ---------- 详情 ----------

    async def _fetch_movie(self, mid: str) -> MediaMeta:
        cache_key = f"tmdb:movie:{self.language}:{mid}"
        cached = await cache_get(cache_key)
        if cached is not None:
            return self._meta_from_movie_detail(cached)
        params = {"api_key": self.api_key, "language": self.language}
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(f"{TMDB_BASE}/movie/{mid}", params=params)
            resp.raise_for_status()
            data = resp.json()
        await cache_set(cache_key, data, ttl=CACHE_TTL_DETAIL)
        return self._meta_from_movie_detail(data)

    async def _fetch_tv(self, tv_id: str) -> MediaMeta:
        cache_key = f"tmdb:tv:{self.language}:{tv_id}"
        cached = await cache_get(cache_key)
        if cached is not None:
            return self._meta_from_tv_detail(cached)
        params = {"api_key": self.api_key, "language": self.language}
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(f"{TMDB_BASE}/tv/{tv_id}", params=params)
            resp.raise_for_status()
            data = resp.json()
        await cache_set(cache_key, data, ttl=CACHE_TTL_DETAIL)
        return self._meta_from_tv_detail(data)

    # ---------- meta 转换 ----------

    @staticmethod
    def _img_url(path: str | None, size: str = "original") -> str | None:
        if not path:
            return None
        return f"{TMDB_IMG_BASE}/{size}{path}"

    def _convert(self, r: dict, kind: str) -> MediaMeta:
        return self._meta_from_movie_search(r) if kind == "movie" else self._meta_from_tv_search(r)

    @classmethod
    def _meta_from_movie_search(cls, r: dict) -> MediaMeta:
        date = r.get("release_date") or ""
        year = int(date[:4]) if len(date) >= 4 and date[:4].isdigit() else None
        return MediaMeta(
            source="tmdb", source_id=str(r.get("id")), media_type="movie",
            title=r.get("title") or "", original_title=r.get("original_title"),
            year=year, overview=r.get("overview"),
            poster_url=cls._img_url(r.get("poster_path"), "w500"),
            fanart_url=cls._img_url(r.get("backdrop_path"), "original"),
            rating=r.get("vote_average"),
            release_date=date or None, raw=r,
        )

    @classmethod
    def _meta_from_movie_detail(cls, r: dict) -> MediaMeta:
        date = r.get("release_date") or ""
        year = int(date[:4]) if len(date) >= 4 and date[:4].isdigit() else None
        genres = [g["name"] for g in r.get("genres", []) if g.get("name")]
        return MediaMeta(
            source="tmdb", source_id=str(r.get("id")), media_type="movie",
            title=r.get("title") or "", original_title=r.get("original_title"),
            year=year, overview=r.get("overview"),
            poster_url=cls._img_url(r.get("poster_path"), "original"),
            fanart_url=cls._img_url(r.get("backdrop_path"), "original"),
            rating=r.get("vote_average"), genres=genres, runtime=r.get("runtime"),
            release_date=date or None, raw=r,
        )

    @classmethod
    def _meta_from_tv_search(cls, r: dict) -> MediaMeta:
        date = r.get("first_air_date") or ""
        year = int(date[:4]) if len(date) >= 4 and date[:4].isdigit() else None
        return MediaMeta(
            source="tmdb", source_id=str(r.get("id")), media_type="tv",
            title=r.get("name") or "", original_title=r.get("original_name"),
            year=year, overview=r.get("overview"),
            poster_url=cls._img_url(r.get("poster_path"), "w500"),
            fanart_url=cls._img_url(r.get("backdrop_path"), "original"),
            rating=r.get("vote_average"), release_date=date or None, raw=r,
        )

    @classmethod
    def _meta_from_tv_detail(cls, r: dict) -> MediaMeta:
        date = r.get("first_air_date") or ""
        year = int(date[:4]) if len(date) >= 4 and date[:4].isdigit() else None
        genres = [g["name"] for g in r.get("genres", []) if g.get("name")]
        return MediaMeta(
            source="tmdb", source_id=str(r.get("id")), media_type="tv",
            title=r.get("name") or "", original_title=r.get("original_name"),
            year=year, overview=r.get("overview"),
            poster_url=cls._img_url(r.get("poster_path"), "original"),
            fanart_url=cls._img_url(r.get("backdrop_path"), "original"),
            rating=r.get("vote_average"), genres=genres, release_date=date or None,
            raw=r,
        )

    @classmethod
    def _meta_from_episode(cls, tv_id: str, r: dict) -> MediaMeta:
        date = r.get("air_date") or ""
        year = int(date[:4]) if len(date) >= 4 and date[:4].isdigit() else None
        return MediaMeta(
            source="tmdb",
            source_id=f"{tv_id}/{r.get('season_number')}/{r.get('episode_number')}",
            media_type="episode",
            title=r.get("name") or "",
            year=year,
            overview=r.get("overview"),
            still_url=cls._img_url(r.get("still_path"), "original"),
            rating=r.get("vote_average"),
            release_date=date or None,
            parent_id=tv_id,
            season_number=r.get("season_number"),
            episode_number=r.get("episode_number"),
            episode_title=r.get("name"),
            raw=r,
        )
