"""Basic text cleaning and URL extraction helpers."""

from __future__ import annotations

import re

URL_PATTERN = re.compile(
    r"https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9.-]+\.(com|net|org|pk|ly|me|io|co)/\S*",
    re.IGNORECASE,
)
REPEATED_LETTER_PATTERN = re.compile(r"(.)\1{2,}", re.IGNORECASE)


def clean_text(text: str) -> str:
    """Lowercase text and collapse runs of 3+ repeated letters."""
    lowered = text.lower().strip()
    collapsed = REPEATED_LETTER_PATTERN.sub(r"\1\1", lowered)
    return re.sub(r"\s+", " ", collapsed)


def extract_urls(text: str) -> list[str]:
    """Return URLs found in the given text."""
    return [m.group(0) for m in URL_PATTERN.finditer(text)]


def preprocess(text: str) -> dict[str, str | list[str]]:
    """Clean text and extract URLs for downstream services."""
    cleaned = clean_text(text)
    urls = extract_urls(cleaned)
    return {"cleaned": cleaned, "urls": urls}
