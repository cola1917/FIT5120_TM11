"""
Recommendations router.
Returns personalised food lists based on user preferences and goal.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.schemas.recommendations import RecommendationRequest, RecommendationResponse
from app.services.recommendation_service import get_recommendations

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post(
    "",
    response_model=RecommendationResponse,
    summary="Get personalised food recommendations",
)
async def recommend(
    payload: RecommendationRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Return three personalised food lists for the given goal and user preferences:

    - **super_power_foods**: healthy (A/B) foods from liked + goal-relevant categories
    - **tiny_hero_foods**: healthy (A/B) foods from disliked / unexplored goal categories
    - **try_less_foods**: unhealthy (D/E) foods from liked / goal categories

    Allergen filtering (blacklist) is applied globally before all queries.
    No food appears in more than one section.

    Empty likes/dislikes/blacklist are valid — the backend has fallback logic
    that returns goal-relevant results even with no user preferences.
    """
    logger.info(
        "Recommendation request: user=%s goal=%s",
        current_user.get("username"),
        payload.goal_id,
    )

    valid_goals = {"grow", "see", "think", "fight", "feel", "strong"}
    if payload.goal_id not in valid_goals:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid goal_id '{payload.goal_id}'. Must be one of: {sorted(valid_goals)}",
        )

    result = get_recommendations(db, payload)
    logger.info(
        "Recommendation response: super=%d tiny=%d trless=%d",
        len(result.super_power_foods),
        len(result.tiny_hero_foods),
        len(result.try_less_foods),
    )
    return result
