"""Local high-risk metadata history. Never accepts message text or URLs."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from pathlib import Path

from app.dashboard_schemas import AlertHistory, AlertRow
from app.schemas import Label, RiskLevel

DB_PATH = Path(__file__).resolve().parents[2] / "data/runtime/alerts.sqlite3"
SOURCES = {"web", "whatsapp"}
ALERT_STATES = {"reserved", "dry_run", "duplicate", "rate_limited", "below_threshold"}


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    """Open a short-lived connection and create only the metadata table."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(DB_PATH, timeout=5)) as db:
        db.row_factory = sqlite3.Row
        db.execute(
            "CREATE TABLE IF NOT EXISTS web_risk_history (id INTEGER PRIMARY KEY, ts TEXT NOT NULL, modality TEXT NOT NULL, label TEXT NOT NULL, risk_level TEXT NOT NULL, risk_score REAL NOT NULL, rule_ids TEXT NOT NULL, source TEXT NOT NULL DEFAULT 'web', alert_state TEXT)"
        )
        columns = {row[1] for row in db.execute("PRAGMA table_info(web_risk_history)")}
        if "source" not in columns:
            db.execute(
                "ALTER TABLE web_risk_history ADD COLUMN source TEXT NOT NULL DEFAULT 'web'"
            )
        if "alert_state" not in columns:
            db.execute("ALTER TABLE web_risk_history ADD COLUMN alert_state TEXT")
        with db:
            yield db


def record(
    *,
    modality: str,
    label: Label,
    risk_level: RiskLevel,
    risk_score: float,
    rule_ids: list[str],
    source: str = "web",
    alert_state: str | None = None,
) -> None:
    """Persist high-risk metadata only; no source content is ever accepted."""
    if risk_level != "high":
        return
    if source not in SOURCES or (alert_state is not None and alert_state not in ALERT_STATES):
        raise ValueError("Unsupported local history metadata.")
    allowed = {f"R{i:02d}" for i in range(1, 12)}
    flags = sorted(set(rule_ids) & allowed)
    with connection() as db:
        db.execute(
            "INSERT INTO web_risk_history(ts,modality,label,risk_level,risk_score,rule_ids,source,alert_state) VALUES(?,?,?,?,?,?,?,?)",
            (
                datetime.now(UTC).isoformat(),
                modality,
                label,
                risk_level,
                risk_score,
                json.dumps(flags),
                source,
                alert_state,
            ),
        )


def history(limit: int, offset: int) -> AlertHistory:
    """Return paginated rows plus full-history aggregate counts."""
    with connection() as db:
        rows = db.execute(
            "SELECT * FROM web_risk_history ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        total = db.execute("SELECT COUNT(*) FROM web_risk_history").fetchone()[0]
        modalities = dict(
            db.execute(
                "SELECT modality,COUNT(*) FROM web_risk_history GROUP BY modality"
            ).fetchall()
        )
        days = dict(
            db.execute(
                "SELECT substr(ts,1,10),COUNT(*) FROM web_risk_history GROUP BY substr(ts,1,10) ORDER BY ts"
            ).fetchall()
        )
    return AlertHistory(
        items=[
            AlertRow(**{**dict(row), "rule_ids": json.loads(row["rule_ids"])})
            for row in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
        by_modality=modalities,
        by_day=days,
    )
