"""Text and URL analysis endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas import AnalyzeResponse, TextAnalyzeRequest, UrlAnalyzeRequest
from app.services import classifier, expert_rules, preprocess, risk_engine, url_features

router = APIRouter(prefix="/analyze", tags=["analyze"])


@router.post("/text", response_model=AnalyzeResponse)
def analyze_text(body: TextAnalyzeRequest) -> AnalyzeResponse:
    """Analyze a free-text message for scam / abuse signals."""
    prep = preprocess.preprocess(body.text)
    cleaned = str(prep["cleaned"])
    urls = list(prep["urls"])  # type: ignore[arg-type]

    probs = classifier.classify_text(cleaned)
    label = classifier.predict_label(probs)
    rules = expert_rules.apply_rules(cleaned, urls)
    risk_score, risk_level, explanation = risk_engine.compute_risk(probs, rules["rule_flags"])

    return AnalyzeResponse(
        label=label,
        probabilities=probs,
        rule_flags=rules["rule_flags"],
        risk_score=risk_score,
        risk_level=risk_level,
        explanation=explanation,
        flagged_words=rules["flagged_words"],
    )


@router.post("/url", response_model=AnalyzeResponse)
def analyze_url(body: UrlAnalyzeRequest) -> AnalyzeResponse:
    """Analyze a standalone URL for phishing-like features."""
    features = url_features.extract_url_features(body.url)

    # Stub classifier over a synthetic description of the URL.
    synthetic = f"url {features.get('host', '')} {'https' if features.get('https') else 'http'}"
    if features.get("is_shortener"):
        synthetic += " shortener"

    probs = classifier.classify_text(synthetic)
    # Bias stub toward scam when shortener / many subdomains / no https
    rule_flags: list[str] = []
    if features.get("is_shortener"):
        rule_flags.append("suspicious_url")
    if int(features.get("subdomain_count", 0)) >= 2:
        rule_flags.append("suspicious_url")
    if not features.get("https"):
        rule_flags.append("link_present")
    else:
        rule_flags.append("link_present")

    # Deduplicate flags
    rule_flags = list(dict.fromkeys(rule_flags))

    # Slightly elevate scam probability for clearly suspicious URLs
    if features.get("is_shortener") or int(features.get("subdomain_count", 0)) >= 2:
        probs = probs.model_copy(update={"scam": max(probs.scam, 0.65), "normal": min(probs.normal, 0.25)})

    label = classifier.predict_label(probs)
    risk_score, risk_level, explanation = risk_engine.compute_risk(probs, rule_flags)

    return AnalyzeResponse(
        label=label,
        probabilities=probs,
        rule_flags=rule_flags,
        risk_score=risk_score,
        risk_level=risk_level,
        explanation=explanation,
        flagged_words=[],
        url_features=features,
    )
