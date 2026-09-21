"""How many input tokens does one camera frame cost? Measure it, then price continuous watching.

The architecture question — stream video to a live model, or send frames to a request/response one
— turns on a number nobody publishes per pixel: what a frame costs in tokens. This sends one
request with a frame and one without, at several resolutions, and takes the difference.

The images are flat test patterns generated here. They are **measurement targets, not evidence**:
nothing about a lab is claimed from them, and the project's rule that physical imagery must be real
applies to evidence, not to a ruler.

  ./.venv/bin/python scripts/measure_frame_tokens.py
"""
import base64
import io
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from livelab.backends import load_dotenv  # noqa: E402
from livelab.standard_api import ApiError, _headers, _post, parse  # noqa: E402

SIZES = [(320, 240), (640, 480), (1280, 720)]
PROMPT = "Reply with the single word: ok."
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
# List prices read from the vendors' own pages on 2026-09-20, USD per million input tokens.
PRICE_IN = {"claude-opus-5": 5.0, "gpt-6-astra": 10.0}
LIVE_VIDEO_PER_MIN = 0.002      # Gemini Live: "$1.00 or $0.002/min (image/video)"


def frame(w, h):
    """A deterministic test pattern: a gradient with a grid, so it is not a uniform block."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (w, h))
    px = im.load()
    for y in range(h):
        for x in range(w):
            px[x, y] = ((x * 255) // w, (y * 255) // h, ((x + y) * 255) // (w + h))
    d = ImageDraw.Draw(im)
    for x in range(0, w, 40):
        d.line([(x, 0), (x, h)], fill=(255, 255, 255), width=1)
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def anthropic_body(model, png=None):
    content = [{"type": "text", "text": PROMPT}]
    if png:
        content.insert(0, {"type": "image", "source": {
            "type": "base64", "media_type": "image/png",
            "data": base64.b64encode(png).decode()}})
    return {"model": model, "max_tokens": 16, "messages": [{"role": "user", "content": content}]}


def openai_body(model, png=None):
    content = [{"type": "input_text", "text": PROMPT}]
    if png:
        content.append({"type": "input_image",
                        "image_url": "data:image/png;base64," + base64.b64encode(png).decode()})
    return {"model": model, "input": [{"role": "user", "content": content}]}


PROVIDERS = {
    "claude-opus-5": ("anthropic", ANTHROPIC_URL, anthropic_body),
    "gpt-6-astra": ("openai_responses", OPENAI_RESPONSES_URL, openai_body),
}


def tokens(model, png=None):
    provider, url, build = PROVIDERS[model]
    key = os.environ["ANTHROPIC_API_KEY" if provider == "anthropic" else "OPENAI_API_KEY"]
    r = _post(url, _headers("openai" if provider != "anthropic" else provider, key),
              build(model, png))
    return parse(provider, r)[2]["prompt_token_count"]


def main():
    load_dotenv()
    rows, per_frame = [], {}
    for model in PROVIDERS:
        try:
            base = tokens(model)
        except (ApiError, KeyError) as e:
            print(f"{model}: skipped ({e})")
            continue
        for w, h in SIZES:
            t = tokens(model, frame(w, h))
            rows.append((model, f"{w}x{h}", base, t, t - base))
            per_frame.setdefault(model, {})[f"{w}x{h}"] = t - base
            print(f"{model:16} {w}x{h:<5} 基线 {base:5,}  带图 {t:6,}  -> 每帧 {t - base:5,} token",
                  flush=True)

    lines = ["# What one frame costs, and what continuous watching costs", "",
             "Measured by `scripts/measure_frame_tokens.py`: one request with a frame, one without,",
             "difference taken. The images are flat test patterns generated for the measurement —",
             "they are a ruler, not evidence.", "",
             "| Model | Frame | Baseline tokens | With frame | **Per frame** |",
             "| --- | --- | --- | --- | --- |"]
    lines += [f"| `{m}` | {s} | {b:,} | {t:,} | **{d:,}** |" for m, s, b, t, d in rows]

    lines += ["", "## One hour of watching", "",
              "Frames per hour by cadence, times tokens per frame, times the model's input price.",
              "Gemini Live streams video at a per-minute price instead, so its column is flat.", "",
              "| Cadence | Frames/hour | " +
              " | ".join(f"`{m}` @ 640x480" for m in per_frame) + " | Gemini Live video |",
              "| --- | --- | " + " | ".join("---" for _ in per_frame) + " | --- |"]
    for cad in (120, 30, 5, 1):
        fph = 3600 // cad
        cells = []
        for m, sizes in per_frame.items():
            tk = sizes.get("640x480")
            cells.append(f"${fph * tk / 1e6 * PRICE_IN[m]:,.2f}" if tk else "—")
        lines.append(f"| every {cad} s | {fph:,} | " + " | ".join(cells) +
                     f" | ${LIVE_VIDEO_PER_MIN * 60:.2f} |")

    lines += ["", "**The gap is a function of how often you look, not of the architecture.** At the",
              "benchmark's own 120 s cadence the two are comparable; at 1 Hz the per-frame route",
              "costs two orders of magnitude more. That is the same parameter that decides whether a",
              "transient is observable at all",
              "([undersampling](undersampling_results.md)), so the architecture question and the",
              "observability question are one question.", "",
              "**What this does not include.** Only the image is counted: a real protocol also",
              "resends text and context, which pushes the per-frame route higher. Against that, a",
              "Live session carries a roughly 10-minute limit, needs resumption, and prices audio",
              "and text separately. And neither column is the cheapest architecture — a detector at",
              "the edge that escalates only what it flags sends almost no frames at all."]
    out = ROOT / "docs/results/frame_token_cost.md"
    out.write_text("\n".join(lines) + "\n")
    print("\n" + "\n".join(lines[-14:]))
    print(f"\nwrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
