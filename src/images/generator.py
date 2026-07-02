"""
src/images/generator.py

Generates 1 image per script segment (3-5 images per Short) using a FREE backend:
  1) Local Stable Diffusion via the AUTOMATIC1111 web UI API (http://127.0.0.1:7860),
     if it's running -- fully free, no API key.
  2) If no local SD server is reachable, falls back to procedurally generated
     gradient/placeholder art (Pillow) using the configured color palette, so the
     pipeline still runs end-to-end for free without any extra installs.
"""

import json
import random
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
VISUAL_STYLE_PATH = ROOT / "config" / "visual_style.json"
COLORS_PATH = ROOT / "config" / "colors.json"


def load_visual_style():
    with open(VISUAL_STYLE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_colors():
    with open(COLORS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _build_prompt(segment_text: str, style_preset: dict) -> tuple[str, str]:
    base = style_preset["base_prompt"]
    keywords = ", ".join(style_preset.get("style_keywords", []))
    prompt = f"{base}, {keywords}, depicting: {segment_text}"
    negative = style_preset.get("negative_prompt", "")
    return prompt, negative


def _sd_available(api_url: str) -> bool:
    try:
        r = requests.get(f"{api_url}/sdapi/v1/sd-models", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def _generate_with_automatic1111(prompt, negative, cfg, out_path: Path):
    a1111 = cfg["automatic1111"]
    payload = {
        "prompt": prompt,
        "negative_prompt": negative,
        "sampler_name": a1111.get("sampler_name", "DPM++ 2M Karras"),
        "steps": a1111.get("steps", 22),
        "cfg_scale": a1111.get("cfg_scale", 6.5),
        "width": a1111.get("width", 768),
        "height": a1111.get("height", 1344),
    }
    resp = requests.post(
        f"{a1111['api_url']}{a1111['endpoint']}", json=payload, timeout=120
    )
    resp.raise_for_status()
    data = resp.json()
    import base64

    img_b64 = data["images"][0]
    img_bytes = base64.b64decode(img_b64.split(",", 1)[-1])
    with open(out_path, "wb") as f:
        f.write(img_bytes)


def _generate_placeholder(segment_text: str, palette: dict, out_path: Path,
                           width=768, height=1344):
    """Free, offline fallback: a stylized gradient card with soft shapes, tinted
    using the active color palette, so the visual style stays consistent even
    without a local SD install."""
    bg = palette["background"]
    accent = palette["text_accent"]
    highlight = palette["highlight"]

    img = Image.new("RGB", (width, height), color=bg)
    draw = ImageDraw.Draw(img)

    def hex_to_rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

    accent_rgb = hex_to_rgb(accent)
    highlight_rgb = hex_to_rgb(highlight)

    # soft diagonal gradient
    for y in range(height):
        t = y / height
        r = int(accent_rgb[0] * (1 - t) + highlight_rgb[0] * t * 0.3)
        g = int(accent_rgb[1] * (1 - t) + highlight_rgb[1] * t * 0.3)
        b = int(accent_rgb[2] * (1 - t) + highlight_rgb[2] * t * 0.3)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # random soft circles for visual interest
    for _ in range(6):
        r = random.randint(80, 260)
        x = random.randint(0, width)
        y = random.randint(0, height)
        color = random.choice([accent_rgb, highlight_rgb])
        overlay = Image.new("RGBA", (r * 2, r * 2), (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)
        odraw.ellipse((0, 0, r * 2, r * 2), fill=color + (60,))
        img.paste(overlay, (x - r, y - r), overlay)

    img = img.filter(ImageFilter.GaussianBlur(radius=2))
    img.save(out_path, quality=92)


def generate_images_for_script(script_path: Path, out_dir: Path,
                                style_name: str = None, palette_name: str = "neon_blue_purple"):
    """Generate one image per segment for a single script JSON file."""
    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)

    cfg = load_visual_style()
    colors = load_colors()
    palette = colors.get(palette_name, next(iter(colors.values())))
    style_name = style_name or cfg.get("default_style", "cinematic_neon")
    style_preset = cfg["style_presets"][style_name]

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    api_url = cfg["automatic1111"]["api_url"]
    use_sd = _sd_available(api_url)

    written = []
    for seg in script["segments"]:
        img_path = out_dir / f"{script_path.stem}_{seg['id']}.png"
        if use_sd:
            prompt, negative = _build_prompt(seg["text"], style_preset)
            try:
                _generate_with_automatic1111(prompt, negative, cfg, img_path)
            except Exception:
                # SD call failed mid-run (e.g. OOM) -> fall back for this image only
                _generate_placeholder(seg["text"], palette, img_path)
        else:
            _generate_placeholder(seg["text"], palette, img_path)
        written.append(img_path)

    return written


def generate_batch(scripts_folder: Path, out_dir: Path, style_name: str = None,
                    palette_name: str = "neon_blue_purple"):
    scripts_folder = Path(scripts_folder)
    out_dir = Path(out_dir)
    all_written = {}
    for script_path in sorted(scripts_folder.glob("script_*.json")):
        images = generate_images_for_script(
            script_path, out_dir / script_path.stem, style_name, palette_name
        )
        all_written[script_path.stem] = images
    return all_written
