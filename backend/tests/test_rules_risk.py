"""Synthetic positive/negative rule cases and risk-boundary contracts."""

import pytest
from app.schemas import Probabilities
from app.services.expert_rules import apply_rules, rule_scores
from app.services.risk_engine import compute_risk, final_label, risk_level

CASES = [
    ("R01", ["example.com", "https://example.org/a"], ["salam", "demo@example.com"]),
    (
        "R02",
        ["https://bit.ly/demo", "example.xyz"],
        ["https://example.com", "https://bit.ly.example.com"],
    ),
    ("R03", ["furan aao", "جلدی آؤ"], ["urgentlyword", "salam dost"]),
    ("R04", ["inaam milay ga", "انعام ملا"], ["prizedword", "salam"]),
    (
        "R05",
        ["OTP bhejo", "send your password"],
        ["OTP mat share karo", "never share your password"],
    ),
    ("R06", ["paisay bhejo", "پیسے بھیجو"], ["advanceword", "salam"]),
    ("R07", ["bank support", "نادرا"], ["riverbank", "salam"]),
    ("R08", ["account block", "قانونی کارروائی"], ["first", "salam"]),
    (
        "R09",
        ["guaranteed profit", "گھر بیٹھے کمائیں"],
        ["guaranteedprofitword", "salam"],
    ),
    ("R10", ["naya number", "نیا نمبر"], ["numbered list", "salam"]),
    (
        "R11",
        ["syntheticinsult", "tum syntheticinsult ho"],
        ["syntheticinsulting", "salam"],
    ),
]


@pytest.mark.parametrize("identifier,positive,negative", CASES)
def test_rule_examples(identifier, positive, negative) -> None:
    for text in positive:
        assert (
            identifier in apply_rules(text, lexicon=("syntheticinsult",))["rule_flags"]
        )
    for text in negative:
        assert (
            identifier
            not in apply_rules(text, lexicon=("syntheticinsult",))["rule_flags"]
        )


def test_masking_and_clause_local_negation() -> None:
    result = apply_rules("syntheticinsult", lexicon=("syntheticinsult",))
    assert result["flagged_words"] == ["s***"]
    assert "R05" in apply_rules("OTP mat share karo. Ab OTP bhejo")["rule_flags"]


def test_axes_and_unique_rule_weights() -> None:
    assert rule_scores(["R03", "R03", "unknown", "R11"]) == (0.15, 0.3)
    assert rule_scores([f"R{i:02}" for i in range(1, 12)]) == (1, 0.3)


@pytest.mark.parametrize(
    "value,expected",
    [(0.349999, "low"), (0.35, "medium"), (0.699999, "medium"), (0.7, "high")],
)
def test_unrounded_thresholds(value, expected) -> None:
    assert risk_level(value) == expected


def test_spec_formula_and_override() -> None:
    probs = Probabilities(normal=0.2, abusive=0.3, scam=0.5)
    assert compute_risk(probs, [])[0] == 0.48
    assert compute_risk(probs, ["R03"], url_probability=0.9)[0] == 0.625
    score, level, _ = compute_risk(
        Probabilities(normal=0.99, abusive=0.005, scam=0.005),
        ["R01", "R05"],
        has_url=True,
    )
    assert score == 0.85 and level == "high"
    assert final_label(probs, ["R01", "R05"], level) == "scam"


def test_abuse_does_not_become_scam_override() -> None:
    probs = Probabilities(normal=0.05, abusive=0.9, scam=0.05)
    assert final_label(probs, ["R11"], "high") == "abusive"
    with pytest.raises(ValueError):
        compute_risk(probs, [], url_probability=1.1)


def test_api_scam_override_and_masking(fake_text_model) -> None:
    from app.main import app
    from fastapi.testclient import TestClient

    result = (
        TestClient(app)
        .post("/api/analyze/text", json={"text": "OTP bhejo example.com"})
        .json()
    )
    assert result["risk_score"] >= 0.85 and result["risk_level"] == "high"
    assert result["label"] == "scam"
    assert {"R01", "R05"}.issubset(result["rule_flags"])


def test_invalid_risk_configuration(monkeypatch) -> None:
    from app.config import Settings

    monkeypatch.setenv("RISK_ML_WEIGHT", "nan")
    with pytest.raises(ValueError):
        Settings()
    monkeypatch.setenv("RISK_ML_WEIGHT", "0.9")
    with pytest.raises(ValueError, match="sum"):
        Settings()


def test_abuse_driven_high_risk_keeps_abuse_label() -> None:
    probs = Probabilities(normal=0.01, abusive=0.98, scam=0.01)
    _, level, _ = compute_risk(probs, ["R11", "R03"])
    assert level == "high"
    assert final_label(probs, ["R11", "R03"], level) == "abusive"
