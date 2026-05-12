"""
Enrichment helper for model-generated food recommendation items.

Responsibilities:
- Infer a food category from the model's food name string.
- Assign a category-level fallback image_url.
- Produce food_id (url-safe slug) for use as a React key.
- Return EnrichedFoodItem objects.

The model chooses specific foods; this module only classifies and annotates
the model's choice. No concrete food candidates are generated here.
"""

from __future__ import annotations

import re

from app.schemas.recommendation import EnrichedFoodItem
from app.services.food_image_cache import (
    get_cached_image,
    get_category_fallback_image,
)
from app.services.food_metadata import find_existing_image as _find_metadata_image

# ─── Category keyword map ─────────────────────────────────────────────────────
# Order matters: more specific terms should appear in earlier entries.
# Each entry: (category_name, list_of_keywords_to_match_in_food_name)

_CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("eggs",        ["egg", "eggs"]),
    ("fish",        ["salmon", "tuna", "cod", "mackerel", "sardine", "tilapia",
                     "trout", "herring", "anchovy", "snapper", "halibut",
                     "seabass", "carp", "fish"]),
    ("meat",        ["chicken", "beef", "lamb", "turkey", "duck", "venison",
                     "bison", "veal", "meat", "poultry"]),
    ("dairy",       ["milk", "yogurt", "yoghurt", "cheese", "cottage",
                     "cream", "butter", "dairy", "kefir", "whey"]),
    ("beans",       ["bean", "lentil", "tofu", "soy", "chickpea", "edamame",
                     "hummus", "pea", "legume", "tempeh"]),
    ("fruits",      ["apple", "banana", "orange", "mango", "berry", "berries",
                     "kiwi", "grape", "melon", "peach", "pear", "plum",
                     "cherry", "papaya", "pineapple", "strawberr", "blueberr",
                     "raspberr", "watermelon", "avocado", "lemon", "lime",
                     "grapefruit", "apricot", "fig", "date", "guava"]),
    ("vegetables",  ["carrot", "spinach", "broccoli", "kale", "tomato",
                     "cucumber", "celery", "capsicum", "bell pepper", "pepper",
                     "zucchini", "eggplant", "pumpkin", "sweet potato",
                     "potato", "beetroot", "beet", "cabbage", "lettuce",
                     "corn", "peas", "asparagus", "cauliflower", "mushroom",
                     "onion", "garlic", "ginger", "vegetable", "veggie"]),
    ("grains",      ["oat", "oatmeal", "whole grain", "bread", "wheat",
                     "barley", "rye", "quinoa", "millet", "cereal",
                     "granola", "cracker", "toast", "grain"]),
    ("rice",        ["rice", "congee", "risotto"]),
    ("noodles",     ["noodle", "pasta", "spaghetti", "udon", "soba",
                     "vermicelli", "ramen", "pho", "fettuccine", "linguine"]),
    ("snacks",      ["chip", "crisp", "candy", "chocolate", "cookie",
                     "cake", "ice cream", "muffin", "fries", "donut",
                     "pastry", "biscuit", "popcorn", "pretzel", "wafer",
                     "snack", "sweet", "lolly", "lollipop", "gummy"]),
    ("drinks",      ["soda", "juice", "milkshake", "smoothie", "drink",
                     "water", "tea", "lemonade", "coconut water"]),
    ("sauces",      ["sauce", "dressing", "dip", "gravy", "ketchup",
                     "mayonnaise", "mayo", "syrup", "spread", "jam", "jelly"]),
    ("mixed_dishes",["soup", "stew", "curry", "stir fry", "stir-fry",
                     "salad", "wrap", "sandwich", "dumpling", "spring roll",
                     "porridge", "casserole", "bowl", "fried rice",
                     "fried noodle"]),
]


def infer_category(food_name: str) -> str:
    """Return the best-matching category for a food name, or 'mixed_dishes'."""
    name = food_name.lower()
    for category, keywords in _CATEGORY_RULES:
        for kw in keywords:
            if kw in name:
                return category
    return "mixed_dishes"


def slugify(text: str) -> str:
    """Convert food name to a url-safe slug for use as food_id."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def enrich_recommendation_items(items: list[dict]) -> list[EnrichedFoodItem]:
    """
    Convert raw model output items [{food, reason}] into EnrichedFoodItem objects.

    - food_id   : slugified food_name
    - category  : inferred from food_name keywords
    - image_url : /static/category_fallback/{category}.png
    - image_status: "fallback" (async generation not yet implemented)
    """
    enriched: list[EnrichedFoodItem] = []
    for item in items:
        food_name = str(item.get("food", "")).strip()
        reason    = str(item.get("reason", "")).strip()
        if not food_name:
            continue
        category = infer_category(food_name)
        metadata_url = _find_metadata_image(food_name)
        if metadata_url:
            # Priority 1: pre-existing photo from clean_food_metadata.json
            image_url    = metadata_url
            image_status = "ready"
        else:
            cached = get_cached_image(food_name)
            if cached:
                # Priority 2: previously AI-generated image (on-disk cache)
                image_url    = cached["image_url"]
                image_status = "ready"
            else:
                # Priority 3: category-level static fallback
                image_url    = get_category_fallback_image(category)
                image_status = "fallback"
        enriched.append(
            EnrichedFoodItem(
                food_id      = slugify(food_name),
                food_name    = food_name,
                category     = category,
                image_url    = image_url,
                image_status = image_status,
                reason       = reason,
            )
        )
    return enriched
