"""Typed public dashboard contracts; no source text or identifiers."""

from pydantic import BaseModel, Field

from app.schemas import Label, RiskLevel


class ClassMetric(BaseModel):
    p: float
    r: float
    f1: float


class ModelMetric(BaseModel):
    name: str
    macro_f1: float
    accuracy: float | None = None
    per_class: dict[str, ClassMetric] = Field(default_factory=dict)
    confusion_matrix: list[list[int]] = Field(default_factory=list)


class Ablation(BaseModel):
    name: str
    rows: list[ModelMetric]


class ModelMetrics(BaseModel):
    evaluation_split: str
    data_review_status: str
    models: list[ModelMetric]
    best_model: str
    url_models: list[ModelMetric] = Field(default_factory=list)
    best_url_model: str | None = None
    ablations: list[Ablation] = Field(default_factory=list)


class AlertRow(BaseModel):
    id: int
    ts: str
    modality: str
    label: Label
    risk_level: RiskLevel
    risk_score: float
    rule_ids: list[str]


class AlertHistory(BaseModel):
    items: list[AlertRow]
    total: int
    limit: int
    offset: int
    by_modality: dict[str, int]
    by_day: dict[str, int]


class PublicSettings(BaseModel):
    medium_threshold: float
    high_threshold: float
    credential_url_floor: float
    dry_run: bool
    whatsapp_available: bool = False
    consent_available: bool = False

    max_upload_mb: int = 25
    max_pdf_pages: int = 20
    max_media_seconds: int = 60
