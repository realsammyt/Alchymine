"""Report generation API endpoints.

Dispatches report generation to a Celery task queue and exposes
endpoints for checking status and retrieving completed reports.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from alchymine.engine.profile import IntakeData
from alchymine.workers.tasks import generate_report as generate_report_task
from alchymine.workers.tasks import report_store

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
    status: str = Field(..., description="queued | processing | complete | failed")
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


# ── Endpoints ────────────────────────────────────────────────────────────


@router.post("/reports", status_code=202)
async def create_report(request: ReportRequest) -> ReportStatus:
    """Queue generation of a full Alchymine report.

    Returns a report ID and ``"queued"`` status immediately.  Use
    ``GET /reports/{id}/status`` to poll for progress or
    ``GET /reports/{id}`` to retrieve the completed result.
    """
    report_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    # Seed the store so status queries work immediately
    report_store[report_id] = {
        "report_id": report_id,
        "status": "queued",
        "user_input": request.user_input,
        "user_profile": request.user_profile,
        "result": None,
        "error": None,
        "created_at": now,
        "updated_at": now,
    }

    # Dispatch Celery task
    generate_report_task.delay(
        report_id,
        request.user_input,
        request.user_profile,
    )

    return ReportStatus(
        id=report_id,
        status="queued",
        created_at=now,
        updated_at=now,
    )


@router.get("/reports/{report_id}/status")
async def get_report_status(report_id: str) -> ReportStatus:
    """Return the current processing status of a report.

    Returns 404 if the report_id is not recognised.
    """
    if report_id not in report_store:
        raise HTTPException(status_code=404, detail="Report not found")

    entry = report_store[report_id]
    return ReportStatus(
        id=report_id,
        status=entry["status"],
        created_at=entry["created_at"],
        updated_at=entry.get("updated_at"),
    )


@router.get("/reports/{report_id}")
async def get_report(report_id: str) -> ReportResult:
    """Retrieve a completed report by ID.

    - **200** — report is complete (or failed) and data is returned.
    - **202** — report is still queued or processing.
    - **404** — report_id not found.
    """
    if report_id not in report_store:
        raise HTTPException(status_code=404, detail="Report not found")

    entry = report_store[report_id]

    if entry["status"] in ("queued", "processing"):
        raise HTTPException(
            status_code=202,
            detail=f"Report is {entry['status']}",
        )

    return ReportResult(
        id=report_id,
        status=entry["status"],
        result=entry.get("result"),
        error=entry.get("error"),
        created_at=entry["created_at"],
        updated_at=entry.get("updated_at"),
    )
