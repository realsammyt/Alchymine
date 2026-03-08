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
from alchymine.engine.profile import IntakeData
from alchymine.engine.reports.html_renderer import render_report_html
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
    report_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    # Persist the report row so status queries work immediately.
    # Commit explicitly before dispatching the Celery task so the
    # task (which uses its own session) can find the row.
    await repository.create_report(
        session,
        report_id=report_id,
        status="pending",
        user_input=request.user_input,
        user_profile=request.user_profile,
        user_id=current_user["sub"],
    )

    # Persist the intake data to the user's profile so it survives across
    # devices and sessions (sessionStorage is browser-tab-scoped).
    try:
        intake_persist = request.intake.model_dump(mode="json")
        # Convert date/time strings back to proper types for the ORM
        from datetime import date as date_type
        from datetime import time as time_type

        intake_persist["birth_date"] = date_type.fromisoformat(intake_persist["birth_date"])
        if intake_persist.get("birth_time"):
            intake_persist["birth_time"] = time_type.fromisoformat(intake_persist["birth_time"])
        else:
            intake_persist["birth_time"] = None
        # Convert intention enum value to plain string
        if hasattr(intake_persist.get("intention"), "value"):
            intake_persist["intention"] = intake_persist["intention"]
        await repository.update_layer(session, current_user["sub"], "intake", intake_persist)
    except LookupError:
        # User row doesn't exist — JWT sub doesn't match a DB user.
        logger.warning(
            "Cannot persist intake for user %s: user row not found in DB",
            current_user["sub"],
        )
    except Exception:
        logger.exception(
            "Failed to persist intake data for user %s",
            current_user["sub"],
        )

    await session.commit()

    # Build a profile dict from the intake data so the orchestrator's
    # engine nodes have the fields they need (full_name, birth_date, etc.)
    intake_dict = request.intake.model_dump(mode="json")
    profile_data = request.user_profile or {}
    profile_data.update(intake_dict)

    # Dispatch Celery task with intention(s) + full intake context
    try:
        generate_report_task.delay(
            report_id,
            request.user_input,
            profile_data,
            request.intake.intention.value,
            [i.value for i in request.intake.intentions],
        )
    except Exception:
        logger.error(
            "Failed to dispatch report task for %s — Celery/Redis may be unavailable",
            report_id,
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
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> HTMLResponse | JSONResponse:
    """Render a completed report as a styled HTML page.

    The HTML is self-contained (inline CSS) and includes a "Save as PDF"
    button that triggers the browser's native print dialog.

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

    # Build a dict compatible with render_report_html
    entry = {
        "report_id": report.id,
        "status": report.status,
        "result": report.result,
        "created_at": report.created_at.isoformat() if report.created_at else "",
    }

    html_content = render_report_html(entry)
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
