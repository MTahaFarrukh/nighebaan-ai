"""Synthetic Urdu image integration check. No media or transcript is saved."""

import io
import json
import tempfile
from pathlib import Path

from app.main import app
from app.services import history
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont


def run() -> None:
    """Exercise actual Urdu OCR and the transliteration path using synthetic text."""
    canvas = Image.new("RGB", (1200, 240), "white")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype("arial.ttf", 62)
    draw.text(
        (1150, 60),
        "اپنا تصدیقی کوڈ فوراً بھیجیں",
        font=font,
        anchor="ra",
        direction="rtl",
        fill="black",
    )
    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG")
    with tempfile.TemporaryDirectory() as folder:
        history.DB_PATH = Path(folder) / "history.sqlite3"
        with TestClient(app) as client:
            response = client.post(
                "/api/analyze/file",
                files={"file": ("synthetic.png", buffer.getvalue(), "image/png")},
            )
    data = response.json()
    report = {
        "synthetic_only": True,
        "http_status": response.status_code,
        "urdu_bridge_used": any(
            "transliteration" in warning.lower() for warning in data.get("warnings", [])
        ),
        "rule_ids": data.get("rule_flags", []),
        "risk_level": data.get("risk_level"),
    }
    output = Path(__file__).resolve().parents[1] / "models/urdu_image_smoke.json"
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))
    if response.status_code != 200 or not report["urdu_bridge_used"]:
        raise SystemExit("Synthetic Urdu OCR did not reach the script bridge.")


if __name__ == "__main__":
    run()
