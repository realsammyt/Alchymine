"""Centralized configuration for Alchymine.

All settings are read from environment variables (or a ``.env`` file) and
validated at startup using Pydantic ``BaseSettings``.  A cached singleton
is exposed via :func:`get_settings` so every module shares a single instance.

Environment variable names follow the field names in UPPER_CASE by default
(no prefix). For example::

    DATABASE_URL=postgresql+asyncpg://user:pass@host/db
    JWT_SECRET_KEY=super-secret
    ALLOWED_ORIGINS='["https://app.example.com"]'
"""

from __future__ import annotations

import logging
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application-wide configuration backed by environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── App ──────────────────────────────────────────────────────────────
    app_name: str = "Alchymine"
    debug: bool = False
    environment: str = "development"  # development | staging | production

    # ── CORS ─────────────────────────────────────────────────────────────
    allowed_origins: list[str] = ["http://localhost:3000"]

    # ── Auth / JWT ───────────────────────────────────────────────────────
    jwt_secret_key: str = "dev-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # ── Database ─────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://alchymine:alchymine@localhost:5432/alchymine"

    # ── Redis ────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── LLM ──────────────────────────────────────────────────────────────
    anthropic_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"

    # ── Celery ───────────────────────────────────────────────────────────
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    celery_always_eager: bool = False

    # ── Validators ───────────────────────────────────────────────────────

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, v: str, info: object) -> str:  # noqa: ANN001
        """Reject the default dev secret when running in production."""
        # ``info.data`` contains previously-validated fields.  ``environment``
        # is declared before ``jwt_secret_key`` so it will be present.
        data: dict = getattr(info, "data", {})  # type: ignore[assignment]
        if data.get("environment") == "production" and v == "dev-secret-key-change-in-production":
            raise ValueError("JWT_SECRET_KEY must be changed from the default value in production")
        return v


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings singleton."""
    return Settings()
