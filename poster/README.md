# Poster

AIASci 2026 workshop at AIAS+, San Francisco, 7 November 2026. Portrait, 24 × 36 in, one page.

- `poster.html`: the source. Edit this, never the PDF.
- `poster.pdf`: printed from the source with headless Chrome. Print at 100 %, no scaling, matte paper.
- `preview.png`: a half-scale screenshot of the same page, for a quick look.
- `fig/`: the images the poster uses, generated from the run records: `hero_poster.png`
  (`scripts/plot_hero.py ... en poster`), `realdata_ci_poster.png` (`scripts/plot_realdata_ci.py ... poster`),
  `cascade_lpcvd.png` (`scripts/plot_cascade.py`); `arms_hits.png` comes from the LiveLab 2.0 repository. The
  abstention bars, the four-errors diagram and the framework diagram are inline SVG in `poster.html`; the bar values
  come from `scripts/plot_realdata_ci.counts()` (corrected rerun). Logo: University of Pennsylvania, reversed version
  for the dark band (used under its brand guidelines). QR codes point to this repository and ai4s.fyi.

Rebuild after editing the source:

```bash
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
cd poster
"$CHROME" --headless=new --disable-gpu --no-pdf-header-footer --virtual-time-budget=15000 --print-to-pdf=poster.pdf "file://$PWD/poster.html"
"$CHROME" --headless=new --disable-gpu --hide-scrollbars --virtual-time-budget=15000 --window-size=2304,3456 --force-device-scale-factor=0.5 --screenshot=preview.png "file://$PWD/poster.html"
```

Layout: three rows, each with its own column split, so both panels in a row end on the same line. Type uses three sizes only (title, headings, body). The three diagrams are inline SVG drawn at their rendered width, so their labels match the body size.

The PDF must come out as one page; a second page means a row overflowed.
