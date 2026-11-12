"""Text and URL analysis endpoints."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, HTTPException

from app.schemas import (
    AnalyzeResponse,
    Probabilities,
    TextAnalyzeRequest,
    UrlAnalyzeRequest,
)
from app.services import (
    classifier,
    expert_rules,
    history,
    risk_engine,
    text_analysis,
    url_classifier,
    url_features,
)

router = APIRouter(prefix="/analyze", tags=["analyze"])


@router.post("/text", response_model=AnalyzeResponse)
def analyze_text(body: TextAnalyzeRequest) -> AnalyzeResponse:
    """Analyze a free-text message for scam / abuse signals."""
    result = text_analysis.analyze(body.text)
    return save_history(result, "text")


@router.post("/url", response_model=AnalyzeResponse)
def analyze_url(body: UrlAnalyzeRequest) -> AnalyzeResponse:
    """Analyze a URL with the trained static model, without fetching its target."""
    try:
        features = url_features.extract_url_features(body.url)
    except ValueError:
        raise HTTPException(
            status_code=422, detail="Enter a valid HTTP(S) URL."
        ) from None
    try:
        probability = url_classifier.phishing_probability([body.url])
    except classifier.ModelUnavailableError:
        raise HTTPException(
            status_code=503, detail="URL model unavailable. Please try again later."
        ) from None
    probs = Probabilities(normal=1 - probability, abusive=0.0, scam=probability)
    rules = expert_rules.apply_rules("", [body.url])
    # Standalone URL has no text evidence: use URL probability directly, not twice in fusion.
    level = risk_engine.risk_level(probability)
    result = AnalyzeResponse(
        label=classifier.predict_label(probs),
        probabilities=probs,
        rule_flags=rules["rule_flags"],
        risk_score=probability,
        risk_level=level,
        explanation=f"Trained static URL model: phishing probability {probability:.2f}. "
        "Only URL structure was analyzed; the link was not visited. This is not a safety guarantee.",
        flagged_words=[],
        url_features=features,
    )

    return save_history(result, "url")


def save_history(result: AnalyzeResponse, modality: str) -> AnalyzeResponse:
    """History failure must not hide a completed risk assessment."""
    try:
        history.record(
            modality=modality,
            label=result.label,
            risk_level=result.risk_level,
            risk_score=result.risk_score,
            rule_ids=result.rule_flags,
        )
    except (OSError, sqlite3.Error):
        result.explanation += " This result could not be added to local history."
    return result
