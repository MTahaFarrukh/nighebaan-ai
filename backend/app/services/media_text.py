"""Best-effort Urdu-script bridge and masked in-memory extraction preview."""

import json
import re
from pathlib import Path

from app.services.expert_rules import load_lexicon
from app.services.preprocess import urdu_script_ratio


def model_text(text: str) -> tuple[str, list[str]]:
    """Preserve original script for rules; transliterate only the ML input."""
    if not urdu_script_ratio(text):
        return text, []
    mapping = json.loads(
        (
            Path(__file__).resolve().parents[1] / "resources/urdu_transliteration.json"
        ).read_text(encoding="utf-8-sig")
    )

    def replace(match: re.Match) -> str:
        word = match.group()
        return mapping["words"].get(
            word, "".join(mapping["characters"].get(char, char) for char in word)
        )

    converted = re.sub(r"[\u0600-\u06ff]+", replace, text)
    return converted, [
        "Urdu-script text used approximate Roman Urdu transliteration for ML. Original-script and transliterated rules were applied; accuracy may be lower."
    ]


def preview(text: str) -> str:
    """Mask lexicon hits; return a bounded preview without saving the transcript."""
    for word in sorted(load_lexicon(), key=len, reverse=True):
        text = re.sub(
            r"(?<!\w)" + re.escape(word) + r"(?!\w)",
            lambda match: match.group()[0] + "***",
            text,
            flags=re.IGNORECASE,
        )
    return text[:5000]
