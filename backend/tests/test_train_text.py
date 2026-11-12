"""Synthetic baseline integration checks, never project evaluation."""

from pathlib import Path

import joblib
import pandas as pd
import pytest
from ml.train_text import train


@pytest.fixture
def dataset(tmp_path: Path) -> Path:
    for split, suffix in [("train", "training"), ("val", "validation")]:
        rows = [
            {"text": f"{word} {suffix} {i}", "label": label}
            for label, word in [
                ("normal", "salam acha"),
                ("abusive", "synthetic hostile"),
                ("scam", "otp inaam"),
            ]
            for i in range(4)
        ]
        pd.DataFrame(rows).to_csv(tmp_path / f"{split}.csv", index=False)
    return tmp_path


def test_baseline_reload_and_test_not_read(
    dataset: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = pd.read_csv

    def guarded(path, *args, **kwargs):
        assert Path(path).name != "test.csv"
        return original(path, *args, **kwargs)

    monkeypatch.setattr(pd, "read_csv", guarded)
    result = train(dataset, dataset / "run")
    assert result["evaluation_split"] == "validation"
    assert 0 <= result["macro_f1"] <= 1
    model = joblib.load(dataset / "run/nb_baseline.joblib")
    assert set(model.classes_) == {"normal", "abusive", "scam"}
    assert len(model.predict(["synthetic placeholder"])) == 1
    assert (dataset / "run/metrics.json").exists()
    assert (dataset / "run/run_metadata.json").exists()
    assert (dataset / "run/experiments.csv").exists()
    with pytest.raises(ValueError):
        train(dataset, dataset / "run")


def test_leakage_rejected(dataset: Path) -> None:
    training = pd.read_csv(dataset / "train.csv")
    validation = pd.read_csv(dataset / "val.csv")
    validation.loc[0, "text"] = training.loc[0, "text"]
    validation.to_csv(dataset / "val.csv", index=False)
    with pytest.raises(ValueError, match="leakage"):
        train(dataset, dataset / "run")
    assert not (dataset / "run").exists()


def test_missing_class_rejected(dataset: Path) -> None:
    frame = pd.read_csv(dataset / "train.csv")
    frame[frame.label != "abusive"].to_csv(dataset / "train.csv", index=False)
    with pytest.raises(ValueError, match="labels"):
        train(dataset, dataset / "run")


def test_in_memory_training_does_not_read_csv(
    dataset: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    frames = tuple(pd.read_csv(dataset / f"{name}.csv") for name in ("train", "val"))

    def forbidden(*args, **kwargs):
        raise AssertionError("In-memory training must not read corpus files")

    monkeypatch.setattr(pd, "read_csv", forbidden)
    result = train(Path("not-present"), dataset / "memory_run", in_memory=frames)
    assert result["evaluation_split"] == "validation"


def test_preliminary_sanitization() -> None:
    from ml.train_preliminary import sanitize

    result = sanitize(
        "demo@example.com @demo_handle +00 000 000 0000 https://example.com/PrivateCase"
    )
    assert result == "emailtoken handletoken phonetoken urltoken"


def test_preliminary_rejects_changed_source(monkeypatch: pytest.MonkeyPatch) -> None:
    from ml.train_preliminary import load_public

    monkeypatch.setattr("ml.train_preliminary.fetch", lambda url: b"synthetic")
    with pytest.raises(ValueError, match="changed"):
        load_public(
            {"sources": [{"url": "https://example.com", "archive_sha256": "wrong"}]}
        )
