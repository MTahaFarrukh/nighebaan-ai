"""Application configuration loaded from environment variables."""

from __future__ import annotations

import math
import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Runtime settings for the Nigehbaan AI API."""

    def __init__(self) -> None:
        self.medium_threshold = float(os.getenv("MEDIUM_THRESHOLD", "0.35"))
        self.alert_threshold = float(os.getenv("ALERT_THRESHOLD", "0.70"))
        self.risk_ml_weight = float(os.getenv("RISK_ML_WEIGHT", "0.60"))
        self.risk_rule_weight = float(os.getenv("RISK_RULE_WEIGHT", "0.40"))
        self.risk_url_ml_weight = float(os.getenv("RISK_URL_ML_WEIGHT", "0.50"))
        self.risk_url_rule_weight = float(os.getenv("RISK_URL_RULE_WEIGHT", "0.30"))
        self.risk_url_weight = float(os.getenv("RISK_URL_WEIGHT", "0.20"))
        self.credential_url_floor = float(os.getenv("CREDENTIAL_URL_FLOOR", "0.85"))
        if not 0 <= self.medium_threshold < self.alert_threshold <= 1:
            raise ValueError("Invalid risk thresholds.")
        weights = (
            self.risk_ml_weight,
            self.risk_rule_weight,
            self.risk_url_ml_weight,
            self.risk_url_rule_weight,
            self.risk_url_weight,
            self.credential_url_floor,
        )
        if not all(0 <= value <= 1 for value in weights):
            raise ValueError("Risk weights/floor must be finite values in [0,1].")
        if not math.isclose(
            self.risk_ml_weight + self.risk_rule_weight, 1
        ) or not math.isclose(
            self.risk_url_ml_weight + self.risk_url_rule_weight + self.risk_url_weight,
            1,
        ):
            raise ValueError("Risk fusion weights must sum to one.")
        self.app_name: str = os.getenv("APP_NAME", "Nigehbaan AI")
        self.api_prefix: str = os.getenv("API_PREFIX", "/api")
        origins = os.getenv("CORS_ORIGINS", "http://localhost:5173")
        self.cors_origins: list[str] = [
            o.strip() for o in origins.split(",") if o.strip()
        ]


settings = Settings()
