"""The registered test from deviation 7: is the silent failure driven by request size?

Three requests at the same minute, all to the Extended Thinking model, each also run against the
control model. Only whether a function call comes back is recorded, never what it said.

  A  the health-check item, 25 events   - known to have answered before
  B  the item that failed all night, 25 events
  C  the same failing item, 3 events    - same tools, same instruction, a short prefix

  A works and B fails        -> request-specific, not a quota the clock will fix
  C works and B fails        -> size-driven, which is what a token-metered quota looks like
  A, B and C all fail        -> the whole path is down for this model right now

  ./.venv/bin/python scripts/check_size_threshold.py
"""
import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from livelab.backends import load_dotenv  # noqa: E402
from livelab.probes import CONTROL_MODEL, calls_come_back, prefix_message, variant_setup  # noqa: E402

MODEL = "gemini-3.8-live-extended-thinking"
CASES = [
    ("A  health-check item, 25 events", "B0", "cvd_seal_leak_apcvd__no_o2", 24),
    ("B  item that failed all night, 25 events", "B2", "cvd_exhaust_blockage_lpcvd_v2__no_o2", 24),
    ("C  same failing item, 3 events", "B2", "cvd_exhaust_blockage_lpcvd_v2__no_o2", 2),
]


async def main():
    from google import genai
    load_dotenv()
    client = genai.Client()
    items = {i["item_id"]: i for i in json.load(open(ROOT / "data/probes/items.json"))["in_context"]}
    out = []
    for label, variant, item_id, k in CASES:
        instruction, tools, required = variant_setup(variant)
        text = prefix_message(items[item_id]["replay_id"], k)
        row = {"case": label, "prompt_chars": len(text)}
        for model in (MODEL, CONTROL_MODEL):
            connect = (lambda cfg, m=model: client.aio.live.connect(model=m, config=cfg))
            t0 = time.time()
            row[model] = await calls_come_back(connect, instruction, tools, required, text, model_id=model,
                                               thinking_level="HIGH" if "extended" in model else None)
            row[model + "_s"] = round(time.time() - t0, 1)
        out.append(row)
        print(f"{time.strftime('%H:%M:%S')}  {label:44} {len(text):6,} chars   "
              f"ET {'CALL' if row[MODEL] else 'none':4} ({row[MODEL + '_s']:5.1f}s)   "
              f"control {'CALL' if row[CONTROL_MODEL] else 'none':4}", flush=True)
    path = ROOT / "results/diagnostics/size_threshold.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1))
    print(f"\nsaved {path}")


if __name__ == "__main__":      # never at import: pytest once collected this and called the API
    asyncio.run(main())
