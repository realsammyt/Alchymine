"""Report generation API endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from alchymine.engine.profile import IntakeData

router = APIRouter()

# In-memory store for development — replaced by PostgreSQL in production
_reports: dict[str, dict] = {}


class ReportRequest(BaseModel):
    """Request to generate a full Alchymine report."""

    intake: IntakeData
    modules: list[str] = Field(
        default_factory=lambda: ["full"],
        description="Modules to generate: 'full' or list of specific modules",
    )
    tone: str = Field("balanced", description="Output tone: mystical | balanced | analytical")


class ReportStatus(BaseModel):
    """Report generation status."""

    id: str
    status: str = Field(..., description="queued | generating | completed | failed")
    progress: float = Field(0.0, ge=0, le=1, description="0.0 to 1.0")
    created_at: datetime
    completed_at: datetime | None = None
    quality_gates_passed: bool | None = None


class ReportResponse(BaseModel):
    """Completed report response."""

    id: str
    status: str
    profile_summary: dict | None = None
    modules: dict | None = None
    quality_gates: dict | None = None
    created_at: datetime
    completed_at: datetime | None = None


@router.post("/reports", status_code=202)
async def generate_report(request: ReportRequest) -> ReportStatus:
    """Generate a full Alchymine report (async).

    Returns a job ID. Poll GET /reports/{id} for status and results.
    In production, this dispatches a Celery task for the full swarm pipeline.
    """
    report_id = str(uuid.uuid4())
    now = datetime.utcnow()

    _reports[report_id] = {
        "id": report_id,
        "status": "queued",
        "progress": 0.0,
        "intake": request.intake.model_dump(),
        "modules": request.modules,
        "tone": request.tone,
        "created_at": now,
        "completed_at": None,
        "result": None,
    }

    # TODO: Dispatch Celery task
    # from alchymine.api.workers.report_pipeline import generate_report_task
    # generate_report_task.delay(report_id, request.model_dump())

    return ReportStatus(
        id=report_id,
        status="queued",
        progress=0.0,
        created_at=now,
    )


@router.get("/reports/{report_id}")
async def get_report(report_id: str) -> ReportResponse:
    """Retrieve a completed report by ID.

    Returns 202 if still generating, 200 if complete, 404 if not found.
    """
    if report_id not in _reports:
        raise HTTPException(status_code=404, detail="Report not found")

    report = _reports[report_id]

    if report["status"] in ("queued", "generating"):
        raise HTTPException(
            status_code=202,
            detail=f"Report is {report['status']} ({report['progress']:.0%} complete)",
        )

    return ReportResponse(
        id=report["id"],
        status=report["status"],
        profile_summary=report.get("result", {}).get("profile_summary"),
        modules=report.get("result", {}).get("modules"),
        quality_gates=report.get("result", {}).get("quality_gates"),
        created_at=report["created_at"],
        completed_at=report.get("completed_at"),
    )
