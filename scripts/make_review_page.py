"""Build the human review page for the 24 CVD micrograph labels.

The labels were written by a model from the crop and its caption, and every row of
data/images/manifest.csv still says "pending human review". They matter: the ground truth calls a
run successful only when its image class is `a`, so the a / not-a line decides every episode's
scientific-evidence truth.

The page stages into a directory (default: the scratchpad) together with the crops and the source
figures, and is published as an Artifact. Verdicts go to the artifact's own store, and are read
back with the ArtifactData tool into data/images/review.csv.

  ./.venv/bin/python scripts/make_review_page.py [out_dir]
"""
import csv
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "build" / "review"

# Written from the label notes, because the class system exists only in those notes and in one
# line of observability.py (`success = image_class == "a"`). Confirming or correcting these
# definitions is part of the review.
LEGEND = [
    ("a", "Monolayer triangles", "The target material: separated or lightly merged single-layer triangles. Only this class counts as a successful run."),
    ("b", "Almost no growth", "Near-bare substrate, or sparse particle-like nuclei with no triangles."),
    ("c", "Multilayer or thickened", "Triangles carrying second-layer or bulk regions, stacked plates."),
    ("d", "Small and sparse", "Triangles present but small and thinly scattered; incomplete coverage."),
    ("e", "Oxide or residue", "Residue crystals, oxide-rich flowers, unreacted precursor."),
    ("g", "Decomposition", "Dendritic rosettes and other etched or decomposed morphology."),
]


def build():
    manifest = {r["id"]: r for r in csv.DictReader(open(ROOT / "data/images/manifest.csv"))}
    crops = {r["image_id"]: r for r in csv.DictReader(open(ROOT / "data/images/crops.csv"))}
    captions = json.load(open(ROOT / "data/images/fetched/captions.json"))

    (OUT / "img").mkdir(parents=True, exist_ok=True)
    (OUT / "fig").mkdir(parents=True, exist_ok=True)
    items, figures = [], {}
    for image_id, m in sorted(manifest.items()):
        c = crops[image_id]
        key = f"{c['source_id']}/fig{c['figure']}"
        cap = captions.get(key, {})
        src = ROOT / cap["file"] if cap.get("file") else None
        fig_name = ""
        if src and src.exists():
            fig_name = f"{c['source_id']}_fig{c['figure']}{src.suffix}"
            if fig_name not in figures:
                shutil.copy(src, OUT / "fig" / fig_name)
                figures[fig_name] = True
        shutil.copy(ROOT / f"data/images/cvd/{image_id}.png", OUT / "img" / f"{image_id}.png")
        items.append({
            "id": image_id,
            "cls": m["outcome_class"],
            "note": m["notes"].split(";")[0].strip(),
            "doi": m["source_doi_or_url"],
            "figure": f"Fig {c['figure']}{c['panel']}",
            "licence": m["license"],
            "caption": (cap.get("caption") or "").strip(),
            "crop": f"img/{image_id}.png",
            "fig": f"fig/{fig_name}" if fig_name else "",
        })

    html = TEMPLATE.replace("__ITEMS__", json.dumps(items, ensure_ascii=False)) \
                   .replace("__LEGEND__", json.dumps(LEGEND, ensure_ascii=False))
    (OUT / "index.html").write_text(html)
    print(f"{len(items)} items, {len(figures)} source figures -> {OUT}")
    return OUT


TEMPLATE = r"""<title>Micrograph Label Review</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Serif:wght@500;600&display=swap">
<style>
  :root {
    --paper: #f4f6f3; --surface: #ffffff; --sunk: #eceee9;
    --ink: #15191b; --muted: #5c6763; --line: #d7dcd6;
    --accent: #2f6f5e; --accent-soft: #e3efe9;
    --flag: #a8542a; --flag-soft: #f6e9e1;
    --shadow: 0 1px 2px rgba(20, 30, 25, .06);
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --paper: #121614; --surface: #1a201d; --sunk: #232a26;
      --ink: #e8ece9; --muted: #9aa8a2; --line: #2f3833;
      --accent: #6fbfa4; --accent-soft: #1e332c;
      --flag: #e0946a; --flag-soft: #3a2a20;
      --shadow: none;
    }
  }
  :root[data-theme="dark"] {
    --paper: #121614; --surface: #1a201d; --sunk: #232a26;
    --ink: #e8ece9; --muted: #9aa8a2; --line: #2f3833;
    --accent: #6fbfa4; --accent-soft: #1e332c;
    --flag: #e0946a; --flag-soft: #3a2a20;
    --shadow: none;
  }
  body { background: var(--paper); color: var(--ink); font-family: "IBM Plex Sans", system-ui, sans-serif; }
  .wrap { max-width: 900px; margin: 0 auto; padding-inline: 16px; padding-block: 28px 64px; }
  h1 { font-family: "IBM Plex Serif", Georgia, serif; font-size: 1.6rem; font-weight: 600; margin: 0 0 .3rem; text-wrap: balance; }
  .lede { color: var(--muted); max-width: 62ch; line-height: 1.55; margin: 0 0 1.4rem; }
  .lede strong { color: var(--ink); font-weight: 600; }
  h2 { font-family: "IBM Plex Serif", Georgia, serif; font-size: 1rem; font-weight: 600; margin: 2rem 0 .6rem; }
  .eyebrow { font-family: "IBM Plex Mono", monospace; font-size: .68rem; letter-spacing: .12em; text-transform: uppercase; color: var(--muted); }
  .legend { display: grid; gap: 1px; background: var(--line); border: 1px solid var(--line); border-radius: 6px; overflow: hidden; }
  .legend div { background: var(--surface); padding: .55rem .7rem; display: grid; grid-template-columns: 2.1rem 1fr; gap: .6rem; align-items: baseline; font-size: .82rem; line-height: 1.45; }
  .legend .k { font-family: "IBM Plex Mono", monospace; font-weight: 500; color: var(--accent); }
  .legend .target { background: var(--accent-soft); }
  .legend b { font-weight: 600; }
  .bar { position: sticky; top: env(safe-area-inset-top, 0px); z-index: 5; background: var(--paper); border-bottom: 1px solid var(--line); margin: 1.6rem -16px 0; padding: .6rem 16px; display: flex; gap: .9rem; align-items: center; flex-wrap: wrap; }
  .bar .count { font-family: "IBM Plex Mono", monospace; font-size: .82rem; font-variant-numeric: tabular-nums; }
  .track { flex: 1 1 140px; height: 5px; background: var(--sunk); border-radius: 3px; overflow: hidden; min-width: 100px; }
  .track i { display: block; height: 100%; background: var(--accent); width: 0; transition: width .25s; }
  button { font: inherit; cursor: pointer; }
  .ghost { background: var(--surface); border: 1px solid var(--line); color: var(--ink); border-radius: 5px; padding: .3rem .65rem; font-size: .78rem; }
  .ghost:hover { border-color: var(--accent); }
  .card { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; box-shadow: var(--shadow); padding: 1rem; margin-top: 1rem; display: grid; grid-template-columns: 260px 1fr; gap: 1.1rem; }
  .card.done { border-left: 3px solid var(--accent); }
  .card.changed { border-left: 3px solid var(--flag); }
  @media (max-width: 660px) { .card { grid-template-columns: 1fr; } }
  .shot { display: grid; gap: .45rem; align-content: start; }
  .shot img { width: 100%; border: 1px solid var(--line); border-radius: 4px; image-rendering: pixelated; background: var(--sunk); }
  .shot .crop { aspect-ratio: 230 / 114; object-fit: cover; }
  .meta { font-family: "IBM Plex Mono", monospace; font-size: .7rem; color: var(--muted); display: flex; justify-content: space-between; gap: .5rem; }
  .meta a { color: var(--accent); }
  details summary { font-size: .74rem; color: var(--muted); cursor: pointer; }
  details p { font-size: .74rem; line-height: 1.5; color: var(--muted); max-height: 11rem; overflow-y: auto; margin: .4rem 0 0; }
  .body h3 { font-family: "IBM Plex Mono", monospace; font-size: .86rem; font-weight: 500; margin: 0 0 .15rem; }
  .said { font-size: .86rem; line-height: 1.5; margin: 0 0 .7rem; }
  .said em { color: var(--muted); font-style: normal; }
  .choices { display: flex; flex-wrap: wrap; gap: .35rem; }
  .choices button { border: 1px solid var(--line); background: var(--sunk); color: var(--ink); border-radius: 5px; padding: .34rem .6rem; font-size: .78rem; display: inline-flex; gap: .4rem; align-items: baseline; }
  .choices button .k { font-family: "IBM Plex Mono", monospace; color: var(--muted); }
  .choices button[aria-pressed="true"] { background: var(--accent); border-color: var(--accent); color: #fff; }
  .choices button[aria-pressed="true"] .k { color: rgba(255,255,255,.75); }
  .choices button:focus-visible, .ghost:focus-visible, textarea:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  textarea { width: 100%; margin-top: .55rem; border: 1px solid var(--line); border-radius: 5px; background: var(--sunk); color: var(--ink); padding: .4rem .5rem; font: inherit; font-size: .8rem; resize: vertical; min-height: 2.2rem; }
  .status { font-size: .72rem; color: var(--muted); margin-top: .45rem; min-height: 1rem; font-family: "IBM Plex Mono", monospace; }
  .status.changed { color: var(--flag); }
  .notice { background: var(--flag-soft); border: 1px solid var(--flag); color: var(--ink); border-radius: 6px; padding: .6rem .75rem; font-size: .8rem; margin-top: 1rem; }
  footer { margin-top: 2.5rem; font-size: .74rem; color: var(--muted); line-height: 1.6; border-top: 1px solid var(--line); padding-top: .9rem; }
  @media (prefers-reduced-motion: reduce) { .track i { transition: none; } }
</style>

<div class="wrap">
  <p class="eyebrow">LiveLab · ground truth</p>
  <h1>Micrograph label review</h1>
  <p class="lede">Twenty-four panels from CC BY papers carry a class that a model assigned from the
    crop and its caption. Every row still reads <em>pending human review</em>, and the class decides
    ground truth: a run counts as successful <strong>only when its class is a</strong>. So the
    decision that matters is <strong>a or not-a</strong>; the finer classes only describe how a run
    failed. Confirm each one, or change it.</p>

  <p class="eyebrow">Proposed class definitions</p>
  <div class="legend" id="legend"></div>

  <div class="bar">
    <span class="count"><b id="done">0</b> / <span id="total">24</span> reviewed</span>
    <span class="track"><i id="fill"></i></span>
    <span class="count" id="changes"></span>
    <button class="ghost" id="copy">Copy as CSV</button>
  </div>

  <div id="cards"></div>
  <div class="notice" id="offline" hidden>Verdicts are not being saved in this view. Use
    <b>Copy as CSV</b> before you leave.</div>

  <footer>
    Crops are cut from the published figures at their source resolution (about 230 × 114 px), which
    is what the model was shown; open the full figure when the crop is not enough. Images are CC BY
    and belong to their authors — see <code>data/images/ATTRIBUTION.md</code>.
  </footer>
</div>

<script>
const ITEMS = __ITEMS__;
const LEGEND = __LEGEND__;
const CLASSES = LEGEND.map(l => l[0]);
const verdicts = new Map();
let db = null;

const el = (t, cls, txt) => { const n = document.createElement(t); if (cls) n.className = cls; if (txt != null) n.textContent = txt; return n; };

function drawLegend() {
  const box = document.getElementById("legend");
  for (const [k, name, desc] of LEGEND) {
    const row = el("div", k === "a" ? "target" : "");
    row.append(el("span", "k", k), (() => { const p = el("span"); p.append(el("b", null, name), document.createTextNode(" — " + desc)); return p; })());
    box.append(row);
  }
}

function render() {
  const wrap = document.getElementById("cards");
  wrap.textContent = "";
  for (const it of ITEMS) {
    const card = el("div", "card");
    card.id = "card-" + it.id;

    const shot = el("div", "shot");
    const crop = el("img", "crop"); crop.src = it.crop; crop.alt = "Crop " + it.id; crop.loading = "lazy";
    shot.append(crop);
    const meta = el("div", "meta");
    const a = el("a", null, it.figure); a.href = it.doi; a.target = "_blank"; a.rel = "noopener noreferrer";
    meta.append(el("span", null, it.id), a);
    shot.append(meta);
    if (it.fig) {
      const d = el("details");
      d.append(el("summary", null, "Full figure and caption"));
      const f = el("img"); f.src = it.fig; f.alt = "Source figure for " + it.id; f.loading = "lazy";
      d.append(f);
      if (it.caption) d.append(el("p", null, it.caption));
      shot.append(d);
    }
    card.append(shot);

    const body = el("div", "body");
    body.append(el("h3", null, it.id));
    const said = el("p", "said");
    said.append(el("em", null, "Labelled "), el("b", null, it.cls), el("em", null, " — " + it.note));
    body.append(said);

    const choices = el("div", "choices");
    for (const [k, name] of LEGEND) {
      const b = el("button");
      b.append(el("span", "k", k), document.createTextNode(name));
      b.setAttribute("aria-pressed", "false");
      b.dataset.cls = k;
      b.addEventListener("click", () => choose(it, k));
      choices.append(b);
    }
    body.append(choices);

    const note = el("textarea");
    note.id = "note-" + it.id;
    note.placeholder = "Why, if you changed it (optional)";
    note.addEventListener("change", () => { if (verdicts.has(it.id)) choose(it, verdicts.get(it.id).cls); });
    body.append(note);
    body.append(el("div", "status"));
    card.append(body);
    wrap.append(card);
  }
  document.getElementById("total").textContent = ITEMS.length;
  paint();
}

function paint() {
  let changed = 0;
  for (const it of ITEMS) {
    const v = verdicts.get(it.id);
    const card = document.getElementById("card-" + it.id);
    const status = card.querySelector(".status");
    for (const b of card.querySelectorAll(".choices button")) {
      b.setAttribute("aria-pressed", String(!!v && v.cls === b.dataset.cls));
    }
    card.classList.toggle("done", !!v);
    const diff = !!v && v.cls !== it.cls;
    card.classList.toggle("changed", diff);
    status.classList.toggle("changed", diff);
    if (diff) changed++;
    status.textContent = !v ? "" : diff ? "changed " + it.cls + " → " + v.cls : "confirmed " + v.cls;
    const note = document.getElementById("note-" + it.id);
    if (v && v.note && document.activeElement !== note) note.value = v.note;
  }
  const done = verdicts.size;
  document.getElementById("done").textContent = done;
  document.getElementById("fill").style.width = (done / ITEMS.length * 100) + "%";
  document.getElementById("changes").textContent = changed ? changed + " changed" : "";
}

async function choose(it, cls) {
  const note = document.getElementById("note-" + it.id).value.trim();
  const v = { cls, note, was: it.cls, at: new Date().toISOString() };
  verdicts.set(it.id, v);
  paint();
  save(it.id, v);
}

let queue = Promise.resolve();
function save(id, v) {
  try { localStorage.setItem("verdict:" + id, JSON.stringify(v)); } catch (e) { /* private window */ }
  if (!db) return;
  queue = queue.then(() => db.doc("reviews/" + id).set(v)).catch(e => {
    const card = document.getElementById("card-" + id);
    if (card) card.querySelector(".status").textContent = "not saved (" + (e && e.code || "error") + ")";
  });
}

function csv() {
  const rows = [["image_id", "labelled_class", "human_class", "agrees", "note"]];
  for (const it of ITEMS) {
    const v = verdicts.get(it.id);
    if (v) rows.push([it.id, it.cls, v.cls, v.cls === it.cls ? "yes" : "no", (v.note || "").replace(/"/g, "'")]);
  }
  return rows.map(r => r.map(c => /[",]/.test(c) ? '"' + c + '"' : c).join(",")).join("\n");
}

document.getElementById("copy").addEventListener("click", async () => {
  const btn = document.getElementById("copy");
  try { await navigator.clipboard.writeText(csv()); btn.textContent = "Copied"; }
  catch (e) { btn.textContent = "Copy failed"; }
  setTimeout(() => { btn.textContent = "Copy as CSV"; }, 1600);
});

drawLegend();
for (const it of ITEMS) {
  try { const raw = localStorage.getItem("verdict:" + it.id); if (raw) verdicts.set(it.id, JSON.parse(raw)); } catch (e) { /* ignore */ }
}
render();

(async () => {
  db = window.claude && claude.use ? await claude.use("db") : null;
  if (!db) { document.getElementById("offline").hidden = false; return; }
  db.collection("reviews").onSnapshot(snap => {
    for (const d of snap.docs) {
      const v = d.data();
      if (v && v.cls) verdicts.set(d.id, v);
    }
    paint();
  }, () => { document.getElementById("offline").hidden = false; });
})();
</script>
"""

if __name__ == "__main__":
    build()
