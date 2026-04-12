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
        
        rewritten_alternatives = []
        for alt in rag_alternatives:
            alt_name = alt.get("name", "").lower()
            # Find matching emoji
            emoji = "🍽️"  # default emoji
            for key, value in emoji_map.items():
                if key == alt_name or key in alt_name or alt_name in key:
                    emoji = value
                    break
            
            # Capitalize name properly
            display_name = alt.get("name", "").title()
            rewritten_alternatives.append({
                "name": f"{emoji} {display_name}",
                "description": alt.get("description", "A healthy and tasty choice")
            })
        
        # Mapping of food names to Wikimedia Commons file names (must match the whitelist in rag_service.py)
        wikimedia_food_map = {
            "apple": "Apple_with_cut.jpg",
            "banana": "Bananas_single.jpg",
            "orange": "Orange_blossom_wb.jpg",
            "grape": "Grapes_-_green_one_layer.jpg",
            "strawberry": "Strawberry_closeup.jpg",
            "watermelon": "Watermelon_cross_section.jpg",
            "broccoli": "Broccoli_flower.jpg",
            "carrot": "Carrots_variety.jpg",
            "cucumber": "Cucumber_slices.jpg",
            "tomato": "Tomato_red.jpg",
            "spinach": "Spinach_leaves.jpg",
            "lettuce": "Lettuce_head.jpg",
            "corn": "Sweet_corn.jpg",
            "avocado": "Avocado_cut.jpg",
            "blueberry": "Blueberries_fresh.jpg",
            "raspberry": "Raspberries_fresh.jpg",
            "pear": "Pear_green.jpg",
            "peach": "Peach_fruit.jpg",
            "kiwi": "Kiwi_fruit_cut.jpg",
            "mango": "Mango_fruit.jpg",
            "pineapple": "Pineapple_whole.jpg",
            "plum": "Plum_fruit.jpg",
            "papaya": "Papaya_cut.jpg",
            "beans": "Green_beans.jpg",
            "salad": "Green_salad.jpg",
            "vegetable salad": "Vegetable_salad.jpg",
            "fruit platter": "Fruit_platter.jpg",
            "plain yoghurt": "Plain_yogurt.jpg",
            "grilled chicken": "Grilled_chicken.jpg",
            "fish": "Fresh_fish.jpg",
        }
        
        import hashlib
        
        for i, alt in enumerate(rewritten_alternatives):
            alt_name = alt.get("name", "").lower()
            # Find matching Wikimedia image from the map (exact match or keyword match)
            wikimedia_file = None
            
            # First try exact match
            if alt_name in wikimedia_food_map:
                wikimedia_file = wikimedia_food_map[alt_name]
            else:
                # Then try keyword match
                for key, value in wikimedia_food_map.items():
                    if key in alt_name or alt_name in key:
                        wikimedia_file = value
                        break
            
            # Build Wikimedia Commons URL using MediaWiki API for reliable image retrieval
            if wikimedia_file:
                # Use MediaWiki API to get the actual image URL
                api_url = f"https://commons.wikimedia.org/w/api.php?action=query&titles=File:{wikimedia_file}&prop=imageinfo&iiprop=url&format=json"
                try:
                    import aiohttp
                    async with aiohttp.ClientSession() as session:
                        async with session.get(api_url) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                pages = data.get("query", {}).get("pages", {})
                                for page_id, page_data in pages.items():
                                    if "imageinfo" in page_data:
                                        alt["image_url"] = page_data["imageinfo"][0]["url"]
                                        break
                                    elif "missing" in page_data:
                                        # File doesn't exist, use fallback
                                        break
                except Exception as e:
                    logger.warning(f"Failed to fetch image URL from Wikimedia API: {e}")
                    # Fallback to direct URL construction
                    alt["image_url"] = f"https://upload.wikimedia.org/wikipedia/commons/thumb/{wikimedia_file[0].lower()}/{wikimedia_file}"
            else:
                # This should not happen since we control the whitelist, but just in case
                logger.warning(f"No image mapping found for: {alt_name}")
                alt["image_url"] = None
                
        result["alternatives"] = rewritten_alternatives

    # Cache the result
    if bool(os.getenv("CACHE_AI_RESPONSE", True)):
        cache_result(db, image_hash, result, ttl_days=1)
    else:
        logger.info("AI response caching disabled")

    logger.info(f"Successfully processed scan for: {result.get('food_name')} (recognised={result['recognised']})")
    return ScanResponse(**result)
