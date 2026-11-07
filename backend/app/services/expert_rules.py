"""Rule-based expert system for Roman Urdu scam / abuse signals."""

from __future__ import annotations

import re

URGENCY_WORDS = ("foran", "abhi", "jaldi", "urgent", "immediately", "turant")
PRIZE_WORDS = ("inaam", "jeet gaye", "lottery", "prize", "winner", "jackpot")
SENSITIVE_REQUESTS = (
    "otp",
    "cnic",
    "account number",
    "account no",
    "password",
    "pin code",
    "bank account",
    "card number",
)
ABUSE_WORDS = ("kutta", "bewaqoof", "ullu", "gadha", "harami", "bhenchod")


def apply_rules(cleaned_text: str, urls: list[str] | None = None) -> dict:
    """
    Evaluate simple expert rules and return flags plus flagged words.

    Rules cover: links, urgency, prize/lottery bait, and sensitive data requests.
    """
    urls = urls or []
    flags: list[str] = []
    flagged: list[str] = []
    text = cleaned_text.lower()

    if urls or re.search(r"https?://|www\.", text):
        flags.append("link_present")

    for word in URGENCY_WORDS:
        if word in text:
            flags.append("urgency_language")
            flagged.append(word)
            break

    for phrase in PRIZE_WORDS:
        if phrase in text:
            flags.append("prize_bait")
            flagged.append(phrase)
            break

    for phrase in SENSITIVE_REQUESTS:
        if phrase in text:
            flags.append("sensitive_data_request")
            flagged.append(phrase)
            break

    for word in ABUSE_WORDS:
        if word in text:
            flags.append("abusive_language")
            flagged.append(word)
            break

    # Deduplicate while preserving order
    flagged_words = list(dict.fromkeys(flagged))
    return {"rule_flags": flags, "flagged_words": flagged_words}
