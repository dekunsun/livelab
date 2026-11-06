# Poster

AIASci 2026 workshop at AIAS+, San Francisco, 7 November 2026. Portrait, 24 × 36 in, one page.

- `poster.html`: the source. Edit this, never the PDF.
- `poster.pdf`: printed from the source with headless Chrome. Print at 100 %, no scaling, matte paper.
- `preview.png`: a half-scale screenshot of the same page, for a quick look.
- `fig/`: the images the poster uses. The four charts (`rules_poster.png`, `realplant_poster.png`,
  `cascade_poster.png`, `arms_poster.png`) are drawn by `scripts/plot_poster_charts.py` at the width they occupy on the
  poster, in Helvetica Neue, so every label is the body size; values are read from the run records (LiveLab 2.0 from
  ../livelab2/results). The four-errors, twin, abstention-bar, dataset and framework drawings are inline SVG in
  `poster.html`. Logo: University of Pennsylvania, reversed version for the dark band (used under its brand guidelines);
  AI4S.fyi logo. QR codes point to this repository and ai4s.fyi.

Rebuild after editing the source:

```bash
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
cd poster
"$CHROME" --headless=new --disable-gpu --no-pdf-header-footer --virtual-time-budget=15000 --print-to-pdf=poster.pdf "file://$PWD/poster.html"
"$CHROME" --headless=new --disable-gpu --hide-scrollbars --virtual-time-budget=15000 --window-size=2304,3456 --force-device-scale-factor=0.5 --screenshot=preview.png "file://$PWD/poster.html"
```

Layout: three rows, each with its own column split, so both panels in a row end on the same line. Type: Helvetica Neue in three sizes only, 83 px title, 34 px panel titles, 26 px everything else, including chart and diagram labels. If a column width changes, update WIDTH in scripts/plot_poster_charts.py and regenerate.

The PDF must come out as one page; a second page means a row overflowed.
