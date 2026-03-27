"""
Scan Router
Handles the /scan endpoint for food image analysis
"""

import logging
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.scan import ScanResponse, ErrorResponse
from app.services.gemini import gemini_service
from app.services.cache import hash_image, get_cached_result, cache_result

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/scan", tags=["scan"])

# Maximum file size (5MB)
MAX_FILE_SIZE = 5 * 1024 * 1024

# Allowed image types
ALLOWED_TYPES = ["image/jpeg", "image/jpg", "image/png"]


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
    db: Session = Depends(get_db)
):
    """
    Scan a food image and return nutritional information.
    
    This endpoint:
    1. Validates the uploaded image
    2. Checks if results are cached
    3. If not cached, sends to Gemini AI for analysis
    4. Caches the results for future requests
    5. Returns comprehensive nutritional information
    
    Args:
        file: Uploaded image file
        db: Database session
        
    Returns:
        ScanResponse containing food analysis
        
    Raises:
        HTTPException: If file validation fails or processing errors occur
    """
    
    # Validate file type
    print('Validating file type:', file.content_type)
    if file.content_type not in ALLOWED_TYPES:
        logger.warning(f"Invalid file type: {file.content_type}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_TYPES)}"
        )
    
    # Read file content
    print('Reading file content')
    try:
        file_content = await file.read()
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read uploaded file"
        )
    
    # Validate file size
    print('Validating file size of:', len(file_content))
    if len(file_content) > MAX_FILE_SIZE:
        logger.warning(f"File too large: {len(file_content)} bytes")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024}MB"
        )
    
    if len(file_content) == 0:
        logger.warning("Empty file uploaded")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file uploaded"
        )
    
    # Generate image hash for caching
    print('Generating image hash')
    image_hash = hash_image(file_content)
    print('Generated image hash:', image_hash)
    logger.info(f"Processing image with hash: {image_hash[:16]}...")
    
    # Check cache
    print('Checking cache')
    cached_result = get_cached_result(db, image_hash)
    if cached_result:
        logger.info("Returning cached result")
        return ScanResponse(**cached_result)
    
    # Analyze image with Gemini
    try:
        logger.info("Analyzing image with Gemini AI")
        result = await gemini_service.analyze_food_image(file_content)
    except Exception as e:
        logger.error(f"Error analyzing image with Gemini: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze image. Please try again later."
        )
    
    # Cache the result
    cache_result(db, image_hash, result, ttl_days=1)
    
    # Return response
    logger.info(f"Successfully processed scan for: {result.get('food_name')}")
    return ScanResponse(**result)
