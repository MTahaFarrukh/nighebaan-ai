"""Classifier contracts use synthetic input and local fake estimators."""

import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pytest
from app.main import app
from app.services import classifier
from app.services.model_input import ModelInputSanitizer
from app.services.preprocess import load_normalization_map
from fastapi.testclient import TestClient
from ml.train_preliminary import sanitize


class FakeModel:
    classes_ = np.array(["scam", "normal", "abusive"])

    def predict_proba(self, texts):
        return np.array([[0.7, 0.2, 0.1]])


def test_probability_order(monkeypatch) -> None:
    monkeypatch.setattr(classifier, "load_model", lambda path: FakeModel())
    result = classifier.classify_text("synthetic")
    assert result.scam == 0.7 and result.normal == 0.2 and result.abusive == 0.1


def test_missing_model_is_503_without_echo(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(classifier, "MODEL_PATH", tmp_path / "absent.joblib")
    response = TestClient(app).post(
        "/api/analyze/text", json={"text": "synthetic private sentinel"}
    )
    assert response.status_code == 503
    assert "sentinel" not in response.text


def test_fingerprint_and_lazy_load(tmp_path, monkeypatch) -> None:
    path = tmp_path / "model.joblib"
    joblib.dump(FakeModel(), path)
    manifest = path.with_suffix(".manifest.json")
    manifest.write_text(
        json.dumps({"sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    )
    classifier.load_model.cache_clear()
    assert classifier.load_model(str(path)) is classifier.load_model(str(path))
    classifier.load_model.cache_clear()
    manifest.write_text(json.dumps({"sha256": "wrong"}))
    with pytest.raises(classifier.ModelUnavailableError):
        classifier.load_model(str(path))


def test_invalid_probabilities_rejected(monkeypatch) -> None:
    model = FakeModel()
    model.predict_proba = lambda texts: np.array([[float("nan"), 0.2, 0.1]])
    monkeypatch.setattr(classifier, "load_model", lambda path: model)
    with pytest.raises(classifier.ModelUnavailableError):
        classifier.classify_text("synthetic")


def test_outer_cleaning_matches_training() -> None:
    texts = [
        "@demo_handle PKR 1000000 demo@example.com",
        "FURAN 03XX-XXXXXXX example.com/A?demo=1",
    ]
    transformer = ModelInputSanitizer(load_normalization_map())
    assert transformer.transform(texts) == [sanitize(text) for text in texts]


def test_raw_request_reaches_model(monkeypatch) -> None:
    seen = []
    model = FakeModel()
    model.predict_proba = lambda texts: (
        seen.extend(texts) or np.array([[0.7, 0.2, 0.1]])
    )
    monkeypatch.setattr(classifier, "load_model", lambda path: model)
    response = TestClient(app).post(
        "/api/analyze/text", json={"text": "FURAN @demo_handle"}
    )
    assert response.status_code == 200
    assert seen == ["FURAN @demo_handle"]
    assert "Preliminary trained" in response.json()["explanation"]


def test_empty_normalized_input_rejected() -> None:
    assert (
        TestClient(app).post("/api/analyze/text", json={"text": "!!!"}).status_code
        == 422
    )


def test_actual_artifact_reload_if_present() -> None:
    if not Path(classifier.MODEL_PATH).exists():
        pytest.skip("Local trained artifact not available in this clone.")
    classifier.load_model.cache_clear()
    result = classifier.classify_text("synthetic demo placeholder")
    assert sum(result.model_dump().values()) == pytest.approx(1.0)
