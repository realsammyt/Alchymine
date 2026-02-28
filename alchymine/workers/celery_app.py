"""Celery application configuration for Alchymine workers.

The Celery app uses Redis as both broker and result backend.
Configuration is loaded from environment variables:

- ``REDIS_URL``: Redis connection URL (default ``redis://localhost:6379/0``)
- ``CELERY_ALWAYS_EAGER``: When ``"true"``, tasks execute synchronously
  in the calling process — useful for testing without a running broker.
"""

from __future__ import annotations

from celery import Celery

from alchymine.config import get_settings

# ── Settings ─────────────────────────────────────────────────────────────

_settings = get_settings()

# ── Celery app ───────────────────────────────────────────────────────────

celery_app = Celery(
    "alchymine",
    broker=_settings.celery_broker_url,
    backend=_settings.celery_result_backend,
)

celery_app.conf.update(
    # Serialisation
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Task routing
    task_routes={
        "alchymine.workers.tasks.generate_report": {"queue": "reports"},
        "alchymine.workers.tasks.generate_pdf_report": {"queue": "reports"},
    },
    # Task defaults
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# ── Eager mode for testing ───────────────────────────────────────────────

if _settings.celery_always_eager:
    celery_app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True,
        result_backend="disabled",
    )

# ── Auto-discover tasks ─────────────────────────────────────────────────

celery_app.autodiscover_tasks(["alchymine.workers"])
