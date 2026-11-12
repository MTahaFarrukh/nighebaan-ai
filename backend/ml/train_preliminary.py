"""Pinned public-corpus preliminary baseline; corpus text never written to disk."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
from pathlib import Path

import pandas as pd
from app.services.preprocess import clean_text, normalize_unicode
from ml.audit_sources import fetch, unzip
from ml.data_prep import (
    assert_disjoint,
    class_counts,
    deduplicate,
    map_rows,
    split_frame,
)
from ml.train_text import train

ROOT = Path(__file__).resolve().parents[2]


def sanitize(text: str, *, normalize: bool = True) -> str:
    """Minimize identifiers in memory; not a claim of complete anonymization."""
    text = normalize_unicode(text)
    text = re.sub(r"(?<!\w)@[\w]+", " handletoken ", text)
    text = re.sub(r"\d(?:[\s().+/-]*\d){5,}", " phonetoken ", text)
    return clean_text(text, normalize=normalize)


def load_public(inventory: dict, raw_lookup: dict | None = None) -> pd.DataFrame:
    """Verify recorded byte hashes before mapping the pinned official sources."""
    frames = []
    for item in inventory["sources"]:
        payload = fetch(item["url"])
        if "archive_sha256" in item:
            if hashlib.sha256(payload).hexdigest() != item["archive_sha256"]:
                raise ValueError("Source archive changed.")
            member = (
                "Roman Urdu DataSet.csv"
                if item["source"] == "uci"
                else "SMSSpamCollection"
            )
            payload = unzip(payload, member)
        if hashlib.sha256(payload).hexdigest() != item["member_sha256"]:
            raise ValueError("Source content changed.")
        source = item["source"]
        records = csv.reader(
            io.StringIO(payload.decode(item["encoding"])),
            delimiter="," if source == "uci" else "\t",
            quoting=csv.QUOTE_MINIMAL if source == "uci" else csv.QUOTE_NONE,
        )
        rows = []
        for record in records:
            if len(record) < 2:
                continue
            text, label = (record[1], record[0]) if source == "sms" else record[:2]
            cleaned = sanitize(text)
            if raw_lookup is not None:
                raw_lookup.setdefault((source, cleaned), text)
            rows.append((cleaned, label))
        mapping = {
            "uci": {"positive": "normal", "neutral": "normal"},
            "sms": {"ham": "normal", "spam": "scam"},
            "ruhsold": {"0": "abusive", "1": "normal"},
        }[source]
        frames.append(
            map_rows(
                pd.DataFrame(rows, columns=["text", "label"]),
                mapping,
                source,
                "en" if source == "sms" else "roman_urdu",
            )
        )
    return pd.concat(frames, ignore_index=True)


def prepare_partitions(
    raw_lookup: dict | None = None,
) -> tuple[dict[str, pd.DataFrame], dict]:
    """Reconstruct frozen partitions without training."""
    inventory_path = ROOT / "docs/DATASET_INVENTORY.json"
    inventory = json.loads(inventory_path.read_text())
    public = load_public(inventory, raw_lookup=raw_lookup)
    custom_path = ROOT / "backend/data/raw/custom/review_v1/custom_scam.draft.csv"
    custom = pd.read_csv(custom_path, keep_default_na=False).drop_duplicates(
        "family_id"
    )
    if raw_lookup is not None:
        for original in custom.text:
            raw_lookup.setdefault(("custom", sanitize(original)), original)
    custom["text"] = custom.text.map(sanitize)
    custom["source"] = "custom"
    custom["lang_hint"] = "roman_urdu"
    merged, dedup_counts = deduplicate(pd.concat([public, custom], ignore_index=True))
    custom_pool, holdout = split_frame(merged[merged.source.eq("custom")], 0.2)
    pool = pd.concat(
        [merged[merged.source.ne("custom")], custom_pool], ignore_index=True
    )
    training, remaining = split_frame(pool, 0.3)
    validation, test = split_frame(remaining, 0.5)
    splits = {
        "train": training,
        "val": validation,
        "test": test,
        "custom_holdout": holdout,
    }
    assert_disjoint(splits)
    manifest = {
        "status": "preliminary_human_unverified",
        "corpus_storage": "memory_only",
        "split_seed": 42,
        "custom_policy": "one representative per template family",
        "source_inventory_sha256": hashlib.sha256(
            inventory_path.read_bytes()
        ).hexdigest(),
        "custom_draft_sha256": hashlib.sha256(custom_path.read_bytes()).hexdigest(),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "deduplication": dedup_counts,
        "splits": {
            name: {
                "rows": len(frame),
                "class_counts": class_counts(frame),
                "membership_sha256": hashlib.sha256(
                    "\n".join(
                        sorted(
                            hashlib.sha256(text.encode()).hexdigest()
                            for text in frame.text
                        )
                    ).encode()
                ).hexdigest(),
            }
            for name, frame in splits.items()
        },
        "test_evaluated": False,
    }
    return splits, manifest


def run(output: Path) -> dict:
    """Train baseline on reconstructed partitions."""
    if output.exists():
        raise ValueError("Output exists.")
    splits, manifest = prepare_partitions()
    result = train(Path(), output, in_memory=(splits["train"], splits["val"]))
    (output / "data_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    metadata_path = output / "run_metadata.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["data_review_status"] = manifest["status"]
    metadata["input_hash_format"] = (
        "canonical dataframe CSV encoded UTF-8; in memory only"
    )
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return {
        "status": manifest["status"],
        "validation_macro_f1": result["macro_f1"],
        "splits": manifest["splits"],
        "test_evaluated": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run(args.output)
    except (OSError, ValueError, KeyError, TypeError):
        parser.exit(
            1,
            "Preliminary run failed; source, schema, network or training error. No corpus contents logged.\n",
        )
    print(json.dumps(result, indent=2))
