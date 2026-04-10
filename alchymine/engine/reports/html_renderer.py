"""HTML report renderer using Jinja2 templates.

Renders completed report data into a styled HTML page suitable for
printing to PDF via the browser's native print dialog. The template
is self-contained (inline CSS) so the exported HTML file works offline.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=True,
)


def render_report_html(
    report_data: dict[str, Any],
    *,
    hero_image_data_uri: str | None = None,
) -> str:
    """Render a completed report as a standalone HTML page.

    Parameters
    ----------
    report_data:
        The report dict from ``report_store`` (or DB), containing
        ``result``, ``report_id``, ``status``, ``created_at``, etc.
    hero_image_data_uri:
        Optional ``data:image/png;base64,...`` URI to embed as the report
        hero image. When *None* (the default) the hero image section is
        not rendered. Passed in by the ``/reports/{id}/html`` endpoint
        when the user has generated art.

    Returns
    -------
    str
        A complete HTML document string ready for display or PDF export.
    """
    template = _env.get_template("report.html")

    # Extract structured data from the orchestrator result
    result = report_data.get("result") or {}
    profile_summary = result.get("profile_summary") or {}
    identity = profile_summary.get("identity") or {}
    coordinator_results = result.get("coordinator_results") or []

    # Build template context
    context = {
        "report_id": report_data.get("report_id", report_data.get("id", "unknown")),
        "created_at": report_data.get("created_at", ""),
        "status": report_data.get("status", "unknown"),
        # Identity layer
        "numerology": identity.get("numerology", {}),
        "astrology": identity.get("astrology", {}),
        "archetype": identity.get("archetype", {}),
        "personality": identity.get("personality", {}),
        "strengths_map": identity.get("strengths_map", []),
        # Coordinator results for other systems
        "coordinator_results": coordinator_results,
        # Quality gates
        "quality_passed": result.get("quality_passed", False),
        # LLM narratives (optional — absent when LLM is unavailable)
        "narratives": result.get("narratives", {}),
        # Generated art hero image (optional)
        "hero_image_data_uri": hero_image_data_uri,
    }

    return template.render(**context)
