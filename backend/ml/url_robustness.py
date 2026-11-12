"""Assumed-benign synthetic path stress cases, never a real-world test set."""

import random
from urllib.parse import urlsplit, urlunsplit

TRAIN_PATHS = (
    "help/overview",
    "account/login",
    "support/contact",
    "products/catalog",
    "orders/status",
    "articles/guide",
    "search/results",
    "news/latest",
)
VALIDATION_PATHS = (
    "services/information",
    "customer/profile",
    "documents/handbook",
    "portal/signin",
    "library/reference",
    "shipping/details",
    "updates/archive",
    "settings/preferences",
)


def benign_variant(url: str, index: int, *, validation: bool = False) -> str:
    """Keep origin/scheme; append ordinary paths only to source-labeled benign URLs."""
    parsed = urlsplit(url)
    if validation:
        path = (
            parsed.path.rstrip("/")
            + "/"
            + VALIDATION_PATHS[index % len(VALIDATION_PATHS)]
        )
        query = (
            ("page=" + str(index % 17 + 1) + "&lang=en")
            if index % 3 == 0
            else parsed.query
        )
    else:
        rng = random.Random(42 + index)
        words = (
            "a",
            "help",
            "account",
            "login",
            "support",
            "contact",
            "products",
            "catalog",
            "orders",
            "status",
            "articles",
            "guide",
            "search",
            "results",
            "news",
            "latest",
            "index",
            "docs",
        )
        parts = []
        for _ in range(rng.randint(1, 4)):
            part = rng.choice(words)
            if rng.random() < 0.3:
                part += "-" + str(rng.randrange(1, 10000000))
            parts.append(part)
        path = parsed.path.rstrip("/") + "/" + ("/".join(parts))
        if rng.random() < 0.2:
            path += rng.choice((".html", ".php", ".pdf"))
        query = parsed.query
        for key in rng.sample(("page", "lang", "view", "item"), rng.randint(0, 4)):
            query += (
                ("&" if query else "")
                + key
                + "="
                + rng.choice(("en", "list", "all", str(rng.randrange(1, 100000))))
            )
    return urlunsplit((parsed.scheme, parsed.netloc, path, query, ""))


def without_www(url: str) -> str:
    """Synthetic hostname variant; inherited label is an explicit assumption."""
    parsed = urlsplit(url)
    if parsed.username is not None or not parsed.netloc.lower().startswith("www."):
        return url
    return urlunsplit((parsed.scheme, parsed.netloc[4:], parsed.path, parsed.query, ""))
