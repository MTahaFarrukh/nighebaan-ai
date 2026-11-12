"""Promotion gates prevent unsafe or test-contaminated candidate activation."""

from copy import deepcopy

import pytest
from ml.promote_url_robust import check_gate


def valid_report() -> dict:
    before = {
        "original_validation": {
            "macro_f1": 0.99,
            "per_class": {"phishing": {"r": 0.99}},
        }
    }
    after = {
        "original_validation": {
            "macro_f1": 0.98,
            "per_class": {"phishing": {"r": 0.98}},
        }
    }
    for key in (
        "synthetic_path_stress",
        "synthetic_no_www_root",
        "synthetic_no_www_path",
    ):
        before[key] = {"benign_false_positive_rate": 1.0}
        after[key] = {"benign_false_positive_rate": 0.15}
    return {
        "test_evaluated": False,
        "evaluation_split": "validation",
        "www_invariance": True,
        "stress_training_overlap": 0,
        "rows": [before, after],
    }


def test_valid_promotion_gates():
    check_gate(valid_report())


@pytest.mark.parametrize("failure", ["recall", "f1", "stress", "test", "overlap"])
def test_reject_regressions(failure):
    report = deepcopy(valid_report())
    after = report["rows"][1]
    if failure == "recall":
        after["original_validation"]["per_class"]["phishing"]["r"] = 0.95
    elif failure == "f1":
        after["original_validation"]["macro_f1"] = 0.95
    elif failure == "stress":
        after["synthetic_no_www_path"]["benign_false_positive_rate"] = 0.3
    elif failure == "test":
        report["test_evaluated"] = True
    else:
        report["stress_training_overlap"] = 1
    with pytest.raises(ValueError):
        check_gate(report)
