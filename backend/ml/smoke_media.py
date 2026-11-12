"""Actual local-media smoke checks; save only aggregate metadata, never content."""

import json
import subprocess
import tempfile
from pathlib import Path

import imageio_ffmpeg
from app.main import app
from app.services import history
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]


def run() -> None:
    """Use synthetic fixtures and an isolated history database."""
    fixtures = ROOT / "data/raw/media_demo"
    spoken_video = fixtures / "synthetic-spoken-video.mp4"
    subprocess.run(
        [
            imageio_ffmpeg.get_ffmpeg_exe(),
            "-nostdin",
            "-loglevel",
            "error",
            "-loop",
            "1",
            "-i",
            str(fixtures / "synthetic-message.png"),
            "-i",
            str(fixtures / "synthetic-speech.wav"),
            "-shortest",
            "-r",
            "2",
            "-vf",
            "scale=1280:-2",
            "-pix_fmt",
            "yuv420p",
            "-y",
            str(spoken_video),
        ],
        check=True,
        timeout=60,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    cases = [
        ("pdf", "synthetic-message.pdf", "application/pdf", 200),
        ("image", "synthetic-message.png", "image/png", 200),
        ("audio", "synthetic-speech.wav", "audio/wav", 200),
        ("video", "synthetic-spoken-video.mp4", "video/mp4", 200),
        ("tone_negative", "synthetic-tone.wav", "audio/wav", 422),
    ]
    rows = []
    with tempfile.TemporaryDirectory() as workspace:
        history.DB_PATH = Path(workspace) / "history.sqlite3"
        with TestClient(app) as client:
            for name, filename, mime, expected in cases:
                response = client.post(
                    "/api/analyze/file",
                    files={
                        "file": ("synthetic", (fixtures / filename).read_bytes(), mime)
                    },
                )
                result = response.json()
                row = {
                    "case": name,
                    "status": response.status_code,
                    "expected_status": expected,
                    "passed": response.status_code == expected,
                    "preview_characters": len(result.get("extracted_text", "")),
                    "risk_level": result.get("risk_level"),
                    "rule_ids": result.get("rule_flags", []),
                    "warning_count": len(result.get("warnings", [])),
                }
                rows.append(row)
                print(json.dumps(row), flush=True)
    report = {
        "synthetic_only": True,
        "real_world_accuracy_measured": False,
        "test_dataset_evaluated": False,
        "cases": rows,
    }
    (ROOT / "models/media_smoke.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    if not all(row["passed"] for row in rows):
        raise ValueError("Media smoke checks failed; inspect aggregate report.")


if __name__ == "__main__":
    run()
