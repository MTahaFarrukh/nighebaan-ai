"""Spec risk fusion, safe deterministic explanations and explicit scam override."""

from __future__ import annotations

from app.config import settings
from app.schemas import Label, Probabilities, RiskLevel
from app.services.expert_rules import load_rules, rule_scores


def risk_level(score: float) -> RiskLevel:
    """Compare unrounded score to configured thresholds."""
    return (
        "high"
        if score >= settings.alert_threshold
        else "medium"
        if score >= settings.medium_threshold
        else "low"
    )


def compute_risk(
    probabilities: Probabilities,
    rule_flags: list[str],
    *,
    url_probability: float | None = None,
    has_url: bool = False,
) -> tuple[float, RiskLevel, str]:
    """Apply TECH_DOC 9.2; URL contribution is omitted until a model supplies it."""
    ml = 1 - probabilities.normal
    scam, abuse = rule_scores(rule_flags)
    # Abuse belongs to its own axis; max avoids counting the same threat twice.
    rules = max(scam, abuse)
    if url_probability is None:
        risk = settings.risk_ml_weight * ml + settings.risk_rule_weight * rules
    else:
        if not 0 <= url_probability <= 1:
            raise ValueError("URL probability must be in [0,1].")
        risk = (
            settings.risk_url_ml_weight * ml
            + settings.risk_url_rule_weight * rules
            + settings.risk_url_weight * url_probability
        )
    override = "R05" in rule_flags and (has_url or "R01" in rule_flags)
    if override:
        risk = max(risk, settings.credential_url_floor)
    risk = min(1.0, max(0.0, risk))
    level = risk_level(risk)
    descriptions = [
        rule["description"] for rule in load_rules() if rule["id"] in set(rule_flags)
    ]
    reason = (
        "; ".join(descriptions) if descriptions else "No configured risk cues matched"
    )
    explanation = f"{level.capitalize()} risk ({risk:.2f}). {reason}."
    top = max(
        probabilities.model_dump(), key=lambda label: probabilities.model_dump()[label]
    )
    explanation += f" Model leans {top} ({probabilities.model_dump()[top]:.2f})."
    if override:
        explanation += " Credential request with a link raises the risk floor."
    if has_url and url_probability is None:
        explanation += " URL model unavailable; URL probability was not used."
    return risk, level, explanation


def final_label(
    probabilities: Probabilities, flags: list[str], level: RiskLevel
) -> Label:
    """Only high risk plus scam-axis rules overrides the ML argmax."""
    scam, abuse = rule_scores(flags)
    if level == "high" and scam > 0 and scam >= abuse:
        return "scam"
    scores = probabilities.model_dump()
    return max(scores, key=lambda label: scores[label])
