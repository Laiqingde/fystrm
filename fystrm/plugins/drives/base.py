"""DrivePlugin 抽象基类。

v0.1 只实现 LocalDrivePlugin 的 list/get_info。
所有 transfer_share / login / get_download_url 等接口提前定义好，
为后续接入真实网盘（115/123/百度/OneDrive/Google）预留扩展位。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar


@dataclass(slots=True, frozen=True)
class DriveFile:
    """网盘里的一个文件或目录。"""
    file_id: str           # 网盘内部 ID
    name: str              # 文件名
    path: str              # 网盘内绝对路径
    size: int              # 字节
    is_dir: bool
    mime_type: str | None = None
    modified_at: datetime | None = None
    extra: dict | None = None


class DrivePlugin(ABC):
    """所有网盘插件的统一接口。

    v0.1 必须实现: list, get_info
    v0.2+ 转存功能上线后实现: login, transfer_share, get_download_url, refresh_token
    """

    drive_type: ClassVar[str] = ""  # "local" | "pan123" | "pan115" | "baidu" | "onedrive" | "gdrive"

    def __init__(self, *, account_id: int | None = None, credentials: dict | None = None) -> None:
        self.account_id = account_id
        self.credentials = credentials or {}

    # ---- v0.1 必实现 ----

    @abstractmethod
    async def list(self, path: str) -> list[DriveFile]:
        """列出目录下的文件。"""

    @abstractmethod
    async def get_info(self, path: str) -> DriveFile:
        """获取单个文件元信息。"""

    # ---- v0.2+ 才实现（先留 stub，子类按需 override）----

    async def login(self, username: str, password: str) -> dict:
        """登录并返回 token / credentials。"""
        raise NotImplementedError(f"{self.drive_type} login not implemented in v0.1")

    async def refresh_token(self) -> dict:
        raise NotImplementedError(f"{self.drive_type} refresh_token not implemented in v0.1")

    async def transfer_share(
        self,
        share_url: str,
        share_password: str | None,
        target_dir: str,
    ) -> list[DriveFile]:
        """把别人的分享链接转存到自己网盘的 target_dir 下。返回转存后的文件列表。"""
        raise NotImplementedError(f"{self.drive_type} transfer_share not implemented in v0.1")

    async def get_download_url(self, file_id: str) -> str:
        """获取文件的直链（带签名/时效）。"""
        raise NotImplementedError(f"{self.drive_type} get_download_url not implemented in v0.1")

    async def get_webdav_url(self, file_id: str) -> str:
        """获取文件的 WebDAV URL（如果支持）。"""
        raise NotImplementedError(f"{self.drive_type} get_webdav_url not implemented in v0.1")
