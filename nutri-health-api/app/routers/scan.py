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
        
        # Mapping of food names to Wikimedia Commons file names
        wikimedia_food_map = {
            "apple": "Apple_with_cut.jpg",
            "banana": "Bananas_single.jpg",
            "orange": "Orange_blossom_wb.jpg",
            "grape": "Grapes_-_green_one_layer.jpg",
            "strawberry": "Strawberry_closeup.jpg",
            "watermelon": "Watermelon_cross_section.jpg",
            "rice": "White_rice_grains.jpg",
            "bread": "Bread_loaf.jpg",
            "croissant": "Croissant_01.jpg",
            "pancake": "Pancakes_with_butter_and_syrup.jpg",
            "cheese": "Cheese_platter.jpg",
            "meat": "Raw_meat.jpg",
            "chicken": "Chicken_breast.jpg",
            "bacon": "Bacon_crispy.jpg",
            "burger": "Hamburger_cheese.jpg",
            "fries": "French_fries.jpg",
            "pizza": "Pizza_margherita.jpg",
            "hotdog": "Hot_dog.jpg",
            "sandwich": "Sandwich_variety.jpg",
            "taco": "Taco_shell.jpg",
            "burrito": "Burrito.jpg",
            "salad": "Green_salad.jpg",
            "soup": "Vegetable_soup.jpg",
            "noodle": "Noodles.jpg",
            "pasta": "Pasta_variety.jpg",
            "sushi": "Sushi_platter.jpg",
            "egg": "Eggs_white_brown.jpg",
            "avocado": "Avocado_cut.jpg",
            "broccoli": "Broccoli_flower.jpg",
            "carrot": "Carrots_variety.jpg",
            "corn": "Sweet_corn.jpg",
            "cucumber": "Cucumber_slices.jpg",
            "tomato": "Tomato_red.jpg",
            "potato": "Potatoes_variety.jpg",
            "mushroom": "Mushroom_variety.jpg",
            "pepper": "Bell_peppers_colorful.jpg",
            "ice cream": "Ice_cream_cone.jpg",
            "cake": "Birthday_cake.jpg",
            "cookie": "Chocolate_chip_cookies.jpg",
            "chocolate": "Chocolate_bar.jpg",
            "donut": "Glazed_donuts.jpg",
            "yogurt": "Yogurt_with_fruit.jpg",
            "milk": "Glass_of_milk.jpg",
            "smoothie": "Fruit_smoothie.jpg",
            "juice": "Orange_juice_glass.jpg",
            "berries": "Mixed_berries.jpg",
            "blueberry": "Blueberries_fresh.jpg",
            "raspberry": "Raspberries_fresh.jpg",
            "pear": "Pear_green.jpg",
            "peach": "Peach_fruit.jpg",
            "plum": "Plum_fruit.jpg",
            "kiwi": "Kiwi_fruit_cut.jpg",
            "mango": "Mango_fruit.jpg",
            "pineapple": "Pineapple_whole.jpg",
            "papaya": "Papaya_cut.jpg",
            "spinach": "Spinach_leaves.jpg",
            "lettuce": "Lettuce_head.jpg",
            "cabbage": "Cabbage_green.jpg",
            "beans": "Green_beans.jpg",
            "lentils": "Lentils_dried.jpg",
            "tofu": "Tofu_block.jpg",
            "fish": "Fresh_fish.jpg",
            "salmon": "Salmon_fillet.jpg",
            "shrimp": "Shrimp_cooked.jpg",
            "oats": "Oatmeal_bowl.jpg",
            "cereal": "Breakfast_cereal.jpg",
            "nuts": "Mixed_nuts.jpg",
            "almonds": "Almonds_raw.jpg",
            "walnuts": "Walnuts_shelled.jpg",
            "healthy": "Healthy_food_platter.jpg",
            "fruit": "Fresh_fruit_bowl.jpg",
            "vegetable": "Mixed_vegetables.jpg",
            "platter": "Fruit_platter.jpg",
            "vegetables": "Vegetable_salad.jpg",
            "yoghurt": "Plain_yogurt.jpg",
            "plain": "Plain_yogurt.jpg",
            "grain": "Whole_grain_bread.jpg",
            "grilled": "Grilled_chicken.jpg",
            "fruit platter": "Fruit_platter.jpg",
            "vegetable salad": "Vegetable_salad.jpg",
            "plain yoghurt": "Plain_yogurt.jpg",
            "whole grain": "Whole_grain_bread.jpg",
            "grilled chicken": "Grilled_chicken.jpg",
        }
        
        import hashlib
        
        for i, alt in enumerate(rewritten_alternatives):
            alt_name = alt.get("name", "").lower()
            # Extract keywords from the alternative name to find matching Wikimedia image
            wikimedia_file = None
            for key, value in wikimedia_food_map.items():
                if key in alt_name:
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
                except Exception as e:
                    logger.warning(f"Failed to fetch image URL from Wikimedia API: {e}")
                    # Fallback to direct URL construction
                    alt["image_url"] = f"https://upload.wikimedia.org/wikipedia/commons/thumb/{wikimedia_file[0].lower()}/{wikimedia_file}"
            else:
                # Fallback: use a generic healthy food image
                fallback_files = ["Healthy_food_platter.jpg", "Fresh_fruit_bowl.jpg", "Mixed_vegetables.jpg"]
                # Use hash of alternative name to pick a consistent fallback
                hash_idx = int(hashlib.md5(alt_name.encode()).hexdigest(), 16) % len(fallback_files)
                fallback_file = fallback_files[hash_idx]
                alt["image_url"] = f"https://upload.wikimedia.org/wikipedia/commons/thumb/{fallback_file[0].lower()}/{fallback_file}"
                
        result["alternatives"] = rewritten_alternatives

    # Cache the result
    if bool(os.getenv("CACHE_AI_RESPONSE", True)):
        cache_result(db, image_hash, result, ttl_days=1)
    else:
        logger.info("AI response caching disabled")

    logger.info(f"Successfully processed scan for: {result.get('food_name')} (recognised={result['recognised']})")
    return ScanResponse(**result)
