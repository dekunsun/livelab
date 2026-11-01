#!/usr/bin/env bash
# Print docs/preprint/preprint.html to docs/preprint/preprint.pdf (A4) with headless Chrome.
set -euo pipefail
cd "$(dirname "$0")"
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
"$CHROME" --headless=new --disable-gpu --no-pdf-header-footer --virtual-time-budget=15000 \
  --print-to-pdf=preprint.pdf "file://$PWD/preprint.html"
echo "wrote $(pwd)/preprint.pdf"
