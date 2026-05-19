"""StrmPathPlugin: 决定 .strm 文件里写什么路径。

v0.1 只实现 cd2_local（写 CD2 挂载点本地路径）。
v0.2+ 会有 webdav / direct_link 等模式。
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
    cd2_mount_prefix: str   # CD2 挂载前缀
    drive_account_id: int | None = None


class StrmPathPlugin(ABC):
    mode: ClassVar[str] = ""

    @abstractmethod
    def render(self, ctx: StrmContext) -> str:
        """返回 strm 文件应该包含的路径字符串。"""
