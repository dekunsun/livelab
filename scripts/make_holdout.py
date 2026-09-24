"""Build a private held-out copy of LiveLab Core: the same families, counts and rules as the public
80 items, drawn from a seed that is never published.

The public items are in the repository and may one day be in a model's training data. The held-out
set is for formal qualification only; it and its seed live in data/core_holdout/, which git ignores.

  ./.venv/bin/python scripts/make_holdout.py            # draws a random seed once, then reuses it

Item ids and replay ids repeat the public names (a replay id hashes the episode name and condition),
while the runs themselves differ: other seeds, onsets and events. Results on the held-out set must
therefore go to their own directory (run_core_v2.py --out results/core_holdout/), never beside the
public results.
"""
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import livelab.core as core  # noqa: E402

HOLDOUT = ROOT / "data" / "core_holdout"


def main():
    HOLDOUT.mkdir(parents=True, exist_ok=True)
    seed_file = HOLDOUT / "SEED"
    if not seed_file.exists():
        seed_file.write_text(str(secrets.randbelow(10**9)))
    seed = int(seed_file.read_text())
    if seed == core.SEED:
        sys.exit("The held-out seed equals the public seed; delete data/core_holdout/SEED and rerun.")
    public_data, public_seed = core.DATA, core.SEED
    core.DATA, core.SEED = HOLDOUT, seed
    try:
        items = core.build(write=True)
    finally:
        core.DATA, core.SEED = public_data, public_seed
    print(f"{len(items)} held-out items written to {HOLDOUT.relative_to(ROOT)} (seed kept there, not published)")


if __name__ == "__main__":
    main()
