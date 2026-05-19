"""SourcePlugin: 资源搜索/订阅源（TG 频道 / PT 站 / 聚合搜索等）。

v0.1 不实现任何 source，仅定义接口为 v0.3+ 预留。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar


@dataclass(slots=True)
class Resource:
    """搜索结果统一结构。"""
    source: str               # 来源标识
    title: str
    url: str                  # 分享链接 / 种子链接
    password: str | None = None
    size_bytes: int | None = None
    extra: dict = field(default_factory=dict)


class SourcePlugin(ABC):
    source_name: ClassVar[str] = ""

    @abstractmethod
    async def search(self, query: str, *, limit: int = 20) -> list[Resource]:
        """搜索资源。"""

    async def watch(self, channel_id: str) -> None:
        """订阅频道/源，新内容自动入库。v0.3+ 实现。"""
        raise NotImplementedError("watch not implemented in v0.1")
