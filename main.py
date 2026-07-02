#!/usr/bin/env python3
"""
main.py — Free, automated YouTube Shorts pipeline orchestrator.

VIRAL OPTIMIZATION CHANGES (SAFE):
- Default duration increased from 1.0 → 1.8 seconds for better readability.
- No logic changed. No pipeline behavior changed. No imports changed.
- All functions preserved exactly as-is.
"""

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.scripts import generator as script_gen
from src.images import generator as image_gen
from src.video import motion as motion_mod
from src.video import text_overlay as text_mod
from src.style import manager as style_mod

ROOT = Path(__file__).resolve().parent


def today_dir(base: str) -> Path:
    return ROOT / base / date.today().isoformat()


def cmd_generate_scripts(args):
    out_dir = Path(args.out) if args.out else today_dir("data/scripts")
    written = script_gen.generate_batch(args.format, args.count, out_dir=out_dir)
    print(f"[generate-scripts] Wrote {len(written)} scripts to {out_dir}")
    return out_dir


def cmd_generate_images(args):
    scripts_folder = Path(args.scripts_folder)
    out_dir = Path(args.out) if args.out else today_dir("data/images")
    results = image_gen.generate_batch(
        scripts_folder, out_dir, style_name=args.style, palette_name=args.palette
    )
    total = sum(len(v) for v in results.values())
    print(f"[generate-images] Wrote {total} images across {len(results)} scripts to {out_dir}")
    return out_dir


def cmd_apply_motion(args):
    images_folder = Path(args.images_folder)
    out_dir = Path(args.out) if args.out else today_dir("data/clips")
    # duration now defaults to 1.8s for viral readability
    results = motion_mod.apply_motion_batch(images_folder, out_dir, duration=args.duration)
    total = sum(len(v) for v in results.values())
    print(f"[apply-motion] Wrote {total} motion clips across {len(results)} scripts to {out_dir}")
    return out_dir


def cmd_add_text(args):
    clips_folder = Path(args.clips_folder)
    scripts_folder = Path(args.scripts_folder)
    out_dir = Path(args.out) if args.out else today_dir("data/final_clips")
    results = text_mod.add_text_batch(clips_folder, scripts_folder, out_dir)
    total = sum(len(v) for v in results.values())
    print(f"[add-text] Wrote {total} text-overlaid clips across {len(results)} scripts to {out_dir}")
    return out_dir


def cmd_apply_style(args):
    clips_folder = Path(args.clips_folder)
    graded_results, graded_root = style_mod.apply_style_to_folder(clips_folder, args.palette)
    total = sum(len(v) for v in graded_results.values())
    print(f"[apply-style] Graded {total} clips with palette '{args.palette}' -> {graded_root}")

    out_dir = Path(args.out) if args.out else (ROOT / "output" / "shorts" / date.today().isoformat())
    finals = style_mod.export_final_shorts(graded_root, out_dir)
    print(f"[apply-style] Exported {len(finals)} final Shorts to {out_dir}")
    return out_dir


def cmd_run(args):
    print(f"=== Running full pipeline: format={args.format} count={args.count} palette={args.palette} ===")

    scripts_dir = cmd_generate_scripts(argparse.Namespace(
        format=args.format, count=args.count, out=None
    ))
    images_dir = cmd_generate_images(argparse.Namespace(
        scripts_folder=scripts_dir, out=None, style=args.style, palette=args.palette
    ))
    clips_dir = cmd_apply_motion(argparse.Namespace(
        images_folder=images_dir, out=None, duration=args.duration
    ))
    final_clips_dir = cmd_add_text(argparse.Namespace(
        clips_folder=clips_dir, scripts_folder=scripts_dir, out=None
    ))
    output_dir = cmd_apply_style(argparse.Namespace(
        clips_folder=final_clips_dir, palette=args.palette, out=None
    ))

    print(f"=== Done. Final Shorts in: {output_dir} ===")


def build_parser():
    parser = argparse.ArgumentParser(description="Free automated YouTube Shorts pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    p1 = sub.add_parser("generate-scripts", help="Generate N scripts for a format")
    p1.add_argument("--format", required=True, help="Format name from config/formats.json")
    p1.add_argument("--count", type=int, default=10)
    p1.add_argument("--out", default=None)
    p1.set_defaults(func=cmd_generate_scripts)

    p2 = sub.add_parser("generate-images", help="Generate images for each script segment")
    p2.add_argument("--scripts-folder", required=True)
    p2.add_argument("--out", default=None)
    p2.add_argument("--style", default=None, help="Style preset name from config/visual_style.json")
    p2.add_argument("--palette", default="neon_blue_purple")
    p2.set_defaults(func=cmd_generate_images)

    p3 = sub.add_parser("apply-motion", help="Apply zoom/pan motion effects to images")
    p3.add_argument("--images-folder", required=True)
    p3.add_argument("--out", default=None)
    # VIRAL UPGRADE: duration default changed from 1.0 → 1.8
    p3.add_argument("--duration", type=float, default=1.8)
    p3.set_defaults(func=cmd_apply_motion)

    p4 = sub.add_parser("add-text", help="Overlay script text onto motion clips")
    p4.add_argument("--clips-folder", required=True)
    p4.add_argument("--scripts-folder", required=True)
    p4.add_argument("--out", default=None)
    p4.set_defaults(func=cmd_add_text)

    p5 = sub.add_parser("apply-style", help="Color-grade clips and export final Shorts")
    p5.add_argument("--palette", required=True)
    p5.add_argument("--clips-folder", required=True)
    p5.add_argument("--out", default=None)
    p5.set_defaults(func=cmd_apply_style)

    p6 = sub.add_parser("run", help="Run the full pipeline end-to-end")
    p6.add_argument("--format", required=True)
    p6.add_argument("--count", type=int, default=20)
    p6.add_argument("--palette", default="neon_blue_purple")
    p6.add_argument("--style", default=None)
    # VIRAL UPGRADE: duration default changed from 1.0 → 1.8
    p6.add_argument("--duration", type=float, default=1.8)
    p6.set_defaults(func=cmd_run)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
