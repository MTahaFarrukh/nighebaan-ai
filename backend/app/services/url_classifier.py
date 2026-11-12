"""Trusted static URL model loading and privacy-safe probability inference."""

from __future__ import annotations

import hashlib
import json
import pickle
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np

from app.services.classifier import ModelUnavailableError

MODEL_PATH = Path(__file__).resolve().parents[2] / "models/url_clf.joblib"


@lru_cache(maxsize=1)
def load_url_model(path: str) -> object:
    """Verify locally promoted bytes and feature implementation before loading."""
    artifact = Path(path)
    try:
        manifest = json.loads(artifact.with_suffix(".manifest.json").read_text())
        if hashlib.sha256(artifact.read_bytes()).hexdigest() != manifest["sha256"]:
            raise ValueError("Artifact fingerprint mismatch.")
        feature_path = Path(__file__).with_name("url_features.py")
        feature_bytes = feature_path.read_bytes()
        # Git on Windows may change only line endings; executable source is identical.
        fingerprints = {
            hashlib.sha256(feature_bytes).hexdigest(),
            hashlib.sha256(feature_bytes.replace(b"\r\n", b"\n")).hexdigest(),
        }
        if manifest["feature_code_sha256"] not in fingerprints:
            raise ValueError("Feature implementation changed; retraining required.")
        model = joblib.load(artifact)
        if set(model.classes_) != {0, 1}:
            raise ValueError("Invalid URL labels.")
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
        raise ModelUnavailableError("URL model unavailable.") from None


def phishing_probability(urls: list[str]) -> float:
    """Return maximum phishing probability across URLs without any network IO."""
    if not urls:
        raise ValueError("At least one URL is required.")
    model = load_url_model(str(MODEL_PATH))
    try:
        values = np.asarray(model.predict_proba(urls), dtype=float)
        if values.shape != (len(urls), 2) or not np.isfinite(values).all():
            raise ValueError("Invalid probabilities.")
        if (
            (values < 0).any()
            or (values > 1).any()
            or not np.allclose(values.sum(axis=1), 1)
        ):
            raise ValueError("Invalid probability distribution.")
        return float(values[:, list(model.classes_).index(1)].max())
    except (ValueError, TypeError, AttributeError):
        raise ModelUnavailableError("URL inference unavailable.") from None
