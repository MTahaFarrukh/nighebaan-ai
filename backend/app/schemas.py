"""Pydantic v2 request/response models for the analyze API."""

from typing import Literal

from pydantic import BaseModel, Field

Label = Literal["normal", "abusive", "scam"]
RiskLevel = Literal["low", "medium", "high"]


class TextAnalyzeRequest(BaseModel):
    """Request body for text analysis."""

    text: str = Field(..., min_length=1, description="Message text to analyze")


class UrlAnalyzeRequest(BaseModel):
    """Request body for URL analysis."""

    url: str = Field(..., min_length=1, description="URL to analyze")


class Probabilities(BaseModel):
    """Class probability scores from the (stub) classifier."""

    normal: float
    abusive: float
    scam: float


class AnalyzeResponse(BaseModel):
    """Shared response shape for text and URL analysis."""

    label: Label
    probabilities: Probabilities
    rule_flags: list[str]
    risk_score: float = Field(..., ge=0.0, le=1.0)
    risk_level: RiskLevel
    explanation: str
    flagged_words: list[str]
    url_features: dict[str, float | int | bool | str] | None = None


class FileAnalyzeResponse(AnalyzeResponse):
    """In-memory preview only; extraction content is never persisted."""

    modality: Literal["image", "pdf", "audio", "video"]
    extracted_text: str
    extraction_confidence: float | None = None
    warnings: list[str] = Field(default_factory=list)
