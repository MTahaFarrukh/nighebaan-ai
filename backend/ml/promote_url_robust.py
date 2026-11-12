"""Promote only a verified local URL candidate that passes robustness and recall gates."""

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
from app.services.url_classifier import MODEL_PATH
from ml.train_url import record_experiments
from ml.url_data import ROOT


def check_gate(result: dict) -> None:
    """Reject test evaluation, training overlap, recall loss or excessive stress errors."""
    if (
        result.get("test_evaluated") is not False
        or result.get("evaluation_split") != "validation"
    ):
        raise ValueError("Validation-only results required.")
    if not result.get("www_invariance") or result.get("stress_training_overlap") != 0:
        raise ValueError("Missing hostname robustness or training overlap.")
    before, after = result["rows"]
    baseline, candidate = before["original_validation"], after["original_validation"]
    if (
        candidate["macro_f1"] < baseline["macro_f1"] - 0.02
        or candidate["per_class"]["phishing"]["r"]
        < baseline["per_class"]["phishing"]["r"] - 0.02
    ):
        raise ValueError("Source-validation regression gate failed.")
    for key in (
        "synthetic_path_stress",
        "synthetic_no_www_root",
        "synthetic_no_www_path",
    ):
        rate = after[key]["benign_false_positive_rate"]
        if rate > 0.25 or rate >= before[key]["benign_false_positive_rate"]:
            raise ValueError("Robustness false-positive gate failed.")


def promote(run: Path) -> None:
    """Keep backups, verify synthetic regression probes, then update active metadata."""
    result = json.loads((run / "metrics.json").read_text(encoding="utf-8"))
    check_gate(result)
    if (
        hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest()
        != result["source_artifact_sha256"]
    ):
        raise ValueError("Active source model changed since experiment.")
    manifest_path = MODEL_PATH.with_suffix(".manifest.json")
    old_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    feature_bytes = (ROOT / "backend/app/services/url_features.py").read_bytes()
    feature_hash = hashlib.sha256(feature_bytes.replace(b"\r\n", b"\n")).hexdigest()
    if old_manifest["feature_code_sha256"] not in {
        feature_hash,
        hashlib.sha256(feature_bytes).hexdigest(),
    }:
        raise ValueError("Feature implementation changed since source training.")
    candidate_path = run / "candidate.joblib"
    model = joblib.load(candidate_path)
    if set(model.classes_) != {0, 1}:
        raise ValueError("Invalid candidate classes.")
    probes = [
        "https://example.com/",
        "https://www.example.com/",
        "https://www.example.com/demo",
        "https://example.com/demo",
    ]
    probabilities = np.asarray(model.predict_proba(probes))
    scores = probabilities[:, list(model.classes_).index(1)]
    if (
        not np.isfinite(probabilities).all()
        or not np.allclose(probabilities.sum(axis=1), 1)
        or (scores >= 0.70).any()
    ):
        raise ValueError("Synthetic placeholder high-risk regression.")
    metrics_path = ROOT / "backend/models/metrics.json"
    originals = {
        MODEL_PATH: MODEL_PATH.read_bytes(),
        manifest_path: manifest_path.read_bytes(),
        metrics_path: metrics_path.read_bytes(),
    }
    for path, content in originals.items():
        backup = run / ("previous_" + path.name)
        if backup.exists():
            raise ValueError(
                "Backup exists; inspect previous promotion before retrying."
            )
        backup.write_bytes(content)
    row = {
        "name": result["rows"][1]["name"],
        **result["rows"][1]["original_validation"],
    }
    matrix = row["confusion_matrix"]
    row["accuracy"] = sum(matrix[i][i] for i in range(2)) / sum(map(sum, matrix))
    active = json.loads(originals[metrics_path])
    active["url_models"] = [
        r for r in active["url_models"] if r["name"] != row["name"]
    ] + [row]
    active["best_url_model"] = row["name"]
    manifest = {
        **old_manifest,
        "sha256": hashlib.sha256(candidate_path.read_bytes()).hexdigest(),
        "best_model": row["name"],
        "feature_code_sha256": feature_hash,
        "run_id": run.name,
    }
    try:
        MODEL_PATH.write_bytes(candidate_path.read_bytes())
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        metrics_path.write_text(json.dumps(active, indent=2), encoding="utf-8")
    except OSError:
        for path, content in originals.items():
            path.write_bytes(content)
        raise
    audit = {
        "generated_at": datetime.now(UTC).isoformat(),
        "run_id": run.name,
        "sha256": manifest["sha256"],
        "synthetic_probe_scores": scores.tolist(),
        "evaluation_split": "validation",
        "test_evaluated": False,
        "models": [row],
    }
    (run / "promotion.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    record_experiments(audit, run.name)
    print("URL candidate promoted; backups and aggregate audit saved.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    try:
        promote(args.run)
    except (OSError, ValueError, KeyError, TypeError):
        parser.exit(
            1, "Promotion rejected or failed; inspect aggregate gates and backups.\n"
        )
