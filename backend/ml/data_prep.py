"""Prepare reviewed offline corpora; never emit text or personal identifiers."""

from __future__ import annotations

import argparse
import csv
import json
from itertools import combinations
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.model_selection import train_test_split

COLUMNS = ("text", "label", "source", "lang_hint")
LABELS = ("normal", "abusive", "scam")
SEED = 42
DEFAULT_DATA = Path(__file__).resolve().parents[1] / "data"


def read_table(path: Path, **kwargs: Any) -> pd.DataFrame:
    """Suppress parser diagnostics that may contain input content."""
    try:
        return pd.read_csv(path, dtype="string", encoding="utf-8-sig", **kwargs)
    except (OSError, ValueError, UnicodeError, pd.errors.ParserError):
        raise ValueError(
            "Cannot read dataset; check file, encoding and schema."
        ) from None


def map_rows(
    frame: pd.DataFrame, mapping: dict[str, str], source: str, lang: str
) -> pd.DataFrame:
    """Map only explicit labels and retain aggregate rejection counts."""
    if not {"text", "label"}.issubset(frame.columns):
        raise ValueError("Dataset requires text and label columns.")
    text = frame["text"].astype("string").str.strip()
    label = frame["label"].astype("string").str.strip().str.lower().map(mapping)
    empty = text.isna() | text.eq("").fillna(False)
    unknown = label.isna() & ~empty
    keep = ~empty & ~unknown
    result = pd.DataFrame(
        {"text": text[keep], "label": label[keep], "source": source, "lang_hint": lang}
    ).reset_index(drop=True)
    result.attrs["counts"] = {
        "input_rows": len(frame),
        "empty_rows": int(empty.sum()),
        "unmapped_rows": int(unknown.sum()),
        "retained_rows": len(result),
    }
    return result


def load_uci(path: Path) -> pd.DataFrame:
    """Read UCI's headerless CSV, ignoring its optional third column."""
    frame = read_table(path, header=None, usecols=[0, 1], names=["text", "label"])
    return map_rows(
        frame, {"positive": "normal", "neutral": "normal"}, "uci", "roman_urdu"
    )


def load_ruhsold(path: Path) -> pd.DataFrame:
    """Read a reviewed UTF-8 CSV export with text and original label columns."""
    mapping = {
        "normal": "normal",
        "offensive": "abusive",
        "abusive": "abusive",
        "hate": "abusive",
        "abusive/offensive": "abusive",
        "religious hate": "abusive",
        "sexism": "abusive",
        "profane/untargeted": "abusive",
        "0": "abusive",
        "1": "normal",
        "2": "abusive",
        "3": "abusive",
        "4": "abusive",
    }
    return map_rows(read_table(path), mapping, "ruhsold", "roman_urdu")


def load_sms(path: Path) -> pd.DataFrame:
    """Read the original label-tab-message format without CSV quote semantics."""
    frame = read_table(
        path, sep="\t", header=None, names=["label", "text"], quoting=csv.QUOTE_NONE
    )
    return map_rows(frame, {"ham": "normal", "spam": "scam"}, "sms", "en")


def load_custom(path: Path) -> pd.DataFrame:
    """Read the human-reviewed synthetic corpus specified in TECH_DOC 6.3."""
    frame = read_table(path)
    if not {"text", "label", "theme", "source", "annotator"}.issubset(frame.columns):
        raise ValueError("Custom CSV requires text,label,theme,source,annotator.")
    return map_rows(frame, {"normal": "normal", "scam": "scam"}, "custom", "roman_urdu")


def deduplicate(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Remove conflicting labels entirely; prefer custom provenance for duplicates."""
    frame = frame.copy()
    frame["text"] = frame["text"].astype("string").str.strip()
    frame = frame.loc[frame["text"].notna() & frame["text"].ne("")].copy()
    conflicts = frame.groupby("text")["label"].transform("nunique").gt(1)
    conflict_rows = int(conflicts.sum())
    frame = frame.loc[~conflicts].copy()
    frame["priority"] = frame["source"].ne("custom").astype(int)
    frame = frame.sort_values(["priority", "source", "text"], kind="stable")
    before = len(frame)
    frame = frame.drop_duplicates("text").loc[:, list(COLUMNS)].reset_index(drop=True)
    return frame, {
        "conflicting_rows": conflict_rows,
        "duplicate_rows": before - len(frame),
    }


def split_frame(
    frame: pd.DataFrame, fraction: float
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split with a fixed seed and fail rather than silently lose stratification."""
    try:
        left, right = train_test_split(
            frame, test_size=fraction, stratify=frame["label"], random_state=SEED
        )
    except ValueError:
        raise ValueError("Insufficient rows per class for stratified splits.") from None
    if set(left["label"]) != set(frame["label"]) or set(right["label"]) != set(
        frame["label"]
    ):
        raise ValueError("Insufficient rows to preserve every class in each split.")
    return left.reset_index(drop=True), right.reset_index(drop=True)


def assert_disjoint(splits: dict[str, pd.DataFrame]) -> None:
    """Check exact-text leakage without including text in failures."""
    for left, right in combinations(splits.values(), 2):
        if set(left["text"]) & set(right["text"]):
            raise AssertionError("Identical text appears in multiple splits.")


def class_counts(frame: pd.DataFrame) -> dict[str, int]:
    """Return aggregate counts, including zero-count classes."""
    counts = frame["label"].value_counts()
    return {label: int(counts.get(label, 0)) for label in LABELS}


def source_counts(frame: pd.DataFrame) -> dict[str, dict[str, int]]:
    """Return class counts grouped by fixed loader provenance."""
    return {
        str(source): class_counts(group) for source, group in frame.groupby("source")
    }


def prepare(raw_dir: Path, output_dir: Path) -> dict[str, Any]:
    """Merge reviewed data, reserve custom hold-out, then save the 70/15/15 split."""
    inputs = (
        ("uci", raw_dir / "uci" / "Roman Urdu DataSet.csv", load_uci),
        ("ruhsold", raw_dir / "ruhsold" / "ruhsold.csv", load_ruhsold),
        ("sms", raw_dir / "sms" / "SMSSpamCollection", load_sms),
        ("custom", raw_dir / "custom" / "custom_scam.csv", load_custom),
    )
    missing = [name for name, path, _ in inputs if not path.is_file()]
    if missing:
        raise ValueError(
            "Missing datasets: " + ", ".join(missing) + "; see docs/DATASETS.md."
        )
    targets = (
        "all.csv",
        "train.csv",
        "val.csv",
        "test.csv",
        "custom_holdout.csv",
        "counts.json",
    )
    if any((output_dir / name).exists() for name in targets):
        raise ValueError(
            "Output exists; use a new output directory to preserve frozen splits."
        )
    frames = {name: loader(path) for name, path, loader in inputs}
    report: dict[str, Any] = {
        "random_state": SEED,
        "loaders": {name: frame.attrs["counts"] for name, frame in frames.items()},
        "source_counts_before_dedup": source_counts(pd.concat(frames.values())),
    }
    merged, report["deduplication"] = deduplicate(
        pd.concat(frames.values(), ignore_index=True)
    )
    report["source_counts_after_dedup"] = source_counts(merged)
    custom = merged.loc[merged["source"].eq("custom")]
    if set(custom["label"]) != {"normal", "scam"}:
        raise ValueError("Custom corpus must retain both normal and scam rows.")
    custom_pool, holdout = split_frame(custom, 0.20)
    pool = pd.concat(
        [merged.loc[merged["source"].ne("custom")], custom_pool], ignore_index=True
    )
    pool = pool.sort_values(["source", "text"], kind="stable").reset_index(drop=True)
    if set(pool["label"]) != set(LABELS):
        raise ValueError("Merged corpus must contain normal, abusive and scam classes.")
    train, remainder = split_frame(pool, 0.30)
    val, test = split_frame(remainder, 0.50)
    splits = {"train": train, "val": val, "test": test, "custom_holdout": holdout}
    assert_disjoint(splits)
    report["all"] = {"rows": len(pool), "class_counts": class_counts(pool)}
    report["splits"] = {
        name: {
            "rows": len(frame),
            "class_counts": class_counts(frame),
            "by_source": source_counts(frame),
        }
        for name, frame in splits.items()
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, frame in {"all": pool, **splits}.items():
        frame.to_csv(output_dir / f"{name}.csv", index=False, encoding="utf-8")
    (output_dir / "counts.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    """Run preparation without dumping corpus contents or parser exceptions."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_DATA / "raw")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_DATA / "processed")
    args = parser.parse_args()
    try:
        report = prepare(args.raw_dir, args.output_dir)
    except (ValueError, OSError):
        parser.exit(
            1,
            "Data preparation failed: verify inputs, class sizes and unused output directory; see docs/DATASETS.md.\n",
        )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
