"""Lazy loading of a trusted local model; input content is never logged."""

from __future__ import annotations

import hashlib
import json
import pickle
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np

from app.schemas import Label, Probabilities

MODEL_PATH = Path(__file__).resolve().parents[2] / "models/text_clf.joblib"


class ModelUnavailableError(RuntimeError):
    """The local classifier cannot safely supply probabilities."""


@lru_cache(maxsize=1)
def load_model(path: str) -> object:
    """Load only a locally promoted artifact after fingerprint verification."""
    artifact = Path(path)
    try:
        manifest = json.loads(artifact.with_suffix(".manifest.json").read_text())
        if hashlib.sha256(artifact.read_bytes()).hexdigest() != manifest["sha256"]:
            raise ValueError("Artifact fingerprint mismatch.")
        model = joblib.load(artifact)
        if set(model.classes_) != {"normal", "abusive", "scam"}:
            raise ValueError("Invalid classifier labels.")
        return model
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
        EOFError,
        ImportError,
        pickle.UnpicklingError,
    ):
        raise ModelUnavailableError("Text model unavailable.") from None


def classify_text(text: str) -> Probabilities:
    """Run the full raw-text pipeline and map probabilities by saved classes_."""
    model = load_model(str(MODEL_PATH))
    try:
        values = np.asarray(model.predict_proba([text]), dtype=float)
        if values.shape != (1, 3) or not np.isfinite(values).all():
            raise ValueError("Invalid probabilities.")
        if (values < 0).any() or (values > 1).any() or not np.isclose(values.sum(), 1):
            raise ValueError("Invalid probability distribution.")
        return Probabilities(
            **dict(zip(model.classes_, values[0].tolist(), strict=True))
        )
    except (ValueError, TypeError, AttributeError):
        raise ModelUnavailableError("Text model unavailable.") from None


def predict_label(probabilities: Probabilities) -> Label:
    """Select the highest named probability."""
    scores: dict[Label, float] = {
        "normal": probabilities.normal,
        "abusive": probabilities.abusive,
        "scam": probabilities.scam,
    }
    return max(scores, key=lambda label: scores[label])
