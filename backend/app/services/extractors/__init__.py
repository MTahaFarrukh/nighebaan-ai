"""Shared extraction results and content-free failure messages."""

from dataclasses import dataclass, field

from app.services.media_config import MAX_TEXT


class ExtractionError(Exception):
    """Public safe error with HTTP status; never includes file names or text."""

    def __init__(self, message: str, status: int = 422) -> None:
        self.message = message
        self.status = status
        super().__init__(message)


@dataclass
class ExtractionResult:
    text: str
    confidence: float | None = None
    warnings: list[str] = field(default_factory=list)


def bounded(text: str) -> str:
    """Reject overlong extraction rather than silently omit risk-bearing content."""
    if len(text) > MAX_TEXT:
        raise ExtractionError(
            "Extracted text exceeds the allowed character limit.", 413
        )
    return text.strip()
