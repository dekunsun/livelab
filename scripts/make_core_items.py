"""Freeze the LiveLab Core items (docs/core_preregistration.md) into data/core/.

Every item is drawn from livelab.core.SEED, so rerunning this writes byte-identical files.
Committed before any model sees an item.

  ./.venv/bin/python scripts/make_core_items.py
"""
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from livelab.core import build  # noqa: E402


def main():
    items = build(write=True)
    print(f"{len(items)} items -> data/core/")
    print("by role and truth:", dict(Counter((i["role"], i["truth"]) for i in items)))
    print("by family:", dict(Counter(i["family"] for i in items)))


if __name__ == "__main__":
    main()
