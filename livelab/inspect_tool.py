"""Model-directed visual inspection: let the model ask for a magnified region of the photograph.

A single-image test of one harness component (the "inspect in space" half of VISTA, arXiv
2610.02200): the model sees the whole photograph, may call `inspect_region` a few times to get any
rectangle back magnified, and then reports. The control arm runs through the same loop with the
same budget and only the report tool, so the tool is the one difference
(docs/pdms_inspect_preregistration.md).
"""
import asyncio
import base64
import io
import json
from pathlib import Path

from PIL import Image

from .runner_v2 import sha256
from .standard_api import _assistant_turn, build_request, parse, url_for

INSPECT = {
    "name": "inspect_region",
    "description": ("Return a magnified view of one rectangle of the photograph. Coordinates are fractions of "
                    "the photograph's width and height, from 0 (left or top) to 1 (right or bottom)."),
    "parameters": {"type": "object", "properties": {
        "x0": {"type": "number"}, "y0": {"type": "number"}, "x1": {"type": "number"}, "y1": {"type": "number"},
        "reason": {"type": "string", "description": "What you want to check in this region."}},
        "required": ["x0", "y0", "x1", "y1"]},
}
MAGNIFIED_LONG_SIDE = 1024          # pixels; the source photographs are 640 x 480
MIN_SIDE_PX = 16                    # a box smaller than this, in source pixels, is widened to it
REMINDER = "Call {} now."


def crop(path, box, long_side=MAGNIFIED_LONG_SIDE):
    """(JPEG bytes, the pixel box actually used). Fractions are clamped to [0, 1] and ordered;
    a degenerate box is widened around its centre to MIN_SIDE_PX."""
    im = Image.open(path).convert("RGB")
    w, h = im.size
    x0, x1 = sorted(min(max(float(box[k]), 0.0), 1.0) for k in ("x0", "x1"))
    y0, y1 = sorted(min(max(float(box[k]), 0.0), 1.0) for k in ("y0", "y1"))
    px = [round(x0 * w), round(y0 * h), round(x1 * w), round(y1 * h)]
    for lo, hi, size in ((0, 2, w), (1, 3, h)):
        if px[hi] - px[lo] < MIN_SIDE_PX:
            mid = (px[lo] + px[hi]) // 2
            px[lo] = max(0, min(mid - MIN_SIDE_PX // 2, size - MIN_SIDE_PX))
            px[hi] = px[lo] + MIN_SIDE_PX
    region = im.crop(tuple(px))
    scale = long_side / max(region.size)
    region = region.resize((max(1, round(region.size[0] * scale)), max(1, round(region.size[1] * scale))),
                           Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    region.save(buf, "JPEG", quality=92)
    return buf.getvalue(), px


def image_parts(provider, jpeg_bytes):
    b64 = base64.b64encode(jpeg_bytes).decode()
    if provider == "gemini":
        return [{"inlineData": {"mimeType": "image/jpeg", "data": b64}}]
    if provider == "anthropic":
        return [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}}]
    raise ValueError(f"inspection is implemented for gemini and anthropic, not {provider}")


def first_turn(provider, text, photo):
    """The photograph first, then the question, as the other image studies send it."""
    img = image_parts(provider, Path(photo).read_bytes())
    if provider == "gemini":
        return {"role": "user", "parts": img + [{"text": text}]}
    return {"role": "user", "content": img + [{"type": "text", "text": text}]}


def results_turn(provider, calls, outputs):
    """Hand each call its result. `outputs[i]` is (text, jpeg bytes or None)."""
    if provider == "gemini":
        parts = []
        for c, (text, _) in zip(calls, outputs):
            parts.append({"functionResponse": dict({"name": c["name"], "response": {"result": text}},
                                                   **({"id": c["id"]} if c.get("id") else {}))})
        for c, (_, jpeg) in zip(calls, outputs):
            if jpeg is not None:
                parts += image_parts(provider, jpeg)
        return [{"role": "user", "parts": parts}]
    blocks = []
    for c, (text, jpeg) in zip(calls, outputs):
        content = [{"type": "text", "text": text}] + (image_parts(provider, jpeg) if jpeg is not None else [])
        blocks.append({"type": "tool_result", "tool_use_id": c["id"], "content": content})
    return [{"role": "user", "content": blocks}]


def reminder(provider, words):
    if provider == "gemini":
        return {"role": "user", "parts": [{"text": words}]}
    return {"role": "user", "content": words}


def elide_images(obj):
    """A copy safe to store: every base64 image replaced by its length and hash."""
    text = json.dumps(obj)
    out = json.loads(text)

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k == "data" and isinstance(v, str) and len(v) > 200:
                    x[k] = f"<{len(v)} base64 chars, sha256 {sha256(v)[:12]}>"
                else:
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(out)
    return out


async def inspect_item(provider, model, instruction, report, text, photo, *, post, headers, inspect=True,
                       max_inspections=3, max_reminders=2, max_requests=8, clock=None, max_tokens=8192):
    """One inspection. Returns a record: every request (images elided) and response, each region
    asked for, the report, and how collection ended. The control arm passes inspect=False and runs
    through the same loop and budget."""
    loop = asyncio.get_running_loop()
    clock = clock or loop.time
    start = clock()
    now = lambda: round(clock() - start, 3)  # noqa: E731
    tools = [INSPECT, report] if inspect else [report]
    need = report["parameters"]["required"]
    messages = [first_turn(provider, text, photo)]
    requests, responses, regions, usage, reminders = [], [], [], [], []
    answer, status, spoken = None, None, ""
    extra = {"max_tokens": max_tokens} if provider == "anthropic" else {}
    for n in range(max_requests):
        body = build_request(provider, model, instruction, tools, messages, **extra)
        requests.append({"t": now(), "content": elide_images(body)})
        response = await asyncio.to_thread(post, url_for(provider, model), headers, body)
        responses.append({"t": now(), "message": elide_images(response)})
        calls, said, u = parse(provider, response)
        spoken += said
        usage.append({"request": n, "usage": u})
        done = [c for c in calls if c["name"] == report["name"] and all(c["args"].get(f) not in (None, "") for f in need)]
        if done:
            answer = done[0]["args"]
            status = "submitted" if not reminders else "submitted_after_reminder"
            break
        asks = [c for c in calls if c["name"] == INSPECT["name"]]
        if asks:
            outputs = []
            for c in asks:
                if not inspect or len(regions) >= max_inspections:
                    outputs.append((f"No inspections left. Call {report['name']} now.", None))
                    continue
                try:
                    jpeg, px = crop(photo, c["args"])
                except (KeyError, TypeError, ValueError) as exc:
                    outputs.append((f"Could not read that region ({type(exc).__name__}); give x0, y0, x1, y1 "
                                    "as fractions from 0 to 1.", None))
                    continue
                regions.append({"t": now(), "request": n, "args": c["args"], "pixels": px,
                                "sha256": sha256(base64.b64encode(jpeg).decode())})
                left = max_inspections - len(regions)
                outputs.append((f"Magnified region {px} of the {Image.open(photo).size[0]}x"
                                f"{Image.open(photo).size[1]} photograph is attached. Inspections left: {left}.", jpeg))
            messages = messages + _assistant_turn(provider, response, calls) + results_turn(provider, asks, outputs)
            continue
        if len(reminders) < max_reminders:          # no usable call: the fixed reminder, as in runner v2
            words = REMINDER.format(report["name"])
            reminders.append({"t": now(), "request": n, "text": words})
            # A call the model did make (say, a report missing a field) must get its own result first.
            tail = (results_turn(provider, calls, [(words, None)] * len(calls)) if calls
                    else [reminder(provider, words)])
            messages = messages + _assistant_turn(provider, response, calls) + tail
            continue
        status = "ended_without_submission"
        break
    else:
        status = "request_limit"
    return {"provider": provider, "model": model, "inspect_tool": inspect, "max_inspections": max_inspections,
            "status": status, "answer": answer, "regions": regions, "reminders": reminders, "spoken": spoken,
            "usage_messages": usage, "requests": requests, "responses": responses}
