"""Report generation API endpoints.

Dispatches report generation to a Celery task queue and exposes
endpoints for checking status and retrieving completed reports.
All report data is persisted to PostgreSQL.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from alchymine.api.auth import get_current_user
from alchymine.api.deps import get_db_session
from alchymine.db import repository
from alchymine.db.models import User
from alchymine.engine.profile import IntakeData
from alchymine.engine.reports.html_renderer import render_report_html
from alchymine.safety.audit import AuditEventType
from alchymine.safety.audit import log_event as audit_log_event
from alchymine.safety.guardrails import GuardrailAction, check_guardrail
from alchymine.workers.tasks import generate_report as generate_report_task

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Request / Response models ────────────────────────────────────────────


class ReportRequest(BaseModel):
    """Request to generate a full Alchymine report."""

    intake: IntakeData
    user_input: str = Field(
        default="Generate my full Alchymine report",
        description="Free-text description of what the user wants",
    )
    user_profile: dict | None = Field(
        default=None,
        description="Optional user profile data to forward to orchestrator",
    )
    modules: list[str] = Field(
        default_factory=lambda: ["full"],
        description="Modules to generate: 'full' or list of specific modules",
    )
    tone: str = Field("balanced", description="Output tone: mystical | balanced | analytical")


class ReportStatus(BaseModel):
    """Report generation status."""

    id: str
    status: str = Field(..., description="pending | generating | complete | failed")
    created_at: str
    updated_at: str | None = None


class ReportResult(BaseModel):
    """Completed report data."""

    id: str
    status: str
    result: dict | None = None
    error: str | None = None
    created_at: str
    updated_at: str | None = None


class ReportListResponse(BaseModel):
    """Paginated list of reports."""

    reports: list[ReportResult]
    count: int
    skip: int
    limit: int


# ── Helpers ──────────────────────────────────────────────────────────────


async def _build_hero_data_uri(session: AsyncSession, user_id: str) -> str | None:
    """Read the user's most recent generated image and return a data URI.

    Returns ``None`` when the user has no images or the file is missing.
    The data URI format is ``data:<mime>;base64,<encoded>`` which can be
    embedded directly into ``<img src=...>`` in the report HTML/PDF.
    """
    import base64

    from alchymine.llm.art_storage import read_image

    rows = await repository.list_generated_images_for_user(session, user_id, limit=1, offset=0)
    if not rows:
        return None

    image_row = rows[0]
    raw = read_image(image_row.file_path)
    if raw is None:
        return None

    mime = image_row.mime_type or "image/png"
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{encoded}"


# ── Endpoints ────────────────────────────────────────────────────────────


@router.post("/reports", status_code=202)
async def create_report(
    request: ReportRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> ReportStatus:
    """Queue generation of a full Alchymine report.

    Returns a report ID and ``"pending"`` status immediately.  Use
    ``GET /reports/{id}/status`` to poll for progress or
    ``GET /reports/{id}`` to retrieve the completed result.
    """
    user_id = current_user["sub"]

    # ── Safety guardrail: rate-limit report generation per user ───────
    try:
        guardrail = check_guardrail(user_id, "report_generation")
        if guardrail.action == GuardrailAction.DENY:
            audit_log_event(
                event_type=AuditEventType.RATE_LIMIT_HIT,
                system="reports",
                summary=guardrail.message,
                user_id=user_id,
                metadata={"operation": "report_generation"},
            )
            raise HTTPException(
                status_code=429,
                detail=guardrail.message,
                headers=(
                    {"Retry-After": str(int(guardrail.retry_after_seconds))}
                    if guardrail.retry_after_seconds
                    else None
                ),
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Guardrail check failed for user %s", user_id)
        raise HTTPException(
            status_code=500,
            detail=f"Guardrail check failed: {type(exc).__name__}: {exc}",
        ) from exc

    report_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    # ── Defensive FK check: verify user exists before INSERT ──────────
    # If the JWT references a user that doesn't exist in the DB, the FK
    # constraint on Report.user_id will cause an IntegrityError.  Check
    # first and fall back to user_id=None (orphan report).
    from sqlalchemy import select

    result = await session.execute(select(User.id).where(User.id == user_id))
    db_user_id: str | None = result.scalar_one_or_none()
    if db_user_id is None:
        logger.warning(
            "User %s from JWT not found in DB — creating report with user_id=None",
            user_id,
        )

    # ── Critical section: create and commit the report row ─────────────
    try:
        await repository.create_report(
            session,
            report_id=report_id,
            status="pending",
            user_input=request.user_input,
            user_profile=request.user_profile,
            user_id=db_user_id,  # None if user doesn't exist in DB
        )
        await session.commit()
    except Exception as exc:
        logger.exception(
            "CRITICAL: Failed to create report row for user %s, report %s",
            user_id,
            report_id,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Report creation failed: {type(exc).__name__}: {exc}",
        ) from exc

    # ── Best-effort section: intake persistence + task dispatch ─────────
    # Nothing below may raise.  Wrap in a single try/except so any
    # unexpected failure is logged but never surfaces as a 500.
    try:
        # Persist intake to the user's profile (cross-device sync).
        if db_user_id is not None:
            try:
                intake_persist = request.intake.model_dump(mode="json")
                from datetime import date as date_type
                from datetime import time as time_type

                intake_persist["birth_date"] = date_type.fromisoformat(intake_persist["birth_date"])
                if intake_persist.get("birth_time"):
                    intake_persist["birth_time"] = time_type.fromisoformat(
                        intake_persist["birth_time"]
                    )
                else:
                    intake_persist["birth_time"] = None
                if hasattr(intake_persist.get("intention"), "value"):
                    intake_persist["intention"] = intake_persist["intention"]
                await repository.update_layer(session, user_id, "intake", intake_persist)
                await session.commit()
            except LookupError:
                await session.rollback()
                logger.warning(
                    "Cannot persist intake for user %s: user row not found in DB",
                    user_id,
                )
            except Exception:
                await session.rollback()
                logger.exception(
                    "Failed to persist intake data for user %s",
                    user_id,
                )

        # Build profile dict and dispatch Celery task.
        intake_dict = request.intake.model_dump(mode="json")
        profile_data = request.user_profile or {}
        profile_data.update(intake_dict)

        generate_report_task.delay(
            report_id,
            request.user_input,
            profile_data,
            request.intake.intention.value,
            [i.value for i in request.intake.intentions],
        )
    except Exception:
        # Catch-all: log everything but NEVER let this become a 500.
        # The report row is already committed — the task can be retried.
        logger.exception(
            "Best-effort post-commit work failed for report %s (user %s). "
            "Report row exists but task may not have been dispatched.",
            report_id,
            user_id,
        )

    return ReportStatus(
        id=report_id,
        status="pending",
        created_at=now,
        updated_at=now,
    )


@router.get("/reports/{report_id}/status")
async def get_report_status(
    report_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> ReportStatus:
    """Return the current processing status of a report.

    Returns 404 if the report_id is not recognised.
    """
    report = await repository.get_report(session, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.user_id and report.user_id != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Access denied")

    return ReportStatus(
        id=report.id,
        status=report.status,
        created_at=report.created_at.isoformat() if report.created_at else "",
        updated_at=report.updated_at.isoformat() if report.updated_at else None,
    )


@router.get("/reports/{report_id}", response_model=None)
async def get_report(
    report_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> ReportResult | JSONResponse:
    """Retrieve a completed report by ID.

    - **200** -- report is complete (or failed) and data is returned.
    - **202** -- report is still pending or generating.
    - **404** -- report_id not found.
    """
    report = await repository.get_report(session, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.user_id and report.user_id != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Access denied")

    if report.status in ("pending", "generating"):
        return JSONResponse(
            status_code=202,
            content={"status": report.status, "detail": f"Report is {report.status}"},
        )

    return ReportResult(
        id=report.id,
        status=report.status,
        result=report.result,
        error=report.error,
        created_at=report.created_at.isoformat() if report.created_at else "",
        updated_at=report.updated_at.isoformat() if report.updated_at else None,
    )


@router.get("/reports/{report_id}/html", response_model=None)
async def get_report_html(
    report_id: str,
    embed_art: bool = Query(
        default=False,
        description="When true, embed the user's most recent generated image as a hero in the report",
    ),
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> HTMLResponse | JSONResponse:
    """Render a completed report as a styled HTML page.

    The HTML is self-contained (inline CSS) and includes a "Save as PDF"
    button that triggers the browser's native print dialog.

    When ``embed_art=true`` is passed, the user's most recently generated
    image is embedded as a ``data:`` URI hero image at the top of the
    report. This makes the PDF export self-contained without external
    image references.

    - **200** -- HTML page with report content.
    - **202** -- report is still being generated.
    - **404** -- report_id not found.
    """
    report = await repository.get_report(session, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.user_id and report.user_id != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Access denied")

    if report.status in ("pending", "generating"):
        return JSONResponse(
            status_code=202,
            content={"status": report.status, "detail": f"Report is {report.status}"},
        )

    # Optionally embed the user's most recent generated art as a data URI.
    hero_data_uri: str | None = None
    if embed_art and report.user_id:
        try:
            hero_data_uri = await _build_hero_data_uri(session, report.user_id)
        except Exception:
            logger.debug(
                "Failed to embed art for report %s — continuing without hero image",
                report_id,
                exc_info=True,
            )

    # Build a dict compatible with render_report_html
    entry = {
        "report_id": report.id,
        "status": report.status,
        "result": report.result,
        "created_at": report.created_at.isoformat() if report.created_at else "",
    }

    html_content = render_report_html(entry, hero_image_data_uri=hero_data_uri)
    return HTMLResponse(content=html_content)


@router.get("/reports/{report_id}/pdf")
async def get_report_pdf(
    report_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> Response:
    """Download a completed report as a PDF file.

    The PDF must have been previously generated via the
    ``generate_pdf_report`` Celery task. If the report exists but
    has not yet been rendered to PDF, a 404 is returned with a
    message indicating the PDF has not been generated.

    - **200** -- PDF binary download with ``Content-Disposition: attachment``.
    - **404** -- report not found, not complete, or PDF not yet generated.
    """
    report = await repository.get_report(session, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.user_id and report.user_id != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Access denied")

    if report.status != "complete":
        raise HTTPException(
            status_code=404,
            detail=f"Report is not complete (status: {report.status})",
        )

    if not report.pdf_data:
        raise HTTPException(
            status_code=404,
            detail="PDF has not been generated for this report",
        )

    import io

    pdf_bytes = report.pdf_data

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="alchymine-report-{report_id}.pdf"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )


@router.get("/reports/user/{user_id}")
async def list_user_reports(
    user_id: str,
    skip: int = Query(0, ge=0, description="Number of reports to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum reports to return"),
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> ReportListResponse:
    """List reports for a specific user with pagination.

    Returns reports ordered by creation date (most recent first).
    """
    if current_user["sub"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        reports = await repository.list_reports_by_user(session, user_id, skip=skip, limit=limit)
        total = await repository.count_reports_by_user(session, user_id)
    except Exception:
        logger.exception("Failed to query reports for user %s", user_id)
        raise
    return ReportListResponse(
        reports=[
            ReportResult(
                id=r.id,
                status=r.status,
                result=None,
                error=r.error,
                created_at=r.created_at.isoformat() if r.created_at else "",
                updated_at=r.updated_at.isoformat() if r.updated_at else None,
            )
            for r in reports
        ],
        count=total,
        skip=skip,
        limit=limit,
    )


# ── Diagnostic endpoint ──────────────────────────────────────────────


@router.get("/reports/diagnose")
async def diagnose_reports(
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> JSONResponse:
    """Diagnostic endpoint to check all components needed for report creation.

    Returns a JSON object with pass/fail status for each component.
    Requires authentication (same as POST /reports).
    """
    from sqlalchemy import select, text

    checks: dict[str, dict[str, object]] = {}
    user_id = current_user["sub"]

    # 1. DB connectivity
    try:
        await session.execute(text("SELECT 1"))
        checks["db_connection"] = {"status": "pass"}
    except Exception as exc:
        checks["db_connection"] = {"status": "fail", "error": f"{type(exc).__name__}: {exc}"}

    # 2. User existence (FK target)
    try:
        result = await session.execute(select(User.id).where(User.id == user_id))
        user_row = result.scalar_one_or_none()
        if user_row:
            checks["user_exists"] = {"status": "pass", "user_id": user_id}
        else:
            checks["user_exists"] = {
                "status": "fail",
                "error": f"No user row for JWT sub={user_id}",
            }
    except Exception as exc:
        checks["user_exists"] = {"status": "fail", "error": f"{type(exc).__name__}: {exc}"}

    # 3. Encryption key availability
    try:
        from alchymine.db.encryption import _get_fernet

        _get_fernet()
        checks["encryption_key"] = {"status": "pass"}
    except Exception as exc:
        checks["encryption_key"] = {"status": "fail", "error": f"{type(exc).__name__}: {exc}"}

    # 4. Report table writable (insert + rollback)
    try:
        test_id = f"diag-{uuid.uuid4()}"
        from alchymine.db.models import Report

        test_report = Report(id=test_id, status="diagnostic", user_id=None)
        session.add(test_report)
        await session.flush()
        await session.rollback()
        checks["report_insert"] = {"status": "pass"}
    except Exception as exc:
        await session.rollback()
        checks["report_insert"] = {"status": "fail", "error": f"{type(exc).__name__}: {exc}"}

    # 5. Celery/Redis connectivity
    try:
        from alchymine.workers.celery_app import celery_app

        insp = celery_app.control.inspect(timeout=2)
        ping = insp.ping()
        if ping:
            checks["celery_workers"] = {"status": "pass", "workers": list(ping.keys())}
        else:
            checks["celery_workers"] = {"status": "warn", "error": "No workers responded"}
    except Exception as exc:
        checks["celery_workers"] = {"status": "fail", "error": f"{type(exc).__name__}: {exc}"}

    all_pass = all(c["status"] == "pass" for c in checks.values())

    return JSONResponse(
        status_code=200 if all_pass else 503,
        content={"overall": "pass" if all_pass else "fail", "checks": checks},
    )
