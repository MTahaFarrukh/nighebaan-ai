"""Audit official public corpora in memory; persist aggregate metadata only."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import urllib.request
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

MAX_BYTES = 20 * 1024 * 1024
UCI_URL = "https://archive.ics.uci.edu/static/public/458/roman%2Burdu%2Bdata%2Bset.zip"
SMS_URL = "https://archive.ics.uci.edu/static/public/228/sms%2Bspam%2Bcollection.zip"
REPO = "haroonshakeel/roman_urdu_hate_speech"


def fetch(url: str) -> bytes:
    """Fetch only caller-specified source locations, never message URLs."""
    request = urllib.request.Request(
        url, headers={"User-Agent": "Nigehbaan-dataset-audit/1.0"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = response.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise ValueError("Source exceeds audit size limit.")
    return payload


def unzip(payload: bytes, name: str) -> bytes:
    """Read one archive member without extracting anything onto disk."""
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        matches = [
            info for info in archive.infolist() if Path(info.filename).name == name
        ]
        if len(matches) != 1 or matches[0].file_size > MAX_BYTES:
            raise ValueError("Unexpected archive structure.")
        return archive.read(matches[0])


def inspect_rows(payload: bytes, dataset: str) -> dict[str, object]:
    """Count known labels and stripped-text duplicates without reporting text."""
    mappings = {
        "uci": {"positive": "normal", "neutral": "normal"},
        "sms": {"ham": "normal", "spam": "scam"},
        "ruhsold": {"0": "abusive", "1": "normal"},
    }
    known = set(mappings[dataset]) | ({"negative"} if dataset == "uci" else set())
    encoding = "utf-8-sig"
    try:
        decoded = payload.decode(encoding)
    except UnicodeDecodeError:
        encoding = "cp1252"
        decoded = payload.decode(encoding)
    reader = csv.reader(
        io.StringIO(decoded),
        delimiter="," if dataset == "uci" else "\t",
        quoting=csv.QUOTE_MINIMAL if dataset == "uci" else csv.QUOTE_NONE,
    )
    labels: Counter[str] = Counter()
    classes: Counter[str] = Counter()
    seen: set[str] = set()
    rows = empty = malformed = duplicates = 0
    for row in reader:
        rows += 1
        if len(row) < 2 or (dataset != "uci" and len(row) != 2):
            malformed += 1
            continue
        text, label = (row[1], row[0]) if dataset == "sms" else (row[0], row[1])
        text, label = text.strip(), label.strip().lower()
        labels[label if label in known else "unknown"] += 1
        if not text:
            empty += 1
            continue
        mapped = mappings[dataset].get(label)
        if mapped:
            classes[mapped] += 1
            digest = hashlib.sha256(text.encode()).hexdigest()
            duplicates += digest in seen
            seen.add(digest)
    return {
        "rows": rows,
        "empty_text_rows": empty,
        "malformed_rows": malformed,
        "original_label_counts": dict(sorted(labels.items())),
        "mapped_class_counts_before_dedup": dict(sorted(classes.items())),
        "mapped_duplicate_text_rows": duplicates,
        "encoding": encoding,
    }


def audit() -> dict[str, object]:
    """Resolve an upstream revision and audit all three public sources."""
    commit = json.loads(fetch(f"https://api.github.com/repos/{REPO}/commits/main"))[
        "sha"
    ]
    if len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit):
        raise ValueError("Invalid source revision.")
    records = []
    for dataset, url, member, license_name in (
        ("uci", UCI_URL, "Roman Urdu DataSet.csv", "CC BY 4.0"),
        ("sms", SMS_URL, "SMSSpamCollection", "CC BY 4.0"),
    ):
        archive = fetch(url)
        payload = unzip(archive, member)
        records.append(
            {
                "source": dataset,
                "url": url,
                "license": license_name,
                "archive_bytes": len(archive),
                "archive_sha256": hashlib.sha256(archive).hexdigest(),
                "member_bytes": len(payload),
                "member_sha256": hashlib.sha256(payload).hexdigest(),
                **inspect_rows(payload, dataset),
            }
        )
    for partition in ("train", "validation", "test"):
        url = (
            f"https://raw.githubusercontent.com/{REPO}/{commit}/task_1_{partition}.tsv"
        )
        payload = fetch(url)
        records.append(
            {
                "source": "ruhsold",
                "upstream_partition": partition,
                "url": url,
                "license": "MIT",
                "upstream_commit": commit,
                "member_bytes": len(payload),
                "member_sha256": hashlib.sha256(payload).hexdigest(),
                **inspect_rows(payload, "ruhsold"),
            }
        )
    return {
        "audited_at": datetime.now(ZoneInfo("Asia/Karachi")).isoformat(),
        "status": "inventory_only_no_corpus_saved",
        "privacy": "Original corpus bytes processed only in memory; no text or identifiers persisted.",
        "evaluation": "No training or evaluation; upstream partitions are inventoried, not project test splits.",
        "sources": records,
    }


def main() -> None:
    """Save aggregate evidence without network exception details."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.exit(1, "Audit output exists; choose a new inventory file.\n")
    try:
        report = audit()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, KeyError, UnicodeError, zipfile.BadZipFile):
        parser.exit(1, "Source audit failed; no public corpus was saved.\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
