"""LocalDrivePlugin: 直接读取本地/挂载文件系统。

v0.1 用这个 plugin 模拟"CD2 挂载的网盘目录"。
后续 v0.2+ 会有 Pan123Plugin / Pan115Plugin 等真实网盘实现。
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import ClassVar

from fystrm.plugins.drives.base import DriveFile, DrivePlugin


class LocalDrivePlugin(DrivePlugin):
    drive_type: ClassVar[str] = "local"

    async def list(self, path: str) -> list[DriveFile]:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(path)
        if not p.is_dir():
            raise NotADirectoryError(path)
        result: list[DriveFile] = []
        for child in p.iterdir():
            result.append(self._to_drive_file(child))
        return result

    async def get_info(self, path: str) -> DriveFile:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(path)
        return self._to_drive_file(p)

    @staticmethod
    def _to_drive_file(p: Path) -> DriveFile:
        stat = p.stat()
        return DriveFile(
            file_id=str(p.resolve()),
            name=p.name,
            path=str(p),
            size=stat.st_size,
            is_dir=p.is_dir(),
            mime_type=None,
            modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
        )
