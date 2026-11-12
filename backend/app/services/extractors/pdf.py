"""Text-first PDF extraction with bounded per-page OCR fallback."""

import math

import pymupdf

from app.services.extractors import ExtractionError, ExtractionResult, bounded
from app.services.extractors.image import image_bytes
from app.services.media_config import MAX_PAGES, MAX_PIXELS

pymupdf.TOOLS.mupdf_display_errors(False)
pymupdf.TOOLS.mupdf_display_warnings(False)


def extract(path: str) -> ExtractionResult:
    """Reject encrypted/oversized documents; keep page text only in memory."""
    try:
        with pymupdf.open(path) as document:
            if document.needs_pass:
                raise ExtractionError("Password-protected PDFs are not supported.", 415)
            if not 0 < document.page_count <= MAX_PAGES:
                raise ExtractionError(
                    "PDF page count exceeds the configured limit.", 413
                )
            texts, notes = [], []
            for page in document:
                text = page.get_text("text").strip()
                if not text:
                    area = page.rect.width * page.rect.height
                    if not math.isfinite(area) or area <= 0:
                        raise ExtractionError("Invalid PDF page dimensions.")
                    scale = min(2.0, math.sqrt(min(MAX_PIXELS, 4000000) / area))
                    pix = page.get_pixmap(
                        matrix=pymupdf.Matrix(scale, scale),
                        colorspace=pymupdf.csRGB,
                        alpha=False,
                    )
                    result = image_bytes(pix.tobytes("png"))
                    text = result.text
                    notes.extend(result.warnings)
                    notes.append("At least one PDF page required OCR.")
                texts.append(text)
                bounded("\n".join(texts))
            return ExtractionResult(
                bounded("\n".join(texts)), None, list(dict.fromkeys(notes))
            )
    except ExtractionError:
        raise
    except (RuntimeError, ValueError, OSError):
        raise ExtractionError("The PDF could not be read.") from None
