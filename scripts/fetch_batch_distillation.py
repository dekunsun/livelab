"""Fetch the parts of the batch distillation record this project uses. Nothing is committed.

Zenodo 17395543 (CC BY 4.0) is 95 GB. This takes the ~45 MB of tabular files the real-plant
replication needs and leaves the audio, video, NMR and raw spectra alone.

  ./.venv/bin/python scripts/fetch_batch_distillation.py
"""
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data/external/batch_distillation"
BASE = "https://zenodo.org/api/records/22250958/files"
WANT = [
    ("00_Batch_Distillation_Plant_M-202210_Timeseries_Label_Anomaly_Metadata.zip", "labels"),
    ("01_Batch_Distillation_Plant_M-202210_Timeseries_Sensors.zip", "ts"),
    ("02_Batch_Distillation_Plant_M-202210_Timeseries_Actuators.zip", "ts"),
    ("Batch_Distillation_Plant_M-202210_Modality_Availability_Overview.md", None),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, extract_to in WANT:
        dest = OUT / name
        if not dest.exists():
            print(f"fetching {name} ...", flush=True)
            urllib.request.urlretrieve(f"{BASE}/{name}/content", dest)
        if extract_to:
            target = OUT / extract_to
            target.mkdir(exist_ok=True)
            with zipfile.ZipFile(dest) as z:
                z.extractall(target)
    print(f"ready in {OUT.relative_to(ROOT)} (gitignored). "
          "Attribution: data/realdata/ATTRIBUTION.md")


if __name__ == "__main__":
    main()
