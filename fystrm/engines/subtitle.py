"""字幕识别 + copy + 重命名。

策略:
- 扫视频同目录下的字幕（.ass .srt .vtt .ssa .sup .smi .idx .sub）
- stem 必须以视频 stem 开头（允许扩展语言后缀如 .zh / .en）
- 提取语言后缀（chs/cht/zh/eng/en/jp...）→ Emby/Kodi 标准 (zh/en/ja...)
- copy 到 strm 同目录，重命名为 {strm_basename}.{lang}.{ext}
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

SUBTITLE_EXTENSIONS: frozenset[str] = frozenset({
    ".ass", ".srt", ".vtt", ".ssa", ".sup", ".smi", ".idx", ".sub",
})

# 跳过 > 10MB 字幕 (通常 .sup 图形字幕才会这么大)
MAX_SUBTITLE_SIZE = 10 * 1024 * 1024

# 语言后缀映射 (lower) → ISO 639-1
_LANG_MAP: dict[str, str] = {
    "chs": "zh", "sc": "zh", "zh-cn": "zh", "zh_cn": "zh", "cn": "zh", "zh": "zh",
    "cht": "zh-TW", "tc": "zh-TW", "zh-tw": "zh-TW", "zh_tw": "zh-TW", "tw": "zh-TW",
    "eng": "en", "en": "en", "english": "en",
    "jpn": "ja", "ja": "ja", "jp": "ja", "japanese": "ja",
    "kor": "ko", "ko": "ko", "kr": "ko",
    "fra": "fr", "fre": "fr", "fr": "fr", "french": "fr",
    "ger": "de", "deu": "de", "de": "de",
    "spa": "es", "es": "es",
    "rus": "ru", "ru": "ru",
}

# 一些字幕 stem 里夹杂的语言组合 (chs&eng 之类)
_LANG_TOKEN_RE = re.compile(r"\b([a-zA-Z]{2,7})\b")


@dataclass(slots=True, frozen=True)
class Subtitle:
    src_path: Path
    lang: str          # ISO code (zh / en / ja / und)
    ext: str           # .ass / .srt ...


def find_subtitles(video_path: Path) -> list[Subtitle]:
    """扫视频同目录下匹配的字幕。"""
    video_stem = video_path.stem
    parent = video_path.parent
    if not parent.is_dir():
        return []

    results: list[Subtitle] = []
    for f in parent.iterdir():
        if not f.is_file():
            continue
        ext = f.suffix.lower()
        if ext not in SUBTITLE_EXTENSIONS:
            continue
        if f.stat().st_size > MAX_SUBTITLE_SIZE:
            logger.warning("subtitle too large, skip: {}", f)
            continue
        if not _matches_video(f.stem, video_stem):
            continue
        lang = _detect_lang(f.stem, video_stem)
        results.append(Subtitle(src_path=f, lang=lang, ext=ext))
    return results


def copy_subtitles(subs: list[Subtitle], target_dir: Path, basename: str) -> list[Path]:
    """copy 到 target_dir，重命名为 {basename}.{lang}.{ext}。返回 copy 后的路径列表。"""
    target_dir.mkdir(parents=True, exist_ok=True)
    out: list[Path] = []
    for s in subs:
        if s.lang == "und":
            target_name = f"{basename}{s.ext}"
        else:
            target_name = f"{basename}.{s.lang}{s.ext}"
        target = target_dir / target_name
        try:
            shutil.copy2(s.src_path, target)
            out.append(target)
            logger.info("subtitle copy {} -> {}", s.src_path.name, target_name)
        except Exception as e:
            logger.warning("subtitle copy failed: {} -> {}: {}", s.src_path, target, e)
    return out


# ---------- 私有 ----------

def _matches_video(sub_stem: str, video_stem: str) -> bool:
    """字幕 stem 匹配视频 stem。

    精确匹配 / 以 video_stem 开头（允许后缀如 .zh / .chs / -en）。
    """
    sub_low = sub_stem.lower()
    vid_low = video_stem.lower()
    if sub_low == vid_low:
        return True
    return sub_low.startswith(vid_low) and (len(sub_low) <= len(vid_low) + 25)


def _detect_lang(sub_stem: str, video_stem: str) -> str:
    """从字幕 stem 推断语言。

    去掉 video_stem 前缀后，尝试匹配语言 token。
    """
    if sub_stem.lower() == video_stem.lower():
        return "und"
    suffix = sub_stem[len(video_stem):].lstrip(".-_ ").lower()
    if not suffix:
        return "und"

    # 优先匹配最长的 token
    candidates = _LANG_TOKEN_RE.findall(suffix)
    for token in candidates:
        if token.lower() in _LANG_MAP:
            return _LANG_MAP[token.lower()]

    # 含某些字符直接判定
    if any(k in suffix for k in ("chs", "sc", "zh")):
        return "zh"
    if any(k in suffix for k in ("eng", "en")):
        return "en"
    return "und"
