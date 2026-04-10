"""Centralized configuration for Alchymine.

All settings are read from environment variables (or a ``.env`` file) and
validated at startup using Pydantic ``BaseSettings``.  A cached singleton
is exposed via :func:`get_settings` so every module shares a single instance.

Environment variable names follow the field names in UPPER_CASE by default
(no prefix). For example::

    DATABASE_URL=postgresql+asyncpg://user:pass@host/db
    JWT_SECRET_KEY=super-secret
    ALLOWED_ORIGINS=https://app.example.com,https://staging.example.com
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
        # Tolerate extra vars in .env files (e.g. production envs that include
        # docker-compose service names, deployment secrets, or other tooling
        # vars that Settings doesn't declare). Without this, a local dev
        # running tests with a production-style .env hits extra_forbidden
        # errors on every Settings() instantiation.
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────
    app_name: str = "Alchymine"
    debug: bool = False
    environment: str = "development"  # development | staging | production

    # ── CORS ─────────────────────────────────────────────────────────────
    # Stored as ``str`` to prevent pydantic-settings from attempting JSON
    # pre-parsing (which fails for comma-separated values passed through
    # docker-compose env files).  Use :meth:`get_allowed_origins` for the
    # parsed ``list[str]``.
    allowed_origins: str = "http://localhost:3000"

    # ── Auth / JWT ───────────────────────────────────────────────────────
    jwt_secret_key: str = "dev-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    admin_email: str = ""  # Used by bootstrap_admin CLI to grant initial admin access

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

    # ── Email ──────────────────────────────────────────────────────────────
    email_provider: str = "resend"
    resend_api_key: str = ""
    email_from: str = "noreply@alchymine.app"
    frontend_url: str = "http://localhost:3000"

    # ── Misc ──────────────────────────────────────────────────────────────
    auto_create_tables: bool = False

    # ── Encryption ───────────────────────────────────────────────────────
    alchymine_encryption_key: str = ""

    # ── Helpers ─────────────────────────────────────────────────────────

    def get_allowed_origins(self) -> list[str]:
        """Return *allowed_origins* as a list, accepting JSON or CSV format."""
        import json

        v = self.allowed_origins.strip()
        if v.startswith("["):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(x) for x in parsed]
            except (json.JSONDecodeError, ValueError):
                pass
        return [origin.strip() for origin in v.split(",") if origin.strip()]

    # ── Validators ───────────────────────────────────────────────────────

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, v: str, info: object) -> str:  # noqa: ANN001
        """Reject the default dev secret and require a minimum length in all environments."""
        if v == "dev-secret-key-change-in-production" or len(v) < 32:
            raise ValueError(
                "JWT_SECRET_KEY must be set to a secure value (min 32 chars). "
                "Generate one with: openssl rand -hex 32"
            )
        return v

    @field_validator("resend_api_key")
    @classmethod
    def validate_resend_api_key(cls, v: str, info: object) -> str:
        """Require Resend API key in production so password reset emails are delivered."""
        data: dict = getattr(info, "data", {})
        env = data.get("environment", "development")
        if env == "production" and not v:
            raise ValueError(
                "RESEND_API_KEY must be set in production for password reset email delivery."
            )
        return v

    @field_validator("alchymine_encryption_key")
    @classmethod
    def validate_encryption_key(cls, v: str, info: object) -> str:
        """Require encryption key in production."""
        data: dict = getattr(info, "data", {})
        env = data.get("environment", "development")
        if env in ("production", "staging") and not v:
            raise ValueError(
                "ALCHYMINE_ENCRYPTION_KEY must be set in production/staging. "
                "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
        return v


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings singleton."""
    return Settings()
