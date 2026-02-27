"""Celery task definitions for Alchymine report generation.

Tasks
~~~~~
- ``generate_report`` — Runs the MasterOrchestrator pipeline for a
  given report_id and stores the result.

Storage
~~~~~~~
Results are held in a module-level dict (``report_store``) keyed by
report_id.  This is intentionally simple and will be replaced by
PostgreSQL persistence in a subsequent issue.
"""

from __future__ import annotations

import asyncio
import json
import logging
import traceback
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from alchymine.agents.orchestrator.orchestrator import MasterOrchestrator
from alchymine.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

# ── In-memory report store (swap for DB later) ──────────────────────────

report_store: dict[str, dict[str, Any]] = {}
"""Module-level dict holding report status and data.

Each entry has the shape::

    {
        "report_id": str,
        "status": "queued" | "processing" | "complete" | "failed",
        "user_input": str,
        "user_profile": dict | None,
        "result": dict | None,
        "error": str | None,
        "created_at": str (ISO-8601),
        "updated_at": str (ISO-8601),
    }
"""


def _now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(UTC).isoformat()


def _run_async(coro: Any) -> Any:
    """Run an async coroutine from synchronous code.

    If no event loop is running, uses ``asyncio.run()``.  If an event
    loop is already active (e.g. Celery eager mode inside a FastAPI
    test), runs the coroutine in a separate thread to avoid the
    ``RuntimeError: asyncio.run() cannot be called from a running
    event loop`` issue.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No running loop — safe to use asyncio.run()
        return asyncio.run(coro)

    # An event loop is already running — execute in a background thread
    with ThreadPoolExecutor(max_workers=1) as pool:
        future: Future = pool.submit(asyncio.run, coro)
        return future.result()


def _serialise_orchestrator_result(result: Any) -> dict:
    """Convert an OrchestratorResult dataclass to a JSON-safe dict.

    Parameters
    ----------
    result:
        An ``OrchestratorResult`` instance (or any dataclass).

    Returns
    -------
    dict
        A plain dict representation.
    """
    raw = asdict(result)
    # asdict produces nested dicts/lists — run through json round-trip
    # to ensure everything is serialisable (enums, dates, etc.).
    return json.loads(json.dumps(raw, default=str))


# ── Celery task ──────────────────────────────────────────────────────────


@celery_app.task(
    bind=True,
    name="alchymine.workers.tasks.generate_report",
    max_retries=3,
    default_retry_delay=5,
    autoretry_for=(ConnectionError, OSError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=60,
    acks_late=True,
)
def generate_report(
    self: Any,
    report_id: str,
    user_input: str,
    user_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate an Alchymine report via the MasterOrchestrator.

    This Celery task bridges the synchronous Celery worker to the async
    orchestrator by using ``asyncio.run()``.

    Parameters
    ----------
    self:
        Celery task instance (``bind=True``).
    report_id:
        Unique identifier for this report.
    user_input:
        Raw text from the user describing their request.
    user_profile:
        Optional user profile data to forward to the orchestrator.

    Returns
    -------
    dict
        The serialised orchestrator result.

    Raises
    ------
    Exception
        Re-raised after recording the failure in ``report_store``.
    """
    now = _now_iso()

    # Initialise store entry if not yet present (e.g. created by the API)
    if report_id not in report_store:
        report_store[report_id] = {
            "report_id": report_id,
            "status": "queued",
            "user_input": user_input,
            "user_profile": user_profile,
            "result": None,
            "error": None,
            "created_at": now,
            "updated_at": now,
        }

    # ── Mark as processing ───────────────────────────────────────────
    report_store[report_id]["status"] = "processing"
    report_store[report_id]["updated_at"] = _now_iso()

    try:
        # ── Run the async orchestrator ───────────────────────────────
        orchestrator = MasterOrchestrator()
        result = _run_async(orchestrator.process_request(user_input, user_profile))

        serialised = _serialise_orchestrator_result(result)

        # ── Store success ────────────────────────────────────────────
        report_store[report_id]["status"] = "complete"
        report_store[report_id]["result"] = serialised
        report_store[report_id]["error"] = None
        report_store[report_id]["updated_at"] = _now_iso()

        logger.info("Report %s completed successfully.", report_id)
        return serialised

    except (ConnectionError, OSError, TimeoutError):
        # Transient failures — let Celery retry via autoretry_for
        report_store[report_id]["status"] = "failed"
        report_store[report_id]["error"] = traceback.format_exc()
        report_store[report_id]["updated_at"] = _now_iso()
        raise

    except Exception as exc:
        # Non-transient failure — record and do not retry
        report_store[report_id]["status"] = "failed"
        report_store[report_id]["error"] = str(exc)
        report_store[report_id]["updated_at"] = _now_iso()

        logger.exception("Report %s failed: %s", report_id, exc)
        return {
            "error": str(exc),
            "report_id": report_id,
            "status": "failed",
        }
