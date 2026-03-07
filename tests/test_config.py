"""Tests for alchymine.config — centralized Settings and get_settings().

Covers default loading, environment-variable overrides, production JWT
validation, and CORS origins parsing.
"""

from __future__ import annotations

import pytest

from alchymine.config import Settings


# ─── Default Settings ──────────────────────────────────────────────────────


from cryptography.fernet import Fernet

_SAFE_JWT_KEY = "test-secret-key-minimum-32-characters-long"
_SAFE_PROMO_CODE = "alchyours"
_SAFE_ENCRYPTION_KEY = Fernet.generate_key().decode()


class TestDefaults:
    """Settings should load reasonable defaults when no env vars are set."""

    def test_app_name(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", _SAFE_JWT_KEY)
        monkeypatch.setenv("SIGNUP_PROMO_CODE", _SAFE_PROMO_CODE)
        s = Settings()
        assert s.app_name == "Alchymine"

    def test_environment(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", _SAFE_JWT_KEY)
        monkeypatch.setenv("SIGNUP_PROMO_CODE", _SAFE_PROMO_CODE)
        s = Settings()
        assert s.environment == "development"

    def test_debug_off(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", _SAFE_JWT_KEY)
        monkeypatch.setenv("SIGNUP_PROMO_CODE", _SAFE_PROMO_CODE)
        s = Settings()
        assert s.debug is False

    def test_jwt_defaults(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", _SAFE_JWT_KEY)
        monkeypatch.setenv("SIGNUP_PROMO_CODE", _SAFE_PROMO_CODE)
        s = Settings()
        assert s.jwt_secret_key == _SAFE_JWT_KEY
        assert s.jwt_algorithm == "HS256"
        assert s.access_token_expire_minutes == 30
        assert s.refresh_token_expire_days == 7

    def test_database_url_default(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", _SAFE_JWT_KEY)
        monkeypatch.setenv("SIGNUP_PROMO_CODE", _SAFE_PROMO_CODE)
        s = Settings()
        assert "alchymine" in s.database_url
        assert s.database_url.startswith("postgresql+asyncpg://")

    def test_redis_url_default(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", _SAFE_JWT_KEY)
        monkeypatch.setenv("SIGNUP_PROMO_CODE", _SAFE_PROMO_CODE)
        s = Settings()
        assert s.redis_url == "redis://localhost:6379/0"

    def test_celery_defaults(self, monkeypatch):
        # CELERY_ALWAYS_EAGER is set to "true" by the test conftest, so
        # we must clear it to verify the actual default.
        monkeypatch.setenv("JWT_SECRET_KEY", _SAFE_JWT_KEY)
        monkeypatch.setenv("SIGNUP_PROMO_CODE", _SAFE_PROMO_CODE)
        monkeypatch.delenv("CELERY_ALWAYS_EAGER", raising=False)
        s = Settings()
        assert s.celery_broker_url == "redis://localhost:6379/1"
        assert s.celery_result_backend == "redis://localhost:6379/2"
        assert s.celery_always_eager is False

    def test_llm_defaults(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", _SAFE_JWT_KEY)
        monkeypatch.setenv("SIGNUP_PROMO_CODE", _SAFE_PROMO_CODE)
        s = Settings()
        assert s.anthropic_api_key == ""
        assert s.ollama_base_url == "http://localhost:11434"

    def test_cors_default(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", _SAFE_JWT_KEY)
        monkeypatch.setenv("SIGNUP_PROMO_CODE", _SAFE_PROMO_CODE)
        s = Settings()
        assert s.get_allowed_origins() == ["http://localhost:3000"]


# ─── Environment Variable Overrides ───────────────────────────────────────


class TestEnvOverrides:
    """Environment variables should override the corresponding settings."""

    def test_override_app_name(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", _SAFE_JWT_KEY)
        monkeypatch.setenv("SIGNUP_PROMO_CODE", _SAFE_PROMO_CODE)
        monkeypatch.setenv("APP_NAME", "TestApp")
        s = Settings()
        assert s.app_name == "TestApp"

    def test_override_debug(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", _SAFE_JWT_KEY)
        monkeypatch.setenv("SIGNUP_PROMO_CODE", _SAFE_PROMO_CODE)
        monkeypatch.setenv("DEBUG", "true")
        s = Settings()
        assert s.debug is True

    def test_override_environment(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", _SAFE_JWT_KEY)
        monkeypatch.setenv("SIGNUP_PROMO_CODE", _SAFE_PROMO_CODE)
        monkeypatch.setenv("ALCHYMINE_ENCRYPTION_KEY", _SAFE_ENCRYPTION_KEY)
        monkeypatch.setenv("ENVIRONMENT", "staging")
        s = Settings()
        assert s.environment == "staging"

    def test_override_jwt_secret(self, monkeypatch):
        monkeypatch.setenv("SIGNUP_PROMO_CODE", _SAFE_PROMO_CODE)
        monkeypatch.setenv("JWT_SECRET_KEY", "my-new-secret-key-that-is-long-enough-abc")
        s = Settings()
        assert s.jwt_secret_key == "my-new-secret-key-that-is-long-enough-abc"

    def test_override_database_url(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", _SAFE_JWT_KEY)
        monkeypatch.setenv("SIGNUP_PROMO_CODE", _SAFE_PROMO_CODE)
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@db:5432/test")
        s = Settings()
        assert s.database_url == "postgresql+asyncpg://u:p@db:5432/test"

    def test_override_redis_url(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", _SAFE_JWT_KEY)
        monkeypatch.setenv("SIGNUP_PROMO_CODE", _SAFE_PROMO_CODE)
        monkeypatch.setenv("REDIS_URL", "redis://redis-host:6380/3")
        s = Settings()
        assert s.redis_url == "redis://redis-host:6380/3"

    def test_override_celery_broker(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", _SAFE_JWT_KEY)
        monkeypatch.setenv("SIGNUP_PROMO_CODE", _SAFE_PROMO_CODE)
        monkeypatch.setenv("CELERY_BROKER_URL", "redis://broker:6379/5")
        s = Settings()
        assert s.celery_broker_url == "redis://broker:6379/5"

    def test_override_celery_always_eager(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", _SAFE_JWT_KEY)
        monkeypatch.setenv("SIGNUP_PROMO_CODE", _SAFE_PROMO_CODE)
        monkeypatch.setenv("CELERY_ALWAYS_EAGER", "true")
        s = Settings()
        assert s.celery_always_eager is True

    def test_override_anthropic_api_key(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", _SAFE_JWT_KEY)
        monkeypatch.setenv("SIGNUP_PROMO_CODE", _SAFE_PROMO_CODE)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        s = Settings()
        assert s.anthropic_api_key == "sk-ant-test-key"

    def test_override_access_token_expire(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", _SAFE_JWT_KEY)
        monkeypatch.setenv("SIGNUP_PROMO_CODE", _SAFE_PROMO_CODE)
        monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
        s = Settings()
        assert s.access_token_expire_minutes == 60


# ─── Production JWT Validation ────────────────────────────────────────────


class TestJWTValidation:
    """JWT secret key validation applies in all environments."""

    def test_rejects_default_secret_in_all_environments(self, monkeypatch):
        monkeypatch.setenv("SIGNUP_PROMO_CODE", _SAFE_PROMO_CODE)
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        with pytest.raises(Exception, match="JWT_SECRET_KEY must be set"):
            Settings()

    def test_rejects_short_secret(self, monkeypatch):
        monkeypatch.setenv("SIGNUP_PROMO_CODE", _SAFE_PROMO_CODE)
        monkeypatch.setenv("JWT_SECRET_KEY", "tooshort")
        with pytest.raises(Exception, match="JWT_SECRET_KEY must be set"):
            Settings()

    def test_accepts_long_enough_secret(self, monkeypatch):
        monkeypatch.setenv("SIGNUP_PROMO_CODE", _SAFE_PROMO_CODE)
        monkeypatch.setenv("JWT_SECRET_KEY", "production-secret-that-is-long-enough-abc")
        s = Settings()
        assert s.jwt_secret_key == "production-secret-that-is-long-enough-abc"

    def test_rejects_missing_promo_code(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", _SAFE_JWT_KEY)
        monkeypatch.delenv("SIGNUP_PROMO_CODE", raising=False)
        with pytest.raises(Exception, match="SIGNUP_PROMO_CODE must be set"):
            Settings()

    def test_rejects_short_promo_code(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", _SAFE_JWT_KEY)
        monkeypatch.setenv("SIGNUP_PROMO_CODE", "abc")
        with pytest.raises(Exception, match="SIGNUP_PROMO_CODE must be set"):
            Settings()

    def test_accepts_valid_promo_code(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", _SAFE_JWT_KEY)
        monkeypatch.setenv("SIGNUP_PROMO_CODE", "validcode")
        s = Settings()
        assert s.signup_promo_code == "validcode"


# ─── CORS Origins Parsing ─────────────────────────────────────────────────


class TestCORSOrigins:
    """CORS origins should support JSON list and comma-separated formats."""

    def test_json_single_origin(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", _SAFE_JWT_KEY)
        monkeypatch.setenv("SIGNUP_PROMO_CODE", _SAFE_PROMO_CODE)
        monkeypatch.setenv("ALLOWED_ORIGINS", '["https://app.example.com"]')
        s = Settings()
        assert s.get_allowed_origins() == ["https://app.example.com"]

    def test_json_multiple_origins(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", _SAFE_JWT_KEY)
        monkeypatch.setenv("SIGNUP_PROMO_CODE", _SAFE_PROMO_CODE)
        monkeypatch.setenv(
            "ALLOWED_ORIGINS",
            '["https://app.example.com", "https://staging.example.com"]',
        )
        s = Settings()
        assert s.get_allowed_origins() == [
            "https://app.example.com",
            "https://staging.example.com",
        ]

    def test_csv_multiple_origins(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", _SAFE_JWT_KEY)
        monkeypatch.setenv("SIGNUP_PROMO_CODE", _SAFE_PROMO_CODE)
        monkeypatch.setenv(
            "ALLOWED_ORIGINS",
            "https://app.example.com,https://staging.example.com",
        )
        s = Settings()
        assert s.get_allowed_origins() == [
            "https://app.example.com",
            "https://staging.example.com",
        ]

    def test_default_origins(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", _SAFE_JWT_KEY)
        monkeypatch.setenv("SIGNUP_PROMO_CODE", _SAFE_PROMO_CODE)
        s = Settings()
        assert s.get_allowed_origins() == ["http://localhost:3000"]


# ─── get_settings() Cache ────────────────────────────────────────────────


class TestGetSettings:
    """get_settings() should return a cached singleton."""

    def test_returns_settings_instance(self):
        from alchymine.config import get_settings

        s = get_settings()
        assert isinstance(s, Settings)

    def test_returns_same_instance(self):
        from alchymine.config import get_settings

        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
