"""
Rule-based candidate facts and lightweight food classification helpers.

This module intentionally stores only factual candidate metadata.
Human-friendly wording is produced later by the LLM rewrite step.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

TARGET_ALTERNATIVE_COUNT = 2

_LEADING_EMOJI_RE = re.compile(r"^[^\w]+")
_MULTISPACE_RE = re.compile(r"\s+")

_CATEGORY_KEYWORDS = {
    "drink": [
        "cola", "coke", "soda", "soft drink", "bubble tea", "milk tea",
        "juice", "drink", "tea", "coffee", "smoothie", "shake", "slush",
        "lemonade", "water",
    ],
    "snack": [
        "chips", "crisps", "cracker", "cookies", "cookie", "snack",
        "popcorn", "nachos", "pretzel", "granola bar", "bar",
    ],
    "dessert": [
        "cake", "donut", "doughnut", "pastry", "ice cream", "pudding",
        "brownie", "muffin", "cupcake", "waffle", "sweet bun",
    ],
    "fast_food": [
        "burger", "pizza", "hot dog", "fries", "fried chicken", "nuggets",
        "ramen", "instant noodles", "fried noodles",
    ],
    "fruit": [
        "apple", "banana", "orange", "berries", "berry", "fruit",
        "grapes", "mango", "pear", "kiwi", "melon",
    ],
    "vegetable": [
        "salad", "broccoli", "vegetable", "carrot", "spinach",
        "cucumber", "tomato",
    ],
    "dairy": [
        "milk", "yoghurt", "yogurt", "cheese",
    ],
    "meal": [
        "sandwich", "rice", "pasta", "noodles", "wrap", "bowl", "meal",
    ],
}

_COMPATIBLE_TARGET_CATEGORIES = {
    "drink": {"drink", "dairy"},
    "snack": {"snack", "fruit", "dairy"},
    "dessert": {"dessert", "fruit", "dairy", "drink"},
    "fast_food": {"meal", "snack", "fruit", "vegetable", "dairy"},
    "fruit": {"fruit", "dairy", "snack"},
    "vegetable": {"vegetable", "fruit", "dairy", "snack"},
    "dairy": {"dairy", "fruit", "snack", "drink"},
    "meal": {"meal", "vegetable", "fruit", "dairy"},
    "general": {"drink", "snack", "fruit", "vegetable", "dairy", "meal"},
}

_UNHEALTHY_KEYWORDS = {
    "cola",
    "coke",
    "soda",
    "cake",
    "candy",
    "fried",
    "fries",
    "pastry",
    "donut",
    "doughnut",
    "ice cream",
    "milk tea",
    "bubble tea",
    "syrup",
    "chocolate bar",
}

_HIGH_RISK_RULES = [
    {
        "id": "sugary_drinks",
        "trigger_keywords": ["cola", "coke", "soda", "soft drink", "milk tea", "bubble tea"],
        "source_category": "drink",
        "candidate_facts": [
            {
                "name": "Sparkling Water with Lemon",
                "candidate_category": "drink",
                "reason_tags": ["lower_sugar", "hydrating"],
                "experience_tags": ["fizzy", "refreshing"],
            },
            {
                "name": "Plain Milk",
                "candidate_category": "dairy",
                "reason_tags": ["less_processed", "calcium", "protein"],
                "experience_tags": ["smooth", "filling"],
            },
            {
                "name": "Fruit-Infused Water",
                "candidate_category": "drink",
                "reason_tags": ["lower_sugar", "hydrating"],
                "experience_tags": ["fruity", "refreshing"],
            },
            {
                "name": "Unsweetened Soy Milk",
                "candidate_category": "drink",
                "reason_tags": ["less_processed", "protein"],
                "experience_tags": ["smooth", "mild"],
            },
        ],
    },
    {
        "id": "fried_or_packaged_snacks",
        "trigger_keywords": ["chips", "crisps", "fries", "cracker", "nachos", "snack"],
        "source_category": "snack",
        "candidate_facts": [
            {
                "name": "Apple Slices with Nut Butter",
                "candidate_category": "fruit",
                "reason_tags": ["more_fibre", "healthy_fats"],
                "experience_tags": ["sweet", "crunchy"],
            },
            {
                "name": "Plain Popcorn",
                "candidate_category": "snack",
                "reason_tags": ["less_oily", "whole_grain"],
                "experience_tags": ["crunchy", "fun"],
            },
            {
                "name": "Yoghurt with Berries",
                "candidate_category": "dairy",
                "reason_tags": ["protein", "calcium", "less_processed"],
                "experience_tags": ["creamy", "sweet"],
            },
            {
                "name": "Roasted Chickpeas",
                "candidate_category": "snack",
                "reason_tags": ["protein", "more_fibre"],
                "experience_tags": ["crunchy", "savory"],
            },
        ],
    },
    {
        "id": "sweet_treats",
        "trigger_keywords": ["cake", "donut", "doughnut", "pastry", "brownie", "cupcake", "ice cream", "candy"],
        "source_category": "dessert",
        "candidate_facts": [
            {
                "name": "Greek Yoghurt with Fruit",
                "candidate_category": "dairy",
                "reason_tags": ["protein", "calcium", "less_added_sugar"],
                "experience_tags": ["creamy", "sweet"],
            },
            {
                "name": "Banana Oat Bites",
                "candidate_category": "snack",
                "reason_tags": ["whole_grain", "more_fibre", "less_processed"],
                "experience_tags": ["soft", "sweet"],
            },
            {
                "name": "Fruit Bowl",
                "candidate_category": "fruit",
                "reason_tags": ["vitamins", "natural_sweetness", "more_fibre"],
                "experience_tags": ["sweet", "fresh"],
            },
            {
                "name": "Frozen Yoghurt Bark",
                "candidate_category": "dessert",
                "reason_tags": ["calcium", "less_added_sugar"],
                "experience_tags": ["cold", "fun"],
            },
        ],
    },
    {
        "id": "fast_food",
        "trigger_keywords": ["burger", "pizza", "hot dog", "fried chicken", "nuggets", "instant noodles", "ramen"],
        "source_category": "fast_food",
        "candidate_facts": [
            {
                "name": "Chicken and Veggie Wrap",
                "candidate_category": "meal",
                "reason_tags": ["lean_protein", "more_vegetables", "less_fried"],
                "experience_tags": ["savory", "filling"],
            },
            {
                "name": "Rice Bowl with Veggies",
                "candidate_category": "meal",
                "reason_tags": ["balanced_meal", "more_vegetables"],
                "experience_tags": ["warm", "filling"],
            },
            {
                "name": "Homemade Sandwich",
                "candidate_category": "meal",
                "reason_tags": ["less_processed", "balanced_meal"],
                "experience_tags": ["handheld", "savory"],
            },
            {
                "name": "Baked Potato Wedges with Yoghurt Dip",
                "candidate_category": "snack",
                "reason_tags": ["less_fried", "more_satisfying"],
                "experience_tags": ["crispy", "savory"],
            },
        ],
    },
]

_GENERIC_FALLBACK_FACTS = [
    {
        "name": "Fruit Bowl",
        "candidate_category": "fruit",
        "reason_tags": ["vitamins", "natural_sweetness", "more_fibre"],
        "experience_tags": ["fresh", "sweet"],
    },
    {
        "name": "Plain Yoghurt",
        "candidate_category": "dairy",
        "reason_tags": ["protein", "calcium", "less_processed"],
        "experience_tags": ["creamy", "mild"],
    },
    {
        "name": "Veggie Sticks with Hummus",
        "candidate_category": "vegetable",
        "reason_tags": ["more_fibre", "less_processed"],
        "experience_tags": ["crunchy", "savory"],
    },
]


def normalize_food_name(name: str) -> str:
    text = _LEADING_EMOJI_RE.sub("", name or "").strip().lower()
    text = re.sub(r"[^a-z0-9\s-]", " ", text)
    return _MULTISPACE_RE.sub(" ", text).strip()


def clean_food_name_for_image(name: str) -> str:
    cleaned = _LEADING_EMOJI_RE.sub("", name or "").strip()
    cleaned = re.sub(r"[^\w\s-]", " ", cleaned)
    cleaned = _MULTISPACE_RE.sub(" ", cleaned).strip()
    return cleaned or "healthy food"


def infer_food_category(food_name: str) -> str:
    normalized = normalize_food_name(food_name)
    for category, keywords in _CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in normalized:
                return category
    return "general"


def is_compatible_category(source_category: str, candidate_category: str) -> bool:
    allowed = _COMPATIBLE_TARGET_CATEGORIES.get(source_category or "general", _COMPATIBLE_TARGET_CATEGORIES["general"])
    return candidate_category in allowed


def contains_unhealthy_keyword(text: str) -> bool:
    normalized = normalize_food_name(text)
    return any(keyword in normalized for keyword in _UNHEALTHY_KEYWORDS)


def match_rule_profile(food_name: str) -> Optional[Dict[str, Any]]:
    normalized = normalize_food_name(food_name)
    for profile in _HIGH_RISK_RULES:
        if any(keyword in normalized for keyword in profile["trigger_keywords"]):
            return profile
    return None


def get_rule_based_candidates(food_name: str, limit: int = 4) -> List[Dict[str, Any]]:
    profile = match_rule_profile(food_name)
    if not profile:
        return []
    candidates: List[Dict[str, Any]] = []
    for fact in profile["candidate_facts"][:limit]:
        candidate = dict(fact)
        candidate["source"] = "rule"
        candidate["source_rule"] = profile["id"]
        candidate["source_category"] = profile["source_category"]
        candidates.append(candidate)
    return candidates


def get_fallback_candidate_facts(limit: int = TARGET_ALTERNATIVE_COUNT) -> List[Dict[str, Any]]:
    return [dict(fact, source="fallback", source_rule="generic_fallback") for fact in _GENERIC_FALLBACK_FACTS[:limit]]


def build_candidate_fact(
    name: str,
    description: str = "",
    candidate_category: Optional[str] = None,
    source: str = "rag",
) -> Dict[str, Any]:
    category = candidate_category or infer_food_category(name)
    combined = f"{name} {description}".lower()
    reason_tags: List[str] = []
    experience_tags: List[str] = []

    if any(word in combined for word in ["water", "sparkling", "drink", "tea", "milk"]):
        reason_tags.extend(["lower_sugar", "hydrating"])
    if any(word in combined for word in ["fruit", "apple", "banana", "berry", "berries"]):
        reason_tags.extend(["vitamins", "more_fibre", "natural_sweetness"])
    if any(word in combined for word in ["yoghurt", "yogurt", "milk", "cheese"]):
        reason_tags.extend(["protein", "calcium"])
    if any(word in combined for word in ["oat", "whole grain", "brown rice", "chickpea"]):
        reason_tags.extend(["whole_grain", "more_fibre"])
    if any(word in combined for word in ["baked", "roasted"]):
        reason_tags.append("less_fried")
    if not reason_tags:
        reason_tags.extend(["less_processed", "more_nutritious"])

    if any(word in combined for word in ["sparkling", "fizzy"]):
        experience_tags.append("fizzy")
    if any(word in combined for word in ["popcorn", "chips", "sticks", "crunchy", "roasted"]):
        experience_tags.append("crunchy")
    if any(word in combined for word in ["yoghurt", "yogurt", "milk", "smoothie"]):
        experience_tags.append("creamy")
    if any(word in combined for word in ["fruit", "banana", "apple", "berries"]):
        experience_tags.append("sweet")
    if any(word in combined for word in ["water", "fresh", "refreshing", "lemon"]):
        experience_tags.append("refreshing")
    if not experience_tags:
        experience_tags.append("tasty")

    return {
        "name": name.strip(),
        "description": description.strip(),
        "candidate_category": category,
        "reason_tags": list(dict.fromkeys(reason_tags)),
        "experience_tags": list(dict.fromkeys(experience_tags)),
        "source": source,
    }
