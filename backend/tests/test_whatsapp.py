"""Exercise the bridge authorization, consent and dry-run policy."""

import sqlite3

import pymupdf
from app.main import app
from app.services import alert_policy
from app.services import history
from fastapi.testclient import TestClient


def synthetic_pdf() -> bytes:
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((72, 72), "Foran OTP bhejo https://example.com")
        return document.tobytes()


def test_history_write_failure_is_reported_without_message_content(
    tmp_path, monkeypatch, caplog, fake_text_model
):
    monkeypatch.setattr(alert_policy, "DB", tmp_path / "whatsapp.sqlite3")
    monkeypatch.setenv("WHATSAPP_API_KEY", "x" * 32)
    monkeypatch.setenv("WHATSAPP_OWNER_OPT_IN", "true")
    monkeypatch.setenv("DRY_RUN", "true")

    def fail(**kwargs):
        raise sqlite3.OperationalError("synthetic")

    monkeypatch.setattr(history, "record", fail)
    client = TestClient(app)
    headers = {"X-API-Key": "x" * 32}
    guardian = "a" * 64
    client.post(
        "/api/consent",
        json={"guardian": guardian, "enabled": True},
        headers=headers,
    )
    response = client.post(
        "/api/whatsapp/event",
        json={
            "guardian": guardian,
            "sender": "b" * 64,
            "text": "OTP bhejo https://example.com",
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["history_recorded"] is False
    assert "OTP bhejo" not in response.text
    assert "example.com" not in caplog.text
    assert "OperationalError" in caplog.text


def test_bridge_policy(tmp_path, monkeypatch, fake_text_model):
    monkeypatch.setattr(alert_policy, "DB", tmp_path / "whatsapp.sqlite3")
    monkeypatch.setenv("WHATSAPP_API_KEY", "x" * 32)
    monkeypatch.setenv("WHATSAPP_OWNER_OPT_IN", "true")
    monkeypatch.delenv("DRY_RUN", raising=False)
    client = TestClient(app)
    headers = {"X-API-Key": "x" * 32}
    body = {
        "guardian": "a" * 64,
        "sender": "b" * 64,
        "text": "OTP bhejo https://example.com",
    }
    assert client.post("/api/whatsapp/event", json=body).status_code == 401

    def event():
        return client.post("/api/whatsapp/event", json=body, headers=headers).json()

    assert event()["reason"] == "consent_required"
    assert client.post(
        "/api/consent",
        json={"guardian": body["guardian"], "enabled": True},
        headers=headers,
    ).json()["enabled"]
    result = event()
    assert result["should_alert"] and result["dry_run"]
    dashboard = client.get("/api/alerts").json()
    assert dashboard["items"][0]["source"] == "whatsapp"
    assert dashboard["items"][0]["alert_state"] == "dry_run"
    assert "Detected keyword(s):" in result["alert_user_text"]
    assert "OTP/password/verification code" in result["alert_user_text"]
    assert "example.com" not in result["alert_guardian_text"]
    assert "example.com" not in str(result)
    assert event()["reason"] == "duplicate"
    for suffix in (" first", " second"):
        body["text"] += suffix
        assert event()["should_alert"]
    body["text"] += " third"
    assert event()["reason"] == "rate_limited"
    client.post(
        "/api/consent",
        json={"guardian": body["guardian"], "enabled": False},
        headers=headers,
    )
    assert event()["reason"] == "consent_required"
    assert b"example.com" not in alert_policy.DB.read_bytes()
    assert b"example.com" not in history.DB_PATH.read_bytes()
    assert client.post("/api/simulate/whatsapp").json()["dry_run"]


def test_consented_whatsapp_pdf_media_is_analyzed_and_recorded(
    tmp_path, monkeypatch, fake_text_model
):
    monkeypatch.setattr(alert_policy, "DB", tmp_path / "whatsapp.sqlite3")
    monkeypatch.setenv("WHATSAPP_API_KEY", "x" * 32)
    monkeypatch.setenv("WHATSAPP_OWNER_OPT_IN", "true")
    monkeypatch.setenv("DRY_RUN", "true")
    client = TestClient(app)
    headers = {"X-API-Key": "x" * 32}
    guardian = "a" * 64

    consent = client.post(
        "/api/consent",
        json={"guardian": guardian, "enabled": True},
        headers=headers,
    )
    assert consent.status_code == 200 and consent.json()["enabled"]
    response = client.post(
        "/api/whatsapp/media",
        data={"guardian": guardian, "sender": "b" * 64},
        files={
            "file": ("synthetic.pdf", synthetic_pdf(), "application/pdf"),
        },
        headers=headers,
    )

    assert response.status_code == 200
    result = response.json()
    assert result["risk_level"] == "high"
    assert result["should_alert"] and result["dry_run"]
    assert result["history_recorded"] is True
    assert "example.com" not in response.text
    history_response = client.get("/api/alerts")
    assert history_response.status_code == 200
    assert history_response.json()["items"][0]["source"] == "whatsapp"
    assert history_response.json()["items"][0]["modality"] == "media"
    assert "example.com" not in str(history_response.json())
