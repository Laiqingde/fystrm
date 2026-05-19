"""扫描器：递归遍历目录，过滤出视频文件 + 同目录字幕。"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from loguru import logger

from fystrm.engines.subtitle import find_subtitles
from fystrm.plugins.drives.base import DriveFile, DrivePlugin

VIDEO_EXTENSIONS: frozenset[str] = frozenset({
    ".mkv", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm",
    ".m4v", ".mpg", ".mpeg", ".ts", ".m2ts", ".rmvb", ".rm",
    ".iso", ".vob",
})

MIN_VIDEO_SIZE = 100 * 1024 * 1024


@dataclass(slots=True, frozen=True)
class ScannedFile:
    drive_file: DriveFile
    rel_path: str
    ext: str
    sidecar_subtitles: tuple = field(default_factory=tuple)  # tuple[Subtitle, ...]


def is_video(name: str) -> bool:
    return PurePosixPath(name).suffix.lower() in VIDEO_EXTENSIONS


async def scan_directory(
    drive: DrivePlugin,
    root: str,
    *,
    min_size: int = MIN_VIDEO_SIZE,
    follow_dirs: bool = True,
    detect_subtitles: bool = True,
) -> AsyncIterator[ScannedFile]:
    stack: list[str] = [root]
    while stack:
        cur = stack.pop()
        try:
            entries = await drive.list(cur)
        except FileNotFoundError:
            logger.warning("path not found, skip: {}", cur); continue
        except NotADirectoryError:
            logger.warning("not a directory, skip: {}", cur); continue
        except Exception as e:
            logger.error("list failed on {}: {}", cur, e); continue
        for entry in entries:
            if entry.is_dir:
                if follow_dirs:
                    stack.append(entry.path)
                continue
            if not is_video(entry.name):
                continue
            if entry.size < min_size:
                logger.debug("skip small file: {} ({} bytes)", entry.path, entry.size)
                continue
            rel = _relpath(entry.path, root)
            subs = tuple(find_subtitles(Path(entry.path))) if detect_subtitles else tuple()
            yield ScannedFile(
                drive_file=entry,
                rel_path=rel,
                ext=PurePosixPath(entry.name).suffix.lower(),
                sidecar_subtitles=subs,
            )


def _relpath(path: str, root: str) -> str:
    p = PurePosixPath(path); r = PurePosixPath(root)
    try:
        return str(p.relative_to(r))
    except ValueError:
        return str(p)
