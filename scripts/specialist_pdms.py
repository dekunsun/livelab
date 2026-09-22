"""Arm S of docs/specialist_preregistration.md: a specialist vision model for PDMS inspections.

Frozen DINOv2 ViT-S/14 embeddings, and a 5-nearest-neighbour vote per check among training
annotations. Every setting is fixed in the registration; nothing here is tuned on the test set.

  ./.venv/bin/python scripts/specialist_pdms.py embed     # all 1,671 images, once
  ./.venv/bin/python scripts/specialist_pdms.py predict   # S, its sensitivity runs, and timing
"""
import collections
import io
import json
import random
import sys
import time
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
ZIP = ROOT / "data/external/pdms/data.zip"
ANN = ROOT / "data/external/pdms/data/annotation/annotation.json"
ITEMS = ROOT / "data/pdms_pilot/items.json"
EMB = ROOT / "data/specialist/embeddings.npz"
OUT = ROOT / "results/specialist"
K = 5
NEAR_DUP = 0.97          # registered primary exclusion
NEAR_DUP_STRICT = 0.90   # registered sensitivity
FRACTIONS = (0.10, 0.25, 0.50)
SEED = 20260921
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def preprocess(img):
    """The DINOv2 evaluation transform: shorter side to 256, centre crop 224, ImageNet normalise."""
    from PIL import Image
    img = img.convert("RGB")
    w, h = img.size
    s = 256 / min(w, h)
    img = img.resize((round(w * s), round(h * s)), Image.BICUBIC)
    w, h = img.size
    left, top = (w - 224) // 2, (h - 224) // 2
    img = img.crop((left, top, left + 224, top + 224))
    a = (np.asarray(img, dtype=np.float32) / 255 - MEAN) / STD
    return a.transpose(2, 0, 1)


def embed():
    import torch
    from PIL import Image
    model = torch.hub.load("facebookresearch/dinov2", "dinov2_vits14")
    model.eval()
    z = zipfile.ZipFile(ZIP)
    names = sorted(n for n in z.namelist() if n.startswith("data/image/") and n.endswith(".jpg"))
    vecs, t0 = [], time.time()
    with torch.no_grad():
        for i in range(0, len(names), 32):
            batch = np.stack([preprocess(Image.open(io.BytesIO(z.read(n)))) for n in names[i:i + 32]])
            v = model(torch.from_numpy(batch)).numpy()
            vecs.append(v / np.linalg.norm(v, axis=1, keepdims=True))
            print(f"  {min(i + 32, len(names))}/{len(names)}", flush=True)
    secs = time.time() - t0
    EMB.parent.mkdir(parents=True, exist_ok=True)
    np.savez(EMB, names=np.array(names), vecs=np.concatenate(vecs), seconds=secs)
    print(f"embedded {len(names)} images in {secs:.0f} s ({secs / len(names) * 1000:.0f} ms each)")


def knn(query, pool, labels):
    """Majority of the K most similar pool rows. Returns (verdict, agreeing)."""
    sims = pool @ query
    top = np.argsort(-sims)[:K]
    abn = sum(labels[j] for j in top)
    verdict = "ABNORMAL" if abn > K // 2 else "NORMAL"
    return verdict, max(abn, K - abn)


def predict_with(train, test, vec):
    by_check = collections.defaultdict(list)
    for a in train:
        by_check[a["Detection_Content"]].append(a)
    out = {}
    for it in test:
        pool = by_check.get(it["context"]["Detection_Content"], [])
        if len(pool) < K:
            out[it["item_id"]] = {"verdict": "UNKNOWN", "agreeing": None, "pool": len(pool)}
            continue
        P = np.stack([vec[a["Image_Id"]] for a in pool])
        v, agree = knn(vec[it["image"]], P, [bool(a["Anomaly_Label"]) for a in pool])
        out[it["item_id"]] = {"verdict": v, "agreeing": agree, "pool": len(pool)}
    return out


def predict():
    d = np.load(EMB)
    vec = dict(zip(d["names"].tolist(), d["vecs"]))
    A = json.load(open(ANN))
    items = json.load(open(ITEMS))["items"]
    test_imgs = sorted({it["image"] for it in items})
    T = np.stack([vec[i] for i in test_imgs])

    def eligible(threshold):
        near = {n for n, v in vec.items() if n not in test_imgs and (T @ v).max() >= threshold}
        pool = [a for a in A if a["Image_Id"] not in test_imgs and a["Image_Id"] not in near]
        return pool, near

    runs, report = {}, {}
    for name, thr in (("primary", NEAR_DUP), ("strict", NEAR_DUP_STRICT)):
        pool, near = eligible(thr)
        t0 = time.time()
        runs[name] = predict_with(pool, items, vec)
        report[name] = {"threshold": thr, "near_duplicate_images_excluded": len(near),
                        "training_annotations": len(pool),
                        "classify_ms_per_item": (time.time() - t0) / len(items) * 1000}
    pool, _ = eligible(NEAR_DUP)
    rng = random.Random(SEED)
    for f in FRACTIONS:
        sub = rng.sample(pool, round(len(pool) * f))
        runs[f"train{int(f * 100)}"] = predict_with(sub, items, vec)
        report[f"train{int(f * 100)}"] = {"threshold": NEAR_DUP, "training_annotations": len(sub)}

    OUT.mkdir(parents=True, exist_ok=True)
    truth = {it["item_id"]: it["truth"] for it in items}
    for name, pred in runs.items():
        (OUT / f"S_{name}.json").write_text(json.dumps(pred, indent=1))
        right = sum(p["verdict"] == truth[i] for i, p in pred.items())
        unk = sum(p["verdict"] == "UNKNOWN" for p in pred.values())
        report[name] |= {"accuracy": right, "unknown": unk}
        print(f"{name:9} train {report[name]['training_annotations']:5}  right {right}/100  "
              f"unknown {unk}", flush=True)
    report["embedding_ms_per_image"] = float(d["seconds"]) / len(d["names"]) * 1000
    (OUT / "report.json").write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    {"embed": embed, "predict": predict}[sys.argv[1]]()
