"""strm 文件生成: 给定路径上下文 + 标题/年份，写 .strm + 落 nfo/poster。

输出目录结构（Emby 标准）：
  {target_strm_path}/{title} ({year})/
    ├── {title}.strm     # 内容 = cd2 路径
    ├── movie.nfo
    ├── poster.jpg
    └── fanart.jpg
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from fystrm.engines.nfo import build_movie_nfo
from fystrm.engines.poster import download_image
from fystrm.plugins.meta.base import MediaMeta
from fystrm.plugins.strm_path.base import StrmContext, StrmPathPlugin


@dataclass(slots=True, frozen=True)
class StrmArtifacts:
    """生成的所有产物路径（绝对路径）。"""
    out_dir: Path
    strm_path: Path
    nfo_path: Path
    poster_path: Path | None
    fanart_path: Path | None


# 文件系统不能用的字符
_INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize_dirname(name: str) -> str:
    """文件夹名安全化：替换非法字符 + 去首尾空白/点。"""
    name = _INVALID_CHARS.sub(" ", name)
    name = re.sub(r"\s+", " ", name).strip()
    name = name.rstrip(".")
    return name or "unknown"


async def generate_strm(
    meta: MediaMeta,
    target_root: Path,
    strm_path_plugin: StrmPathPlugin,
    strm_ctx: StrmContext,
    *,
    download_artwork: bool = True,
) -> StrmArtifacts:
    """按 Emby 标准布局生成 strm + nfo + poster。

    Args:
        meta: TMDB 元数据
        target_root: 媒体库根目录（绝对路径）
        strm_path_plugin: 决定 strm 文件内容的插件
        strm_ctx: 给 strm_path_plugin.render 的上下文
        download_artwork: 是否下载 poster/fanart
    """
    # 文件夹名：标题 (年份)
    folder_name = sanitize_dirname(meta.title)
    if meta.year:
        folder_name = f"{folder_name} ({meta.year})"
    out_dir = target_root / folder_name
    out_dir.mkdir(parents=True, exist_ok=True)

    # 文件名（不带年份的标题，更符合 Emby 习惯）
    base_name = sanitize_dirname(meta.title)

    # 1. 写 strm
    strm_content = strm_path_plugin.render(strm_ctx)
    strm_path = out_dir / f"{base_name}.strm"
    strm_path.write_text(strm_content, encoding="utf-8")
    logger.info("strm -> {} -> {}", strm_path, strm_content)

    # 2. 写 nfo
    nfo_xml = build_movie_nfo(meta)
    nfo_path = out_dir / "movie.nfo"
    nfo_path.write_text(nfo_xml, encoding="utf-8")

    # 3. 海报
    poster_path: Path | None = None
    fanart_path: Path | None = None
    if download_artwork:
        if meta.poster_url:
            target = out_dir / "poster.jpg"
            if await download_image(meta.poster_url, target):
                poster_path = target
        if meta.fanart_url:
            target = out_dir / "fanart.jpg"
            if await download_image(meta.fanart_url, target):
                fanart_path = target

    return StrmArtifacts(
        out_dir=out_dir,
        strm_path=strm_path,
        nfo_path=nfo_path,
        poster_path=poster_path,
        fanart_path=fanart_path,
    )
