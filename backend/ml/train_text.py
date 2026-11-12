"""Train the NB baseline on train only; select/report on validation only."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

import joblib
import pandas as pd
import sklearn
from app.services.text_transformer import TextPreprocessor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import FeatureUnion, Pipeline

LABELS = ["normal", "abusive", "scam"]


def build_pipeline() -> Pipeline:
    """Bundle preprocessing resources, both TF-IDF views and MultinomialNB."""
    return Pipeline(
        [
            ("preprocess", TextPreprocessor()),
            (
                "features",
                FeatureUnion(
                    [
                        ("word", TfidfVectorizer(ngram_range=(1, 2), lowercase=False)),
                        (
                            "char",
                            TfidfVectorizer(
                                analyzer="char_wb", ngram_range=(2, 5), lowercase=False
                            ),
                        ),
                    ]
                ),
            ),
            ("classifier", MultinomialNB()),
        ]
    )


def train(
    data: Path,
    output: Path,
    *,
    in_memory: tuple[pd.DataFrame, pd.DataFrame] | None = None,
) -> dict:
    """Refuse leakage and write validation-only artifacts in a fresh directory."""
    if output.exists():
        raise ValueError("Use a new output directory.")
    frames = (
        list(in_memory)
        if in_memory is not None
        else [
            pd.read_csv(data / f"{name}.csv", dtype=str, keep_default_na=False)
            for name in ("train", "val")
        ]
    )
    for frame in frames:
        if not {"text", "label"}.issubset(frame.columns):
            raise ValueError("Missing columns.")
        if set(frame.label) != set(LABELS) or frame.text.str.strip().eq("").any():
            raise ValueError("Invalid labels or empty text.")
        if frame.text.str.strip().duplicated().any():
            raise ValueError("Duplicate text within split.")
    training, validation = frames
    if set(training.text.str.strip()) & set(validation.text.str.strip()):
        raise ValueError("Train/validation leakage.")
    model = build_pipeline().fit(training.text.tolist(), training.label.tolist())
    started = perf_counter()
    predicted = model.predict(validation.text.tolist())
    latency_ms = (perf_counter() - started) * 1000 / len(validation)
    report = {
        "model": "nb_baseline",
        "evaluation_split": "validation",
        "train_rows": len(training),
        "val_rows": len(validation),
        "macro_f1": float(f1_score(validation.label, predicted, average="macro")),
        "labels": LABELS,
        "confusion_matrix": confusion_matrix(
            validation.label, predicted, labels=LABELS
        ).tolist(),
        "classification_report": classification_report(
            validation.label,
            predicted,
            labels=LABELS,
            output_dict=True,
            zero_division=0,
        ),
    }
    output.mkdir(parents=True)
    joblib.dump(model, output / "nb_baseline.joblib")
    (output / "validation_metrics.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    timestamp = datetime.now(UTC).isoformat()
    detail = report["classification_report"]
    metrics = {
        "generated_at": timestamp,
        "evaluation_split": "validation",
        "dataset": {
            "train": len(training),
            "val": len(validation),
            "test": None,
            "class_counts": {
                label: int((training.label == label).sum()) for label in LABELS
            },
        },
        "models": [
            {
                "name": "nb_baseline",
                "macro_f1": report["macro_f1"],
                "accuracy": detail["accuracy"],
                "latency_ms": latency_ms,
                "per_class": {
                    label: {
                        "p": detail[label]["precision"],
                        "r": detail[label]["recall"],
                        "f1": detail[label]["f1-score"],
                    }
                    for label in LABELS
                },
                "confusion_matrix": report["confusion_matrix"],
            }
        ],
        "ablations": [],
        "best_model": "nb_baseline",
    }
    metadata = {
        "generated_at": timestamp,
        "python": platform.python_version(),
        "sklearn": sklearn.__version__,
        "pandas": pd.__version__,
        "evaluation_split": "validation",
        "test_accessed": False,
        "data_review_status": "not_verified_by_trainer",
        "input_sha256": {
            name: hashlib.sha256(frame.to_csv(index=False).encode()).hexdigest()
            for name, frame in zip(("train", "val"), frames, strict=True)
        },
        "parameters": {"alpha": 1.0, "word_ngrams": [1, 2], "char_ngrams": [2, 5]},
        "source_sha256": {
            name: hashlib.sha256(path.read_bytes()).hexdigest()
            for name, path in (
                ("trainer", Path(__file__)),
                (
                    "preprocess",
                    Path(__file__).parents[1] / "app/services/preprocess.py",
                ),
                (
                    "transformer",
                    Path(__file__).parents[1] / "app/services/text_transformer.py",
                ),
            )
        },
    }
    for name, payload in [
        ("metrics", metrics),
        ("run_metadata", metadata),
        ("label_map", {"labels": LABELS, "probability_order": model.classes_.tolist()}),
    ]:
        (output / f"{name}.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )
    pd.DataFrame(
        [
            {
                "timestamp": timestamp,
                "model": "nb_baseline",
                "params": json.dumps(metadata["parameters"]),
                "val_macro_f1": report["macro_f1"],
            }
        ]
    ).to_csv(output / "experiments.csv", index=False)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data/processed"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = train(args.data, args.output)
    except (OSError, ValueError):
        parser.exit(
            1,
            "Training failed: check approved inputs, split integrity and output directory.\n",
        )
    print(json.dumps(result, indent=2))
