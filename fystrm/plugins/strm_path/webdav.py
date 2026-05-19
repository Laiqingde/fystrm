"""WebDAV strm 模式：strm 内容是 WebDAV URL。

例:
  source_root         = /scan-source/TV
  webdav_base_url     = http://cd2:19798/dav
  webdav_path_prefix  = /115/绝命毒师 Season 1
  source_path         = /scan-source/TV/Breaking.Bad.S01E01.mkv

  → http://cd2:19798/dav/115/绝命毒师%20Season%201/Breaking.Bad.S01E01.mkv
"""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import ClassVar
from urllib.parse import quote

from fystrm.plugins.strm_path.base import StrmContext, StrmPathPlugin


class WebDAVStrmPathPlugin(StrmPathPlugin):
    mode: ClassVar[str] = "webdav"

    def render(self, ctx: StrmContext) -> str:
        if not ctx.webdav_base_url:
            raise ValueError("webdav_base_url is required for webdav mode")

        src = PurePosixPath(ctx.source_path)
        root = PurePosixPath(ctx.source_root)
        try:
            rel = src.relative_to(root)
        except ValueError as exc:
            raise ValueError(
                f"source_path {ctx.source_path} not under source_root {ctx.source_root}"
            ) from exc

        # 组合 prefix + rel，统一斜杠
        prefix = (ctx.webdav_path_prefix or "").strip().rstrip("/")
        base = ctx.webdav_base_url.rstrip("/")

        rel_str = str(rel).replace("\\", "/")
        if prefix and not prefix.startswith("/"):
            prefix = "/" + prefix

        full_path = f"{prefix}/{rel_str}" if prefix else f"/{rel_str}"
        # URL 编码（保留 /）
        encoded = quote(full_path, safe="/:")
        return f"{base}{encoded}"
