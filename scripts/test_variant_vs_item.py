"""Is the silent failure tied to the item or to the variant? The size test could not tell.

The registered size test (deviation 7) compared a working request with a failing one, but they
differed in BOTH the item and the variant, so it settled only that size is not the cause. This
crosses two items with three variants at one sitting; the control model runs every request too.

  ./.venv/bin/python scripts/test_variant_vs_item.py
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
ITEMS = ["cvd_seal_leak_apcvd__no_o2",              # answered on 2026-09-19 and again this morning
         "cvd_exhaust_blockage_lpcvd_v2__no_o2"]    # silent through 6 cooldowns overnight


async def main():
    from google import genai
    load_dotenv()
    client = genai.Client()
    items = {i["item_id"]: i for i in json.load(open(ROOT / "data/probes/items.json"))["in_context"]}
    out = []
    for item_id in ITEMS:
        for variant in ("B0", "B1", "B2"):
            instruction, tools, required = variant_setup(variant)
            text = prefix_message(items[item_id]["replay_id"], items[item_id]["k"])
            row = {"item": item_id, "variant": variant}
            for model in (MODEL, CONTROL_MODEL):
                connect = (lambda cfg, m=model: client.aio.live.connect(model=m, config=cfg))
                t0 = time.time()
                row[model] = await calls_come_back(connect, instruction, tools, required, text, model_id=model,
                                                   thinking_level="HIGH" if "extended" in model else None)
                row[model + "_s"] = round(time.time() - t0, 1)
            out.append(row)
            print(f"{time.strftime('%H:%M:%S')}  {item_id:38} {variant}   "
                  f"ET {'CALL' if row[MODEL] else 'none':4} ({row[MODEL + '_s']:6.1f}s)   "
                  f"control {'CALL' if row[CONTROL_MODEL] else 'none'}", flush=True)
    path = ROOT / "results/diagnostics/variant_vs_item.json"
    path.write_text(json.dumps(out, indent=1))
    print(f"\nsaved {path}")


asyncio.run(main())
