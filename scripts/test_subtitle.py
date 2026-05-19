"""字幕识别 + 复制单元测试。"""
import shutil
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tempfile

from fystrm.engines.subtitle import find_subtitles, copy_subtitles

tmpdir = Path(tempfile.mkdtemp(prefix="fystrm-sub-"))
print(f"workdir: {tmpdir}")

# 准备测试数据
(tmpdir / "Breaking.Bad.S01E01.mkv").touch()
(tmpdir / "Breaking.Bad.S01E01.zh.ass").write_text("zh")
(tmpdir / "Breaking.Bad.S01E01.en.srt").write_text("en")
(tmpdir / "Breaking.Bad.S01E01.chs&eng.ass").write_text("chs")
(tmpdir / "Breaking.Bad.S01E01.ass").write_text("und")  # 无语言后缀
(tmpdir / "Random.subtitle.ass").write_text("nope")
(tmpdir / "Other.movie.S01E01.zh.srt").write_text("other")  # 不匹配此视频

subs = find_subtitles(tmpdir / "Breaking.Bad.S01E01.mkv")
print(f"\n=== Detected {len(subs)} subtitles ===")
for s in subs:
    print(f"  {s.src_path.name} -> lang={s.lang} ext={s.ext}")

# 应该识别到 4 个 (zh/en/chs/und)，跳过 Random + Other
assert len(subs) == 4, f"expected 4, got {len(subs)}"
langs = sorted([s.lang for s in subs])
print(f"\nLangs sorted: {langs}")
assert "zh" in langs and "en" in langs and "und" in langs

# 复制测试
out_dir = tmpdir / "out"
copies = copy_subtitles(subs, out_dir, "绝命毒师 - S01E01")
print(f"\n=== Copied {len(copies)} subs ===")
for c in copies:
    print(f"  {c.name}")

assert len(copies) == 4
copied_names = sorted([c.name for c in copies])
print(f"\nNames: {copied_names}")

shutil.rmtree(tmpdir)
print("\n=== 字幕引擎全部测试通过 ===")
