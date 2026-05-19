"""文件名识别：guessit 主, anitopy 兜底动漫。

输出统一的 IdentifyResult。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import anitopy
from guessit import guessit
from loguru import logger


@dataclass(slots=True)
class IdentifyResult:
    title: str
    year: int | None = None
    media_type: str = "movie"  # movie | tv | anime
    season: int | None = None
    episode: int | None = None
    container: str | None = None
    resolution: str | None = None
    source: str | None = None  # WEB-DL / BluRay / HDTV
    raw: dict[str, Any] = field(default_factory=dict)


def identify(filename: str, *, hint_type: str | None = None) -> IdentifyResult:
    """识别一个文件名。

    Args:
        filename: 文件名（含扩展，不含路径）
        hint_type: 可选提示 "movie" / "tv" / "anime"
    """
    options: dict[str, Any] = {}
    if hint_type in {"movie", "tv"}:
        options["type"] = hint_type

    raw = dict(guessit(filename, options=options))
    raw_title = raw.get("title")
    if isinstance(raw_title, list):
        raw_title = " ".join(str(x) for x in raw_title)
    title = str(raw_title) if raw_title else _fallback_title(filename)

    year_v = raw.get("year")
    year = int(year_v) if year_v else None
    media_type = "movie"
    season = raw.get("season")
    episode = raw.get("episode")
    if season is not None or episode is not None:
        media_type = "tv"

    # 动漫 fallback: 如果 guessit 给的 title 看起来不正常（含大量罗马音/japanese 标识）
    # 用 anitopy 再试一次
    if _looks_like_anime(filename):
        try:
            ani = anitopy.parse(filename) or {}
            ani_title = ani.get("anime_title")
            if ani_title and len(str(ani_title)) > 1:
                title = str(ani_title)
                media_type = "anime"
                if ani.get("anime_year"):
                    try:
                        year = int(str(ani["anime_year"]))
                    except (TypeError, ValueError):
                        pass
                if ani.get("episode_number"):
                    try:
                        episode = int(str(ani["episode_number"]))
                        media_type = "anime"
                    except (TypeError, ValueError):
                        pass
        except Exception as e:
            logger.debug("anitopy parse failed for {}: {}", filename, e)

    return IdentifyResult(
        title=title,
        year=year,
        media_type=media_type,
        season=int(season) if isinstance(season, int) else None,
        episode=int(episode) if isinstance(episode, int) else None,
        container=raw.get("container"),
        resolution=raw.get("screen_size"),
        source=raw.get("source"),
        raw=raw,
    )


def _fallback_title(filename: str) -> str:
    """guessit 没识别出 title 时的兜底：去后缀，替换分隔符。"""
    from pathlib import PurePosixPath
    stem = PurePosixPath(filename).stem
    return stem.replace(".", " ").replace("_", " ").strip()


def _looks_like_anime(filename: str) -> bool:
    name = filename.lower()
    markers = ["[", "]", " - ", "raw", "bd-rip", "bd ", "anime", "[fansub"]
    bracket_count = name.count("[") + name.count("]")
    return bracket_count >= 2 or any(m in name for m in markers)
