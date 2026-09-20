"""Is a Live model's function-call path working? Ask it and the control model the same real item.

A trivial call is not enough: on 2026-09-19 a one-enum call succeeded in the same minute a real
probe item failed three times (pre-registration, deviation 7). This replays a registered item, so
the request carries the same prefix and the same tool schema as the study does.

  ./.venv/bin/python scripts/check_live_health.py                 # Extended Thinking vs the control
  ./.venv/bin/python scripts/check_live_health.py gemini-3.8-live # any model against the control
"""
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from livelab.backends import load_dotenv  # noqa: E402
from livelab.probes import CONTROL_MODEL, calls_come_back, prefix_message, variant_setup  # noqa: E402

MODEL = sys.argv[1] if len(sys.argv) > 1 else "gemini-3.8-live-extended-thinking"
VARIANT, ITEM = "B0", "cvd_seal_leak_apcvd__no_o2"      # answered at 14:58, failed 3/3 at 19:55


async def main():
    from google import genai
    load_dotenv()
    client = genai.Client()
    item = next(i for i in json.load(open(ROOT / "data/probes/items.json"))["in_context"]
                if i["item_id"] == ITEM)
    instruction, tools, required = variant_setup(VARIANT)
    text = prefix_message(item["replay_id"], item["k"])

    out = {}
    for model in dict.fromkeys([MODEL, CONTROL_MODEL]):
        connect = (lambda cfg, m=model: client.aio.live.connect(model=m, config=cfg))
        out[model] = await calls_come_back(connect, instruction, tools, required, text, model_id=model,
                                           thinking_level="HIGH" if "extended" in model else None)
        print(f"{model}: {'emits the call' if out[model] else 'NO CALL'}")

    if out[MODEL]:
        print(f"\nHEALTHY. {MODEL} can answer a real item; rerunning the probes is safe.")
    elif out.get(CONTROL_MODEL):
        print(f"\nSTILL BROKEN. {MODEL} emits no call on a request {CONTROL_MODEL} answers.\n"
              "Do not rerun: silence would say nothing about the model. Check again later.")
    else:
        print("\nNeither model answered. That is unusual: check the key, the quota and the network "
              "before reading anything into it.")
    sys.exit(0 if out[MODEL] else 1)


asyncio.run(main())
