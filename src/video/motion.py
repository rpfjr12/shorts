"""
src/video/motion.py

Turns each static image into a short vertical video clip with a motion effect
(zoom-in, zoom-out, pan-left, pan-right, parallax-style) using FFmpeg's
`zoompan` filter. FFmpeg is free/open-source and must be installed and on PATH.
"""

import subprocess
import random
from pathlib import Path

OUT_W, OUT_H = 1080, 1920
FPS = 30

MOTIONS = ["zoom-in", "zoom-out", "pan-left", "pan-right", "parallax"]


def _zoompan_expr(motion: str, frames: int):
    """Return the zoompan filter's z/x/y expressions for a given motion type."""
    if motion == "zoom-in":
        z = f"min(zoom+0.0015,1.3)"
        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2)"
    elif motion == "zoom-out":
        z = f"if(eq(on,0),1.3,max(zoom-0.0015,1.0))"
        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2)"
    elif motion == "pan-left":
        z = "1.15"
        x = f"if(eq(on,0),iw-iw/zoom,x-2)"
        y = "ih/2-(ih/zoom/2)"
    elif motion == "pan-right":
        z = "1.15"
        x = f"if(eq(on,0),0,x+2)"
        y = "ih/2-(ih/zoom/2)"
    elif motion == "parallax":
        z = "min(zoom+0.001,1.2)"
        x = "iw/2-(iw/zoom/2)+sin(on/20)*5"
        y = "ih/2-(ih/zoom/2)"
    else:
        raise ValueError(f"Unknown motion type: {motion}")
    return z, x, y


def apply_motion_to_image(image_path: Path, out_path: Path, motion: str = None,
                           duration: float = 1.0):
    """Apply a zoom/pan motion effect to a single image, producing a short clip."""
    motion = motion or random.choice(MOTIONS)
    frames = max(1, int(duration * FPS))
    z, x, y = _zoompan_expr(motion, frames)

    filter_str = (
        f"scale={OUT_W * 2}:{OUT_H * 2},"
        f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={OUT_W}x{OUT_H}:fps={FPS},"
        f"format=yuv420p"
    )

    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", str(image_path),
        "-vf", filter_str,
        "-t", str(duration),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        str(out_path),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return out_path


def apply_motion_to_folder(images_folder: Path, out_folder: Path,
                            duration: float = 1.0):
    """Apply motion effects to every image in a script's image subfolder."""
    images_folder = Path(images_folder)
    out_folder = Path(out_folder)
    out_folder.mkdir(parents=True, exist_ok=True)

    written = []
    for img_path in sorted(images_folder.glob("*.png")):
        out_path = out_folder / f"{img_path.stem}.mp4"
        motion = random.choice(MOTIONS)
        apply_motion_to_image(img_path, out_path, motion=motion, duration=duration)
        written.append(out_path)
    return written


def apply_motion_batch(images_root: Path, out_root: Path, duration: float = 1.0):
    """Walk data/images/{date}/<script_stem>/ subfolders and produce
    data/clips/{date}/<script_stem>/*.mp4 for each."""
    images_root = Path(images_root)
    out_root = Path(out_root)
    results = {}
    for script_dir in sorted(p for p in images_root.iterdir() if p.is_dir()):
        out_dir = out_root / script_dir.name
        results[script_dir.name] = apply_motion_to_folder(script_dir, out_dir, duration)
    return results
