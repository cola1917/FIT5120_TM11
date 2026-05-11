"""
Scan Router
Handles the /scan endpoint for food image analysis
"""

import asyncio
import logging
import os
from urllib.parse import quote
import json
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.scan import ScanResponse, ErrorResponse
from app.services.gemini import gemini_service
from app.services.alternative_rules import (
    TARGET_ALTERNATIVE_COUNT,
    clean_food_name_for_image,
    infer_food_category,
)
from app.services.cache import hash_image, get_cached_result, cache_result
from app.services.health_scoring import apply_database_first_score
from app.services.scan_alternative_service import get_scan_alternatives
from app.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scan", tags=["scan"])

MAX_FILE_SIZE = 5 * 1024 * 1024
ALLOWED_TYPES = ["image/jpeg", "image/jpg", "image/png"]
MIN_RECOGNITION_CONFIDENCE = 0.75
SCAN_CACHE_VERSION = "scan-v2-not-food-filter"
ANALYSIS_FAILED_REASON = "analysis_failed"
NON_FOOD_REJECT_REASONS = {"not_food", "screenshot", "blurry", "unclear", "multiple_objects"}
NON_FOOD_TERMS = {
    "mouse", "keyboard", "phone", "screen", "monitor", "toy", "book", "remote",
    "controller", "laptop", "tablet", "wall", "chair", "table", "desk", "door",
    "window", "cable", "charger", "headphone", "earphone", "camera", "bottle cap",
}


def _normalize_label(value: str) -> str:
    return " ".join((value or "").strip().lower().replace("_", " ").split())


def _looks_like_non_food(*labels: str) -> bool:
    for raw in labels:
        label = _normalize_label(raw)
        if not label:
            continue
        for bad_term in NON_FOOD_TERMS:
            if bad_term in label:
                return True
    return False


def _reject_reason(result: dict) -> str:
    return (result.get("reject_reason", "") or "").strip().lower()


def _is_recognised(result: dict) -> bool:
    food_name = _normalize_label(result.get("food_name", ""))
    primary_object = _normalize_label(result.get("primary_object", ""))
    confidence = float(result.get("confidence", 0) or 0)
    if result.get("is_food") is not True:
        return False
    if confidence < MIN_RECOGNITION_CONFIDENCE:
        return False
    if food_name in {"", "food item", "__not food__", "__not_food__"}:
        return False
    if _reject_reason(result) in NON_FOOD_REJECT_REASONS:
        return False
    if _looks_like_non_food(food_name, primary_object):
        return False
    return True


def _raise_not_food(result: dict) -> None:
    logger.info(
        "Rejected non-food scan: food_name=%r primary_object=%r confidence=%.2f reject_reason=%s",
        result.get("food_name"),
        result.get("primary_object"),
        float(result.get("confidence", 0) or 0),
        _reject_reason(result) or "none",
    )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="No food detected. Please retake a photo with one food item clearly visible.",
        headers={"X-Error-Code": "NOT_FOOD"},
    )


def get_food_image_url(food_name: str) -> str:
    encoded = quote(clean_food_name_for_image(food_name))
    return f"https://image.pollinations.ai/prompt/{encoded}%20food%20photography%20white%20background?model=flux&width=512&height=512"


@router.post(
    "",
    response_model=ScanResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file type or size"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Scan food image",
    description="Upload a food image to get nutritional information and health assessment"
)
async def scan_food(
    file: UploadFile = File(..., description="Image file (JPEG or PNG, max 5MB)"),
    blacklist: str = Form(default="[]", description="JSON array of blacklisted terms e.g. '[\"nuts\",\"egg\"]'"),
    likes: str = Form(default="[]", description="JSON array of liked categories e.g. '[\"fruits\",\"dairy\"]'"),
    dislikes: str = Form(default="[]", description="JSON array of disliked categories e.g. '[\"fish\",\"meat\"]'"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    def _parse_str_list(raw: str) -> list[str]:
        try:
            parsed = json.loads(raw) if raw else []
            return parsed if isinstance(parsed, list) else []
        except (json.JSONDecodeError, ValueError):
            return []

    blacklist_terms = _parse_str_list(blacklist)
    likes_terms     = _parse_str_list(likes)
    dislikes_terms  = _parse_str_list(dislikes)
    # Validate file type
    if file.content_type not in ALLOWED_TYPES:
        logger.warning(f"Invalid file type: {file.content_type}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_TYPES)}",
            headers={"X-Error-Code": "INVALID_FILE"},
        )

    # Read file content
    try:
        file_content = await file.read()
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read uploaded file",
            headers={"X-Error-Code": "INVALID_FILE"},
        )

    # Validate file size
    if len(file_content) > MAX_FILE_SIZE:
        logger.warning(f"File too large: {len(file_content)} bytes")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024}MB",
            headers={"X-Error-Code": "INVALID_FILE"},
        )

    if len(file_content) == 0:
        logger.warning("Empty file uploaded")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file uploaded",
            headers={"X-Error-Code": "INVALID_FILE"},
        )

    # Check cache — skip when user has a blacklist (results are personalised)
    has_prefs = bool(blacklist_terms or likes_terms or dislikes_terms)
    image_hash = hash_image(file_content + SCAN_CACHE_VERSION.encode("utf-8"))
    logger.info(f"Processing image with hash: {image_hash[:16]}...")
    if not has_prefs:
        cached_result = get_cached_result(db, image_hash)
        if cached_result:
            logger.info("Returning cached result")
            return ScanResponse(**cached_result)

    # Analyse image
    try:
        logger.info("Analysing image with vision LLM")
        result = await gemini_service.analyze_food_image(file_content)
    except Exception as e:
        logger.error(f"Error analysing image with vision LLM: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyse image. Please try again later.",
            headers={"X-Error-Code": "ANALYSIS_FAILED"},
        )

    if _reject_reason(result) == ANALYSIS_FAILED_REASON:
        logger.error("Vision analysis returned fallback failure payload")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyse image. Please try again later.",
            headers={"X-Error-Code": "ANALYSIS_FAILED"},
        )

    if not _is_recognised(result):
        _raise_not_food(result)

    # Set recognised flag
    result["recognised"] = True
    source_category = infer_food_category(result.get("food_name", ""))

    final_score = apply_database_first_score(result, db)
    result["assessment_score"] = final_score["assessment_score"]
    result["assessment"] = final_score["assessment"]
    logger.info(
        "Final score for %r: %s (source=%s, cn_code=%s, grade=%s)",
        result.get("food_name"),
        result["assessment_score"],
        final_score["score_source"],
        final_score["matched_cn_code"],
        final_score["health_grade"],
    )

    # For healthy foods, hide alternatives entirely.
    if int(result.get("assessment_score", 3) or 3) >= 3:
        result["alternatives"] = []

    # For moderate/unhealthy recognised foods, generate alternatives via fine-tuned model.
    else:
        food_name = result.get("food_name", "")
        rewritten_alternatives = await asyncio.to_thread(
            get_scan_alternatives,
            food_name,
            result["assessment_score"],
            blacklist_terms,
            likes_terms,
            dislikes_terms,
        )
        normalized_alternatives = []
        for alt in rewritten_alternatives[:TARGET_ALTERNATIVE_COUNT]:
            alt["image_url"] = get_food_image_url(alt.get("name", ""))
            normalized_alternatives.append(alt)
        result["alternatives"] = normalized_alternatives

    # Cache the result — skip when user has a blacklist (personalised results must not be shared)
    if not has_prefs and os.getenv("CACHE_AI_RESPONSE", "true").lower() not in ("false", "0", "no"):
        cache_result(db, image_hash, result, ttl_days=1)
    elif has_prefs:
        logger.info("Skipping cache write: personalised result (blacklist present)")
    else:
        logger.info("AI response caching disabled")

    logger.info(f"Successfully processed scan for: {result.get('food_name')} (recognised={result['recognised']})")
    return ScanResponse(**result)
