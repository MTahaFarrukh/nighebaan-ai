"""Lazy CPU OCR with preinstalled local weights and bounded image decoding."""

import warnings
from functools import lru_cache
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from app.services.extractors import ExtractionError, ExtractionResult, bounded
from app.services.media_config import MAX_PIXELS, MODEL_DIR


@lru_cache(maxsize=1)
def reader():
    """Do not download weights while handling user uploads."""
    try:
        import easyocr
        import torch

        torch.set_num_threads(4)

        return easyocr.Reader(
            ["ur", "en"],
            gpu=False,
            model_storage_directory=str(MODEL_DIR / "ocr"),
            download_enabled=False,
            verbose=False,
        )
    except (ImportError, OSError, RuntimeError, ValueError, AssertionError):
        raise ExtractionError(
            "OCR model unavailable. Run the documented media setup command.", 503
        ) from None


def image_bytes(data: bytes) -> ExtractionResult:
    """Decode a bounded raster and recognize Urdu/English text in memory."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as source:
                if source.width * source.height > MAX_PIXELS:
                    raise ExtractionError(
                        "Image dimensions exceed the allowed pixel limit.", 413
                    )
                if getattr(source, "n_frames", 1) != 1:
                    raise ExtractionError("Animated images are not supported.", 415)
                normalized = ImageOps.exif_transpose(source).convert("RGB")
                normalized.thumbnail((2400, 2400))
                pixels = np.asarray(ImageOps.grayscale(normalized))
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ExtractionError(
            "Image dimensions exceed the allowed pixel limit.", 413
        ) from None
    except (UnidentifiedImageError, OSError, ValueError):
        raise ExtractionError("The image could not be decoded.") from None
    rows = reader().readtext(pixels, detail=1, paragraph=False, workers=0)
    text = bounded("\n".join(str(row[1]) for row in rows))
    confidence = float(np.mean([float(row[2]) for row in rows])) if rows else None
    notes = ["OCR can miss text or misread spelling. Review the extracted preview."]
    if confidence is not None and confidence < 0.5:
        notes.append("OCR confidence is low; treat this assessment cautiously.")
    return ExtractionResult(text, confidence, notes)


def extract(path: str) -> ExtractionResult:
    return image_bytes(Path(path).read_bytes())
