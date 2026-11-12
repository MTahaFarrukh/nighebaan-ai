"""Static URL features; no DNS, HTTP or content lookup is performed."""

from __future__ import annotations

import ipaddress
import math
from collections import Counter
from urllib.parse import parse_qsl, urlsplit, urlunsplit

SHORTENER_DOMAINS = frozenset(
    {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd", "buff.ly", "cutt.ly"}
)
SUSPICIOUS_TLDS = frozenset({"xyz", "top", "tk"})
KEYWORDS = ("login", "verify", "secure", "bank", "update", "prize")
FEATURE_NAMES = (
    "length",
    "host_length",
    "dots_count",
    "subdomain_count",
    "digits_count",
    "hyphens_count",
    "has_at",
    "ip_as_host",
    "https",
    "is_shortener",
    "suspicious_tld",
    "keyword_hits",
    "path_length",
    "query_params",
    "entropy",
    "special_chars_count",
)


def canonical_url(url: str) -> str:
    """Normalize scheme/host while preserving case-sensitive paths and queries."""
    raw = url.strip()
    if (
        not raw
        or len(raw) > 8192
        or any(c.isspace() or ord(c) < 32 for c in raw)
        or "\\" in raw
    ):
        raise ValueError("Invalid HTTP URL.")
    if raw.startswith("//"):
        raw = "http:" + raw
    elif "://" not in raw:
        raw = "http://" + raw
    try:
        parsed = urlsplit(raw)
        host = parsed.hostname
        port = parsed.port
        if parsed.scheme.lower() not in {"http", "https"} or not host:
            raise ValueError
        host = host.rstrip(".").encode("idna").decode("ascii").lower()
        if not host or any(c in host for c in "/?#@%"):
            raise ValueError
        if ":" in host:
            ipaddress.IPv6Address(host)
            host = "[" + host + "]"
        credentials = (
            parsed.netloc.rsplit("@", 1)[0] + "@" if "@" in parsed.netloc else ""
        )
        netloc = credentials + host
        if port is not None and (parsed.scheme.lower(), port) not in {
            ("http", 80),
            ("https", 443),
        }:
            netloc += ":" + str(port)
        return urlunsplit(
            (parsed.scheme.lower(), netloc, parsed.path or "/", parsed.query, "")
        )
    except (ValueError, UnicodeError):
        raise ValueError("Invalid HTTP URL.") from None


def extract_url_features(url: str) -> dict[str, float | int | bool | str]:
    """Return numeric lexical cues only, never echo the URL or credentials."""
    raw = canonical_url(url)
    parsed = urlsplit(raw)
    host = parsed.hostname or ""
    try:
        ipaddress.ip_address(host)
        is_ip = True
    except ValueError:
        is_ip = False
    host_no_www = host.removeprefix("www.")
    counts = Counter(raw)
    return {
        "length": len(raw),
        "host_length": len(host),
        "dots_count": raw.count("."),
        "subdomain_count": 0 if is_ip else max(0, len(host_no_www.split(".")) - 2),
        "digits_count": sum(c.isdigit() for c in raw),
        "hyphens_count": raw.count("-"),
        "has_at": "@" in parsed.netloc,
        "ip_as_host": is_ip,
        "https": parsed.scheme == "https",
        "is_shortener": host_no_www in SHORTENER_DOMAINS,
        "suspicious_tld": host.rsplit(".", 1)[-1] in SUSPICIOUS_TLDS,
        "keyword_hits": sum(word in raw.lower() for word in KEYWORDS),
        "path_length": len(parsed.path),
        "query_params": len(parse_qsl(parsed.query, keep_blank_values=True)),
        "entropy": -sum(
            (n / len(raw)) * math.log2(n / len(raw)) for n in counts.values()
        ),
        "special_chars_count": sum(not c.isalnum() and c not in "/:.-_" for c in raw),
    }
