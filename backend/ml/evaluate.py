"""Controlled validation-only ablations; original texts and temporary models stay in memory."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import sklearn
from app.services.text_transformer import TextPreprocessor
from ml.train_improved import score_model, verify_partitions
from ml.train_preliminary import prepare_partitions, sanitize
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline

VARIANTS = (
    "normalized_both",
    "word_only",
    "char_only",
    "with_stopwords_removed",
    "without_sms",
    "raw_both",
    "no_lexical_normalization",
)


def make_pipeline(variant: str, c_value: float) -> Pipeline:
    """Keep classifier settings fixed and fit feature statistics on train only."""
    if variant not in VARIANTS:
        raise ValueError("Unknown ablation variant.")
    views = []
    if variant != "char_only":
        views.append(
            (
                "word",
                TfidfVectorizer(
                    ngram_range=(1, 2), lowercase=False, max_features=15000
                ),
            )
        )
    if variant != "word_only":
        views.append(
            (
                "char",
                TfidfVectorizer(
                    analyzer="char_wb",
                    ngram_range=(2, 5),
                    lowercase=False,
                    max_features=25000,
                ),
            )
        )
    steps = []
    if variant != "raw_both":
        steps.append(
            (
                "preprocess",
                TextPreprocessor(
                    normalize=variant != "no_lexical_normalization",
                    remove_stopwords=variant == "with_stopwords_removed",
                ),
            )
        )
    steps.extend(
        [
            ("features", FeatureUnion(views)),
            (
                "classifier",
                LogisticRegression(
                    C=c_value, class_weight="balanced", max_iter=1000, random_state=42
                ),
            ),
        ]
    )
    return Pipeline(steps)


def variant_inputs(
    variant: str, training: pd.DataFrame, validation: pd.DataFrame, raw_lookup: dict
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Preserve validation population; recover original text only through frozen keys."""
    selected = (
        training[training.source.ne("sms")] if variant == "without_sms" else training
    )
    if set(selected.label) != {"normal", "abusive", "scam"}:
        raise ValueError("Ablation training subset lost a class.")

    def texts(frame: pd.DataFrame) -> list[str]:
        if variant not in ("raw_both", "no_lexical_normalization"):
            return frame.text.tolist()
        original = [raw_lookup[(row.source, row.text)] for row in frame.itertuples()]
        return (
            [sanitize(text, normalize=False) for text in original]
            if variant == "no_lexical_normalization"
            else original
        )

    return (
        texts(selected),
        selected.label.tolist(),
        texts(validation),
        validation.label.tolist(),
    )


def run(output: Path, comparison: Path, variants: tuple[str, ...] = VARIANTS) -> dict:
    """Resume aggregate checkpoints without saving original text or ablation models."""
    raw_lookup = {}
    splits, manifest = prepare_partitions(raw_lookup=raw_lookup)
    verify_partitions(
        manifest, json.loads((comparison / "data_manifest.json").read_text())
    )
    c_value = json.loads((comparison / "lr.json").read_text())["best_params"][
        "classifier__C"
    ]
    configuration = {
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "loader_sha256": hashlib.sha256(
            Path(__file__).with_name("train_preliminary.py").read_bytes()
        ).hexdigest(),
        "splits": manifest["splits"],
        "sklearn": sklearn.__version__,
        "C": c_value,
        "test_evaluated": False,
        "data_review_status": manifest["status"],
    }
    output.mkdir(parents=True, exist_ok=True)
    meta = output / "run_metadata.json"
    if meta.exists() and json.loads(meta.read_text()) != configuration:
        raise ValueError("Ablation resume configuration changed.")
    meta.write_text(json.dumps(configuration, indent=2), encoding="utf-8")
    rows = []
    for variant in variants:
        checkpoint = output / f"{variant}.json"
        if checkpoint.exists():
            row = json.loads(checkpoint.read_text())
        else:
            print(json.dumps({"ablation": variant}), flush=True)
            X, y, V, vy = variant_inputs(
                variant, splits["train"], splits["val"], raw_lookup
            )
            model = make_pipeline(variant, c_value).fit(X, y)
            row = score_model(model, V, vy, variant)
            row.update(
                {
                    "train_rows": len(y),
                    "val_rows": len(vy),
                    "C": c_value,
                    "evaluation_split": "validation",
                }
            )
            checkpoint.write_text(json.dumps(row, indent=2), encoding="utf-8")
            del model, X, y, V, vy
        rows.append(row)
        print(json.dumps({"variant": variant, "macro_f1": row["macro_f1"]}), flush=True)
    metrics = json.loads((comparison / "metrics.json").read_text())
    metrics["generated_at"] = datetime.now(UTC).isoformat()
    metrics["ablations"] = [
        {"name": "controlled_lr_preprocessing_features_sms", "rows": rows}
    ]
    metrics["ablation_notes"] = [
        "Fixed LR C selected previously on training CV; no per-variant retuning.",
        "Raw means original text in memory, not normalize=False on already-cleaned text.",
        "No-SMS removes SMS from training only; validation unchanged.",
        "Word/char feature caps retained; word-only/char-only consequently have fewer features.",
        "Rules/hybrid comparison deferred until M5; no test predictions.",
    ]
    (output / "metrics.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8"
    )
    pd.DataFrame(
        [
            {
                "variant": row["name"],
                "train_rows": row["train_rows"],
                "val_macro_f1": row["macro_f1"],
                "C": c_value,
            }
            for row in rows
        ]
    ).to_csv(output / "experiments.csv", index=False)
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--comparison", type=Path, default=Path("models/m4_preliminary_001")
    )
    parser.add_argument("--variant", action="append", choices=VARIANTS)
    args = parser.parse_args()
    try:
        result = run(
            args.output,
            args.comparison,
            tuple(args.variant) if args.variant else VARIANTS,
        )
    except (OSError, ValueError, KeyError, TypeError):
        parser.exit(
            1,
            "Ablation failed; check source integrity, configuration and checkpoints. No input text logged.\n",
        )
    print(
        json.dumps({"complete": True, "variants": len(result["ablations"][0]["rows"])})
    )
