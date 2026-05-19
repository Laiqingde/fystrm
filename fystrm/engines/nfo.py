"""生成 Emby/Kodi/Jellyfin 兼容的 movie.nfo XML。

参考: https://kodi.wiki/view/NFO_files/Movies
"""

from __future__ import annotations

from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString

from fystrm.plugins.meta.base import MediaMeta


def build_movie_nfo(meta: MediaMeta) -> str:
    root = Element("movie")

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
    if meta.runtime:
        _add(root, "runtime", str(meta.runtime))
    for genre in meta.genres:
        _add(root, "genre", genre)
    if meta.source_id:
        # Emby/Kodi 都识别 <uniqueid type="tmdb"> 和兼容 <tmdbid>
        uid = SubElement(root, "uniqueid", type=meta.source, default="true")
        uid.text = meta.source_id
        _add(root, "tmdbid", meta.source_id)
    # poster / fanart 引用（绝对 URL，Kodi 支持远程; Emby 倾向本地图，这俩字段两边都识别）
    if meta.poster_url:
        thumb = SubElement(root, "thumb", aspect="poster")
        thumb.text = meta.poster_url
    if meta.fanart_url:
        fanart = SubElement(root, "fanart")
        SubElement(fanart, "thumb").text = meta.fanart_url
    _add(root, "dateadded", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    raw = tostring(root, encoding="utf-8")
    return parseString(raw).toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")


def _add(parent: Element, tag: str, value: str) -> None:
    el = SubElement(parent, tag)
    el.text = value
