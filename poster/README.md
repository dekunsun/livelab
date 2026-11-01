# Poster

AIASci 2026 workshop at AIAS+, San Francisco, 7 November 2026. Portrait, 36 × 48 in, one page.

- `poster.html`: the source. Edit this, never the PDF.
- `poster.pdf`: printed from the source with headless Chrome. Print at 100 %, no scaling, matte paper.
- `preview.png`: a half-scale screenshot of the same page, for a quick look.
- `fig/`: the figures the poster uses. The result figures (`tradeoff_poster.png`, `realdata_ci_poster.png`,
  `cascade_lpcvd.png`, `probe.png`) are generated from the run records by the scripts in `scripts/`
  (`plot_tradeoff.py ... poster`, `plot_realdata_ci.py ... poster`, `plot_cascade.py`, `plot_results.py`);
  `arms_hits.png` comes from the LiveLab 2.0 repository. Logos: University of Pennsylvania (used under
  its brand guidelines) and ai4s.fyi. QR codes point to this repository, ai4s.fyi and x.com/gloria_sun.

Rebuild after editing the source:

```bash
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
cd poster
"$CHROME" --headless=new --disable-gpu --no-pdf-header-footer --virtual-time-budget=15000 --print-to-pdf=poster.pdf "file://$PWD/poster.html"
"$CHROME" --headless=new --disable-gpu --hide-scrollbars --virtual-time-budget=15000 --window-size=3456,4608 --force-device-scale-factor=0.5 --screenshot=preview.png "file://$PWD/poster.html"
```

The PDF must come out as one page; a second page means a column overflowed.
