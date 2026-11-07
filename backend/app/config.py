"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Runtime settings for the Nigehbaan AI API."""

    def __init__(self) -> None:
        self.app_name: str = os.getenv("APP_NAME", "Nigehbaan AI")
        self.api_prefix: str = os.getenv("API_PREFIX", "/api")
        origins = os.getenv("CORS_ORIGINS", "http://localhost:5173")
        self.cors_origins: list[str] = [o.strip() for o in origins.split(",") if o.strip()]


settings = Settings()
