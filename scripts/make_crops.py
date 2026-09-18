"""Cut the panels listed in data/images/crops.csv out of the fetched figures.

Crops exclude panel letters, overlaid growth parameters and scale-bar text where possible, so
the model sees morphology only. Cropping is the only change made (disclosed per CC BY).
Also writes a labeled contact sheet for checking the crops by eye.
"""
import csv
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
FETCHED = ROOT / "data" / "images" / "fetched"
OUT = ROOT / "data" / "images" / "cvd"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(open(ROOT / "data" / "images" / "crops.csv")))
    tiles = []
    for r in rows:
        src = FETCHED / r["source_id"] / f"fig{r['figure']}.jpg"
        box = tuple(int(r[k]) for k in ("x0", "y0", "x1", "y1"))
        crop = Image.open(src).convert("RGB").crop(box)
        crop.save(OUT / f"{r['image_id']}.png")
        tiles.append((r, crop))
    w, h, cols = 240, 170, 5
    sheet = Image.new("RGB", (cols * w, -(-len(tiles) // cols) * h), "white")
    draw = ImageDraw.Draw(sheet)
    for i, (r, crop) in enumerate(tiles):
        t = crop.copy()
        t.thumbnail((w - 10, h - 28))
        x, y = (i % cols) * w, (i // cols) * h
        sheet.paste(t, (x + 5, y + 22))
        draw.text((x + 5, y + 5), f"{r['image_id']} {r['source_id']}/{r['figure']}{r['panel']} [{r['outcome_class']}]", fill="black")
    sheet.save(FETCHED / "contact_sheet.png")
    print(f"{len(tiles)} crops -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
