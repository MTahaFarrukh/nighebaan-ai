"""Synthetic M4 scoring and frozen-source integrity checks."""

import pytest
from ml.train_improved import candidates, score_model, verify_partitions
from ml.train_text import build_pipeline


def test_partition_drift_rejected() -> None:
    original = {
        "source_inventory_sha256": "a",
        "custom_draft_sha256": "b",
        "splits": {"train": "c"},
    }
    verify_partitions(original, original)
    with pytest.raises(ValueError, match="changed"):
        verify_partitions({**original, "splits": {}}, original)


def test_search_models_balanced() -> None:
    for estimator, grid in candidates().values():
        assert estimator.class_weight == "balanced"
        assert estimator.random_state == 42
        assert len(next(iter(grid.values()))) == 2


def test_metrics_probability_alignment() -> None:
    texts = ["salam acha", "synthetic hostile", "otp inaam"]
    labels = ["normal", "abusive", "scam"]
    model = build_pipeline().fit(texts, labels)
    result = score_model(model, texts, labels, "synthetic")
    assert result["macro_f1"] == 1.0
    assert result["roc_auc_ovr"] == 1.0
    assert result["confusion_matrix"] == [[1, 0, 0], [0, 1, 0], [0, 0, 1]]


def test_end_to_end_resume_without_refitting(tmp_path, monkeypatch) -> None:
    import json

    import joblib
    import pandas as pd
    from ml import train_improved as module
    from sklearn.linear_model import LogisticRegression
    from sklearn.naive_bayes import MultinomialNB

    training = pd.DataFrame(
        [
            {"text": f"{word} synthetic train {i}", "label": label}
            for label, word in [
                ("normal", "salam acha"),
                ("abusive", "hostile placeholder"),
                ("scam", "otp inaam"),
            ]
            for i in range(10)
        ]
    )
    validation = pd.DataFrame(
        [
            {"text": f"{word} synthetic validation", "label": label}
            for label, word in [
                ("normal", "salam acha"),
                ("abusive", "hostile placeholder"),
                ("scam", "otp inaam"),
            ]
        ]
    )
    manifest = {
        "source_inventory_sha256": "a",
        "custom_draft_sha256": "b",
        "splits": {"train": {"rows": 30}, "val": {"rows": 3}},
        "status": "synthetic_test",
    }
    monkeypatch.setattr(
        module,
        "prepare_partitions",
        lambda: ({"train": training, "val": validation}, manifest),
    )
    monkeypatch.setattr(
        module,
        "candidates",
        lambda: {
            "lr": (
                LogisticRegression(class_weight="balanced"),
                {"classifier__C": [1.0]},
            ),
            "nb": (MultinomialNB(), {"classifier__alpha": [1.0]}),
        },
    )
    baseline = tmp_path / "baseline"
    baseline.mkdir()
    model = build_pipeline().fit(training.text.tolist(), training.label.tolist())
    joblib.dump(model, baseline / "nb_baseline.joblib")
    (baseline / "data_manifest.json").write_text(json.dumps(manifest))
    (baseline / "metrics.json").write_text(
        json.dumps(
            {
                "models": [
                    score_model(
                        model,
                        validation.text.tolist(),
                        validation.label.tolist(),
                        "nb_baseline",
                    )
                ],
                "dataset": {"train": 30, "val": 3, "test": None},
            }
        )
    )
    first = module.run(tmp_path / "run", baseline)
    assert len(first["models"]) == 4
    assert (tmp_path / "run/text_clf.joblib").exists()

    def no_fit(*args, **kwargs):
        raise AssertionError("Completed checkpoints must not refit")

    monkeypatch.setattr(module.GridSearchCV, "fit", no_fit)
    monkeypatch.setattr(module.VotingClassifier, "fit", no_fit)
    second = module.run(tmp_path / "run", baseline)
    assert second["best_model"] == first["best_model"]
