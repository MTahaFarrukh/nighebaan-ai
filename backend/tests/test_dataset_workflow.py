"""Synthetic-only tests for source inventories and human-review promotion."""

import json
from pathlib import Path

import pandas as pd
import pytest
from ml.audit_sources import inspect_rows
from ml.custom_dataset import THEMES, build_pack, promote


@pytest.fixture
def pack(tmp_path: Path) -> Path:
    seeds = {
        theme: {
            label: [f"synthetic {theme} {label} {i}" for i in range(count)]
            for label, count in (("scam", 5), ("normal", 3))
        }
        for theme in THEMES
    }
    path = tmp_path / "seeds.json"
    path.write_text(json.dumps(seeds), encoding="utf-8")
    directory = tmp_path / "review"
    build_pack(path, directory)
    return directory


def complete_synthetic_review(directory: Path) -> None:
    """Simulate human input exclusively for generated test placeholders."""
    draft = pd.read_csv(directory / "custom_scam.draft.csv").set_index("id")
    for filename, reviewer in (
        ("review_all.csv", "reviewer_final"),
        ("reviewer_a.csv", "reviewer_a"),
        ("reviewer_b.csv", "reviewer_b"),
    ):
        path = directory / filename
        table = pd.read_csv(path, keep_default_na=False)
        table["label"] = table["id"].map(draft["label"])
        table["reviewer"] = reviewer
        if filename == "review_all.csv":
            table["privacy_ok"] = "yes"
        table.to_csv(path, index=False)


def test_pack_is_blind_and_meets_targets(pack: Path) -> None:
    manifest = json.loads((pack / "manifest.json").read_text())
    assert manifest["class_counts"] == {"scam": 500, "normal": 300}
    assert manifest["families"] == 80
    draft = pd.read_csv(pack / "custom_scam.draft.csv", keep_default_na=False)
    assert draft["annotator"].eq("").all()
    assert draft["source"].eq("llm_assisted").all()
    sample = pd.read_csv(pack / "reviewer_a.csv", keep_default_na=False)
    assert list(sample.columns) == ["id", "text", "label", "reviewer"]
    assert len(sample) == 100 and sample["label"].eq("").all()
    assert not (pack / "custom_scam.csv").exists()


def test_unreviewed_cannot_be_promoted(pack: Path) -> None:
    with pytest.raises(ValueError, match="human"):
        promote(pack, pack / "approved.csv")
    assert not (pack / "approved.csv").exists()


def test_completed_review_agreement_and_no_overwrite(pack: Path) -> None:
    complete_synthetic_review(pack)
    report = promote(pack, pack / "approved.csv")
    assert report["cohens_kappa"] == 1.0
    assert report["rows"] == 800
    assert report["sample_disagreements"] == 0
    assert list(pd.read_csv(pack / "approved.csv").columns) == [
        "text",
        "label",
        "theme",
        "source",
        "annotator",
    ]
    with pytest.raises(ValueError, match="exists"):
        promote(pack, pack / "approved.csv")


@pytest.mark.parametrize(
    "problem",
    ["same_reviewer", "missing_id", "missing_privacy", "changed_text", "changed_draft"],
)
def test_invalid_reviews_rejected(pack: Path, problem: str) -> None:
    complete_synthetic_review(pack)
    filename = "reviewer_b.csv" if problem == "same_reviewer" else "review_all.csv"
    if problem == "changed_draft":
        filename = "custom_scam.draft.csv"
    path = pack / filename
    table = pd.read_csv(path, keep_default_na=False)
    if problem == "same_reviewer":
        table["reviewer"] = "reviewer_a"
    elif problem == "missing_id":
        table = table.iloc[1:]
    elif problem == "missing_privacy":
        table.loc[0, "privacy_ok"] = ""
    else:
        table.loc[0, "text"] = "synthetic changed placeholder"
    table.to_csv(path, index=False)
    with pytest.raises(ValueError):
        promote(pack, pack / "approved.csv")


def test_kappa_uses_independent_labels(pack: Path) -> None:
    complete_synthetic_review(pack)
    path = pack / "reviewer_b.csv"
    table = pd.read_csv(path)
    table.loc[0, "label"] = "normal" if table.loc[0, "label"] == "scam" else "scam"
    table.to_csv(path, index=False)
    result = promote(pack, pack / "approved.csv")
    assert result["sample_disagreements"] == 1
    assert 0 < result["cohens_kappa"] < 1


def test_audit_suppresses_unknown_label_content() -> None:
    result = inspect_rows(
        b"placeholder,Positive\nplaceholder,Neutral\nother,Negative\nx,private_sentinel\n",
        "uci",
    )
    assert result["mapped_class_counts_before_dedup"] == {"normal": 2}
    assert result["mapped_duplicate_text_rows"] == 1
    assert result["original_label_counts"]["unknown"] == 1
    assert "private_sentinel" not in json.dumps(result)


def test_native_sms_and_ruhsold_formats() -> None:
    assert inspect_rows(b"ham\tplaceholder\nspam\tother\n", "sms")[
        "mapped_class_counts_before_dedup"
    ] == {"normal": 1, "scam": 1}
    assert inspect_rows(b"placeholder\t0\nother\t1\n", "ruhsold")[
        "mapped_class_counts_before_dedup"
    ] == {"abusive": 1, "normal": 1}
