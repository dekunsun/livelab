"""Prove the frames reach the model, before believing any result that says they changed nothing.

This study's registered prediction is a null: adding a camera does not restore the judgment. An
image path that silently drops its attachments produces that null perfectly, and the Live backend
reports no token counts, so the usual evidence — the prompt got bigger — is not available.

So the frames are sent with a question only the frames can answer. A model that describes the
glass, the coil and the six views saw them; a model that says it was sent no images did not.

  ./.venv/bin/python scripts/check_frames_arrive.py --backend gemini

Writes results/vision/frames_arrived/<model>.json as evidence beside the study.
"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from livelab.backends import load_dotenv  # noqa: E402
from livelab.probes import run_single_turn  # noqa: E402
from livelab.standard_api import StandardAsker  # noqa: E402
from scripts.run_probes import MODELS, PATIENCE_S, PROVIDER, real_connect  # noqa: E402

VISION = ROOT / "data/vision"
OUT = ROOT / "results/vision/frames_arrived"

DESCRIBE = {
    "name": "describe_attachments",
    "description": "Report what images, if any, were attached to this message.",
    "parameters": {
        "type": "object",
        "properties": {
            "image_count": {"type": "integer",
                            "description": "How many images were attached. 0 if none."},
            "what_is_shown": {"type": "string",
                              "description": "What the images show, in one sentence. Empty if "
                                             "no images were attached."},
            "differences": {"type": "string",
                            "description": "One difference between the first and the last image, "
                                           "or 'none visible'."}},
        "required": ["image_count", "what_is_shown", "differences"]},
}
ASK = ("Images may or may not be attached to this message. Report exactly what you received by "
       "calling describe_attachments. Do not guess: if no image reached you, say 0.")


async def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="gemini", choices=sorted(MODELS))
    ap.add_argument("--item", type=int, default=0, help="index into data/vision/items.json")
    args = ap.parse_args(argv)
    model = MODELS[args.backend]
    it = json.load(open(VISION / "items.json"))["items"][args.item]
    frames = [str(VISION / f) for f in it["frames"]]

    if model in PROVIDER:
        load_dotenv()
        provider = PROVIDER[model]
        env = "ANTHROPIC_API_KEY" if provider == "anthropic" else "OPENAI_API_KEY"
        if not os.environ.get(env):
            sys.exit(f"Set {env} in livelab/.env (never commit it).")
        asker = StandardAsker(provider, model)

        async def ask(images):
            return await asker("", [DESCRIBE], ["describe_attachments"], ASK, images=images)
    else:
        connect = real_connect(model)

        async def ask(images):
            blobs = [("image/jpeg", Path(f).read_bytes()) for f in images]
            return await run_single_turn(connect, "", [DESCRIBE], ["describe_attachments"], ASK,
                                         model_id=model, patience=PATIENCE_S, images=blobs)

    record = {"model": model, "item_id": it["item_id"], "frames": it["frames"]}
    for arm, images in (("frames", frames), ("telemetry", [])):
        res = await ask(images)
        a = [c["args"] for c in res["calls"] if c["name"] == "describe_attachments"][-1]
        record[arm] = a
        print(f"{arm:9} sent {len(images)} -> reported {a.get('image_count')}: "
              f"{str(a.get('what_is_shown'))[:110]}", flush=True)

    sent, seen = len(frames), record["frames"].get("image_count")
    none_arm = record["telemetry"].get("image_count")
    record["verdict"] = ("frames arrive" if seen == sent and none_arm == 0 else "FAILED")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{model}.json").write_text(json.dumps(record, indent=1))
    print(f"\n{record['verdict']}: {seen} of {sent} reported with frames, {none_arm} without.")
    if record["verdict"] == "FAILED":
        sys.exit("the image path is not delivering what it is sent; do not run the study")


if __name__ == "__main__":
    asyncio.run(main())
