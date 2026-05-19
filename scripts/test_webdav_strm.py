"""WebDAV strm 单元测试 (含中文/空格/斜杠 edge case)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fystrm.plugins.strm_path.base import StrmContext
from fystrm.plugins.strm_path.webdav import WebDAVStrmPathPlugin
from fystrm.plugins.strm_path.cd2_local import CD2LocalStrmPathPlugin


def assert_eq(actual, expected, label):
    ok = "✓" if actual == expected else "✗"
    print(f"{ok} {label}")
    print(f"   got:  {actual}")
    if not actual == expected:
        print(f"   want: {expected}")
        sys.exit(1)


webdav = WebDAVStrmPathPlugin()

# 1. 基础
ctx = StrmContext(
    source_path="/scan-source/TV/绝命毒师/Season 01/Breaking.Bad.S01E01.mkv",
    source_root="/scan-source/TV",
    webdav_base_url="http://cd2:19798/dav",
    webdav_path_prefix="/115/TV",
)
assert_eq(
    webdav.render(ctx),
    "http://cd2:19798/dav/115/TV/%E7%BB%9D%E5%91%BD%E6%AF%92%E5%B8%88/Season%2001/Breaking.Bad.S01E01.mkv",
    "中文 + 空格 URL 编码",
)

# 2. trailing slash 容错
ctx2 = StrmContext(
    source_path="/scan-source/x.mkv",
    source_root="/scan-source",
    webdav_base_url="http://cd2:19798/dav/",
    webdav_path_prefix="115/movies/",
)
assert_eq(webdav.render(ctx2), "http://cd2:19798/dav/115/movies/x.mkv", "trailing slash 容错")

# 3. 无 prefix
ctx3 = StrmContext(
    source_path="/scan-source/x.mkv",
    source_root="/scan-source",
    webdav_base_url="http://cd2:19798/dav",
)
assert_eq(webdav.render(ctx3), "http://cd2:19798/dav/x.mkv", "无 prefix")

# 4. CD2 plugin 仍然工作
cd2 = CD2LocalStrmPathPlugin()
ctx4 = StrmContext(
    source_path="/scan-source/电影/X.mkv",
    source_root="/scan-source/电影",
    cd2_mount_prefix="/CloudNAS/115/电影",
)
assert_eq(cd2.render(ctx4), "/CloudNAS/115/电影/X.mkv", "CD2 plugin 向后兼容")

# 5. 缺 base_url 报错
try:
    webdav.render(StrmContext(source_path="/x/a", source_root="/x"))
    print("✗ 缺 base_url 没报错")
    sys.exit(1)
except ValueError:
    print("✓ 缺 base_url 正确报错")

print()
print("=== WebDAV strm 单元测试全部通过 ===")
