"""Run the system-state test (docs/system_state_preregistration.md).

The probe's 38 in-context items under B0, with nothing added (V0), a per-event system sentence
(V1), or the same fact as a field in the last event (V2). The fact comes from the truth file's
`missing_required_sensors`, which the benchmark computes from the manifest and the stage.

  ./.venv/bin/python scripts/run_system_state.py --backend opus-5
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
from livelab.probes import SENSOR_WORDS, prefix_message, run_single_turn, variant_setup  # noqa: E402
from livelab.standard_api import StandardAsker  # noqa: E402
from scripts.run_probes import MODELS, PATIENCE_S, PROVIDER, real_connect  # noqa: E402

OUT = ROOT / "results/system_state"
ARMS = ("V0", "V1", "V2")
REQUIRED = ("thermocouple", "pressure_gauge", "o2_exhaust")    # the growth stage, every item


def missing_for(item):
    rows = [json.loads(l) for l in open(ROOT / f"data/truth/{item['replay_id']}.jsonl")]
    row = rows[int(item["k"])]
    assert row["stage"] == "growth", item["item_id"]
    return list(row["missing_required_sensors"])


def words(sensors):
    names = [f"the {SENSOR_WORDS[s]}" for s in sensors]
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def sentence(missing):
    if not missing:
        return "System check for this event: every sensor the growth stage requires is installed."
    verb = "is" if len(missing) == 1 else "are"
    return (f"System check for this event: the growth stage requires {words(REQUIRED)}; "
            f"{words(missing)} {verb} not installed, so the atmosphere cannot be verified with the "
            "installed sensors.")


def text_for(item, arm):
    text = prefix_message(item["replay_id"], item["k"])
    if arm == "V0":
        return text
    missing = missing_for(item)
    if arm == "V1":
        return text + "\n" + sentence(missing)
    lines = text.splitlines()
    last = json.loads(lines[-1])
    assert json.dumps(last, separators=(",", ":")) == lines[-1], "re-serialising changed the event"
    last["system_check"] = {"stage": "growth", "required_not_installed": missing,
                            "verifiable": not missing}
    return "\n".join(lines[:-1] + [json.dumps(last, separators=(",", ":"))])


async def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", required=True, choices=sorted(MODELS))
    ap.add_argument("--arm", nargs="*", default=list(ARMS), choices=ARMS)
    args = ap.parse_args(argv)
    model = MODELS[args.backend]
    items = json.load(open(ROOT / "data/probes/items.json"))["in_context"]
    instruction, tools, required = variant_setup("B0")
    if model in PROVIDER:
        load_dotenv()
        provider = PROVIDER[model]
        env = "ANTHROPIC_API_KEY" if provider == "anthropic" else "OPENAI_API_KEY"
        if not os.environ.get(env):
            sys.exit(f"Set {env} in livelab/.env (never commit it).")
        asker = StandardAsker(provider, model)
        ask = lambda text: asker(instruction, tools, required, text)        # noqa: E731
    else:
        connect = real_connect(model)
        ask = lambda text: run_single_turn(connect, instruction, tools, required, text,  # noqa: E731
                                           model_id=model, patience=PATIENCE_S)
    # Interleave the arms item by item, so no arm is collected in different hours from another.
    for it in items:
        for arm in args.arm:
            dest = OUT / model / arm / f"{it['item_id']}.json"
            if dest.exists():
                continue
            text = text_for(it, arm)
            res = None
            for attempt in range(3):
                try:
                    got = await asyncio.wait_for(ask(text), 600)
                except Exception as exc:  # noqa: BLE001
                    print(f"  {arm} {it['item_id']} attempt {attempt + 1} failed: "
                          f"{type(exc).__name__}: {str(exc)[:100]}", flush=True)
                    await asyncio.sleep(20 * (attempt + 1))
                    continue
                if all(r in {c["name"] for c in got["calls"]} for r in required):
                    res = got
                    break
                print(f"  {arm} {it['item_id']} attempt {attempt + 1}: no answer", flush=True)
            if res is None:
                continue
            a = [c["args"] for c in res["calls"] if c["name"] == "report_assessment"][-1]
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps({"model": model, "arm": arm, "item_id": it["item_id"],
                                        "set": it["set"], "missing": missing_for(it),
                                        "truth": it["truth_execution_state"],
                                        "said": a.get("execution_state"), "text_tail": text[-400:],
                                        "calls": res["calls"], "usage": res.get("usage")}, indent=1))
            print(f"[{arm}] {it['item_id'][:44]:44} {it['set']} -> {a.get('execution_state')}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
