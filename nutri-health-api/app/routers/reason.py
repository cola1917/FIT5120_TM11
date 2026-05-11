"""
On-demand personalized reason endpoint.

POST /recommendations/reason

Generates a child-friendly, goal-aware reason for a single food item
using deterministic templates only.  No LLM, no database, no model call.
"""

import logging

from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.schemas.reason import ReasonRequest, ReasonResponse
from app.services.reason_builder import build_personalized_reason

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post(
    "/reason",
    response_model=ReasonResponse,
    summary="Get a personalized reason for a recommended food item",
)
async def get_reason(
    payload: ReasonRequest,
    current_user: dict = Depends(get_current_user),
) -> ReasonResponse:
    """
    Return a deterministic, child-friendly reason for why a food item
    was recommended.  The reason is personalised to goal, section, and
    user likes/dislikes without any LLM or database call.
    """
    logger.info(
        "Reason request: user=%s food=%r goal=%s section=%s",
        current_user.get("username"),
        payload.food_name,
        payload.goal_id,
        payload.section_name,
    )

    reason = build_personalized_reason(
        food_name    = payload.food_name,
        category     = payload.category,
        section_name = payload.section_name,
        goal_id      = payload.goal_id,
        likes        = payload.likes,
        dislikes     = payload.dislikes,
    )

    return ReasonResponse(
        food_id   = payload.food_id,
        food_name = payload.food_name,
        reason    = reason,
    )
