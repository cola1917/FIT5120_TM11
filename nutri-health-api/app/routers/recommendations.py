"""
Recommendations router.
Returns personalised food lists based on user preferences and goal.
Uses fine-tuned OpenAI model pipeline: call_model → parse → filter → enrich.
"""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from app.auth import get_current_user
from app.schemas.recommendation import (
    RecommendationRequest,
    RecommendationResponse,
)
from app.services.enrichment import enrich_recommendation_items
from app.services.filter import filter_output, filter_tiny_hero_by_likes, resolve_forbidden
from app.services.food_image_cache import (
    generate_and_cache_food_image,
    mark_pending,
    should_queue_generation,
)
from app.services.food_metadata import find_existing_image as _find_metadata_image
from app.services.recommendation import call_model, parse_model_output, topup_sections, rewrite_try_less_by_likes

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post(
    "",
    response_model=RecommendationResponse,
    summary="Get personalised food recommendations",
)
async def recommend(
    payload: RecommendationRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """
    Return three personalised food lists for the given goal and user preferences:

    - **super_power_foods**: goal-aligned foods from liked categories
    - **tiny_hero_foods**: goal-aligned foods from disliked / challenge categories
    - **try_less_foods**: less healthy foods related to liked categories

    Blacklist and allergy filtering is applied after model generation.
    """
    logger.info(
        "Recommendation request: user=%s goal=%s",
        current_user.get("username"),
        payload.goal_id,
    )

    raw = call_model(
        goal=payload.goal_id,
        likes=payload.likes,
        dislikes=payload.dislikes,
        blacklist=payload.blacklist,
        allergies=payload.allergies,
    )
    logger.debug("Raw model output: %s", raw)

    parsed = parse_model_output(raw)
    if parsed is None:
        logger.error("Model returned unparseable output: %s", raw)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Model returned invalid output. Please try again.",
        )

    # Resolve forbidden sets once per request — reused by filter_output and topup_sections.
    forbidden_cats, forbidden_kws = resolve_forbidden(payload.blacklist + payload.allergies)

    filtered = filter_output(
        parsed, payload.blacklist, payload.allergies,
        forbidden_cats=forbidden_cats, forbidden_kws=forbidden_kws,
    )
    filtered = filter_tiny_hero_by_likes(filtered, payload.likes)
    if filtered is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Filtering failed. Please try again.",
        )

    filtered = rewrite_try_less_by_likes(filtered, payload.likes)
    filtered = topup_sections(
        filtered,
        goal=payload.goal_id,
        blacklist=payload.blacklist,
        allergies=payload.allergies,
        likes=payload.likes,
        forbidden_cats=forbidden_cats,
        forbidden_kws=forbidden_kws,
    )

    logger.info(
        "Recommendation response: super=%d tiny=%d try_less=%d",
        len(filtered.get("super_power_foods", [])),
        len(filtered.get("tiny_hero_foods", [])),
        len(filtered.get("try_less_foods", [])),
    )

    response = RecommendationResponse(
        super_power_foods=enrich_recommendation_items(
            filtered.get("super_power_foods", [])
        ),
        tiny_hero_foods=enrich_recommendation_items(
            filtered.get("tiny_hero_foods", [])
        ),
        try_less_foods=enrich_recommendation_items(
            filtered.get("try_less_foods", [])
        ),
    )

    # Queue background image generation for any item without a cached image.
    # mark_pending is called synchronously before add_task to prevent duplicate queuing.
    all_items = (
        response.super_power_foods
        + response.tiny_hero_foods
        + response.try_less_foods
    )
    for item in all_items:
        # Skip AI generation when a pre-existing metadata image already covers this food.
        if _find_metadata_image(item.food_name):
            continue
        if should_queue_generation(item.food_name):
            mark_pending(item.food_name, item.category)
            background_tasks.add_task(
                generate_and_cache_food_image, item.food_name, item.category
            )
            logger.debug("Queued image generation for '%s'", item.food_name)

    return response
