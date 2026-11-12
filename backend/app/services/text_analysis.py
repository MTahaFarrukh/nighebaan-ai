"""Shared text/rule/URL pipeline for typed and extracted content."""

from fastapi import HTTPException

from app.schemas import AnalyzeResponse
from app.services import (
    classifier,
    expert_rules,
    explain,
    preprocess,
    risk_engine,
    url_classifier,
)


def analyze(text: str, *, ml_text: str | None = None) -> AnalyzeResponse:
    """Keep original content for rule and URL cues; allow an explicit ML script bridge."""
    prep = preprocess.preprocess(text)
    cleaned = str(prep["cleaned"])
    urls = list(prep["urls"])  # type: ignore[arg-type]

    if not cleaned:
        raise HTTPException(status_code=422, detail="Enter meaningful message text.")
    try:
        probs = classifier.classify_text(ml_text if ml_text is not None else text)
    except classifier.ModelUnavailableError:
        raise HTTPException(
            status_code=503, detail="Text model unavailable. Please try again later."
        ) from None
    rules = expert_rules.apply_rules(text, urls)
    if ml_text is not None and ml_text != text:
        bridged = expert_rules.apply_rules(ml_text, urls)
        rules = {key: list(dict.fromkeys(rules[key] + bridged[key])) for key in rules}

    url_probability = None
    if urls:
        try:
            url_probability = url_classifier.phishing_probability(urls)
        except classifier.ModelUnavailableError:
            pass  # Text analysis remains available with an explicit fallback explanation.
    risk_score, risk_level, explanation = risk_engine.compute_risk(
        probs, rules["rule_flags"], has_url=bool(urls), url_probability=url_probability
    )
    if url_probability is not None:
        explanation += f" Static URL model: maximum phishing probability {url_probability:.2f}; links were not visited."

    ml_label = classifier.predict_label(probs)
    cues = explain.component_cues(ml_text if ml_text is not None else text, ml_label)
    if cues:
        explanation += f" LR component word cues for {ml_label}: {', '.join(cues)}. This is a partial explanation; the ensemble also uses character features and SVM."
    label = risk_engine.final_label(probs, rules["rule_flags"], risk_level)
    result = AnalyzeResponse(
        label=label,
        probabilities=probs,
        rule_flags=rules["rule_flags"],
        risk_score=risk_score,
        risk_level=risk_level,
        explanation="Preliminary trained LR/SVM ensemble; human-unverified data. "
        + explanation,
        flagged_words=rules["flagged_words"],
    )

    return result
