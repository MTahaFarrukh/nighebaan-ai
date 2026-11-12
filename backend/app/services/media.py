"""Magic-byte media dispatch and temporary-workspace lifecycle."""

import tempfile
import threading
from pathlib import Path

import filetype

from app.services.extractors import (
    ExtractionError,
    ExtractionResult,
    audio,
    image,
    pdf,
    video,
)
from app.services.media_config import MAX_BYTES

MEDIA_LOCK = threading.Lock()
MIME_KIND = {
    "application/pdf": "pdf",
    "image/png": "image",
    "image/jpeg": "image",
    "image/webp": "image",
    "audio/mpeg": "audio",
    "audio/x-wav": "audio",
    "audio/wav": "audio",
    "audio/ogg": "audio",
    "application/ogg": "audio",
    "audio/flac": "audio",
    "audio/x-flac": "audio",
    "audio/mp4": "audio",
    "audio/x-m4a": "audio",
    "video/mp4": "video",
    "video/webm": "video",
    "audio/webm": "audio",
}


def detect(data: bytes, declared: str | None) -> str:
    """Use signature, not filename; reject unsupported types or MIME families."""
    match = filetype.guess(data)
    mime = match.mime if match else ""
    kind = MIME_KIND.get(mime)
    if not kind:
        raise ExtractionError(
            "Supported files: PDF, PNG/JPEG/WebP, WAV/MP3/OGG/FLAC/M4A and MP4/WebM.",
            415,
        )
    declared = (declared or "").split(";", 1)[0].lower()
    declared_kind = MIME_KIND.get(declared)
    if declared not in {"", "application/octet-stream"} and (
        declared_kind is None
        or declared_kind != kind
        and {declared_kind, kind} != {"audio", "video"}
    ):
        raise ExtractionError("Declared file type does not match its contents.", 415)
    return kind


def extract(data: bytes, declared: str | None) -> tuple[str, ExtractionResult]:
    """Delete original uploads, converted audio and frames even on errors."""
    if not data:
        raise ExtractionError("The uploaded file is empty.")
    if len(data) > MAX_BYTES:
        raise ExtractionError("File exceeds the configured upload size limit.", 413)
    kind = detect(data, declared)
    if not MEDIA_LOCK.acquire(blocking=False):
        raise ExtractionError(
            "Another media file is being processed. Please retry shortly.", 429
        )
    try:
        with tempfile.TemporaryDirectory(prefix="nigehbaan-media-") as directory:
            path = Path(directory) / "upload.bin"
            path.write_bytes(data)
            result = {
                "image": image.extract,
                "pdf": pdf.extract,
                "audio": audio.extract,
                "video": video.extract,
            }[kind](str(path))
            if not result.text.strip():
                raise ExtractionError(
                    "No readable text or speech was detected. Try a clearer file."
                )
            return kind, result
    finally:
        MEDIA_LOCK.release()
