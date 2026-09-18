"""Run an observer over frozen replays and score it.

  # offline, no API key needed:
  python scripts/run_benchmark.py --backend mock:observability_aware --arm C-full
  # a short, cheap smoke test against Gemini (needs GEMINI_API_KEY in .env):
  python scripts/run_benchmark.py --backend gemini --arm A --replays 5787ea699858 --max-events 5

Audit logs go to runs/ (gitignored). Scores are printed; nothing is written to docs/ from here.
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from livelab.backends import GeminiLiveBackend, MockBackend  # noqa: E402
from livelab.harness import run_replay  # noqa: E402
from livelab.mock_models import MOCKS  # noqa: E402
from livelab.prompting import ARMS  # noqa: E402
from livelab.scoring import score_runs  # noqa: E402


RETRIES, RETRY_WAIT_S = 2, 60


def load_jsonl(path):
    return [json.loads(line) for line in open(path)]


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", required=True, help="gemini | gemini-extended | mock:<name>")
    ap.add_argument("--arm", default="C-full", choices=sorted(ARMS))
    ap.add_argument("--replays", nargs="*", help="replay ids (default: all)")
    ap.add_argument("--seeds", type=int, nargs="*", default=[0])
    ap.add_argument("--max-events", type=int, help="truncate each replay (smoke tests only; not scored)")
    ap.add_argument("--out", default=str(ROOT / "runs"))
    args = ap.parse_args()

    index = json.load(open(ROOT / "data/replays/INDEX.json"))
    replay_ids = args.replays or list(index)
    all_reports = {}
    for rid in replay_ids:
        for seed in args.seeds:
            events = load_jsonl(ROOT / f"data/replays/{rid}.jsonl")
            if args.backend.startswith("mock:"):
                mock = next(m for m in MOCKS if m.name == args.backend[5:])
                if mock.name == "oracle":
                    sys.exit("oracle needs ground truth; it is only for scripts/score_mocks.py")
                backend = MockBackend(mock, events)
            else:
                model = {"gemini": "gemini-3.8-live", "gemini-extended": "gemini-3.8-live-extended-thinking"}[args.backend]
                backend = GeminiLiveBackend(model)
            out_dir = Path(args.out) / backend.model_id.replace(":", "_") / args.arm
            # Free tier: quota and rate limits are the risk. A failed replay restarts from the first
            # event after a pause, so every scored run saw the complete, identical evidence stream.
            for attempt in range(RETRIES + 1):
                try:
                    reports, log = await run_replay(backend, rid, args.arm, seed, out_dir, max_events=args.max_events)
                    break
                except Exception as exc:  # noqa: BLE001 - report any API failure and retry
                    print(f"{rid} seed={seed} attempt {attempt + 1} failed: {type(exc).__name__}: {str(exc)[:200]}")
                    if attempt == RETRIES:
                        reports = None
                        break
                    await asyncio.sleep(RETRY_WAIT_S * (attempt + 1))
                    if not args.backend.startswith("mock:"):
                        backend = GeminiLiveBackend(backend.model_id)
            if reports is None:
                print(f"{rid} seed={seed} INCOMPLETE: not scored")
                continue
            print(f"{rid} seed={seed} -> {log.relative_to(ROOT) if log.is_relative_to(ROOT) else log}")
            if args.max_events is None and seed == args.seeds[0]:
                all_reports[rid] = reports      # scores use the first seed; repeats are for variance
    if all_reports:
        card = score_runs(all_reports, index, lambda r: load_jsonl(ROOT / f"data/truth/{r}.jsonl"))
        for name, v in card.items():
            shown = f"{v[0]:.2f}  [{v[1]:.2f}, {v[2]:.2f}]" if isinstance(v, tuple) and len(v) == 3 else v
            print(f"  {name:24} {shown}")


if __name__ == "__main__":
    asyncio.run(main())
