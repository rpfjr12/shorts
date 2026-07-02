"""
src/style/manager.py

Applies a chosen color palette's grading (saturation/contrast) to each clip
for visual consistency, then concatenates a script's segment clips into a
single final MP4 Short. Uses FFmpeg's `eq` filter (free, built-in).
"""

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COLORS_PATH = ROOT / "config" / "colors.json"


def load_colors():
    with open(COLORS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def grade_clip(clip_path: Path, out_path: Path, saturation: float, contrast: float):
    filter_str = f"eq=saturation={saturation}:contrast={contrast}"
    cmd = [
        "ffmpeg", "-y", "-i", str(clip_path),
        "-vf", filter_str,
        "-c:a", "copy",
        str(out_path),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return out_path


def concat_clips(clip_paths: list[Path], out_path: Path):
    """Concatenate multiple clips into one final MP4 using ffmpeg's concat demuxer."""
    list_file = out_path.with_suffix(".txt")
    with open(list_file, "w", encoding="utf-8") as f:
        for p in clip_paths:
            f.write(f"file '{p.resolve()}'\n")

    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
        "-c", "copy", str(out_path),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    list_file.unlink(missing_ok=True)
    return out_path


def apply_style_to_folder(final_clips_root: Path, palette_name: str,
                           graded_root: Path = None):
    """Grade every clip under data/final_clips/{date}/<script_stem>/ with the
    chosen palette's saturation/contrast values. Writes graded clips to
    graded_root (defaults to overwriting in place under a `_graded` suffix dir
    at the same level)."""
    colors = load_colors()
    if palette_name not in colors:
        raise ValueError(f"Unknown palette '{palette_name}'. Available: {', '.join(colors.keys())}")
    palette = colors[palette_name]

    final_clips_root = Path(final_clips_root)
    graded_root = Path(graded_root) if graded_root else final_clips_root.parent / (
        final_clips_root.name + "_graded"
    )

    results = {}
    for script_dir in sorted(p for p in final_clips_root.iterdir() if p.is_dir()):
        out_dir = graded_root / script_dir.name
        out_dir.mkdir(parents=True, exist_ok=True)
        written = []
        for clip_path in sorted(script_dir.glob("*.mp4")):
            out_path = out_dir / clip_path.name
            grade_clip(
                clip_path, out_path,
                saturation=palette["grade_saturation"],
                contrast=palette["grade_contrast"],
            )
            written.append(out_path)
        results[script_dir.name] = written

    return results, graded_root


def export_final_shorts(graded_root: Path, output_root: Path):
    """Concatenate each script's graded segment clips into one final Short MP4
    at output/shorts/{date}/short_XXX.mp4."""
    graded_root = Path(graded_root)
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    written = []
    for i, script_dir in enumerate(sorted(p for p in graded_root.iterdir() if p.is_dir())):
        clips = sorted(script_dir.glob("*.mp4"))
        if not clips:
            continue
        out_path = output_root / f"short_{i:03d}.mp4"
        concat_clips(clips, out_path)
        written.append(out_path)

    return written
