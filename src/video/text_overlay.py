"""
src/video/text_overlay.py

Overlays script text on top of each motion clip using FFmpeg's `drawtext`
filter (free, no ImageMagick dependency). Adds a fade-in and a subtle
slide-up for a simple, punchy animation, plus an outline/stroke for
readability on any background.
"""

import json
import subprocess
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_BUNDLED_FONT = ROOT / "assets" / "fonts" / "Anton-Regular.ttf"

# Common free system fonts to fall back to if no bundled font is present
# (e.g. on a fresh Linux box with fonts-dejavu-core installed, which is free
# and usually pre-installed or a one-line apt-get away).
_SYSTEM_FONT_FALLBACKS = [
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
]


def _resolve_default_font() -> Path:
    if _BUNDLED_FONT.exists():
        return _BUNDLED_FONT
    for fp in _SYSTEM_FONT_FALLBACKS:
        if fp.exists():
            return fp
    # Last resort: return the bundled path anyway; ffmpeg will error with a
    # clear "no such file" message telling the user to add a font.
    return _BUNDLED_FONT


DEFAULT_FONT = _resolve_default_font()


def _escape_text(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\u2019")
        .replace("%", "\\%")
    )


def _wrap(text: str, width: int = 22) -> str:
    return "\n".join(textwrap.wrap(text, width=width))


def build_drawtext_filter(text: str, font_path: Path, fontsize: int = 64,
                           fontcolor: str = "white", outline_color: str = "black",
                           duration: float = 1.0):
    """Build a drawtext filter string with a fade-in + slide-up animation and
    an outline/stroke around the text for contrast against any image."""
    safe_text = _escape_text(_wrap(text))
    fade_in = 0.25  # seconds
    slide_frames = "min(1,t/0.3)"  # 0->1 over 0.3s, used to ease the y-position

    # y position slides up from y+40 to final y over the first 0.3s
    y_expr = f"(h*0.72)-(1-{slide_frames})*40"
    alpha_expr = f"if(lt(t,{fade_in}),t/{fade_in},1)"

    return (
        f"drawtext=fontfile='{font_path}':text='{safe_text}':"
        f"fontsize={fontsize}:fontcolor={fontcolor}:"
        f"borderw=4:bordercolor={outline_color}:"
        f"x=(w-text_w)/2:y='{y_expr}':"
        f"alpha='{alpha_expr}':line_spacing=10"
    )


def add_text_to_clip(clip_path: Path, text: str, out_path: Path,
                      font_path: Path = None, fontsize: int = 64,
                      fontcolor: str = "white", outline_color: str = "black"):
    font_path = font_path or DEFAULT_FONT
    filter_str = build_drawtext_filter(
        text, font_path, fontsize=fontsize, fontcolor=fontcolor,
        outline_color=outline_color,
    )
    cmd = [
        "ffmpeg", "-y", "-i", str(clip_path),
        "-vf", filter_str,
        "-c:a", "copy",
        str(out_path),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return out_path


def add_text_batch(clips_root: Path, scripts_folder: Path, out_root: Path,
                    fontcolor: str = "white", outline_color: str = "black"):
    """For each script, read its segments and overlay matching text onto the
    corresponding clip (matched by segment id in the filename)."""
    clips_root = Path(clips_root)
    scripts_folder = Path(scripts_folder)
    out_root = Path(out_root)
    results = {}

    for script_path in sorted(scripts_folder.glob("script_*.json")):
        with open(script_path, "r", encoding="utf-8") as f:
            script = json.load(f)
        stem = script_path.stem
        clip_dir = clips_root / stem
        out_dir = out_root / stem
        out_dir.mkdir(parents=True, exist_ok=True)
        if not clip_dir.exists():
            continue

        written = []
        for seg in script["segments"]:
            clip_path = clip_dir / f"{stem}_{seg['id']}.mp4"
            if not clip_path.exists():
                continue
            out_path = out_dir / f"{stem}_{seg['id']}.mp4"
            add_text_to_clip(
                clip_path, seg["text"], out_path,
                fontcolor=fontcolor, outline_color=outline_color,
            )
            written.append(out_path)
        results[stem] = written

    return results
