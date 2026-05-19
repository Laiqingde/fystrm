"""生成 Emby/Kodi/Jellyfin 兼容的 NFO XML。

参考: https://kodi.wiki/view/NFO_files/
"""

from __future__ import annotations

from datetime import datetime
from xml.dom.minidom import parseString
from xml.etree.ElementTree import Element, SubElement, tostring

from fystrm.plugins.meta.base import MediaMeta


def build_movie_nfo(meta: MediaMeta) -> str:
    root = Element("movie")
    _common_show_fields(root, meta)
    if meta.runtime:
        _add(root, "runtime", str(meta.runtime))
    if meta.poster_url:
        SubElement(root, "thumb", aspect="poster").text = meta.poster_url
    if meta.fanart_url:
        SubElement(SubElement(root, "fanart"), "thumb").text = meta.fanart_url
    _add(root, "dateadded", _now_str())
    return _pretty(root)


def build_tvshow_nfo(meta: MediaMeta) -> str:
    """剧集根 tvshow.nfo（Emby/Kodi 标准）。"""
    root = Element("tvshow")
    _common_show_fields(root, meta)
    if meta.poster_url:
        SubElement(root, "thumb", aspect="poster").text = meta.poster_url
    if meta.fanart_url:
        SubElement(SubElement(root, "fanart"), "thumb").text = meta.fanart_url
    _add(root, "dateadded", _now_str())
    return _pretty(root)


def build_episode_nfo(episode_meta: MediaMeta, parent_meta: MediaMeta | None = None) -> str:
    """单集 NFO，对应文件 {title} - S01E01.nfo。"""
    root = Element("episodedetails")
    _add(root, "title", episode_meta.episode_title or episode_meta.title or "")
    if episode_meta.season_number is not None:
        _add(root, "season", str(episode_meta.season_number))
    if episode_meta.episode_number is not None:
        _add(root, "episode", str(episode_meta.episode_number))
    if episode_meta.overview:
        _add(root, "plot", episode_meta.overview)
        _add(root, "outline", episode_meta.overview)
    if episode_meta.release_date:
        _add(root, "aired", episode_meta.release_date)
    if episode_meta.rating is not None:
        _add(root, "rating", f"{episode_meta.rating:.1f}")
    if episode_meta.parent_id:
        # showtitle 帮助 Emby 关联到剧集
        if parent_meta and parent_meta.title:
            _add(root, "showtitle", parent_meta.title)
        SubElement(root, "uniqueid", type="tmdb", default="true").text = (
            f"{episode_meta.parent_id}/{episode_meta.season_number}/{episode_meta.episode_number}"
        )
        _add(root, "tmdbid", episode_meta.parent_id)
    if episode_meta.still_url:
        SubElement(root, "thumb").text = episode_meta.still_url
    _add(root, "dateadded", _now_str())
    return _pretty(root)


# ---------- 私有 ----------

def _common_show_fields(root: Element, meta: MediaMeta) -> None:
    _add(root, "title", meta.title)
    if meta.original_title:
        _add(root, "originaltitle", meta.original_title)
    if meta.year:
        _add(root, "year", str(meta.year))
    if meta.release_date:
        _add(root, "premiered", meta.release_date)
        _add(root, "releasedate", meta.release_date)
    if meta.overview:
        _add(root, "plot", meta.overview)
        _add(root, "outline", meta.overview)
    if meta.rating is not None:
        _add(root, "rating", f"{meta.rating:.1f}")
    for genre in meta.genres:
        _add(root, "genre", genre)
    if meta.source_id:
        SubElement(root, "uniqueid", type=meta.source, default="true").text = meta.source_id
        _add(root, "tmdbid", meta.source_id)


def _add(parent: Element, tag: str, value: str) -> None:
    el = SubElement(parent, tag)
    el.text = value


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _pretty(root: Element) -> str:
    raw = tostring(root, encoding="utf-8")
    return parseString(raw).toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")
