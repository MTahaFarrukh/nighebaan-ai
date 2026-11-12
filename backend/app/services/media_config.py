"""Bounded media settings; all limits are enforced before model inference."""

import os
from pathlib import Path


def positive(name: str, default: int) -> int:
    value = int(os.getenv(name, str(default)))
    if value <= 0:
        raise ValueError(f"{name} must be positive.")
    return value


MAX_UPLOAD_MB = positive("MAX_UPLOAD_MB", 25)
MAX_BYTES = MAX_UPLOAD_MB * 1024 * 1024
MAX_PAGES = positive("MAX_PDF_PAGES", 20)
MAX_SECONDS = positive("MAX_VIDEO_SECONDS", 60)
MAX_PIXELS = positive("MAX_IMAGE_PIXELS", 16000000)
MAX_TEXT = positive("MAX_EXTRACTED_CHARS", 30000)
MODEL_DIR = Path(__file__).resolve().parents[2] / "models/media"
