"""
Scan Router
Handles the /scan endpoint for food image analysis
"""

import logging
import os
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.scan import ScanResponse, ErrorResponse
from app.services.gemini import gemini_service
from app.services.cache import hash_image, get_cached_result, cache_result
from app.services.rag_service import rag_service
from app.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scan", tags=["scan"])

MAX_FILE_SIZE = 5 * 1024 * 1024
ALLOWED_TYPES = ["image/jpeg", "image/jpg", "image/png"]


def _is_recognised(result: dict) -> bool:
    return result.get("confidence", 0) > 0 and result.get("food_name", "").strip().lower() != "food item"


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
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
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

    # Check cache
    image_hash = hash_image(file_content)
    logger.info(f"Processing image with hash: {image_hash[:16]}...")
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

    # Set recognised flag
    result["recognised"] = _is_recognised(result)

    # Enrich alternatives with RAG and rewrite in child-friendly language
    if rag_service.is_ready and result["recognised"]:
        food_name = result.get("food_name", "")
        rag_alternatives = rag_service.get_alternatives(food_name, k=3)
        rewritten_alternatives = await gemini_service.rewrite_alternatives(rag_alternatives)
        result["alternatives"] = rewritten_alternatives

    # Cache the result
    if bool(os.getenv("CACHE_AI_RESPONSE", True)):
        cache_result(db, image_hash, result, ttl_days=1)
    else:
        logger.info("AI response caching disabled")

    logger.info(f"Successfully processed scan for: {result.get('food_name')} (recognised={result['recognised']})")
    return ScanResponse(**result)
