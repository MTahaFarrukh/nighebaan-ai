"""Synthetic-only checks for mappings, leakage and offline CLI behavior."""

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from ml.data_prep import (
    COLUMNS,
    assert_disjoint,
    deduplicate,
    load_custom,
    load_ruhsold,
    load_sms,
    load_uci,
    prepare,
    split_frame,
)


@pytest.fixture
def raw_dir(tmp_path: Path) -> Path:
    """Build all supported input formats with placeholder-only content."""
    raw = tmp_path / "raw"
    for name in ("uci", "ruhsold", "sms", "custom"):
        (raw / name).mkdir(parents=True)
    pd.DataFrame(
        [(f"synthetic uci acha {i}", "Positive", "") for i in range(40)]
        + [("synthetic excluded", "Negative", "")]
    ).to_csv(raw / "uci" / "Roman Urdu DataSet.csv", header=False, index=False)
    pd.DataFrame(
        [(f"synthetic ruhsold placeholder {i}", "0") for i in range(40)],
        columns=["text", "label"],
    ).to_csv(raw / "ruhsold" / "ruhsold.csv", index=False)
    (raw / "sms" / "SMSSpamCollection").write_text(
        "".join(f"spam\tsynthetic sms placeholder {i}\n" for i in range(40)),
        encoding="utf-8",
    )
    pd.DataFrame(
        [
            (f"synthetic custom {label} {i}", label, "demo", "template", "reviewer_a")
            for label in ("normal", "scam")
            for i in range(50)
        ],
        columns=["text", "label", "theme", "source", "annotator"],
    ).to_csv(raw / "custom" / "custom_scam.csv", index=False)
    return raw


def test_uci_mapping_empty_and_unknown(tmp_path: Path) -> None:
    path = tmp_path / "uci.csv"
    pd.DataFrame(
        [
            [" acha ", "Positive"],
            ["theek", " Neutral "],
            ["nhi", "Negative"],
            [None, "Positive"],
            ["   ", "Neutral"],
            ["placeholder", "unexpected"],
        ]
    ).to_csv(path, header=False, index=False)
    frame = load_uci(path)
    assert frame["text"].tolist() == ["acha", "theek"]
    assert frame["label"].tolist() == ["normal", "normal"]
    assert frame.attrs["counts"] == {
        "input_rows": 6,
        "empty_rows": 2,
        "unmapped_rows": 2,
        "retained_rows": 2,
    }


def test_ruhsold_verified_label_mapping(tmp_path: Path) -> None:
    path = tmp_path / "ruhsold.csv"
    labels = [
        "0",
        "1",
        "2",
        "3",
        "4",
        "normal",
        "offensive",
        "abusive",
        "hate",
        "negative",
    ]
    pd.DataFrame(
        {"text": [f"placeholder {i}" for i in range(len(labels))], "label": labels}
    ).to_csv(path, index=False)
    frame = load_ruhsold(path)
    assert frame["label"].tolist() == [
        "abusive",
        "normal",
        "abusive",
        "abusive",
        "abusive",
        "normal",
        "abusive",
        "abusive",
        "abusive",
    ]
    assert frame.attrs["counts"]["unmapped_rows"] == 1


def test_sms_quotes_and_labels(tmp_path: Path) -> None:
    path = tmp_path / "sms"
    path.write_text(
        'ham\t"synthetic quoted placeholder"\nspam\tsynthetic scam placeholder\n',
        encoding="utf-8",
    )
    frame = load_sms(path)
    assert frame["label"].tolist() == ["normal", "scam"]
    assert frame["text"].iloc[0] == '"synthetic quoted placeholder"'
    assert set(frame["lang_hint"]) == {"en"}


def test_custom_requires_provenance(tmp_path: Path) -> None:
    path = tmp_path / "custom.csv"
    path.write_text("text,label\nplaceholder,normal\n", encoding="utf-8")
    with pytest.raises(ValueError, match="theme,source,annotator"):
        load_custom(path)


def test_dedupe_conflicts_and_custom_priority() -> None:
    frame = pd.DataFrame(
        [
            [" same ", "normal", "uci", "roman_urdu"],
            ["same", "normal", "custom", "roman_urdu"],
            ["conflict", "normal", "uci", "roman_urdu"],
            ["conflict", "abusive", "ruhsold", "roman_urdu"],
        ],
        columns=COLUMNS,
    )
    clean, counts = deduplicate(frame)
    assert len(clean) == 1
    assert clean.iloc[0]["source"] == "custom"
    assert counts == {"conflicting_rows": 2, "duplicate_rows": 1}


def test_full_pipeline_determinism_and_holdout(raw_dir: Path, tmp_path: Path) -> None:
    first, second = tmp_path / "first", tmp_path / "second"
    report = prepare(raw_dir, first)
    assert prepare(raw_dir, second) == report
    for path in first.iterdir():
        assert path.read_bytes() == (second / path.name).read_bytes()
    splits = {
        name: pd.read_csv(first / f"{name}.csv")
        for name in ("train", "val", "test", "custom_holdout")
    }
    assert_disjoint(splits)
    assert [len(splits[name]) for name in splits] == [140, 30, 30, 20]
    for name in ("train", "val", "test"):
        assert set(splits[name]["label"]) == {"normal", "abusive", "scam"}
        assert tuple(splits[name].columns) == COLUMNS
    pool = pd.read_csv(first / "all.csv")
    assert set(pool["text"]) == set(
        pd.concat([splits[n] for n in ("train", "val", "test")])["text"]
    )
    assert not set(pool["text"]) & set(splits["custom_holdout"]["text"])
    assert set(splits["custom_holdout"]["source"]) == {"custom"}
    assert report["all"]["rows"] == 200
    with pytest.raises(ValueError, match="Output exists"):
        prepare(raw_dir, first)


def test_cross_source_duplicate_cannot_leak(raw_dir: Path, tmp_path: Path) -> None:
    with (raw_dir / "sms" / "SMSSpamCollection").open("a", encoding="utf-8") as stream:
        stream.write("ham\tsynthetic custom normal 0\n")
    report = prepare(raw_dir, tmp_path / "output")
    assert report["deduplication"]["duplicate_rows"] == 1
    assert report["all"]["rows"] == 200


def test_leakage_assertion_and_tiny_class() -> None:
    frame = pd.DataFrame({"text": ["placeholder"], "label": ["normal"]})
    with pytest.raises(AssertionError, match="Identical text"):
        assert_disjoint({"train": frame, "test": frame})
    with pytest.raises(ValueError, match="Insufficient"):
        split_frame(frame, 0.30)


def test_missing_inputs_write_nothing(tmp_path: Path) -> None:
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="Missing datasets"):
        prepare(tmp_path, output)
    assert not output.exists()


def test_cli_aggregate_only(raw_dir: Path, tmp_path: Path) -> None:
    command = [
        sys.executable,
        "-m",
        "ml.data_prep",
        "--raw-dir",
        str(raw_dir),
        "--output-dir",
        str(tmp_path / "output"),
    ]
    backend = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        command, cwd=backend, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["all"]["rows"] == 200
    assert "synthetic" not in result.stdout + result.stderr
    result = subprocess.run(
        command, cwd=backend, capture_output=True, text=True, check=False
    )
    assert result.returncode == 1
    assert "Traceback" not in result.stderr


def test_parser_errors_do_not_expose_content(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text('text,label\n"synthetic private sentinel', encoding="utf-8")
    with pytest.raises(ValueError) as error:
        load_ruhsold(path)
    assert "sentinel" not in str(error.value)
