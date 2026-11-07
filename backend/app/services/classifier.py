"""Stub ML classifier — returns dummy probabilities until models are trained."""

from __future__ import annotations

from app.schemas import Label, Probabilities


def classify_text(cleaned_text: str) -> Probabilities:
    """
    STUB: Return heuristic dummy probabilities based on simple keyword hints.

    Replace this with a loaded scikit-learn / joblib model once trained.
    """
    text = cleaned_text.lower()

    # Lightweight heuristic so the UI shows varied output before real ML lands.
    scam_hints = ("lottery", "inaam", "otp", "account", "password", "cnic", "prize")
    abuse_hints = ("kutta", "bewaqoof", "ullu", "gadha", "harami")

    scam_hits = sum(1 for w in scam_hints if w in text)
    abuse_hits = sum(1 for w in abuse_hints if w in text)

    if scam_hits > abuse_hits and scam_hits > 0:
        return Probabilities(normal=0.15, abusive=0.10, scam=0.75)
    if abuse_hits > 0:
        return Probabilities(normal=0.20, abusive=0.70, scam=0.10)
    if "http" in text or "www." in text:
        return Probabilities(normal=0.40, abusive=0.10, scam=0.50)

    return Probabilities(normal=0.80, abusive=0.10, scam=0.10)


def predict_label(probabilities: Probabilities) -> Label:
    """Pick the label with the highest probability."""
    scores: dict[Label, float] = {
        "normal": probabilities.normal,
        "abusive": probabilities.abusive,
        "scam": probabilities.scam,
    }
    return max(scores, key=scores.get)
