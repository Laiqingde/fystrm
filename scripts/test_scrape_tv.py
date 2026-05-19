"""CLI: TV 剧集刮削验证。

用法:
  python scripts/test_scrape_tv.py "Breaking Bad" 1 1
  python scripts/test_scrape_tv.py "鬼灭之刃" 1 1
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fystrm.plugins.meta.tmdb import TMDBPlugin


async def main():
    if len(sys.argv) < 4:
        print(f"Usage: {sys.argv[0]} <title> <season> <episode>")
        sys.exit(1)
    title = sys.argv[1]
    season = int(sys.argv[2])
    episode = int(sys.argv[3])

    p = TMDBPlugin()
    print(f"=== search tv: {title!r} ===")
    results = await p.search(title, media_type="tv")
    if not results:
        print("nomatch")
        return
    show = results[0]
    print(f"-> id={show.source_id} name={show.title} year={show.year} rating={show.rating}")

    print(f"\n=== fetch tv {show.source_id} ===")
    detail = await p.fetch(show.source_id, media_type="tv")
    print(f"-> title={detail.title} original={detail.original_title}")
    print(f"   genres={detail.genres} overview={(detail.overview or '')[:100]}...")

    print(f"\n=== fetch episode S{season:02d}E{episode:02d} ===")
    try:
        ep = await p.fetch_episode(show.source_id, season, episode)
        print(f"-> name={ep.episode_title} air_date={ep.release_date}")
        print(f"   overview={(ep.overview or '')[:120]}...")
        print(f"   still_url={ep.still_url}")
    except LookupError as e:
        print(f"episode lookup failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
