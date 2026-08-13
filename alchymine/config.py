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

    # ── Gemini (Generative Art) ──────────────────────────────────────────
    # Optional — when unset, the generative art endpoints degrade gracefully
    # and return 204 No Content so the frontend can render placeholder art.
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.1-flash-image-preview"
    # Filesystem cache location for generated image bytes (relative paths
    # are resolved against the project root at runtime).
    art_cache_dir: str = "data/generated_images"

    # ── Cost ceilings ────────────────────────────────────────────────────
    # Sized for the invite beta (2026-08). The global ceiling bounds a
    # runaway loop or scraped key at roughly $100-200/day worst case at
    # Sonnet pricing, while sitting well above a legitimate beta day
    # (a full report burns ~5-10 calls, a long chat session ~50-100).
    # The art cap is the per-account bound on the one endpoint where a
    # single user can run up Gemini spend alone; 3/day also serves the
    # wait/upsell state in the monetization roadmap. Tune via env as
    # traffic grows; a tripped breaker takes every paid surface down
    # until UTC midnight, so raise it before it pinches real users.
    #
    # The breaker counts *calls*, not tokens or dollars. A call count is
    # enough to stop a runaway loop or a scraped key from billing all night.
    # NOTE: per-token dollar accounting is a separate roadmap item. Swap the
    # count for a token/dollar ledger once per-call cost varies enough that a
    # flat call count stops approximating spend.
    global_daily_llm_call_ceiling: int = 2000
    daily_art_generations_per_user: int = 3

    # ── Plans and monthly spend allowances ───────────────────────────────
    # Sized by ``price x (1 - margin target)``: pro is 11 x 0.25 = 275 cents,
    # blueprint is 33 x 0.03 = 99 cents per 33-day window. free is 0 on
    # purpose, which makes "give away artifact-shaped things, never
    # recurring-cost things" structural rather than a policy someone has to
    # remember. beta sits deliberately above the expected p95 so the cap does
    # not truncate the distribution it exists to measure.
    #
    # Every one of these is PROVISIONAL. They are modelled, not measured, and
    # should be revisited as a set once the ledger has 2 to 4 weeks of real
    # beta data.
    #
    # A ``str`` rather than a ``dict`` for the same reason allowed_origins is:
    # pydantic-settings v2 JSON-parses structured field types at source level,
    # before any validator runs, so a dict field blows up on the plain
    # comma-separated value that comes out of a docker-compose env file.
    plan_allowance_cents: str = "free:0,beta:555,blueprint:99,pro:275,founding:333"

    # ── Cost ledger ──────────────────────────────────────────────────────
    # Per-model prices in MICRO-DOLLARS PER TOKEN, as
    # ``model:input_micros:output_micros`` entries. $3/MTok is 3 micros per
    # token, which is why the numbers look small. A ``str`` rather than a
    # dict for the same pydantic-settings reason as plan_allowance_cents.
    #
    # Prices live here and are never written at a call site. Changing the
    # published API price list means changing LLM_PRICE_TABLE, nothing else.
    llm_price_table: str = "claude-sonnet-4-6:3:15,claude-haiku-4-5-20251001:1:5"

    # Gemini image generation has no per-token accounting — generate_image
    # returns bytes — so the ledger pins a flat per-image figure. This is the
    # published price for gemini-3.1-flash-image-preview at 1K resolution as
    # of August 2026, and the one number in the ledger that cannot be
    # corrected by measurement from inside the app: it has to be reconciled
    # against a real Google Cloud invoice.
    gemini_image_cost_micros: int = 67000

    # Kill switch for the ledger. False stops all usage_records writes and
    # all spend-meter increments; it does not touch the call-count breaker,
    # which is a separate, older mechanism.
    usage_ledger_enabled: bool = True

    # How long a failed ledger write blocks paid calls before one of them may
    # probe to see whether the ledger is writable again. Tuning this trades
    # two costs against each other: too short and a database that is properly
    # down gets probed by a paid call every few seconds, too long and a
    # transient failure keeps every paid surface dark for no reason. 60s is a
    # guess like everything else in this design, which is why it is an env
    # var — a wrong number under real beta traffic should be a restart, not a
    # code change.
    ledger_degraded_retry_seconds: float = 60.0

    # ── Celery ───────────────────────────────────────────────────────────
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    celery_always_eager: bool = False

    # ── Email ──────────────────────────────────────────────────────────────
    email_provider: str = "resend"
    resend_api_key: str = ""
    email_from: str = "noreply@alchymine.app"
    frontend_url: str = "http://localhost:3000"

    # ── Healing ─────────────────────────────────────────────────────────
    # Optional path to an external directory of healing skill YAML files.
    # When set, the SkillRegistry will load from both the bundled
    # ``alchymine/engine/healing/skills/yaml/`` AND this directory.
    healing_skills_external_dir: str | None = None

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

    def get_plan_allowance_cents(self) -> dict[str, int]:
        """Return *plan_allowance_cents* parsed into ``{plan: cents}``.

        Malformed entries are skipped with an ERROR log rather than raised.
        A typo in an env var should not take the app down at import time, and
        a plan that drops out of the mapping resolves to the free allowance
        (see :meth:`allowance_cents_for`), which is the closed direction.
        """
        allowances: dict[str, int] = {}
        for entry in self.plan_allowance_cents.split(","):
            entry = entry.strip()
            if not entry:
                continue
            name, sep, raw = entry.partition(":")
            if not sep or not name.strip():
                logger.error("PLAN_ALLOWANCE_CENTS: skipping malformed entry %r", entry)
                continue
            try:
                allowances[name.strip()] = int(raw.strip())
            except ValueError:
                logger.error(
                    "PLAN_ALLOWANCE_CENTS: %r is not an integer number of cents (entry %r)",
                    raw.strip(),
                    entry,
                )
        return allowances

    def allowance_cents_for(self, plan: str) -> int:
        """Return the monthly allowance in cents for *plan*.

        An unknown plan name falls back to the free allowance and logs at
        ERROR: a plan we cannot price is a plan we should not be funding, and
        the error is the signal that the config and the code have drifted. If
        the mapping has no ``free`` key either, the answer is 0.
        """
        allowances = self.get_plan_allowance_cents()
        if plan in allowances:
            return allowances[plan]

        free = allowances.get("free", 0)
        logger.error(
            "Unknown plan %r has no configured allowance; falling back to the "
            "free allowance of %d cents. Add it to PLAN_ALLOWANCE_CENTS.",
            plan,
            free,
        )
        return free

    def get_llm_prices(self) -> dict[str, tuple[int, int]]:
        """Return *llm_price_table* parsed into ``{model: (in, out)}`` micros.

        Malformed entries are skipped with an ERROR log rather than raised,
        for the same reason ``get_plan_allowance_cents`` does it: a typo in
        an env var should not take the app down at import time. A model that
        drops out of the mapping is then priced at the most expensive rate in
        the table (see :meth:`llm_price_for`), which is the safe direction —
        it over-counts rather than hiding spend.
        """
        prices: dict[str, tuple[int, int]] = {}
        for entry in self.llm_price_table.split(","):
            entry = entry.strip()
            if not entry:
                continue
            parts = [p.strip() for p in entry.split(":")]
            if len(parts) != 3 or not parts[0]:
                logger.error("LLM_PRICE_TABLE: skipping malformed entry %r", entry)
                continue
            try:
                prices[parts[0]] = (int(parts[1]), int(parts[2]))
            except ValueError:
                logger.error("LLM_PRICE_TABLE: %r has non-integer micro-dollar prices", entry)
        return prices

    def llm_price_for(self, model: str) -> tuple[int, int]:
        """Return ``(input_micros, output_micros)`` per token for *model*.

        An unknown model is priced at the most expensive rate in the table
        and logged at ERROR. Never at zero: a model we forgot to add must
        show up as expensive spend rather than as free, or the first thing a
        pricing mistake does is hide itself.

        The maximum is taken per field, so a table whose priciest input and
        priciest output belong to different models still yields the
        conservative pair.
        """
        prices = self.get_llm_prices()
        if model in prices:
            return prices[model]

        if prices:
            fallback = (
                max(p[0] for p in prices.values()),
                max(p[1] for p in prices.values()),
            )
        else:
            # An empty or entirely malformed table. Sonnet's published price
            # is the most expensive model this app has ever called; anything
            # is better than pricing at zero.
            fallback = (3, 15)

        logger.error(
            "Unknown model %r is not in LLM_PRICE_TABLE; pricing it at the most "
            "expensive rate in the table (%d/%d micros per token). Add it.",
            model,
            fallback[0],
            fallback[1],
        )
        return fallback

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
