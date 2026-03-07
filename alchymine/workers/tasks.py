"""Celery task definitions for Alchymine report generation.

Tasks
~~~~~
- ``generate_report`` — Runs the MasterOrchestrator pipeline for a
  given report_id and stores the result in PostgreSQL.
- ``generate_pdf_report`` — Renders a completed report to PDF via
  Playwright and stores the resulting bytes.

Storage
~~~~~~~
Results are persisted to the ``reports`` table via the async repository
layer.  The ``_run_async`` helper bridges synchronous Celery tasks to
the async database and orchestrator calls.
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
from alchymine.db import repository
from alchymine.db.base import get_async_engine, get_async_session_factory
from alchymine.db.repository import (
    create_report as db_create_report,
)
from alchymine.db.repository import (
    get_report as db_get_report,
)
from alchymine.db.repository import (
    update_report_content,
    update_report_status,
)
from alchymine.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

# ── In-memory report store (compatibility shim) ─────────────────────────

report_store: dict[str, dict[str, Any]] = {}
"""Module-level dict holding report status and data.

Retained for backward compatibility with the API router and tests while
the DB migration is completed.  New code should use the database via
``_db_*`` helpers instead.

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


# ── Helpers ──────────────────────────────────────────────────────────────


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


# ── Database helpers (sync wrappers) ─────────────────────────────────────

# Engine used by the Celery worker process.
# May be overridden during tests via ``_set_task_engine``.
_task_engine: Any = None


def _get_task_engine() -> Any:
    """Return the async engine used by task DB helpers.

    Falls back to the default engine from ``get_async_engine()`` when
    no override has been set (production path).
    """
    if _task_engine is not None:
        return _task_engine
    return get_async_engine()


def _set_task_engine(engine: Any) -> None:
    """Override the engine used by task DB helpers (for tests)."""
    global _task_engine
    _task_engine = engine


async def _db_create_report(
    report_id: str,
    user_input: str,
    user_profile: dict[str, Any] | None = None,
) -> None:
    """Create a report row with status ``'pending'``."""
    engine = _get_task_engine()
    factory = get_async_session_factory(engine)
    async with factory() as session:
        await db_create_report(
            session,
            report_id=report_id,
            status="pending",
            user_input=user_input,
            user_profile=user_profile,
        )
        await session.commit()


async def _db_set_generating(report_id: str) -> None:
    """Update report status to ``'generating'``."""
    engine = _get_task_engine()
    factory = get_async_session_factory(engine)
    async with factory() as session:
        await update_report_status(session, report_id, "generating")
        await session.commit()


async def _db_set_complete(report_id: str, result: dict[str, Any]) -> None:
    """Mark report as complete and store the result."""
    engine = _get_task_engine()
    factory = get_async_session_factory(engine)
    async with factory() as session:
        await update_report_content(
            session,
            report_id,
            result=result,
            status="complete",
        )
        await session.commit()


async def _db_set_failed(report_id: str, error_msg: str) -> None:
    """Mark report as failed with an error message."""
    engine = _get_task_engine()
    factory = get_async_session_factory(engine)
    async with factory() as session:
        await update_report_status(session, report_id, "failed", error=error_msg)
        await session.commit()


async def _db_get_report(report_id: str) -> Any:
    """Fetch a report row by id (returns ORM object or None)."""
    engine = _get_task_engine()
    factory = get_async_session_factory(engine)
    async with factory() as session:
        report = await db_get_report(session, report_id)
        if report is not None:
            # Detach from session so attributes are accessible outside
            await session.refresh(report)
        return report


async def _db_populate_profiles(
    user_id: str | None,
    coordinator_results: list,
) -> None:
    """Persist coordinator results to the 5 profile layer tables."""
    if not user_id:
        return
    engine = _get_task_engine()
    factory = get_async_session_factory(engine)

    layer_map = {
        "intelligence": "identity",
        "healing": "healing",
        "wealth": "wealth",
        "creative": "creative",
        "perspective": "perspective",
    }

    for cr in coordinator_results:
        system = cr.get("system", "")
        data = cr.get("data", {})
        if not data or cr.get("status") == "error":
            continue

        layer = layer_map.get(system)
        if not layer:
            continue

        try:
            async with factory() as session:
                await repository.update_layer(session, user_id, layer, data)
                await session.commit()
        except Exception as exc:
            logger.warning(
                "Failed to populate %s profile for %s: %s", layer, user_id, exc
            )


async def _db_store_pdf(report_id: str, pdf_bytes: bytes) -> None:
    """Persist generated PDF bytes to the ``pdf_data`` column of the report row."""
    engine = _get_task_engine()
    factory = get_async_session_factory(engine)
    async with factory() as session:
        report = await db_get_report(session, report_id)
        if report is not None:
            report.pdf_data = pdf_bytes
            await session.commit()


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
    intention: str | None = None,
    intentions: list[str] | None = None,
) -> dict[str, Any]:
    """Generate an Alchymine report via the MasterOrchestrator.

    This Celery task bridges the synchronous Celery worker to the async
    orchestrator and database layer by using ``_run_async()``.

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
    intention:
        Optional primary intention string for guided synthesis.
    intentions:
        Optional list of 1-3 intention strings for multi-intention support.

    Returns
    -------
    dict
        The serialised orchestrator result.

    Raises
    ------
    Exception
        Re-raised after recording the failure in the database.
    """
    # Ensure a report row exists (the API normally creates it first, but
    # handle the case where the task runs without prior seeding).
    existing = _run_async(_db_get_report(report_id))
    if existing is None:
        _run_async(_db_create_report(report_id, user_input, user_profile))

    # ── Mark as generating ────────────────────────────────────────────
    _run_async(_db_set_generating(report_id))

    # Resolve intentions: prefer the list, fall back to the single string
    _resolved_intentions = intentions or ([intention] if intention else None)

    try:
        # ── Run the async orchestrator ────────────────────────────────
        orchestrator = MasterOrchestrator()
        result = _run_async(
            orchestrator.process_request(
                user_input,
                user_profile,
                intention=intention,
                intentions=_resolved_intentions,
            )
        )

        serialised = _serialise_orchestrator_result(result)

        # Build profile_summary in the shape the HTML renderer expects
        try:
            from alchymine.agents.orchestrator.synthesis import (
                transform_to_profile_summary,
            )

            serialised["profile_summary"] = transform_to_profile_summary(
                result.coordinator_results
            )
        except Exception as exc:
            logger.warning("Failed to build profile_summary: %s", exc)

        # Generate LLM narratives (optional — reports work without them)
        try:
            from alchymine.llm.narrative import NarrativeGenerator

            generator = NarrativeGenerator()

            systems = []
            engine_data = {}
            for cr in result.coordinator_results:
                if cr.status != "error":
                    systems.append(cr.system)
                    engine_data[cr.system] = cr.data

            if systems:
                narratives = _run_async(generator.generate_all(systems, engine_data))
                serialised["narratives"] = {
                    system: {
                        "text": nr.narrative,
                        "disclaimers": nr.disclaimers,
                        "ethics_passed": nr.ethics_passed,
                    }
                    for system, nr in narratives.items()
                    if nr.narrative
                }
        except Exception as exc:
            logger.warning("Narrative generation failed (non-fatal): %s", exc)

        # ── Store success ─────────────────────────────────────────────
        _run_async(_db_set_complete(report_id, serialised))

        # ── Populate profile layer tables from coordinator results ────
        try:
            _user_id = (user_profile or {}).get("id")
            _coordinator_results = serialised.get("coordinator_results", [])
            _run_async(_db_populate_profiles(_user_id, _coordinator_results))
        except Exception as exc:
            logger.warning("Failed to populate profile tables: %s", exc)

        # ── Trigger PDF generation ────────────────────────────────────
        try:
            generate_pdf_report.delay(report_id)
        except Exception as exc:
            logger.warning("Failed to queue PDF generation for %s: %s", report_id, exc)

        logger.info("Report %s completed successfully.", report_id)
        return serialised

    except (ConnectionError, OSError, TimeoutError):
        # Transient failures — let Celery retry via autoretry_for
        _run_async(_db_set_failed(report_id, traceback.format_exc()))
        raise

    except Exception as exc:
        # Non-transient failure — record and do not retry
        logger.exception("Report %s failed: %s", report_id, exc)
        try:
            _run_async(_db_set_failed(report_id, str(exc)))
        except Exception as db_exc:
            logger.error("Failed to persist error status for %s: %s", report_id, db_exc)
        return {
            "error": str(exc),
            "report_id": report_id,
            "status": "failed",
        }


# ── PDF store ────────────────────────────────────────────────────────────

pdf_store: dict[str, bytes] = {}
"""Module-level dict holding generated PDF bytes keyed by report_id."""


# ── PDF generation task ──────────────────────────────────────────────────


@celery_app.task(
    bind=True,
    name="alchymine.workers.tasks.generate_pdf_report",
    max_retries=2,
    default_retry_delay=5,
    acks_late=True,
)
def generate_pdf_report(self: Any, report_id: str) -> dict[str, Any]:
    """Render a completed report as a PDF via Playwright.

    This Celery task retrieves the report from the database, renders
    its result data to HTML, then to PDF using
    :class:`~alchymine.engine.reports.pdf_renderer.PDFRenderer`,
    and stores the resulting bytes in ``pdf_store``.

    Parameters
    ----------
    self:
        Celery task instance (``bind=True``).
    report_id:
        Unique identifier for the report to render.

    Returns
    -------
    dict
        ``{"report_id": ..., "status": "complete", "size_bytes": ...}``
        on success, or ``{"report_id": ..., "status": "failed", "error": ...}``
        on failure.
    """
    from alchymine.engine.reports.html_renderer import render_report_html
    from alchymine.engine.reports.pdf_renderer import PDFRenderer

    # ── Validate report exists and is complete ────────────────────────
    report = _run_async(_db_get_report(report_id))
    if report is None:
        logger.error("PDF generation failed: report %s not found", report_id)
        return {
            "report_id": report_id,
            "status": "failed",
            "error": "Report not found",
        }

    if report.status != "complete":
        logger.error(
            "PDF generation failed: report %s has status %s",
            report_id,
            report.status,
        )
        return {
            "report_id": report_id,
            "status": "failed",
            "error": f"Report is not complete (status: {report.status})",
        }

    try:
        # Build a dict compatible with render_report_html
        entry: dict[str, Any] = {
            "report_id": report.id,
            "status": report.status,
            "result": report.result,
            "created_at": report.created_at.isoformat() if report.created_at else "",
        }

        # ── Render HTML ───────────────────────────────────────────────
        html_content = render_report_html(entry)

        # ── Detect wealth report ──────────────────────────────────────
        result_data = report.result or {}
        coordinator_results = result_data.get("coordinator_results") or []
        is_wealth_report = any(
            cr.get("system", "").lower() == "wealth"
            or cr.get("coordinator", "").lower() == "wealth"
            for cr in coordinator_results
            if isinstance(cr, dict)
        )

        # ── Render PDF ────────────────────────────────────────────────
        renderer = PDFRenderer()
        pdf_bytes = _run_async(
            renderer.render_pdf(
                html_content,
                is_wealth_report=is_wealth_report,
                include_evidence_footer=True,
            )
        )

        # ── Store result ──────────────────────────────────────────────
        _run_async(_db_store_pdf(report_id, pdf_bytes))
        pdf_store[report_id] = pdf_bytes  # compatibility shim — removed in Phase 5

        logger.info(
            "PDF for report %s generated successfully (%d bytes).",
            report_id,
            len(pdf_bytes),
        )
        return {
            "report_id": report_id,
            "status": "complete",
            "size_bytes": len(pdf_bytes),
        }

    except Exception as exc:
        logger.exception("PDF generation for report %s failed: %s", report_id, exc)
        return {
            "report_id": report_id,
            "status": "failed",
            "error": str(exc),
        }
