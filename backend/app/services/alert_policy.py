"""Consent and atomic alert reservations for one dedicated demo account."""

import os
import sqlite3
import time
from pathlib import Path

DB = Path(__file__).resolve().parents[2] / "data/runtime/whatsapp.sqlite3"


def connect() -> sqlite3.Connection:
    DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB)
    db.execute(
        "CREATE TABLE IF NOT EXISTS consent (guardian TEXT PRIMARY KEY, enabled INTEGER NOT NULL)"
    )
    db.execute(
        "CREATE TABLE IF NOT EXISTS reservations (guardian TEXT, sender TEXT, digest TEXT, ts INTEGER)"
    )
    return db


def opted_in() -> bool:
    return os.getenv("WHATSAPP_OWNER_OPT_IN") == "true"


def dry_run() -> bool:
    return os.getenv("DRY_RUN", "true").lower() != "false"


def consent(guardian: str, enabled: bool | None = None) -> bool:
    from contextlib import closing

    with closing(connect()) as db, db:
        if enabled is not None:
            db.execute(
                "INSERT OR REPLACE INTO consent VALUES (?, ?)", (guardian, enabled)
            )
        row = db.execute(
            "SELECT enabled FROM consent WHERE guardian = ?", (guardian,)
        ).fetchone()
        return bool(row and row[0])


def reserve(guardian: str, sender: str, digest: str) -> str:
    from contextlib import closing

    now = int(time.time())
    with closing(connect()) as db, db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT enabled FROM consent WHERE guardian = ?", (guardian,)
        ).fetchone()
        if not opted_in() or not row or not row[0]:
            return "consent_required"
        db.execute("DELETE FROM reservations WHERE ts <= ?", (now - 86400,))
        if db.execute(
            "SELECT 1 FROM reservations WHERE guardian=? AND sender=? AND digest=?",
            (guardian, sender, digest),
        ).fetchone():
            return "duplicate"
        count = db.execute(
            "SELECT count(*) FROM reservations WHERE guardian=? AND sender=? AND ts>?",
            (guardian, sender, now - 3600),
        ).fetchone()[0]
        if count >= 3:
            return "rate_limited"
        db.execute(
            "INSERT INTO reservations VALUES (?,?,?,?)", (guardian, sender, digest, now)
        )
        return "eligible"
