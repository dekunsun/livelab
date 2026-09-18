"""Fetch figure images and captions for the sources in data/images/sources.csv.

Only open-access articles on PMC are fetched, and only the figures listed per source.
Images land in data/images/fetched/<source_id>/ (gitignored); captions go to
data/images/fetched/captions.json so they can be checked for "reproduced from" credits
before any figure enters the manifest.
"""
import csv
import html
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "images" / "fetched"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"


def get(url):
    # curl rather than urllib: it uses the system trust store, which some networks require.
    return subprocess.run(["curl", "-sSfL", "--max-time", "60", "-A", UA, url],
                          check=True, capture_output=True).stdout


def text(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def figures(page):
    """Yield (figure number, image url, caption) for each <figure> on a PMC article page."""
    for block in re.findall(r"<figure[^>]*>(.*?)</figure>", page, flags=re.S):
        label = re.search(r"<h[34][^>]*>(.*?)</h[34]>", block, flags=re.S)
        number = re.search(r"(\d+)", text(label.group(1))) if label else None
        img = re.search(r'src="(https://cdn\.ncbi\.nlm\.nih\.gov/pmc/blobs/[^"]+)"', block)
        caption = re.search(r'<figcaption[^>]*>(.*?)</figcaption>', block, flags=re.S)
        if number and img:
            yield int(number.group(1)), img.group(1), text(caption.group(1)) if caption else ""


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    captions_path = OUT / "captions.json"
    captions = json.loads(captions_path.read_text()) if captions_path.exists() else {}
    with open(ROOT / "data" / "images" / "sources.csv") as f:
        sources = list(csv.DictReader(f))
    for s in sources:
        wanted = {int(n) for n in s["figures"].split(";")}
        page = get(f"https://pmc.ncbi.nlm.nih.gov/articles/{s['pmcid']}/").decode("utf-8", "replace")
        found = set()
        for number, url, caption in figures(page):
            if number not in wanted or number in found:
                continue
            found.add(number)
            dest = OUT / s["source_id"] / f"fig{number}{Path(url).suffix}"
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                dest.write_bytes(get(url))
                time.sleep(1)
            captions[f"{s['source_id']}/fig{number}"] = {
                "doi": s["doi"], "license": s["license"], "url": url,
                "file": str(dest.relative_to(ROOT)), "bytes": dest.stat().st_size, "caption": caption,
            }
        missing = wanted - found
        print(f"{s['source_id']} {s['pmcid']}: got {sorted(found)}" + (f", MISSING {sorted(missing)}" if missing else ""))
        time.sleep(1)
    captions_path.write_text(json.dumps(captions, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
