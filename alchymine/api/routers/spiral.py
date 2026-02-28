"""Alchemical Spiral API endpoints — adaptive routing and recommendations.

The Spiral replaces linear user journeys with a hub-and-spoke model.
Users can enter at any point and receive personalized recommendations
for which system to engage next based on their profile, intention,
and engagement history.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from alchymine.engine.spiral.router import SpiralRouteResult, route_user

router = APIRouter()


# ── Request / Response models ───────────────────────────────────────────


class SpiralRouteRequest(BaseModel):
    """Request for adaptive system routing."""

    intention: str = Field(
        ...,
        description="Primary intention: career | love | purpose | money | health | family | business | legacy",
    )
    life_path: int | None = Field(None, ge=1, le=33, description="Numerology Life Path number")
    personality_openness: float | None = Field(
        None, ge=0, le=100, description="Big Five Openness score"
    )
    personality_neuroticism: float | None = Field(
        None, ge=0, le=100, description="Big Five Neuroticism score"
    )
    systems_engaged: list[str] = Field(
        default_factory=list,
        description="Systems already engaged with (to encourage breadth)",
    )


# ── Endpoints ───────────────────────────────────────────────────────────


@router.post("/spiral/route")
async def get_spiral_route(request: SpiralRouteRequest) -> SpiralRouteResult:
    """Determine the highest-leverage system for a user.

    Uses deterministic scoring based on:
    - Primary intention (40% weight)
    - Life Path number alignment (bonus)
    - Personality traits (adjustment)
    - Engagement history (breadth encouragement)

    Returns all 5 systems ranked by relevance with human-readable
    reasons and suggested entry actions.
    """
    return route_user(
        intention=request.intention,
        life_path=request.life_path,
        personality_openness=request.personality_openness,
        personality_neuroticism=request.personality_neuroticism,
        systems_engaged=request.systems_engaged,
    )
