"""Synthetic media contracts, bounds, script handling and guaranteed cleanup."""

import asyncio
import wave
from io import BytesIO
from pathlib import Path

import numpy as np
import pymupdf
import pytest
from app import upload_limit
from app.main import app
from app.services import media, media_text
from app.services.extractors import (
    ExtractionError,
    ExtractionResult,
    audio,
    image,
    pdf,
    video,
)
from app.services.extractors.ffmpeg import probe
from fastapi.testclient import TestClient
from PIL import Image

client = TestClient(app)


def pdf_bytes(text="Foran OTP bhejo https://example.com", pages=1):
    with pymupdf.open() as document:
        for _ in range(pages):
            page = document.new_page()
            page.insert_text((72, 72), text)
        return document.tobytes()


def png_bytes():
    output = BytesIO()
    Image.new("RGB", (120, 50), "white").save(output, format="PNG")
    return output.getvalue()


def wav_bytes(seconds=2):
    output = BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        samples = (
            np.sin(np.arange(seconds * 16000) * 2 * np.pi * 440 / 16000) * 1000
        ).astype("<i2")
        wav.writeframes(samples.tobytes())
    return output.getvalue()


def test_pdf_end_to_end_metadata(fake_text_model):
    response = client.post(
        "/api/analyze/file",
        files={"file": ("ignored-name.jpg", pdf_bytes(), "application/pdf")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["modality"] == "pdf" and data["risk_level"] == "high"
    assert data["extracted_text"] and "R05" in data["rule_flags"]
    history = client.get("/api/alerts").json()
    assert history["total"] == 1 and history["items"][0]["modality"] == "pdf"
    assert "example.com" not in str(history)


@pytest.mark.parametrize(
    "payload,mime,status",
    [
        (b"", "application/pdf", 422),
        (b"plain text", "image/png", 415),
        (b"%PDF-invalid", "application/pdf", 422),
    ],
)
def test_bad_media(payload, mime, status):
    response = client.post(
        "/api/analyze/file", files={"file": ("private-sentinel", payload, mime)}
    )
    assert response.status_code == status
    assert "private-sentinel" not in response.text


def test_mime_mismatch_and_oversize(monkeypatch):
    response = client.post(
        "/api/analyze/file", files={"file": ("x", png_bytes(), "application/pdf")}
    )
    assert response.status_code == 415
    from app.routers import files

    monkeypatch.setattr(files, "MAX_BYTES", 10)
    assert (
        client.post(
            "/api/analyze/file", files={"file": ("x", png_bytes(), "image/png")}
        ).status_code
        == 413
    )


def test_page_and_pixel_limits(monkeypatch, tmp_path):
    path = tmp_path / "test.pdf"
    path.write_bytes(pdf_bytes(pages=2))
    monkeypatch.setattr(pdf, "MAX_PAGES", 1)
    with pytest.raises(ExtractionError) as error:
        pdf.extract(str(path))
    assert error.value.status == 413
    monkeypatch.setattr(image, "MAX_PIXELS", 100)
    with pytest.raises(ExtractionError) as error:
        image.image_bytes(png_bytes())
    assert error.value.status == 413


def test_ocr_confidence_and_blank(monkeypatch):
    class Reader:
        def readtext(self, *args, **kwargs):
            return [(None, "synthetic placeholder", 0.4)]

    monkeypatch.setattr(image, "reader", lambda: Reader())
    result = image.image_bytes(png_bytes())
    assert result.confidence == 0.4 and any("low" in note for note in result.warnings)
    monkeypatch.setattr(image, "extract", lambda path: ExtractionResult(""))
    with pytest.raises(ExtractionError, match="No readable"):
        media.extract(png_bytes(), "image/png")


def test_scanned_pdf_uses_ocr(monkeypatch, tmp_path):
    path = tmp_path / "blank.pdf"
    path.write_bytes(pdf_bytes(""))
    monkeypatch.setattr(
        pdf, "image_bytes", lambda data: ExtractionResult("OCR placeholder", 0.9)
    )
    result = pdf.extract(str(path))
    assert result.text == "OCR placeholder" and result.warnings


@pytest.mark.parametrize("fail", [False, True])
def test_temp_cleanup_on_success_failure(monkeypatch, fail):
    paths = []

    def extract(path):
        paths.append(Path(path))
        (Path(path).parent / "converted.wav").write_bytes(b"synthetic")
        if fail:
            raise ExtractionError("Synthetic failure")
        return ExtractionResult("synthetic")

    monkeypatch.setattr(pdf, "extract", extract)
    if fail:
        with pytest.raises(ExtractionError):
            media.extract(pdf_bytes(), "application/pdf")
    else:
        media.extract(pdf_bytes(), "application/pdf")
    assert paths and not paths[0].parent.exists()
    assert not media.MEDIA_LOCK.locked()


def test_busy_rejects_without_processing():
    media.MEDIA_LOCK.acquire()
    try:
        with pytest.raises(ExtractionError) as error:
            media.extract(png_bytes(), "image/png")
        assert error.value.status == 429
    finally:
        media.MEDIA_LOCK.release()


def test_duration_limit_before_transcription(tmp_path):
    path = tmp_path / "long.wav"
    path.write_bytes(wav_bytes(61))
    with pytest.raises(ExtractionError) as error:
        probe(str(path))
    assert error.value.status == 413


def test_audio_conversion_and_cleanup(tmp_path, monkeypatch):
    path = tmp_path / "input.wav"
    path.write_bytes(wav_bytes())
    seen = []

    def transcribe(path):
        seen.append(path)
        with wave.open(path, "rb") as wav:
            assert wav.getframerate() == 16000 and wav.getnchannels() == 1
        return ExtractionResult("synthetic transcript")

    monkeypatch.setattr(audio, "transcribe", transcribe)
    result = audio.extract(str(path))
    assert result.text == "synthetic transcript" and seen and not Path(seen[0]).exists()


def test_video_combines_audio_and_sampled_frames(tmp_path, monkeypatch):
    path = tmp_path / "video.mp4"
    path.write_bytes(b"synthetic")
    monkeypatch.setattr(
        video, "probe", lambda path: {"video": True, "audio": True, "duration": 2}
    )
    monkeypatch.setattr(
        video.audio, "extract", lambda path: ExtractionResult("audio text")
    )

    def frames(path, destination, arguments):
        assert "fps=1/10" in " ".join(arguments)
        (tmp_path / "frame-001.png").write_bytes(png_bytes())

    monkeypatch.setattr(video, "convert", frames)
    monkeypatch.setattr(
        video.image, "extract", lambda path: ExtractionResult("frame text")
    )
    result = video.extract(str(path))
    assert "audio text" in result.text and "frame text" in result.text
    assert not list(tmp_path.glob("frame-*.png"))


def test_urdu_bridge_and_masking(monkeypatch):
    converted, notes = media_text.model_text("فوراً کوڈ بھیجو")
    assert converted == "foran code bhejo" and notes
    monkeypatch.setattr(media_text, "load_lexicon", lambda: ("syntheticbadword",))
    assert media_text.preview("SYNTHETICBADWORD") == "S***"
    assert media_text.model_text("normal text") == ("normal text", [])


def test_media_urdu_preserves_original_rule_cues(fake_text_model, monkeypatch):
    from app.schemas import Probabilities
    from app.services import classifier

    seen = []
    monkeypatch.setattr(
        media,
        "extract",
        lambda data, mime: (
            "audio",
            ExtractionResult("فوراً OTP بھیجو https://example.com"),
        ),
    )
    monkeypatch.setattr(
        classifier,
        "classify_text",
        lambda text: (
            seen.append(text) or Probabilities(normal=0.1, abusive=0.1, scam=0.8)
        ),
    )
    response = client.post(
        "/api/analyze/file", files={"file": ("x", b"synthetic", "audio/wav")}
    )
    assert response.status_code == 200 and response.json()["warnings"]
    assert "foran" in seen[0] and "R05" in response.json()["rule_flags"]


def test_chunked_size_guard_before_parser(monkeypatch):
    monkeypatch.setattr(upload_limit, "MAX_BYTES", 1)
    called = []
    sent = []

    async def downstream(scope, receive, send):
        called.append(True)

    chunks = iter(
        [
            {"type": "http.request", "body": b"x" * (1024 * 1024), "more_body": True},
            {"type": "http.request", "body": b"xx", "more_body": False},
        ]
    )

    async def receive():
        return next(chunks)

    async def send(message):
        sent.append(message)

    asyncio.run(
        upload_limit.UploadLimitMiddleware(downstream)(
            {"type": "http", "path": "/api/analyze/file", "headers": []}, receive, send
        )
    )
    assert not called and sent[0]["status"] == 413


def test_decoder_error_not_echoed(monkeypatch):
    def fail(*args):
        raise RuntimeError("private-sentinel")

    monkeypatch.setattr(media, "extract", fail)
    response = client.post(
        "/api/analyze/file", files={"file": ("x", b"synthetic", "application/pdf")}
    )
    assert response.status_code == 422 and "private-sentinel" not in response.text


def test_missing_ocr_reports_503_and_cleans(monkeypatch):
    def unavailable():
        raise ExtractionError("OCR model unavailable.", 503)

    monkeypatch.setattr(image, "reader", unavailable)
    response = client.post(
        "/api/analyze/file", files={"file": ("x", png_bytes(), "image/png")}
    )
    assert response.status_code == 503
    assert not media.MEDIA_LOCK.locked()


def test_upload_closed_on_rejection(monkeypatch):
    from app.routers import files

    class Upload:
        content_type = "application/pdf"
        closed = False

        async def read(self, size):
            return b"too big"

        async def close(self):
            self.closed = True

    upload = Upload()
    monkeypatch.setattr(files, "MAX_BYTES", 2)
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        asyncio.run(files.analyze_file(upload))
    assert upload.closed


def test_urdu_resource_flags_and_preview_are_masked():
    from app.services.expert_rules import RESOURCES, apply_rules

    word = (
        (RESOURCES / "abuse_lexicon_urdu.txt")
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    result = apply_rules(word)
    assert "R11" in result["rule_flags"]
    assert result["flagged_words"] == [word[0] + "***"]
    assert media_text.preview(word) == word[0] + "***"
