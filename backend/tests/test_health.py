"""Smoke tests for the health endpoint."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok() -> None:
    """GET /api/health returns status ok."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_text_shape() -> None:
    """POST /api/analyze/text returns the expected response shape."""
    response = client.post("/api/analyze/text", json={"text": "foran otp bhejo lottery jeet gaye"})
    assert response.status_code == 200
    data = response.json()
    assert data["label"] in {"normal", "abusive", "scam"}
    assert set(data["probabilities"].keys()) == {"normal", "abusive", "scam"}
    assert 0.0 <= data["risk_score"] <= 1.0
    assert data["risk_level"] in {"low", "medium", "high"}
    assert isinstance(data["rule_flags"], list)
    assert isinstance(data["explanation"], str)
