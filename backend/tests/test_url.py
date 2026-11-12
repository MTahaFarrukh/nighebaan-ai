"""Synthetic URL tests: parsing, leakage, inference and API contracts."""

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import joblib
import numpy as np
import pandas as pd
import pytest
from app.main import app
from app.services import url_classifier
from app.services.classifier import ModelUnavailableError
from app.services.url_features import FEATURE_NAMES, canonical_url, extract_url_features
from app.services.url_transformer import URLFeatureTransformer
from fastapi.testclient import TestClient
from ml.url_data import prepare_frame


class FakeURLModel:
    classes_ = np.array([1, 0])

    def predict_proba(self, urls):
        return np.array([[0.8, 0.2] for _ in urls])


@pytest.fixture
def fake_url(monkeypatch):
    monkeypatch.setattr(url_classifier, "load_url_model", lambda path: FakeURLModel())


def test_static_features_no_network():
    with patch("socket.getaddrinfo", side_effect=AssertionError("Network forbidden")):
        features = extract_url_features(
            "https://user:demo@a.example.xyz:8443/login-2?q=1&b="
        )
    assert features["host_length"] == len("a.example.xyz")
    assert features["has_at"] and features["https"] and features["suspicious_tld"]
    assert features["subdomain_count"] == 1 and features["query_params"] == 2
    assert features["keyword_hits"] == 1
    assert set(features) == set(FEATURE_NAMES)
    assert all(isinstance(v, (int, float, bool)) for v in features.values())


@pytest.mark.parametrize("url", ["http://127.0.0.1/a", "http://[::1]:80/a"])
def test_ip_hosts(url):
    features = extract_url_features(url)
    assert features["ip_as_host"] and features["subdomain_count"] == 0


def test_shortener_uses_actual_host():
    assert extract_url_features("https://bit.ly/demo")["is_shortener"]
    assert not extract_url_features("https://bit.ly.example.com/demo")["is_shortener"]
    assert not extract_url_features("https://bit.ly@example.com/demo")["is_shortener"]


def test_canonicalization():
    assert canonical_url("HTTPS://EXAMPLE.COM:443#demo") == "https://example.com/"
    assert canonical_url("//example.com/Case") == "http://example.com/Case"
    assert canonical_url("https://example.com/Case") != canonical_url(
        "https://example.com/case"
    )
    assert "xn--" in canonical_url("https://mÃ¼nich.example/path")


@pytest.mark.parametrize(
    "url",
    [
        "",
        "https://",
        "ftp://example.com",
        "https://[bad",
        "https://example.com:bad",
        "https://exa mple.com",
        "http://example.com\\bad",
        "https://example.com/" + "x" * 8192,
    ],
)
def test_invalid_urls(url):
    with pytest.raises(ValueError, match="Invalid HTTP URL"):
        extract_url_features(url)


def test_transformer_no_url_storage():
    transformer = URLFeatureTransformer().fit(["https://example.com"])
    assert transformer.transform(["https://example.com"]).shape == (
        1,
        len(FEATURE_NAMES),
    )
    assert not vars(transformer)


def test_dedup_mapping_splits_deterministic():
    frame = pd.DataFrame(
        {
            "URL": [f"https://example.com/{i}" for i in range(100)],
            "label": [i % 2 for i in range(100)],
        }
    )
    frame = pd.concat(
        [
            frame,
            frame.iloc[:3],
            pd.DataFrame({"URL": ["https://EXAMPLE.COM:443/0#fragment"], "label": [0]}),
        ]
    )
    splits, manifest = prepare_frame(frame)
    _again, repeat = prepare_frame(frame.sample(frac=1, random_state=3))
    assert manifest == repeat
    assert [len(splits[k]) for k in ["train", "val", "test"]] == [70, 15, 15]
    assert not set(splits["train"].URL) & set(splits["test"].URL)
    combined = pd.concat(splits.values())
    assert combined.loc[combined.URL == "https://example.com/0", "label"].item() == 1
    conflict = pd.concat(
        [frame, pd.DataFrame({"URL": ["https://example.com/0"], "label": [1]})]
    )
    cleaned, report = prepare_frame(conflict)
    assert report["conflicting_url_groups"] == 1
    assert "https://example.com/0" not in set(pd.concat(cleaned.values()).URL)


def test_probability_class_order_and_max(fake_url, monkeypatch):
    assert url_classifier.phishing_probability(["https://example.com"]) == 0.8
    model = FakeURLModel()
    model.predict_proba = lambda urls: np.array([[0.2, 0.8], [0.9, 0.1]])
    monkeypatch.setattr(url_classifier, "load_url_model", lambda path: model)
    assert (
        url_classifier.phishing_probability(
            ["https://example.com/a", "https://example.com/b"]
        )
        == 0.9
    )


def test_invalid_model_probabilities(fake_url, monkeypatch):
    model = FakeURLModel()
    model.predict_proba = lambda urls: np.array([[np.nan, 0.2]])
    monkeypatch.setattr(url_classifier, "load_url_model", lambda path: model)
    with pytest.raises(ModelUnavailableError):
        url_classifier.phishing_probability(["https://example.com"])


def test_manifest_validation(tmp_path):
    path = tmp_path / "url.joblib"
    joblib.dump(FakeURLModel(), path)
    manifest = {
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "feature_code_sha256": hashlib.sha256(
            Path(url_classifier.__file__).with_name("url_features.py").read_bytes()
        ).hexdigest(),
    }
    path.with_suffix(".manifest.json").write_text(json.dumps(manifest))
    url_classifier.load_url_model.cache_clear()
    assert url_classifier.load_url_model(str(path)) is url_classifier.load_url_model(
        str(path)
    )
    url_classifier.load_url_model.cache_clear()
    manifest["sha256"] = "wrong"
    path.with_suffix(".manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ModelUnavailableError):
        url_classifier.load_url_model(str(path))


def test_url_api(fake_url):
    response = TestClient(app).post(
        "/api/analyze/url", json={"url": "https://example.com/demo"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] == 0.8 and data["risk_level"] == "high"
    assert data["probabilities"] == {
        "normal": pytest.approx(0.2),
        "abusive": 0.0,
        "scam": 0.8,
    }
    assert "example.com" not in response.text
    assert data["explanation"].startswith("Trained static URL model")


def test_url_missing_and_invalid(monkeypatch, tmp_path):
    monkeypatch.setattr(url_classifier, "MODEL_PATH", tmp_path / "missing.joblib")
    client = TestClient(app)
    assert (
        client.post("/api/analyze/url", json={"url": "https://example.com"}).status_code
        == 503
    )
    assert (
        client.post("/api/analyze/url", json={"url": "ftp://example.com"}).status_code
        == 422
    )


def test_text_url_fusion(fake_text_model, fake_url):
    data = (
        TestClient(app)
        .post("/api/analyze/text", json={"text": "hello https://example.com"})
        .json()
    )
    assert data["risk_score"] == pytest.approx(0.5 * 0.8 + 0.3 * 0.15 + 0.2 * 0.8)
    assert "Static URL model" in data["explanation"]


def test_text_url_missing_fallback(fake_text_model, monkeypatch, tmp_path):
    monkeypatch.setattr(url_classifier, "MODEL_PATH", tmp_path / "missing.joblib")
    response = TestClient(app).post(
        "/api/analyze/text", json={"text": "hello https://example.com"}
    )
    assert response.status_code == 200
    assert "URL model unavailable" in response.json()["explanation"]


def test_optional_real_url_artifact():
    if not url_classifier.MODEL_PATH.exists():
        pytest.skip("Local URL model not trained in this clone.")
    url_classifier.load_url_model.cache_clear()
    assert 0 <= url_classifier.phishing_probability(["https://example.com"]) <= 1


def test_feature_hash_accepts_crlf_but_rejects_changed_code(tmp_path, monkeypatch):
    path = tmp_path / "url.joblib"
    joblib.dump(FakeURLModel(), path)
    source = tmp_path / "url_features.py"
    source.write_bytes(b"x = 1\r\n")
    monkeypatch.setattr(url_classifier, "__file__", str(tmp_path / "url_classifier.py"))
    manifest = {
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "feature_code_sha256": hashlib.sha256(b"x = 1\n").hexdigest(),
    }
    path.with_suffix(".manifest.json").write_text(json.dumps(manifest))
    url_classifier.load_url_model.cache_clear()
    assert url_classifier.load_url_model(str(path)) is not None
    source.write_bytes(b"x = 2\r\n")
    url_classifier.load_url_model.cache_clear()
    with pytest.raises(ModelUnavailableError):
        url_classifier.load_url_model(str(path))
