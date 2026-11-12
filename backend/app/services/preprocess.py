"""Deterministic text preparation; never log, persist or fetch input entities."""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Mapping
from pathlib import Path
from typing import TypedDict

RESOURCES = Path(__file__).resolve().parents[1] / "resources"
URL_PATTERN = re.compile(
    r"(?<![\w@.])(?:https?://[^\s<>\"']+|www\.[^\s<>\"']+|"
    r"(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,24}"
    r"(?::\d{1,5})?(?:[/?#][^\s<>\"']*)?)(?![\w@])",
    re.IGNORECASE,
)
EMAIL_PATTERN = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+", re.UNICODE)
AMOUNT_PATTERN = re.compile(
    r"(?<!\w)(?:(?:rs\.?|pkr|rupay|rupees?|₨)\s*\d[\d,]*(?:\.\d+)?"
    r"(?:\s*(?:lakh|lac|crore|hazaar|thousand|million))?|"
    r"\d[\d,]*(?:\.\d+)?\s*(?:rs\.?|pkr|rupay|rupees?|lakh|lac|crore|hazaar))"
    r"(?!\w)",
    re.IGNORECASE,
)
PHONE_PATTERN = re.compile(
    r"(?<!\w)(?:\+?\d(?:[\s().-]*\d){6,14}|03[xX]{2}[-\s]?[xX]{7})(?!\w)"
)
REPEATED_LETTER_PATTERN = re.compile(r"([^\W\d_])\1{2,}", re.UNICODE)
# Cover common pictographs, modifiers, ZWJ sequences, flags and keycaps.
EMOJI_BASE = r"[\U0001F300-\U0001FAFF\u2600-\u27BF\u00A9\u00AE\u203C\u2049\u2122\u2139]"
EMOJI_UNIT = EMOJI_BASE + r"[\uFE0E\uFE0F]?[\U0001F3FB-\U0001F3FF]?"
EMOJI_PATTERN = re.compile(
    r"[0-9#*]\uFE0F?\u20E3|[\U0001F1E6-\U0001F1FF]{2}|"
    + EMOJI_UNIT
    + r"(?:\u200D"
    + EMOJI_UNIT
    + r")*"
)


class TextFeatures(TypedDict):
    length: int
    uppercase_ratio: float
    exclamation_count: int
    question_count: int
    digit_ratio: float
    has_url: bool
    url_count: int
    emoji_count: int


class PreprocessResult(TypedDict):
    cleaned: str
    urls: list[str]
    script: str
    urdu_ratio: float
    features: TextFeatures


def normalize_unicode(text: str) -> str:
    """Apply NFKC and remove controls, preserving whitespace and emoji joiners."""
    normalized = unicodedata.normalize("NFKC", text)
    emoji_joiners = {
        index
        for match in EMOJI_PATTERN.finditer(normalized)
        for index in range(match.start(), match.end())
        if normalized[index] == "\u200d"
    }
    return "".join(
        " " if char.isspace() else char
        for index, char in enumerate(normalized)
        if char.isspace()
        or index in emoji_joiners
        or not unicodedata.category(char).startswith("C")
    )


def urdu_script_ratio(text: str) -> float:
    """Measure Arabic-script letters among all letters; this is not language ID."""
    letters = [char for char in text if char.isalpha()]
    urdu = sum(
        any(
            low <= ord(char) <= high
            for low, high in (
                (0x0600, 0x06FF),
                (0x0750, 0x077F),
                (0x08A0, 0x08FF),
                (0xFB50, 0xFDFF),
                (0xFE70, 0xFEFF),
            )
        )
        for char in letters
    )
    return urdu / len(letters) if letters else 0.0


def _trim_url(url: str) -> str:
    """Remove sentence delimiters while retaining balanced URL parentheses."""
    url = url.rstrip(".,!?;:،۔؟")
    for closing, opening in ((")", "("), ("]", "["), ("}", "{")):
        while url.endswith(closing) and url.count(closing) > url.count(opening):
            url = url[:-1]
    return url


def extract_urls(text: str) -> list[str]:
    """Return static URL candidates in original case/order, including repeats."""
    # Mask emails first so their domains cannot become independent URL features.
    masked = EMAIL_PATTERN.sub(" ", text)
    return [_trim_url(match.group()) for match in URL_PATTERN.finditer(masked)]


def replace_entities(text: str) -> str:
    """Tokenize overlapping entities with email/URL and amount/phone precedence."""
    text = EMAIL_PATTERN.sub(" emailtoken ", text)
    text = URL_PATTERN.sub(" urltoken ", text)
    text = AMOUNT_PATTERN.sub(" amounttoken ", text)
    return PHONE_PATTERN.sub(" phonetoken ", text)


def collapse_repeated_letters(text: str) -> str:
    """Limit letter repetitions to two without altering digit sequences."""
    return REPEATED_LETTER_PATTERN.sub(r"\1\1", text)


def normalize_spelling(text: str, mapping: Mapping[str, str]) -> str:
    """Replace whole word tokens only; never replace substrings inside words."""
    return re.sub(r"\w+", lambda match: mapping.get(match.group(), match.group()), text)


def remove_punctuation(text: str) -> str:
    """Retain Unicode letters, marks and digits, splitting on all other symbols."""
    return " ".join(
        "".join(
            char if unicodedata.category(char)[0] in "LMN" else " " for char in text
        ).split()
    )


def load_normalization_map() -> dict[str, str]:
    """Load versioned lexical data without retaining any request text."""
    return json.loads(
        (RESOURCES / "normalization_map.json").read_text(encoding="utf-8")
    )


def load_stopwords() -> frozenset[str]:
    """Load conservative optional stopwords; retain negation and risk cues."""
    return frozenset(
        line.strip()
        for line in (RESOURCES / "stopwords_ru.txt")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip() and not line.startswith("#")
    )


def extract_features(text: str, urls: list[str] | None = None) -> TextFeatures:
    """Compute signals before lowercasing, token replacement or punctuation removal."""
    urls = extract_urls(text) if urls is None else urls
    letters = sum(char.isalpha() for char in text)
    return {
        "length": len(text),
        "uppercase_ratio": sum(char.isupper() for char in text) / letters
        if letters
        else 0.0,
        "exclamation_count": text.count("!"),
        "question_count": text.count("?") + text.count("؟"),
        "digit_ratio": sum(char.isdigit() for char in text) / len(text)
        if text
        else 0.0,
        "has_url": bool(urls),
        "url_count": len(urls),
        "emoji_count": len(EMOJI_PATTERN.findall(text)),
    }


def preprocess(
    text: str,
    *,
    normalize: bool = True,
    remove_stopwords: bool = False,
    normalization_map: Mapping[str, str] | None = None,
    stopwords: frozenset[str] | None = None,
) -> PreprocessResult:
    """Prepare text and in-memory metadata; flag Urdu script for the later M7 path."""
    normalized = normalize_unicode(text)
    ratio = urdu_script_ratio(normalized)
    urls = extract_urls(normalized)
    features = extract_features(normalized, urls)
    cleaned = replace_entities(normalized.lower())
    cleaned = EMOJI_PATTERN.sub(" emojitoken ", cleaned)
    cleaned = collapse_repeated_letters(cleaned)
    if normalize:
        mapping = (
            load_normalization_map() if normalization_map is None else normalization_map
        )
        cleaned = normalize_spelling(cleaned, mapping)
    cleaned = remove_punctuation(cleaned)
    if remove_stopwords:
        stopwords = load_stopwords() if stopwords is None else stopwords
        cleaned = " ".join(word for word in cleaned.split() if word not in stopwords)
    return {
        "cleaned": cleaned,
        "urls": urls,
        "script": "urdu" if ratio > 0.3 else "roman_or_other",
        "urdu_ratio": ratio,
        "features": features,
    }


def clean_text(
    text: str,
    *,
    normalize: bool = True,
    remove_stopwords: bool = False,
    normalization_map: Mapping[str, str] | None = None,
    stopwords: frozenset[str] | None = None,
) -> str:
    """String-in/string-out entry point for future sklearn preprocessing pipelines."""
    return preprocess(
        text,
        normalize=normalize,
        remove_stopwords=remove_stopwords,
        normalization_map=normalization_map,
        stopwords=stopwords,
    )["cleaned"]
