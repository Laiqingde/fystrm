"""元数据镜像引擎: 把 metadata_extensions 命中的文件原样 copy 到 strm 输出目录.

跟字幕的语义不同:
- 字幕: 同名同源 video, copy 时跟随 strm basename 重命名
- 元数据: 任何后缀命中的文件, 按相对路径镜像到 target_strm_path 下, 原文件名保留

例:
  source_root = /mnt/CloudNAS/电影
  target_root = /media/电影
  扫到 /mnt/CloudNAS/电影/焚城 (2024)/poster.jpg
    -> copy 到 /media/电影/焚城 (2024)/poster.jpg
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterator

from loguru import logger

# 跳过 > 50MB 元数据 (避免 copy 海报/截图之外的大文件)
MAX_METADATA_SIZE = 50 * 1024 * 1024


@dataclass(slots=True, frozen=True)
class MetadataFile:
    src: Path
    rel_path: str
    ext: str


def walk_metadata(source_root: str, extensions: frozenset[str]) -> Iterator[MetadataFile]:
    """递归扫 source_root, 返回所有命中扩展名的文件 (含相对路径)."""
    if not extensions:
        return
    root = Path(source_root)
    if not root.exists():
        return
    root_posix = PurePosixPath(source_root)
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        ext = p.suffix.lower()
        if ext not in extensions:
            continue
        try:
            size = p.stat().st_size
        except OSError:
            continue
        if size > MAX_METADATA_SIZE:
            logger.debug("metadata too large, skip: {} ({} bytes)", p, size)
            continue
        try:
            rel = str(PurePosixPath(str(p)).relative_to(root_posix))
        except ValueError:
            rel = p.name
        yield MetadataFile(src=p, rel_path=rel, ext=ext)


def sync_metadata(
    source_root: str, target_root: str, extensions: frozenset[str],
    progress_cb=None,
) -> dict:
    """把 source_root 下命中后缀的文件镜像 copy. 返回 {copied, skipped, total}.

    progress_cb(scanned, total_hint, copied, skipped): 每 50 文件回调一次,
    用于 UI 推 stage_message.
    """
    if not extensions:
        return {"copied": 0, "skipped": 0, "total": 0}
    target = Path(target_root)
    copied = 0
    skipped = 0
    scanned = 0
    last_cb = 0
    for m in walk_metadata(source_root, extensions):
        scanned += 1
        dest = target / m.rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            # 已存在且 size>0 就跳过 (size>0 防之前失败留的空文件; 不强制 size 匹配避免 CD2 size 不准)
            if dest.exists() and dest.stat().st_size > 0:
                skipped += 1
            else:
                shutil.copy2(m.src, dest)
                copied += 1
                if copied <= 3 or copied % 200 == 0:
                    logger.info("metadata copy {} -> {}", m.rel_path, dest)
        except Exception as e:
            logger.warning("metadata copy failed {} -> {}: {}", m.src, dest, e)
        # 进度回调每 50 文件触发一次
        if progress_cb and scanned - last_cb >= 50:
            last_cb = scanned
            try:
                progress_cb(scanned, copied, skipped)
            except Exception:
                pass
    if progress_cb:
        try:
            progress_cb(scanned, copied, skipped)
        except Exception:
            pass
    return {"copied": copied, "skipped": skipped, "total": scanned}
