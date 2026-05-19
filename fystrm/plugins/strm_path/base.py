"""StrmPathPlugin: 决定 .strm 文件里写什么路径。

v0.1: cd2_local 模式 (写 CD2 挂载点本地路径)
v0.2: webdav 模式 (写 WebDAV URL)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar


@dataclass(slots=True, frozen=True)
class StrmContext:
    """生成 strm 路径需要的上下文。"""
    source_path: str        # 扫描源中的绝对路径
    source_root: str        # 扫描源根目录（用于计算相对路径）

    # cd2_local 模式
    cd2_mount_prefix: str = ""

    # webdav 模式
    webdav_base_url: str | None = None
    webdav_path_prefix: str | None = None

    drive_account_id: int | None = None


class StrmPathPlugin(ABC):
    mode: ClassVar[str] = ""

    @abstractmethod
    def render(self, ctx: StrmContext) -> str:
        """返回 strm 文件应该包含的路径字符串。"""
