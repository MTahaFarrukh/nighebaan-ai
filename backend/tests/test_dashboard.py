"""Public dashboard contracts and metadata privacy regression tests."""

import json
import sqlite3

from app.main import app
from app.routers import dashboard
from app.services import history
from fastapi.testclient import TestClient

client = TestClient(app)


def test_empty_history_and_pagination_validation():
    result = client.get("/api/alerts").json()
    assert result["items"] == [] and result["total"] == 0
    for query in ["limit=0", "limit=101", "offset=-1"]:
        assert client.get("/api/alerts?" + query).status_code == 422


def test_metadata_only_and_pagination():
    for i in range(3):
        history.record(
            modality="text",
            label="scam",
            risk_level="high",
            risk_score=0.9,
            rule_ids=["R05", "private-sentinel"],
        )
    history.record(
        modality="url", label="normal", risk_level="low", risk_score=0.1, rule_ids=[]
    )
    response = client.get("/api/alerts?limit=2&offset=1")
    data = response.json()
    assert data["total"] == 3 and len(data["items"]) == 2
    assert data["by_modality"] == {"text": 3}
    assert sum(data["by_day"].values()) == 3
    assert data["items"][0]["id"] > data["items"][1]["id"]
    assert "private-sentinel" not in response.text
    with sqlite3.connect(history.DB_PATH) as db:
        columns = {row[1] for row in db.execute("pragma table_info(web_risk_history)")}
    assert columns == {
        "id",
        "ts",
        "modality",
        "label",
        "risk_level",
        "risk_score",
        "rule_ids",
    }


def test_analysis_records_no_input(fake_text_model):
    response = client.post(
        "/api/analyze/text",
        json={"text": "private-sentinel OTP bhejo https://example.com"},
    )
    assert response.status_code == 200
    saved = client.get("/api/alerts")
    assert saved.json()["total"] == 1
    assert "private-sentinel" not in saved.text and "example.com" not in saved.text
    assert b"private-sentinel" not in history.DB_PATH.read_bytes()


def test_history_write_failure_does_not_hide_analysis(fake_text_model, monkeypatch):
    def fail(**kwargs):
        raise sqlite3.OperationalError("synthetic")

    monkeypatch.setattr(history, "record", fail)
    response = client.post(
        "/api/analyze/text", json={"text": "OTP bhejo https://example.com"}
    )
    assert response.status_code == 200
    assert "could not be added" in response.json()["explanation"]


def test_metrics_allowlist_and_missing(monkeypatch, tmp_path):
    path = tmp_path / "metrics.json"
    path.write_text(
        json.dumps(
            {
                "evaluation_split": "validation",
                "data_review_status": "preliminary",
                "models": [],
                "best_model": "none",
                "secret": "private-sentinel",
            }
        )
    )
    monkeypatch.setattr(dashboard, "METRICS_PATH", path)
    response = client.get("/api/metrics/models")
    assert response.status_code == 200
    assert "private-sentinel" not in response.text
    path.write_text("{}")
    assert client.get("/api/metrics/models").status_code == 503
    path.unlink()
    assert client.get("/api/metrics/models").status_code == 503


def test_real_aggregate_metrics_contract():
    if dashboard.METRICS_PATH.exists():
        response = client.get("/api/metrics/models")
        assert response.status_code == 200
        assert response.json()["evaluation_split"] == "validation"


def test_public_settings_no_secrets(monkeypatch):
    monkeypatch.setenv("API_KEY", "private-sentinel")
    response = client.get("/api/settings")
    assert response.status_code == 200
    assert "private-sentinel" not in response.text
    assert response.json()["whatsapp_available"] is False
    assert (
        0
        <= response.json()["medium_threshold"]
        < response.json()["high_threshold"]
        <= 1
    )
