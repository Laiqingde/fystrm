"""CD2 本地路径模式：strm 文件内容 = CD2 挂载前缀 + 相对路径。

例: source_root=/scan-source/电影, cd2_mount_prefix=/CloudNAS/115/电影
    source_path=/scan-source/电影/复仇者联盟 (2012).mkv
    -> /CloudNAS/115/电影/复仇者联盟 (2012).mkv
"""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import ClassVar

from fystrm.plugins.strm_path.base import StrmContext, StrmPathPlugin


class CD2LocalStrmPathPlugin(StrmPathPlugin):
    mode: ClassVar[str] = "cd2_local"

    def render(self, ctx: StrmContext) -> str:
        src = PurePosixPath(ctx.source_path)
        root = PurePosixPath(ctx.source_root)
        try:
            rel = src.relative_to(root)
        except ValueError as exc:
            raise ValueError(
                f"source_path {ctx.source_path} not under source_root {ctx.source_root}"
            ) from exc
        prefix = PurePosixPath(ctx.cd2_mount_prefix)
        return str(prefix / rel)
