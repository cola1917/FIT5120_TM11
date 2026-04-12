"""
Scan Router
Handles the /scan endpoint for food image analysis
"""

import logging
import os
import requests
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

    # Enrich alternatives with RAG (no LLM rewrite to preserve exact food names for image mapping)
    if rag_service.is_ready and result["recognised"]:
        food_name = result.get("food_name", "")
        rag_alternatives = rag_service.get_alternatives(food_name, k=3)
        
        # Add emojis to food names (no LLM rewrite to ensure exact name matching for images)
        emoji_map = {
            "apple": "🍎",
            "banana": "🍌",
            "orange": "🍊",
            "grape": "🍇",
            "strawberry": "🍓",
            "watermelon": "🍉",
            "broccoli": "🥦",
            "carrot": "🥕",
            "cucumber": "🥒",
            "tomato": "🍅",
            "spinach": "🥬",
            "lettuce": "🥗",
            "corn": "🌽",
            "avocado": "🥑",
            "blueberry": "🫐",
            "raspberry": "🍇",
            "pear": "🍐",
            "peach": "🍑",
            "kiwi": "🥝",
            "mango": "🥭",
            "pineapple": "🍍",
            "plum": "🍑",
            "papaya": "🥭",
            "beans": "🫘",
            "salad": "🥗",
            "vegetable salad": "🥗",
            "fruit platter": "🍎",
            "plain yoghurt": "🥛",
            "grilled chicken": "🍗",
            "fish": "🐟",
        }
        
        # Store the original clean name for image lookup, and create display name with emoji
        processed_alternatives = []
        for alt in rag_alternatives:
            original_name = alt.get("name", "").lower()  # Keep clean lowercase name for lookup
            
            # Find matching emoji
            emoji = "🍽️"  # default emoji
            for key, value in emoji_map.items():
                if key == original_name or key in original_name or original_name in key:
                    emoji = value
                    break
            
            # Create display name with emoji
            display_name = f"{emoji} {alt.get('name', '').title()}"
            
            processed_alternatives.append({
                "original_name": original_name,  # Store clean name for image lookup
                "name": display_name,            # Display name with emoji
                "description": alt.get("description", "A healthy and tasty choice")
            })
        
        # Mapping from standardized food name to Wikimedia Commons filename
        # We store only the filename and fetch the real URL dynamically via API
        WIKIMEDIA_FILE_MAP = {
            "apple": "Apples.jpg",
            "banana": "Banana-Single.jpg",
            "orange": "Orange_blossom_2.jpg",
            "grape": "Grapes_-_green_and_red.jpg",
            "strawberry": "Fragaria_'Ananassa'_Garten_Erdbeere.jpg",
            "watermelon": "Watermelon_stylized.jpg",
            "broccoli": "Broccoli_closeup.jpg",
            "carrot": "Carrots_of_many_colors.jpg",
            "cucumber": "Cucumbers.jpg",
            "tomato": "Tomato_je.jpg",
            "spinach": "Spinach_leaves.jpg",
            "lettuce": "Lettuce_leaves.jpg",
            "corn": "Corn_on_the_cob.jpg",
            "avocado": "Avocado_open_and_closed.jpg",
            "blueberry": "Blueberries.jpg",
            "raspberry": "Raspberries.jpg",
            "pear": "Pears.jpg",
            "peach": "Peaches_-_whole_and_halved.jpg",
            "kiwi": "Kiwi_fruit.jpg",
            "mango": "Mango_frucht.jpg",
            "pineapple": "Pineapple_and_cross_section.jpg",
            "plum": "Cherries.jpg",  # Using cherries as fallback for plum
            "papaya": "Papaya_cross_section.jpg",
            "beans": "Peas_in_a_pod.jpg",
            "salad": "Lettuce_leaves.jpg",
            "vegetable salad": "Lettuce_leaves.jpg",
            "fruit platter": "Apples.jpg",
            "plain yoghurt": "Yogurt_with_fruit.jpg",
            "grilled chicken": "Grilled_chicken.jpg",
            "fish": "Salmon_fillet.jpg",
        }
        
        def get_wikimedia_image_url(filename: str) -> str | None:
            """Fetch real image URL from Wikimedia API to avoid hardcoded paths."""
            try:
                api_url = "https://commons.wikimedia.org/w/api.php"
                params = {
                    "action": "query",
                    "titles": f"File:{filename}",
                    "prop": "imageinfo",
                    "iiprop": "url",
                    "format": "json"
                }
                response = requests.get(api_url, params=params, timeout=5)
                response.raise_for_status()
                data = response.json()
                
                pages = data.get("query", {}).get("pages", {})
                page_data = next(iter(pages.values()), {})
                
                if "imageinfo" in page_data and len(page_data["imageinfo"]) > 0:
                    return page_data["imageinfo"][0]["url"]
            except Exception as e:
                logger.warning(f"Failed to fetch image URL for {filename}: {e}")
            return None
        
        for alt in processed_alternatives:
            # Use the stored original_name for exact matching
            image_key = alt.get("original_name", "")
            filename = WIKIMEDIA_FILE_MAP.get(image_key)
            
            image_url = None
            if filename:
                image_url = get_wikimedia_image_url(filename)
            
            if image_url:
                alt["image_url"] = image_url
            else:
                # Fallback to generic healthy food image if specific one fails
                logger.warning(f"No image mapping found for: {image_key}")
                alt["image_url"] = None
        
        # Remove the internal 'original_name' field before returning
        rewritten_alternatives = []
        for alt in processed_alternatives:
            rewritten_alternatives.append({
                "name": alt["name"],
                "description": alt["description"],
                "image_url": alt.get("image_url")
            })
        
        result["alternatives"] = rewritten_alternatives

    # Cache the result
    if bool(os.getenv("CACHE_AI_RESPONSE", True)):
        cache_result(db, image_hash, result, ttl_days=1)
    else:
        logger.info("AI response caching disabled")

    logger.info(f"Successfully processed scan for: {result.get('food_name')} (recognised={result['recognised']})")
    return ScanResponse(**result)
