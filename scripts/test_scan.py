"""CLI 测试: 扫指定目录 + 文件名识别。

用法（容器内）: python scripts/test_scan.py /scan-source
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# 允许直接 python scripts/xxx.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fystrm.engines.identifier import identify
from fystrm.engines.scanner import scan_directory
from fystrm.plugins.drives.local import LocalDrivePlugin


async def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <scan_root>")
        sys.exit(1)
    root = sys.argv[1]
    drive = LocalDrivePlugin()
    count = 0
    async for sf in scan_directory(drive, root, min_size=0):
        count += 1
        info = identify(sf.drive_file.name)
        print(f"[{count}] {sf.rel_path}")
        print(f"    size={sf.drive_file.size:,} ext={sf.ext}")
        print(f"    -> title={info.title!r} year={info.year} type={info.media_type}"
              f" season={info.season} episode={info.episode}"
              f" resolution={info.resolution} source={info.source}")
    print(f"\n=== Total: {count} video files ===")


if __name__ == "__main__":
    asyncio.run(main())
