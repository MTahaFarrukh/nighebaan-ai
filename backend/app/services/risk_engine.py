"""Combine classifier scores and expert-rule flags into a risk assessment."""

from __future__ import annotations

from app.schemas import Probabilities, RiskLevel

# Rule weights used in the risk formula (documented below).
RULE_WEIGHTS: dict[str, float] = {
    "link_present": 0.10,
    "urgency_language": 0.15,
    "prize_bait": 0.20,
    "sensitive_data_request": 0.25,
    "abusive_language": 0.20,
    "suspicious_url": 0.20,
}


def compute_risk(
    probabilities: Probabilities,
    rule_flags: list[str],
) -> tuple[float, RiskLevel, str]:
    """
    Compute risk_score in [0, 1] and map to risk_level.

    Formula
    -------
    ml_threat = max(P(scam), P(abusive))
    rules_score = min(1.0, sum(RULE_WEIGHTS[f] for f in rule_flags))
    risk_score = clip(0.6 * ml_threat + 0.4 * rules_score, 0, 1)

    Levels: low < 0.35, medium < 0.70, else high.
    """
    ml_threat = max(probabilities.scam, probabilities.abusive)
    rules_score = min(1.0, sum(RULE_WEIGHTS.get(flag, 0.05) for flag in rule_flags))
    risk_score = round(min(1.0, max(0.0, 0.6 * ml_threat + 0.4 * rules_score)), 3)

    if risk_score < 0.35:
        level: RiskLevel = "low"
    elif risk_score < 0.70:
        level = "medium"
    else:
        level = "high"

    explanation = _build_explanation(ml_threat, rules_score, rule_flags, risk_score, level)
    return risk_score, level, explanation


def _build_explanation(
    ml_threat: float,
    rules_score: float,
    rule_flags: list[str],
    risk_score: float,
    level: RiskLevel,
) -> str:
    """Human-readable summary of why this risk was assigned."""
    if not rule_flags and ml_threat < 0.3:
        return (
            f"Low risk (score={risk_score}). No expert-rule flags fired and "
            f"ML threat probability is low ({ml_threat:.2f})."
        )

    flags_text = ", ".join(rule_flags) if rule_flags else "none"
    return (
        f"Risk level '{level}' (score={risk_score}). "
        f"ML threat={ml_threat:.2f}, rules_score={rules_score:.2f} "
        f"(flags: {flags_text}). "
        f"Formula: 0.6*ml_threat + 0.4*rules_score."
    )
