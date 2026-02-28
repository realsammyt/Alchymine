"""Celery application configuration for Alchymine workers.

The Celery app uses Redis as both broker and result backend.
Configuration is loaded from environment variables:

- ``REDIS_URL``: Redis connection URL (default ``redis://localhost:6379/0``)
- ``CELERY_ALWAYS_EAGER``: When ``"true"``, tasks execute synchronously
  in the calling process — useful for testing without a running broker.
"""

from __future__ import annotations

import os

from celery import Celery

# ── Redis URL ────────────────────────────────────────────────────────────

REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# ── Celery app ───────────────────────────────────────────────────────────

celery_app = Celery(
    "alchymine",
    broker=REDIS_URL,
    backend=REDIS_URL,
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
    },
    # Task defaults
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# ── Eager mode for testing ───────────────────────────────────────────────

_always_eager = os.environ.get("CELERY_ALWAYS_EAGER", "").lower() in (
    "true",
    "1",
    "yes",
)
if _always_eager:
    celery_app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True,
        result_backend="disabled",
    )

# ── Auto-discover tasks ─────────────────────────────────────────────────

celery_app.autodiscover_tasks(["alchymine.workers"])
