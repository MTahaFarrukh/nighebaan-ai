"""Exercise the bridge authorization, consent and dry-run policy."""

from app.main import app
from app.services import alert_policy
from fastapi.testclient import TestClient


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
    assert client.post("/api/simulate/whatsapp").json()["dry_run"]
