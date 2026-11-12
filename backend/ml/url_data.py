"""Pinned UCI URL corpus, parsed in memory; only aggregate metadata is saved."""

from __future__ import annotations

import hashlib
import io
import json
import urllib.request
import zipfile
from pathlib import Path
from urllib.parse import urlsplit

import pandas as pd
from app.services.url_features import canonical_url
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[2]
SOURCE = "https://archive.ics.uci.edu/static/public/967/phiusiil%2Bphishing%2Burl%2Bdataset.zip"
INVENTORY = ROOT / "docs/URL_DATASET_INVENTORY.json"


def prepare_frame(frame: pd.DataFrame) -> tuple[dict, dict]:
    """Canonical deduplication precedes deterministic stratified 70/15/15 splits."""
    original_count = len(frame)
    frame = frame[["URL", "label"]].dropna().copy()
    frame = frame[frame.label.isin([0, 1])]
    canonical = []
    for value in frame.URL:
        try:
            canonical.append(canonical_url(str(value)))
        except ValueError:
            canonical.append(None)
    frame["URL"] = canonical
    frame = frame.dropna()
    # Contradictory labels cannot be resolved without review: discard the group.
    conflict = frame.groupby("URL").label.nunique()
    conflict = set(conflict[conflict > 1].index)
    frame = (
        frame[~frame.URL.isin(conflict)]
        .drop_duplicates("URL")
        .sort_values("URL")
        .reset_index(drop=True)
    )
    frame["label"] = 1 - frame.label.astype(int)
    train, rest = train_test_split(
        frame, test_size=0.30, stratify=frame.label, random_state=42
    )
    val, test = train_test_split(
        rest, test_size=0.50, stratify=rest.label, random_state=42
    )
    splits = {"train": train, "val": val, "test": test}
    sets = {key: set(value.URL) for key, value in splits.items()}
    assert not (
        sets["train"] & sets["val"]
        or sets["train"] & sets["test"]
        or sets["val"] & sets["test"]
    )
    train_hosts = {urlsplit(value).hostname for value in train.URL}
    manifest = {
        "raw_rows": original_count,
        "usable_rows": len(frame),
        "discarded_rows": original_count - len(frame),
        "conflicting_url_groups": len(conflict),
        "random_state": 42,
        "splits": {},
    }
    for name, split in splits.items():
        membership = "\n".join(
            sorted(
                hashlib.sha256(f"{url}\t{label}".encode()).hexdigest()
                for url, label in zip(split.URL, split.label)
            )
        )
        manifest["splits"][name] = {
            "rows": len(split),
            "class_counts": {
                str(k): int(v) for k, v in split.label.value_counts().items()
            },
            "membership_sha256": hashlib.sha256(membership.encode()).hexdigest(),
        }
    manifest["validation_rows_with_training_hostname"] = sum(
        urlsplit(value).hostname in train_hosts for value in val.URL
    )
    return splits, manifest


def prepare() -> tuple[dict, dict]:
    """Download only the fixed official corpus; reject changed pinned bytes."""
    request = urllib.request.Request(
        SOURCE, headers={"User-Agent": "Nigehbaan-dataset-audit/1.0"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = response.read(20 * 1024 * 1024 + 1)
    if len(payload) > 20 * 1024 * 1024:
        raise ValueError("Dataset archive too large.")
    digest = hashlib.sha256(payload).hexdigest()
    if (
        INVENTORY.exists()
        and json.loads(INVENTORY.read_text())["archive_sha256"] != digest
    ):
        raise ValueError("Pinned dataset hash changed.")
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        candidates = [
            i
            for i in archive.infolist()
            if Path(i.filename).name == "PhiUSIIL_Phishing_URL_Dataset.csv"
        ]
        if len(candidates) != 1 or candidates[0].file_size > 70 * 1024 * 1024:
            raise ValueError("Unexpected URL corpus structure.")
        frame = pd.read_csv(
            io.BytesIO(archive.read(candidates[0])), usecols=["URL", "label"]
        )
    splits, manifest = prepare_frame(frame)
    manifest.update(
        {
            "source": SOURCE,
            "archive_sha256": digest,
            "license": "CC BY 4.0",
            "attribution": "Prasad, A. & Chandra, S. (2024), PhiUSIIL Phishing URL (Website), UCI.",
            "label_mapping": {"source_0": "phishing=1", "source_1": "benign=0"},
            "features": "Only static features computed from URL; supplied webpage/derived features excluded.",
            "test_evaluated": False,
        }
    )
    if INVENTORY.exists():
        old = json.loads(INVENTORY.read_text())
        if old["splits"] != manifest["splits"]:
            raise ValueError("Frozen URL partition mismatch.")
    else:
        INVENTORY.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return splits, manifest
