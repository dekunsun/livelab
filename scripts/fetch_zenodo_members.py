"""Pull individual members out of a Zenodo zip over HTTP, without downloading the archive.

The batch distillation record's image archive is 38 GB and its audio archive is 47 GB, and this
project needs the Operation-phase media of about twenty experiments. Zenodo serves byte ranges
(`accept-ranges: bytes`), and Python's `zipfile` works on any seekable file object — so the
archive is opened in place and only the wanted members are transferred.

Nothing is committed: data/external/ is gitignored. Licence and attribution:
data/realdata/ATTRIBUTION.md (CC BY 4.0).

  ./.venv/bin/python scripts/fetch_zenodo_members.py --list
  ./.venv/bin/python scripts/fetch_zenodo_members.py --archive image --phase Operation
"""
import argparse
import http.client
import io
import json
import ssl
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from livelab.standard_api import _CTX  # noqa: E402  - certifi bundle; urllib here verifies nothing
DATA = ROOT / "data/external/batch_distillation"
BASE = "https://zenodo.org/api/records/22250958/files"
ARCHIVES = {"image": "12_Batch_Distillation_Plant_M-202210_Image.zip",
            "audio": "11_Batch_Distillation_Plant_M-202210_Audio.zip"}
CHUNK = 8 << 20        # each range is a fresh HTTPS connection; at 1 MB the handshakes dominated
TIMEOUT_S = 120        # without this urllib waits on a dead socket forever
RETRIES = 6
BACKOFF_S = 5


class HttpFile(io.RawIOBase):
    """A seekable read-only file backed by HTTP range requests, with a one-chunk cache.

    zipfile seeks to the end for the central directory, then to each member's local header, so a
    naive implementation issues hundreds of tiny requests; caching one chunk collapses the reads
    that zipfile makes back to back.
    """

    def __init__(self, url):
        self.url, self.pos = url, 0
        self._cache = (0, b"")
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), context=_CTX,
                                   timeout=TIMEOUT_S) as r:
            self.size = int(r.headers["content-length"])
        self.requests = self.bytes_read = 0

    def _fetch(self, start, length):
        """One range request, retried.

        A multi-gigabyte fetch issues thousands of these, so a single timed-out connection is a
        matter of when, not whether. The first attempt at this took two hours and then died on one
        `Errno 60` with nothing to show for the transfer that preceded it.
        """
        end = min(start + length, self.size) - 1
        if start > end:
            return b""
        req = urllib.request.Request(self.url, headers={"Range": f"bytes={start}-{end}"})
        for attempt in range(RETRIES):
            try:
                with urllib.request.urlopen(req, context=_CTX, timeout=TIMEOUT_S) as r:
                    data = r.read()
                break
            except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.HTTPException,
                    ssl.SSLError) as exc:
                if attempt == RETRIES - 1:
                    raise
                wait = BACKOFF_S * 2 ** attempt
                print(f"    range {start}+{length} failed ({type(exc).__name__}); "
                      f"retry {attempt + 1}/{RETRIES - 1} in {wait}s", flush=True)
                time.sleep(wait)
        self.requests += 1
        self.bytes_read += len(data)
        return data

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=io.SEEK_SET):
        self.pos = (offset if whence == io.SEEK_SET else
                    self.pos + offset if whence == io.SEEK_CUR else self.size + offset)
        return self.pos

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self.pos
        n = min(n, self.size - self.pos)
        if n <= 0:
            return b""
        cstart, cdata = self._cache
        if not (cstart <= self.pos and self.pos + n <= cstart + len(cdata)):
            start = self.pos
            cdata = self._fetch(start, max(n, CHUNK))
            cstart = start
            self._cache = (cstart, cdata)
        off = self.pos - cstart
        self.pos += n
        return cdata[off:off + n]


def wanted_experiments(conditions):
    """The experiments this project's real-plant items use, as `system/point/experiment`."""
    items = json.load(open(ROOT / "data/realdata/items.json"))["items"]
    return {i["experiment"] for i in items if i["condition"] in conditions}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", default="image", choices=sorted(ARCHIVES))
    ap.add_argument("--phase", default="Operation")
    ap.add_argument("--list", action="store_true", help="only print what would be fetched")
    ap.add_argument("--limit", type=int, help="fetch at most this many members")
    ap.add_argument("--cam", default="Cam0", help="one camera view; the plant records three")
    ap.add_argument("--ext", default="mp4,txt",
                    help="the video and its timestamp sidecar; frames without the sidecar "
                         "cannot be placed on the plant's clock")
    ap.add_argument("--conditions", nargs="*", default=["blind", "control"],
                    choices=["blind", "control", "full"])
    ap.add_argument("--shard", default="0/1",
                    help="k/n: take every n-th member starting at k, so n processes can fetch "
                         "disjoint sets side by side without writing the same file")
    args = ap.parse_args()

    url = f"{BASE}/{ARCHIVES[args.archive]}/content"
    fh = HttpFile(url)
    print(f"{ARCHIVES[args.archive]}: {fh.size / 1e9:.1f} GB, reading the directory over ranges ...",
          flush=True)
    zf = zipfile.ZipFile(fh)
    names = zf.namelist()
    keys = wanted_experiments(args.conditions)
    exts = tuple("." + e.strip().lstrip(".") for e in args.ext.split(","))
    picked = [n for n in names
              if f"/{args.phase}/" in n and n.endswith(exts) and args.cam in n
              and any(k in n for k in keys)]
    print(f"{len(names):,} members in the archive; {len(picked)} match {len(keys)} experiments "
          f"in phase {args.phase}")
    if args.limit:
        picked = picked[:args.limit]
    k, n = (int(x) for x in args.shard.split("/"))
    picked = picked[k::n]
    if args.list:
        for n in picked[:20]:
            print("   ", n, f"{zf.getinfo(n).file_size / 1e6:.1f} MB")
        total = sum(zf.getinfo(n).file_size for n in picked)
        print(f"    ... total {total / 1e9:.2f} GB of {fh.size / 1e9:.1f} GB")
        return

    out = DATA / "media" / args.archive
    out.mkdir(parents=True, exist_ok=True)
    failed = []
    for i, name in enumerate(picked, 1):
        dest = out / Path(name).relative_to(Path(name).parts[0])
        want = zf.getinfo(name).file_size
        if dest.exists() and dest.stat().st_size == want:
            continue
        if dest.exists():
            # Existing is not the same as complete: a fetch killed before .part was introduced
            # left a 100 MB file of 120 MB under the final name, and it would have decoded.
            print(f"  [{i}/{len(picked)}] truncated ({dest.stat().st_size:,} of {want:,} bytes); "
                  f"fetching again: {dest.relative_to(out)}", flush=True)
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_name(dest.name + ".part")     # an interrupted fetch must not look complete
        try:
            with zf.open(name) as src, open(part, "wb") as f:
                while chunk := src.read(1 << 20):
                    f.write(chunk)
        except Exception as exc:      # noqa: BLE001 - one bad member must not lose the whole run
            part.unlink(missing_ok=True)
            failed.append((name, f"{type(exc).__name__}: {exc}"))
            print(f"  [{i}/{len(picked)}] FAILED {dest.relative_to(out)}: "
                  f"{type(exc).__name__}", flush=True)
            continue
        part.rename(dest)
        print(f"  [{i}/{len(picked)}] {dest.relative_to(out)} "
              f"{dest.stat().st_size / 1e6:.1f} MB", flush=True)
    print(f"transferred {fh.bytes_read / 1e9:.2f} GB in {fh.requests} range requests "
          f"-> {out.relative_to(ROOT)}")
    if failed:
        # Re-running picks these up: whatever landed is kept, and only the gaps are fetched.
        for name, why in failed:
            print(f"  missing: {name} ({why})")
        sys.exit(f"{len(failed)} of {len(picked)} members did not transfer; run again")


if __name__ == "__main__":
    main()
