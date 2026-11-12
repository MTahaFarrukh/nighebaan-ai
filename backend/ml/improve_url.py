"""Audit URL shortcuts and train one robust candidate; validation only."""

import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

import joblib
import numpy as np
from app.services.url_classifier import MODEL_PATH, load_url_model
from app.services.url_transformer import URLFeatureTransformer
from ml.url_data import ROOT, prepare
from ml.url_robustness import benign_variant, without_www
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.pipeline import Pipeline


def score(truth, predicted) -> dict:
    detail = classification_report(
        truth,
        predicted,
        labels=[0, 1],
        target_names=["benign", "phishing"],
        output_dict=True,
        zero_division=0,
    )
    matrix = confusion_matrix(truth, predicted, labels=[0, 1]).tolist()
    return {
        "macro_f1": float(f1_score(truth, predicted, average="macro")),
        "per_class": {
            key: {
                "p": detail[key]["precision"],
                "r": detail[key]["recall"],
                "f1": detail[key]["f1-score"],
            }
            for key in ["benign", "phishing"]
        },
        "confusion_matrix": matrix,
        "benign_false_positive_rate": matrix[0][1] / max(1, sum(matrix[0])),
    }


def run(
    output: Path,
    *,
    www_invariance: bool = False,
    phishing_weight: float = 1.0,
    classifier: str = "gb",
) -> None:
    if not np.isfinite(phishing_weight) or phishing_weight <= 0:
        raise ValueError("Phishing weight must be finite and positive.")
    if output.exists():
        raise ValueError("Run exists; do not overwrite.")
    splits, manifest = prepare()
    train, val = splits["train"], splits["val"]
    transform = URLFeatureTransformer()
    old = load_url_model(str(MODEL_PATH))
    benign_train = train.loc[train.label.eq(0), "URL"].tolist()
    augmented = [benign_variant(url, index) for index, url in enumerate(benign_train)]
    if www_invariance:
        augmented += [without_www(url) for url in benign_train] + [
            without_www(url) for url in augmented
        ]
    all_urls = train.URL.tolist() + augmented
    labels = np.concatenate(
        [train.label.to_numpy(), np.zeros(len(augmented), dtype=int)]
    )
    # Prevent synthetic variants from overlapping frozen source validation/test membership.
    heldout = set(val.URL) | set(splits["test"].URL)
    if www_invariance:
        for partition in (val, splits["test"]):
            heldout.update(without_www(url) for url in partition.URL)
            heldout.update(
                without_www(benign_variant(url, index, validation=True))
                for index, url in enumerate(partition.URL)
            )
    keep = [i for i, url in enumerate(all_urls) if i < len(train) or url not in heldout]
    unique = {}
    for i in keep:
        url = all_urls[i]
        if url not in unique:
            unique[url] = int(labels[i])
    all_urls = list(unique)
    labels = np.asarray(list(unique.values()))
    validation_urls = val.URL.tolist()
    stress_urls = [
        benign_variant(url, index, validation=True) if label == 0 else url
        for index, (url, label) in enumerate(zip(validation_urls, val.label))
    ]
    assert not (set(stress_urls) & set(all_urls)), "Stress/training URL overlap."
    print(
        "Training robust URL candidate on original train plus synthetic benign paths.",
        flush=True,
    )
    model = HistGradientBoostingClassifier(
        max_iter=150, max_leaf_nodes=31, class_weight="balanced", random_state=42
    )
    if classifier == "rf":
        model = RandomForestClassifier(
            n_estimators=250,
            max_depth=28,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=42,
            n_jobs=2,
        )
    model.fit(
        transform.transform(all_urls),
        labels,
        sample_weight=np.where(labels == 1, phishing_weight, 1.0),
    )
    candidate = Pipeline([("features", transform), ("classifier", model)])
    train_hosts = {urlsplit(url).hostname for url in train.URL}
    unseen = np.array(
        [urlsplit(url).hostname not in train_hosts for url in validation_urls]
    )
    extra_stress = {}
    if www_invariance:
        for name, urls in [
            (
                "synthetic_no_www_root",
                [
                    without_www(url) if label == 0 else url
                    for url, label in zip(validation_urls, val.label)
                ],
            ),
            (
                "synthetic_no_www_path",
                [
                    without_www(url) if label == 0 else url
                    for url, label in zip(stress_urls, val.label)
                ],
            ),
        ]:
            eligible = np.array([url not in unique for url in urls])
            extra_stress[name] = (
                [url for url, keep in zip(urls, eligible) if keep],
                val.label.to_numpy()[eligible],
                int((~eligible).sum()),
            )
    rows = []
    for name, pipeline in [
        ("deployed_before", old),
        ("url_robust_" + classifier, candidate),
    ]:
        original_pred = pipeline.predict(validation_urls)
        stress_pred = pipeline.predict(stress_urls)
        extra_scores = {
            name: {
                **score(truth, pipeline.predict(urls)),
                "excluded_training_overlap": excluded,
            }
            for name, (urls, truth, excluded) in extra_stress.items()
        }
        rows.append(
            {
                "name": name,
                **extra_scores,
                "original_validation": score(val.label, original_pred),
                "synthetic_path_stress": score(val.label, stress_pred),
                "unseen_hostname_validation": score(
                    val.label.to_numpy()[unseen], original_pred[unseen]
                ),
            }
        )
    before, after = rows
    gate = (
        after["original_validation"]["macro_f1"]
        >= before["original_validation"]["macro_f1"] - 0.02
        and after["original_validation"]["per_class"]["phishing"]["r"]
        >= before["original_validation"]["per_class"]["phishing"]["r"] - 0.02
        and after["synthetic_path_stress"]["benign_false_positive_rate"]
        < before["synthetic_path_stress"]["benign_false_positive_rate"]
    )
    audit = {}
    for label in [0, 1]:
        values = train.loc[train.label.eq(label), "URL"]
        audit[str(label)] = {
            "rows": len(values),
            "non_root_path_fraction": float(
                np.mean([urlsplit(url).path not in {"", "/"} for url in values])
            ),
            "www_fraction": float(
                np.mean(
                    [
                        (urlsplit(url).hostname or "").startswith("www.")
                        for url in values
                    ]
                )
            ),
            "https_fraction": float(
                np.mean([urlsplit(url).scheme == "https" for url in values])
            ),
        }
    result = {
        "classifier": classifier,
        "phishing_weight": phishing_weight,
        "www_invariance": www_invariance,
        "evaluation_split": "validation",
        "test_evaluated": False,
        "source": manifest["source"],
        "archive_sha256": manifest["archive_sha256"],
        "frozen_splits": manifest["splits"],
        "training_rows_after_augmentation": len(all_urls),
        "original_train_rows": len(train),
        "training_shape_audit": audit,
        "stress_training_overlap": len(set(stress_urls) & set(all_urls)),
        "rows": rows,
        "promotion_gate_passed": bool(gate),
        "gate": "Original macro-F1/recall drop no greater than .02, and lower synthetic benign false-positive rate.",
        "limits": "Synthetic no-www variants also inherit source labels; www and apex need not serve the same site. Benign path variants inherit source labels as an assumption; this is a synthetic stress test, not external accuracy. Unseen hostname is not registrable-domain separation. Test only used for membership exclusion, never inference.",
        "source_artifact_sha256": hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest(),
    }
    output.mkdir(parents=True)
    joblib.dump(candidate, output / "candidate.joblib")
    (output / "metrics.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (ROOT / "docs/URL_ROBUSTNESS_RESULTS.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--www-invariance", action="store_true")
    parser.add_argument("--phishing-weight", type=float, default=1.0)
    parser.add_argument("--classifier", choices=("gb", "rf"), default="gb")
    args = parser.parse_args()
    try:
        run(
            args.output,
            www_invariance=args.www_invariance,
            phishing_weight=args.phishing_weight,
            classifier=args.classifier,
        )
    except (OSError, ValueError, KeyError, TypeError):
        parser.exit(1, "URL robustness run failed; no source URLs logged.\n")
