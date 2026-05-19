"""验证 v0.2 NFO 模板 + episode 布局。"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fystrm.engines.nfo import build_episode_nfo, build_tvshow_nfo
from fystrm.plugins.meta.tmdb import TMDBPlugin


async def main():
    p = TMDBPlugin()
    # 拿绝命毒师 + S01E01 + S01E02 真实数据
    show = await p.fetch("1396", media_type="tv")
    ep1 = await p.fetch_episode("1396", 1, 1)
    ep2 = await p.fetch_episode("1396", 1, 2)

    print("=== tvshow.nfo ===")
    print(build_tvshow_nfo(show)[:600])

    print("\n=== S01E01.nfo ===")
    print(build_episode_nfo(ep1, parent_meta=show))

    print("\n=== S01E02.nfo (前 400 字) ===")
    print(build_episode_nfo(ep2, parent_meta=show)[:400])


if __name__ == "__main__":
    asyncio.run(main())
