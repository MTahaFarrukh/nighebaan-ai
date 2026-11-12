"""Promote the trusted local preliminary ensemble without retraining."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
from app.services.model_input import ModelInputSanitizer
from sklearn.pipeline import Pipeline


def promote(source: Path, destination: Path) -> None:
    """Freeze training-time outer cleaning and write a fingerprinted API artifact."""
    if destination.exists():
        raise ValueError(
            "Promoted artifact exists; archive it before intentional replacement."
        )
    metrics = json.loads((source / "metrics.json").read_text(encoding="utf-8"))
    if metrics["best_model"] != "voting_ensemble":
        raise ValueError("This promotion expects the selected LR/SVM ensemble.")
    ensemble = joblib.load(source / "text_clf.joblib")
    mapping = dict(
        ensemble.named_estimators_["lr"].named_steps["preprocess"].normalization_map_
    )
    pipeline = Pipeline(
        [("input", ModelInputSanitizer(mapping)), ("classifier", ensemble)]
    )
    values = pipeline.predict_proba(["synthetic placeholder"])
    if (
        values.shape != (1, 3)
        or not np.isfinite(values).all()
        or not np.allclose(values.sum(axis=1), 1)
    ):
        raise ValueError("Invalid artifact probabilities.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, destination)
    manifest = {
        "model": "voting_ensemble",
        "status": "preliminary_human_unverified",
        "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "source_sha256": hashlib.sha256(
            (source / "text_clf.joblib").read_bytes()
        ).hexdigest(),
        "probability_order": pipeline.classes_.tolist(),
    }
    destination.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    for name in ("metrics.json", "label_map.json"):
        (destination.parent / name).write_bytes((source / name).read_bytes())


if __name__ == "__main__":
    base = Path(__file__).resolve().parents[1] / "models"
    promote(base / "m4_preliminary_001", base / "text_clf.joblib")
    print("Preliminary ensemble promoted; no retraining or test evaluation.")
