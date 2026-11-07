"""Extract lightweight URL features for phishing heuristics."""

from __future__ import annotations

from urllib.parse import urlparse

SHORTENER_DOMAINS = {
    "bit.ly",
    "tinyurl.com",
    "t.co",
    "goo.gl",
    "ow.ly",
    "is.gd",
    "buff.ly",
    "cutt.ly",
}


def extract_url_features(url: str) -> dict[str, float | int | bool | str]:
    """Compute simple structural features from a URL string."""
    raw = url.strip()
    if not re_has_scheme(raw):
        raw = "http://" + raw

    parsed = urlparse(raw)
    host = parsed.netloc.lower() or parsed.path.split("/")[0].lower()
    path = parsed.path or ""
    full = raw.lower()

    # Subdomains: exclude bare "example.com" and "www.example.com" edge cases
    host_no_www = host.removeprefix("www.")
    parts = [p for p in host_no_www.split(".") if p]
    subdomain_count = max(0, len(parts) - 2)  # e.g. a.b.example.com -> 2

    digits = sum(c.isdigit() for c in full)
    special_chars = sum(1 for c in full if not c.isalnum() and c not in ("/", ":", ".", "-", "_"))

    is_https = parsed.scheme == "https"
    is_shortener = any(host_no_www == d or host_no_www.endswith("." + d) for d in SHORTENER_DOMAINS)

    return {
        "url": url,
        "length": len(url),
        "digits_count": digits,
        "special_chars_count": special_chars,
        "subdomain_count": subdomain_count,
        "https": is_https,
        "is_shortener": is_shortener,
        "host": host_no_www,
    }


def re_has_scheme(url: str) -> bool:
    """Return True if the URL already includes a scheme."""
    return "://" in url
