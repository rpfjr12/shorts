"""
src/scripts/generator.py

Generates unlimited short-form video scripts using local JSON templates + randomness.
No paid APIs required. Optionally, a local LLM (e.g. via Ollama) can be plugged in
to replace the fact-filler step for higher-quality output — see `use_local_llm`.
"""

import json
import random
import string
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parents[2]
FORMATS_PATH = ROOT / "config" / "formats.json"

# A small local fact bank used to fill {fact_1}/{fact_2}/{misconception}/{takeaway}
# placeholders when no local LLM is configured. Free-text, expandable by editing
# this dict or by wiring in your own generator via `fill_fn` below.
FACT_BANK = {
    "fact_1": [
        "small consistent actions compound faster than big rare ones",
        "your brain treats social rejection like physical pain",
        "the average person only remembers 10% of what they read",
        "most successful people fail more often than they succeed",
        "your habits are shaped more by environment than willpower",
        "the first five minutes of your morning set the tone for your whole day",
        "delaying gratification is one of the strongest predictors of long-term success",
        "the brain can't tell the difference between imagined and real stress",
    ],
    "fact_2": [
        "that's why tiny daily habits beat motivation every time",
        "which is why criticism feels so much heavier than praise",
        "so writing things down forces your brain to actually retain them",
        "which means failure is actually a required step, not an exception",
        "so changing your surroundings is often easier than changing your mindset",
        "that's why high performers protect their morning routine fiercely",
        "so learning to wait is a skill you can actually train",
        "which is why calming your body first can calm your mind too",
    ],
    "misconception": [
        "more effort always means better results",
        "motivation has to come before action",
        "talent matters more than consistency",
        "saving money means cutting out all small purchases",
    ],
    "takeaway": [
        "start small, stay consistent, and let time do the rest",
        "protect your attention like it's your most valuable asset",
        "progress beats perfection every single time",
        "the habit matters more than the intensity",
    ],
    "behavior": [
        "procrastinate", "overthink", "compare yourself to others", "get anxious for no reason"
    ],
}


def load_formats():
    with open(FORMATS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _pick(seq):
    return random.choice(seq)


def _fill_placeholders(template: str, fmt: dict) -> str:
    """Fill {placeholder} tokens in a template string using the fact bank and
    format-specific lists (topics/years/behaviors) when present."""
    out = template
    if "{topic}" in out and "topics" in fmt:
        out = out.replace("{topic}", _pick(fmt["topics"]))
    if "{year}" in out and "years" in fmt:
        out = out.replace("{year}", _pick(fmt["years"]))
    if "{behavior}" in out:
        behaviors = fmt.get("behaviors", FACT_BANK["behavior"])
        out = out.replace("{behavior}", _pick(behaviors))
    for key in ("fact_1", "fact_2", "misconception", "takeaway"):
        token = "{" + key + "}"
        if token in out:
            out = out.replace(token, _pick(FACT_BANK[key]))
    return out


def generate_script(format_name: str, fmt: dict, fill_fn=None) -> dict:
    """Build one script dict with hook/body1/body2/twist/loop segments.

    fill_fn: optional callable(template:str, fmt:dict)->str to override the
    default local fact-bank filler (e.g. to call a local LLM via Ollama).
    """
    filler = fill_fn or _fill_placeholders

    hook = filler(_pick(fmt["hook_patterns"]), fmt)
    body1 = filler(_pick(fmt["body_patterns"]), fmt)
    body2 = filler(_pick(fmt.get("body_patterns_2", fmt["body_patterns"])), fmt)
    twist = filler(_pick(fmt["twist_patterns"]), fmt)
    loop = "Follow for more."  # simple loop-back / CTA ending, always short

    segments = [
        {"id": "hook", "text": hook, "role": "hook"},
        {"id": "body1", "text": body1, "role": "body"},
        {"id": "body2", "text": body2, "role": "body"},
        {"id": "twist", "text": twist, "role": "twist"},
        {"id": "loop", "text": loop, "role": "loop"},
    ]

    return {
        "format": format_name,
        "display_name": fmt.get("display_name", format_name),
        "segments": segments,
    }


def _random_id(n=6):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def generate_batch(format_name: str, count: int, out_dir: Path = None, fill_fn=None):
    """Generate `count` scripts for `format_name` and write them as JSON files to
    data/scripts/{date}/script_XXX.json. Returns list of written file paths."""
    formats = load_formats()
    if format_name not in formats:
        raise ValueError(
            f"Unknown format '{format_name}'. Available: {', '.join(formats.keys())}"
        )
    fmt = formats[format_name]

    if out_dir is None:
        out_dir = ROOT / "data" / "scripts" / date.today().isoformat()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    written = []
    for i in range(count):
        script = generate_script(format_name, fmt, fill_fn=fill_fn)
        script["index"] = i
        script["uid"] = _random_id()
        out_path = out_dir / f"script_{i:03d}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(script, f, indent=2, ensure_ascii=False)
        written.append(out_path)

    return written


# --- Optional local LLM hook (fully free, only if the user runs Ollama locally) ---
def make_ollama_fill_fn(model: str = "llama3", api_url: str = "http://127.0.0.1:11434"):
    """Returns a fill_fn that calls a locally-running Ollama model instead of the
    static fact bank, for more varied output. Requires `requests` and a running
    `ollama serve` — entirely free/local, no API key."""
    import requests

    def fill_fn(template: str, fmt: dict) -> str:
        if "{" not in template:
            return template
        prompt = (
            "Fill in the placeholders in this short-video script line with a "
            "punchy, factual, one-sentence completion. Keep it under 20 words. "
            f"Topic area: {fmt.get('display_name', '')}. Line: {template}\n"
            "Return only the completed line, no quotes, no explanation."
        )
        try:
            resp = requests.post(
                f"{api_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=30,
            )
            resp.raise_for_status()
            text = resp.json().get("response", "").strip()
            return text if text else _fill_placeholders(template, fmt)
        except Exception:
            # Local LLM not available/running -> fall back gracefully
            return _fill_placeholders(template, fmt)

    return fill_fn
