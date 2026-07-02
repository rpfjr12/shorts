# Free YouTube Shorts Automation Pipeline

Generate unlimited short-form videos (finance facts, psychology facts, history
facts, motivation quotes, AI mini-stories) end-to-end with **only free, local
tools** — no paid APIs, no subscriptions.

Pipeline stages: **script generation → AI images → motion effects → text
overlays → color grading → final MP4 export.**

---

## How it stays 100% free

| Stage          | Tool used                                                                 |
|----------------|----------------------------------------------------------------------------|
| Scripts        | Local JSON templates + Python `random` (optional: local Ollama LLM)        |
| Images         | Local Stable Diffusion (AUTOMATIC1111 API) — falls back to a free procedural placeholder generator (Pillow) if no local SD server is running |
| Motion         | FFmpeg `zoompan` filter (open source, no cost)                             |
| Text overlays  | FFmpeg `drawtext` + free system/bundled fonts                              |
| Color grading  | FFmpeg `eq` filter                                                         |
| Final export   | FFmpeg concat demuxer                                                      |

Nothing in this repo calls a paid API. Everything runs on your own machine.

---

## Installation

### 1. Requirements
- Python 3.10+
- **FFmpeg** (required, free): `sudo apt-get install ffmpeg` (Linux) /
  `brew install ffmpeg` (macOS) / [ffmpeg.org](https://ffmpeg.org) (Windows)
- A free TrueType font for text overlays. The pipeline auto-detects
  `DejaVuSans-Bold` if installed (`sudo apt-get install fonts-dejavu-core`),
  or you can drop any free/OFL-licensed `.ttf` (e.g. "Anton" from Google
  Fonts) into `assets/fonts/Anton-Regular.ttf`.

### 2. Python dependencies
```bash
pip install -r requirements.txt
```

### 3. (Optional but recommended) Local Stable Diffusion
For real AI-generated artwork instead of the procedural placeholder images:
1. Install [AUTOMATIC1111's Stable Diffusion WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui)
   (free, open source, runs on your own GPU/CPU).
2. Launch it with the API flag: `./webui.sh --api` (or `webui-user.bat --api`
   on Windows).
3. Leave it running on `http://127.0.0.1:7860` (default). The pipeline
   auto-detects it — if it's not running, images are generated with the free
   built-in placeholder artist instead, so the pipeline never blocks on this.

### 4. (Optional) Local LLM for richer script text
If you have [Ollama](https://ollama.com) installed and running locally
(`ollama serve`, `ollama pull llama3`), you can swap in
`src/scripts/generator.make_ollama_fill_fn()` for more varied fact text
instead of the built-in local fact bank. Fully free/local, no API key.

---

## Repo structure

```
yt-shorts-pipeline/
├── main.py                     # CLI orchestrator (entry point)
├── requirements.txt
├── config/
│   ├── formats.json            # viral format templates (hook/body/twist)
│   ├── visual_style.json       # SD model + style presets
│   └── colors.json             # viral color palettes
├── src/
│   ├── scripts/generator.py    # unlimited script generation
│   ├── images/generator.py     # AI image generation (local SD / fallback)
│   ├── video/motion.py         # zoom/pan motion effects (FFmpeg)
│   ├── video/text_overlay.py   # text overlays + animation (FFmpeg)
│   └── style/manager.py        # color grading + final export
├── assets/fonts/               # drop free .ttf fonts here
├── data/                       # generated scripts/images/clips (per date)
└── output/shorts/{date}/       # final MP4 Shorts land here
```

---

## Usage

### Run the full pipeline in one command
```bash
python main.py run --format psychology --count 20 --palette neon_blue_purple
```
This runs all 5 stages and writes final videos to
`output/shorts/{date}/short_000.mp4`, `short_001.mp4`, ...

For large batches (up to 100/day), just increase `--count`:
```bash
python main.py run --format finance --count 100 --palette gold_black
```

### Run each stage individually
```bash
# 1. Generate scripts
python main.py generate-scripts --format psychology --count 100

# 2. Generate AI images per script segment
python main.py generate-images --scripts-folder data/scripts/2026-07-02 --out data/images/2026-07-02

# 3. Apply motion effects (zoom/pan)
python main.py apply-motion --images-folder data/images/2026-07-02 --out data/clips/2026-07-02

# 4. Add text overlays
python main.py add-text --clips-folder data/clips/2026-07-02 --scripts-folder data/scripts/2026-07-02 --out data/final_clips/2026-07-02

# 5. Apply color palette + export final Shorts
python main.py apply-style --palette neon_blue_purple --clips-folder data/final_clips/2026-07-02
```

---

## Extending

- **Add a new viral format**: add a new entry to `config/formats.json` with
  `hook_patterns`, `body_patterns`, `body_patterns_2`, `twist_patterns`, and
  any placeholder lists you reference (e.g. `topics`, `years`).
- **Add a new color palette**: add an entry to `config/colors.json` with a
  background/text/accent/outline/highlight and grading values.
- **Add a new visual style preset**: add an entry to
  `config/visual_style.json` under `style_presets`.
- **Swap the fact-filler for a local LLM**: pass
  `fill_fn=script_gen.make_ollama_fill_fn()` into `generate_batch(...)`.

---

## Notes & limits

- This is a starter/reference implementation meant to be extended — the
  built-in fact bank and placeholder art are intentionally simple so the
  pipeline runs end-to-end with zero paid services. Swap in local SD and/or a
  local LLM for production-quality output.
- Vertical video output is 1080x1920 @ 30fps by default (standard Shorts
  format); adjust `OUT_W`/`OUT_H`/`FPS` in `src/video/motion.py` if needed.
- You are responsible for the content you publish, including compliance with
  YouTube's Community Guidelines, monetization/spam policies (e.g. around
  repetitive or mass-produced content), and copyright for any fonts/assets
  you add.
