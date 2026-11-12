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


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    """Open a short-lived connection and create only the metadata table."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(DB_PATH, timeout=5)) as db:
        db.row_factory = sqlite3.Row
        db.execute(
            "CREATE TABLE IF NOT EXISTS web_risk_history (id INTEGER PRIMARY KEY, ts TEXT NOT NULL, modality TEXT NOT NULL, label TEXT NOT NULL, risk_level TEXT NOT NULL, risk_score REAL NOT NULL, rule_ids TEXT NOT NULL)"
        )
        with db:
            yield db


def record(
    *,
    modality: str,
    label: Label,
    risk_level: RiskLevel,
    risk_score: float,
    rule_ids: list[str],
) -> None:
    """Persist only high-risk web results; no notification delivery is implied."""
    if risk_level != "high":
        return
    allowed = {f"R{i:02d}" for i in range(1, 12)}
    flags = sorted(set(rule_ids) & allowed)
    with connection() as db:
        db.execute(
            "INSERT INTO web_risk_history(ts,modality,label,risk_level,risk_score,rule_ids) VALUES(?,?,?,?,?,?)",
            (
                datetime.now(UTC).isoformat(),
                modality,
                label,
                risk_level,
                risk_score,
                json.dumps(flags),
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
