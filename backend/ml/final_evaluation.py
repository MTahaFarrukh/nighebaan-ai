"""One-shot evaluation of frozen deployed artifacts; aggregate outputs only."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

import numpy as np
from app.schemas import Probabilities
from app.services import (
    classifier,
    expert_rules,
    preprocess,
    risk_engine,
    url_classifier,
)
from ml.train_preliminary import prepare_partitions
from ml.url_data import prepare as prepare_urls
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "backend/models/final_evaluation"
LABELS = ["normal", "abusive", "scam"]


def summarize(truth, predicted, labels: list) -> dict:
    """Return class metrics without storing individual predictions or source content."""
    detail = classification_report(
        truth, predicted, labels=labels, output_dict=True, zero_division=0
    )
    return {
        "rows": len(truth),
        "macro_f1": float(f1_score(truth, predicted, average="macro")),
        "accuracy": float(accuracy_score(truth, predicted)),
        "label_order": labels,
        "confusion_matrix": confusion_matrix(truth, predicted, labels=labels).tolist(),
        "per_class": {
            str(k): {
                "p": detail[str(k)]["precision"],
                "r": detail[str(k)]["recall"],
                "f1": detail[str(k)]["f1-score"],
                "support": detail[str(k)]["support"],
            }
            for k in labels
        },
    }


def evaluate_text(frame, originals: dict, model) -> dict:
    """Score frozen raw-input model and full hybrid without writing input content."""
    texts = [originals[(row.source, row.text)] for row in frame.itertuples()]
    started = perf_counter()
    values = model.predict_proba(texts)
    elapsed = perf_counter() - started
    predictions = model.classes_[np.argmax(values, axis=1)]
    hybrid = []
    levels = {"low": 0, "medium": 0, "high": 0}
    for text, vector in zip(texts, values, strict=True):
        probs = Probabilities(**dict(zip(model.classes_, vector.tolist(), strict=True)))
        urls = list(preprocess.preprocess(text)["urls"])
        flags = expert_rules.apply_rules(text, urls)["rule_flags"]
        url_probability = url_classifier.phishing_probability(urls) if urls else None
        _, level, _ = risk_engine.compute_risk(
            probs, flags, has_url=bool(urls), url_probability=url_probability
        )
        hybrid.append(risk_engine.final_label(probs, flags, level))
        levels[level] += 1
    return {
        "ml": summarize(frame.label, predictions, LABELS),
        "hybrid": summarize(frame.label, hybrid, LABELS),
        "risk_level_counts": levels,
        "batch_ml_ms_per_row": elapsed * 1000 / len(texts),
    }


def run() -> None:
    """Refuse repeats even after inference failure; freeze artifacts before first prediction."""
    if OUTPUT.exists() or (ROOT / "docs/FINAL_RESULTS.json").exists():
        raise ValueError("Final evaluation already reserved or completed; never rerun.")
    originals = {}
    splits, manifest = prepare_partitions(raw_lookup=originals)
    baseline = json.loads(
        (ROOT / "backend/models/m4_preliminary_001/data_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    if (
        manifest["splits"] != baseline["splits"]
        or manifest["custom_draft_sha256"] != baseline["custom_draft_sha256"]
    ):
        raise ValueError("Frozen text membership changed.")
    url_splits, url_manifest = prepare_urls()
    text_model = classifier.load_model(str(classifier.MODEL_PATH))
    url_model = url_classifier.load_url_model(str(url_classifier.MODEL_PATH))
    fingerprint_paths = [
        classifier.MODEL_PATH,
        url_classifier.MODEL_PATH,
        ROOT / "backend/app/config.py",
        ROOT / "backend/app/services/risk_engine.py",
        ROOT / "backend/app/resources/rules.yaml",
    ]
    frozen = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in fingerprint_paths
    }
    # Exclusive directory creation is the one-shot lock; even a failed run is not silently repeated.
    OUTPUT.mkdir()
    result = {
        "status": "started",
        "generated_at": datetime.now(UTC).isoformat(),
        "evaluation_split": "test",
        "data_review_status": "preliminary_human_unverified",
        "frozen_sha256": frozen,
        "text_splits": manifest["splits"],
        "url_splits": url_manifest["splits"],
        "limitations": "Final numbers for frozen artifacts on source-specific proxy labels; synthetic custom labels are not human-reviewed. No tuning or model changes may use these test results. Custom hold-out is template-family synthetic data, not realistic external prevalence.",
    }
    destination = OUTPUT / "results.json"

    def save() -> None:
        destination.write_text(json.dumps(result, indent=2), encoding="utf-8")

    save()
    print(
        "Frozen one-shot evaluation started; source content stays in memory.",
        flush=True,
    )
    result["text_test"] = evaluate_text(splits["test"], originals, text_model)
    save()
    result["custom_holdout"] = evaluate_text(
        splits["custom_holdout"], originals, text_model
    )
    save()
    result["url_test"] = summarize(
        url_splits["test"].label, url_model.predict(url_splits["test"].URL), [0, 1]
    )
    result["status"] = "complete"
    save()
    (ROOT / "docs/FINAL_RESULTS.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print("One-shot test evaluation complete; aggregate report saved.", flush=True)


if __name__ == "__main__":
    try:
        run()
    except (OSError, ValueError, KeyError, TypeError):
        raise SystemExit(
            "Final evaluation failed or already reserved; no source content logged. Inspect reservation before any recovery."
        ) from None
