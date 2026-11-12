"""Resumable balanced-model tuning using frozen preliminary validation partitions."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

import joblib
import pandas as pd
import sklearn
from ml.train_preliminary import prepare_partitions
from ml.train_text import LABELS, build_pipeline
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.svm import LinearSVC


def verify_partitions(current: dict, baseline: dict) -> None:
    """Reject source or frozen-partition drift before fitting."""
    for key in ("source_inventory_sha256", "custom_draft_sha256", "splits"):
        if current[key] != baseline[key]:
            raise ValueError("Frozen source or partition changed.")


def candidates() -> dict:
    """Small predetermined balanced search spaces."""
    return {
        "lr": (
            LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42),
            {"classifier__C": [0.5, 2.0]},
        ),
        "svm": (
            LinearSVC(class_weight="balanced", max_iter=5000, random_state=42),
            {"classifier__C": [0.5, 2.0]},
        ),
        "rf": (
            RandomForestClassifier(
                class_weight="balanced", n_estimators=80, n_jobs=2, random_state=42
            ),
            {"classifier__max_depth": [30, None]},
        ),
    }


def score_model(model: object, texts: list[str], labels: list[str], name: str) -> dict:
    """Return aggregate validation metrics in explicit display-label order."""
    start = perf_counter()
    predicted = model.predict(texts)
    latency = (perf_counter() - start) * 1000 / len(texts)
    detail = classification_report(
        labels, predicted, labels=LABELS, output_dict=True, zero_division=0
    )
    return {
        "name": name,
        "macro_f1": detail["macro avg"]["f1-score"],
        "accuracy": detail["accuracy"],
        "latency_ms": latency,
        "per_class": {
            label: {
                "p": detail[label]["precision"],
                "r": detail[label]["recall"],
                "f1": detail[label]["f1-score"],
            }
            for label in LABELS
        },
        "confusion_matrix": confusion_matrix(labels, predicted, labels=LABELS).tolist(),
        "roc_auc_ovr": float(
            roc_auc_score(
                labels,
                model.predict_proba(texts),
                labels=model.classes_,
                multi_class="ovr",
            )
        ),
    }


def run(output: Path, baseline: Path) -> dict:
    """Fit training folds only, checkpoint each model, and select on validation."""
    splits, manifest = prepare_partitions()
    verify_partitions(
        manifest, json.loads((baseline / "data_manifest.json").read_text())
    )
    metadata = {
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "partitions": manifest["splits"],
        "sklearn": sklearn.__version__,
        "data_review_status": manifest["status"],
        "test_evaluated": False,
        "cv": "five shuffled stratified folds, seed 42",
        "word_max_features": 15000,
        "char_max_features": 25000,
    }
    output.mkdir(parents=True, exist_ok=True)
    meta = output / "run_metadata.json"
    if meta.exists() and json.loads(meta.read_text()) != metadata:
        raise ValueError("Resume configuration changed.")
    meta.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (output / "data_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    X, y = splits["train"].text.tolist(), splits["train"].label.tolist()
    V, vy = splits["val"].text.tolist(), splits["val"].label.tolist()
    models, rows, experiments = {}, [], []
    for name, (estimator, grid) in candidates().items():
        artifact, result_path = output / f"{name}.joblib", output / f"{name}.json"
        if artifact.exists() and result_path.exists():
            models[name] = joblib.load(artifact)
            result = json.loads(result_path.read_text())
        else:
            print(json.dumps({"training": name}), flush=True)
            pipeline = build_pipeline()
            pipeline.set_params(
                classifier=estimator,
                features__word__max_features=15000,
                features__char__max_features=25000,
            )
            search = GridSearchCV(
                pipeline,
                grid,
                scoring="f1_macro",
                cv=StratifiedKFold(5, shuffle=True, random_state=42),
                n_jobs=1,
                error_score="raise",
            )
            search.fit(X, y)
            model = search.best_estimator_
            if name == "svm":
                model = CalibratedClassifierCV(
                    model, cv=StratifiedKFold(3, shuffle=True, random_state=42)
                )
                model.fit(X, y)
            models[name] = model
            result = {
                "metrics": score_model(model, V, vy, name),
                "best_params": search.best_params_,
                "cv_scores": [
                    {"params": params, "mean_macro_f1": float(score)}
                    for params, score in zip(
                        search.cv_results_["params"],
                        search.cv_results_["mean_test_score"],
                        strict=True,
                    )
                ],
            }
            joblib.dump(model, artifact)
            result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        rows.append(result["metrics"])
        experiments.extend(
            {
                "model": name,
                "params": json.dumps(item["params"]),
                "train_cv_macro_f1": item["mean_macro_f1"],
                "val_macro_f1": result["metrics"]["macro_f1"],
            }
            for item in result["cv_scores"]
        )
        pd.DataFrame(experiments).to_csv(output / "experiments.csv", index=False)
        print(json.dumps(result["metrics"]), flush=True)
    top = sorted(rows, key=lambda row: row["macro_f1"], reverse=True)[:2]
    ensemble_path = output / "voting_ensemble.joblib"
    if ensemble_path.exists():
        ensemble = joblib.load(ensemble_path)
    else:
        print(json.dumps({"training": "voting_ensemble"}), flush=True)
        ensemble = VotingClassifier(
            [(row["name"], models[row["name"]]) for row in top], voting="soft"
        )
        ensemble.fit(X, y)
        joblib.dump(ensemble, ensemble_path)
    models["voting_ensemble"] = ensemble
    rows.append(score_model(ensemble, V, vy, "voting_ensemble"))
    baseline_metrics = json.loads((baseline / "metrics.json").read_text())
    rows.insert(0, baseline_metrics["models"][0])
    best = max(rows, key=lambda row: row["macro_f1"])["name"]
    selected = (
        joblib.load(baseline / "nb_baseline.joblib")
        if best == "nb_baseline"
        else models[best]
    )
    joblib.dump(selected, output / "text_clf.joblib")
    metrics = {
        "generated_at": datetime.now(UTC).isoformat(),
        "evaluation_split": "validation",
        "data_review_status": manifest["status"],
        "dataset": baseline_metrics["dataset"],
        "models": rows,
        "ablations": [],
        "best_model": best,
    }
    (output / "metrics.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8"
    )
    (output / "label_map.json").write_text(
        json.dumps({"labels": LABELS, "probability_order": selected.classes_.tolist()}),
        encoding="utf-8",
    )
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--baseline", type=Path, default=Path("models/nb_preliminary_001")
    )
    args = parser.parse_args()
    try:
        result = run(args.output, args.baseline)
    except (OSError, ValueError, KeyError, TypeError):
        parser.exit(
            1,
            "M4 run failed; inspect configuration and completed checkpoints. No input text logged.\n",
        )
    print(json.dumps(result, indent=2))
