"""Deterministic resource-driven rules; no input content is persisted or logged."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TypedDict
from urllib.parse import urlsplit

from app.services.preprocess import (
    collapse_repeated_letters,
    extract_urls,
    load_normalization_map,
    normalize_spelling,
    normalize_unicode,
)

RESOURCES = Path(__file__).resolve().parents[1] / "resources"


class RuleResult(TypedDict):
    rule_flags: list[str]
    flagged_words: list[str]


def load_rules() -> tuple[dict, ...]:
    """Read JSON-compatible YAML 1.2 without executable YAML constructors."""
    return tuple(json.loads((RESOURCES / "rules.yaml").read_text(encoding="utf-8")))


def load_lexicon() -> tuple[str, ...]:
    """Read lexical data without exposing it in diagnostics."""
    return tuple(
        line.strip()
        for resource in ("abuse_lexicon.txt", "abuse_lexicon_urdu.txt")
        for line in (RESOURCES / resource).read_text(encoding="utf-8").splitlines()
        if line.strip()
    )


def rule_scores(flags: list[str]) -> tuple[float, float]:
    """Sum unique known rule weights on separate scam and abuse axes."""
    selected = set(flags)
    return tuple(
        min(
            1.0,
            sum(
                rule["weight"]
                for rule in load_rules()
                if rule["id"] in selected and rule["axis"] == axis
            ),
        )
        for axis in ("scam", "abuse")
    )


def suspicious_url(url: str) -> bool:
    """Inspect host only; never visit a URL."""
    try:
        host = (urlsplit(url if "://" in url else "//" + url).hostname or "").lower()
    except ValueError:
        return False
    return host in {"bit.ly", "tinyurl.com", "t.co", "is.gd"} or host.endswith(
        (".xyz", ".top", ".tk")
    )


def apply_rules(
    text: str, urls: list[str] | None = None, *, lexicon: tuple[str, ...] | None = None
) -> RuleResult:
    """Match whole-token cues by clause, preserving raw URL host information."""
    text = normalize_spelling(
        collapse_repeated_letters(normalize_unicode(text).lower()),
        load_normalization_map(),
    )
    urls = extract_urls(text) if urls is None else urls
    clauses = re.split(r"[.!?;\n۔؟]+", text)
    flags, masked = [], []
    for rule in load_rules():
        identifier = rule["id"]
        if identifier == "R01":
            fired = bool(urls)
        elif identifier == "R02":
            fired = any(suspicious_url(url) for url in urls)
        elif identifier == "R11":
            hits = [
                word
                for word in (load_lexicon() if lexicon is None else lexicon)
                if re.search(r"(?<!\w)" + re.escape(word) + r"(?!\w)", text)
            ]
            fired = bool(hits)
            masked.extend(word[0] + "***" for word in hits)
        else:
            fired = any(
                any(re.search(pattern, clause) for pattern in rule["patterns"])
                and not any(
                    re.search(pattern, clause)
                    for pattern in rule.get("exclude_patterns", [])
                )
                for clause in clauses
            )
        if fired:
            flags.append(identifier)
    return {"rule_flags": flags, "flagged_words": list(dict.fromkeys(masked))}
