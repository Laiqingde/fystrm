"""CLI 测试: 给定文件名 → 识别 → TMDB 刮削 → 生成 nfo + 下载海报到 /tmp"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fystrm.engines.identifier import identify
from fystrm.engines.nfo import build_movie_nfo
from fystrm.engines.poster import download_image
from fystrm.engines.scraper import scrape_movie
from fystrm.plugins.meta.tmdb import TMDBPlugin


async def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <filename>")
        sys.exit(1)
    filename = sys.argv[1]

    info = identify(filename)
    print(f"Identify -> title={info.title!r} year={info.year} type={info.media_type}")

    plugin = TMDBPlugin()
    meta = await scrape_movie(plugin, info)
    if not meta:
        print("No match.")
        sys.exit(2)
    print(f"TMDB -> {meta.source_id} | {meta.title} ({meta.year}) | rating={meta.rating}")
    print(f"  genres: {meta.genres}")
    print(f"  overview: {(meta.overview or '')[:120]}...")

    out_dir = Path("/tmp/fystrm-test")
    out_dir.mkdir(parents=True, exist_ok=True)

    nfo_path = out_dir / "movie.nfo"
    nfo_path.write_text(build_movie_nfo(meta), encoding="utf-8")
    print(f"\nNFO -> {nfo_path} ({nfo_path.stat().st_size} bytes)")

    if meta.poster_url:
        ok = await download_image(meta.poster_url, out_dir / "poster.jpg")
        print(f"Poster -> {out_dir / 'poster.jpg'} ({'OK' if ok else 'FAILED'})")
    if meta.fanart_url:
        ok = await download_image(meta.fanart_url, out_dir / "fanart.jpg")
        print(f"Fanart -> {out_dir / 'fanart.jpg'} ({'OK' if ok else 'FAILED'})")


if __name__ == "__main__":
    asyncio.run(main())
