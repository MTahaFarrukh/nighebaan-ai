"""Validation-only ML/rules/hybrid comparison and conservative risk calibration audit."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from app.config import settings
from app.schemas import Probabilities
from app.services.classifier import MODEL_PATH, load_model
from app.services.expert_rules import apply_rules, rule_scores
from app.services.risk_engine import compute_risk, final_label
from ml.train_improved import verify_partitions
from ml.train_preliminary import prepare_partitions
from ml.train_text import LABELS
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

ROOT = Path(__file__).resolve().parents[2]


def evaluate(output: Path) -> dict:
    """Report only aggregate validation evidence; never use test predictions."""
    if output.exists():
        raise ValueError("Output exists.")
    originals = {}
    splits, manifest = prepare_partitions(raw_lookup=originals)
    verify_partitions(
        manifest,
        json.loads(
            (ROOT / "backend/models/m4_preliminary_001/data_manifest.json").read_text()
        ),
    )
    validation = splits["val"]
    texts = [originals[(row.source, row.text)] for row in validation.itertuples()]
    model = load_model(str(MODEL_PATH))
    values = model.predict_proba(texts)
    ml_labels, rule_labels, hybrid_labels = [], [], []
    risks, axes, override, category_errors = [], [], [], {}
    for text, truth, vector in zip(texts, validation.label, values, strict=True):
        probs = Probabilities(**dict(zip(model.classes_, vector.tolist(), strict=True)))
        flags = apply_rules(text)["rule_flags"]
        scam, abuse = rule_scores(flags)
        score, level, _ = compute_risk(probs, flags, has_url="R01" in flags)
        prediction = final_label(probs, flags, level)
        ml = max(probs.model_dump(), key=lambda key: probs.model_dump()[key])
        rule_label = (
            "abusive"
            if abuse >= 0.3 and abuse > scam
            else "scam"
            if scam >= 0.35
            else "normal"
        )
        ml_labels.append(ml)
        rule_labels.append(rule_label)
        hybrid_labels.append(prediction)
        risks.append(score)
        axes.append(max(scam, abuse))
        override.append("R05" in flags and "R01" in flags)
        if prediction != truth:
            category = (
                "credential_url_override"
                if override[-1]
                else "high_rule_override"
                if prediction != ml
                else "ml_error_no_rule_correction"
            )
            category_errors[category] = category_errors.get(category, 0) + 1
    rows = []
    for name, predicted in [
        ("ml_only", ml_labels),
        ("rules_only", rule_labels),
        ("hybrid", hybrid_labels),
    ]:
        detail = classification_report(
            validation.label,
            predicted,
            labels=LABELS,
            output_dict=True,
            zero_division=0,
        )
        rows.append(
            {
                "name": name,
                "macro_f1": float(
                    f1_score(validation.label, predicted, average="macro")
                ),
                "per_class": {
                    label: {
                        "p": detail[label]["precision"],
                        "r": detail[label]["recall"],
                        "f1": detail[label]["f1-score"],
                    }
                    for label in LABELS
                },
                "confusion_matrix": confusion_matrix(
                    validation.label, predicted, labels=LABELS
                ).tolist(),
            }
        )
    normal_column = list(model.classes_).index("normal")
    p_ml = 1 - values[:, normal_column]
    harmful = validation.label.ne("normal").to_numpy()
    sweep = []
    for weight in (0.5, 0.6, 0.7):
        scores = np.maximum(
            weight * p_ml + (1 - weight) * np.asarray(axes), np.where(override, 0.85, 0)
        )
        for threshold in (0.35, 0.5, 0.6, 0.7, 0.8):
            predicted = scores >= threshold
            sweep.append(
                {
                    "ml_weight": weight,
                    "rule_weight": 1 - weight,
                    "threshold": threshold,
                    "harmful_f1": float(f1_score(harmful, predicted, zero_division=0)),
                    "harmful_precision": float(
                        precision_score(harmful, predicted, zero_division=0)
                    ),
                    "harmful_recall": float(
                        recall_score(harmful, predicted, zero_division=0)
                    ),
                }
            )
    result = {
        "evaluation_split": "validation",
        "status": manifest["status"],
        "test_evaluated": False,
        "rows": rows,
        "validation_rows": len(validation),
        "risk_sweep": sweep,
        "recommended_candidate_by_harmful_f1": max(
            sweep, key=lambda item: item["harmful_f1"]
        ),
        "deployed_policy": {
            "ml_weight": settings.risk_ml_weight,
            "rule_weight": settings.risk_rule_weight,
            "medium_threshold": settings.medium_threshold,
            "high_threshold": settings.alert_threshold,
            "credential_url_floor": settings.credential_url_floor,
        },
        "policy_note": "Spec defaults retained; binary harmful-F1 optimum is diagnostic, not automatic guardian-alert calibration.",
        "rule_only_policy": "abuse >= .30 and abuse > scam -> abusive; otherwise scam >= .35 -> scam; else normal",
        "aggregate_hybrid_error_categories": category_errors,
        "source_fingerprints": {
            "rules": hashlib.sha256(
                (ROOT / "backend/app/resources/rules.yaml").read_bytes()
            ).hexdigest(),
            "risk": hashlib.sha256(
                (ROOT / "backend/app/services/risk_engine.py").read_bytes()
            ).hexdigest(),
        },
        "url_model_used": False,
    }
    output.mkdir(parents=True)
    (output / "validation_metrics.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = evaluate(args.output)
    except (OSError, ValueError, KeyError, TypeError):
        parser.exit(1, "Hybrid validation failed; no input text logged.\n")
    print(json.dumps(result, indent=2))
