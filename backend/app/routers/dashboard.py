"""Read-only frontend endpoints with an explicit public-field allowlist."""

import json
import os
import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from pydantic import ValidationError

from app.config import settings
from app.dashboard_schemas import AlertHistory, ModelMetrics, PublicSettings
from app.services import history, media_config

router = APIRouter(tags=["dashboard"])
METRICS_PATH = Path(__file__).resolve().parents[2] / "models/metrics.json"


@router.get("/metrics/models", response_model=ModelMetrics)
def model_metrics() -> ModelMetrics:
    """Expose aggregate measured metrics, excluding paths and artifact metadata."""
    try:
        return ModelMetrics.model_validate(
            json.loads(METRICS_PATH.read_text(encoding="utf-8"))
        )
    except (OSError, ValueError, ValidationError):
        raise HTTPException(
            status_code=503, detail="Model metrics are unavailable."
        ) from None


@router.get("/alerts", response_model=AlertHistory)
def alerts(
    limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)
) -> AlertHistory:
    """High-risk web analysis history, not sent WhatsApp notifications."""
    try:
        return history.history(limit, offset)
    except (OSError, sqlite3.Error):
        raise HTTPException(status_code=503, detail="History is unavailable.") from None


@router.get("/settings", response_model=PublicSettings)
def public_settings() -> PublicSettings:
    """Return display-only thresholds; never return environment secrets."""
    return PublicSettings(
        max_upload_mb=media_config.MAX_UPLOAD_MB,
        max_pdf_pages=media_config.MAX_PAGES,
        max_media_seconds=media_config.MAX_SECONDS,
        medium_threshold=settings.medium_threshold,
        high_threshold=settings.alert_threshold,
        credential_url_floor=settings.credential_url_floor,
        dry_run=os.getenv("DRY_RUN", "true").lower() != "false",
    )
