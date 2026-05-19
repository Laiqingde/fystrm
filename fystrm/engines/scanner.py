"""扫描器：递归遍历目录，过滤出视频文件。

通过 DrivePlugin 抽象访问文件系统，未来真实网盘也能复用同一份代码。
v0.1 走 LocalDrivePlugin。
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import PurePosixPath

from loguru import logger

from fystrm.plugins.drives.base import DriveFile, DrivePlugin

# 媒体文件后缀（保守列表，过滤掉字幕/海报/nfo）
VIDEO_EXTENSIONS: frozenset[str] = frozenset({
    ".mkv", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm",
    ".m4v", ".mpg", ".mpeg", ".ts", ".m2ts", ".rmvb", ".rm",
    ".iso", ".vob",
})

# 排除的小文件阈值（小于此大小的视频通常是 sample / 预告片）
MIN_VIDEO_SIZE = 100 * 1024 * 1024  # 100 MB


@dataclass(slots=True, frozen=True)
class ScannedFile:
    drive_file: DriveFile
    rel_path: str  # 相对于扫描源根的路径
    ext: str


def is_video(name: str) -> bool:
    return PurePosixPath(name).suffix.lower() in VIDEO_EXTENSIONS


async def scan_directory(
    drive: DrivePlugin,
    root: str,
    *,
    min_size: int = MIN_VIDEO_SIZE,
    follow_dirs: bool = True,
) -> AsyncIterator[ScannedFile]:
    """递归扫描，async 生成 ScannedFile 流。

    Args:
        drive: 网盘插件实例
        root: 扫描根目录（drive 内的路径）
        min_size: 过滤小文件
        follow_dirs: 是否递归子目录
    """
    stack: list[str] = [root]
    while stack:
        cur = stack.pop()
        try:
            entries = await drive.list(cur)
        except FileNotFoundError:
            logger.warning("path not found, skip: {}", cur)
            continue
        except NotADirectoryError:
            logger.warning("not a directory, skip: {}", cur)
            continue
        except Exception as e:
            logger.error("list failed on {}: {}", cur, e)
            continue
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
            yield ScannedFile(
                drive_file=entry,
                rel_path=rel,
                ext=PurePosixPath(entry.name).suffix.lower(),
            )


def _relpath(path: str, root: str) -> str:
    p = PurePosixPath(path)
    r = PurePosixPath(root)
    try:
        return str(p.relative_to(r))
    except ValueError:
        return str(p)
