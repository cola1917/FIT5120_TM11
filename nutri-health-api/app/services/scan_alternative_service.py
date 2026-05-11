"""
Scan alternative suggestion service using the existing fine-tuned OpenAI model.

Replaces the RAG + Gemini rewrite pipeline for generating healthier food alternatives
in the /scan endpoint.

Flow:
  get_scan_alternatives(food_name, assessment_score, blacklist, likes, dislikes)
    → score < 3: call fine-tuned model (Task: alternative_generation)
    → parse alternatives list
    → filter global banned terms
    → filter user blacklist (hard)
    → filter user dislikes (hard)
    → fill from fallback map if < 2 remain (likes-aware ordering)
    → return [{"name": "...", "description": "..."}]
"""

from __future__ import annotations

import json
import logging
import os
import re

import openai

from app.services.alternative_rules import get_rule_based_candidates

logger = logging.getLogger(__name__)

# ─── Model config ─────────────────────────────────────────────────────────────

_MODEL       = os.getenv("OPENAI_FOOD_MODEL", "ft:gpt-4o-mini-2024-07-18:personal::Dcz8w84o")
_TEMPERATURE = 0.3   # lowered from 0.4 for more consistent output; still above recommendation (0.25) for variety
_TOP_P       = 0.9

# ─── Score → health_level mapping ────────────────────────────────────────────

_SCORE_TO_HEALTH_LEVEL: dict[int, str] = {
    1: "try_less",
    2: "sometimes",
}

# ─── Global banned terms (child-safety + halal) ───────────────────────────────

_SCAN_BANNED_TERMS: list[str] = [
    "pork", "bacon", "ham", "lard", "pepperoni", "salami",
    "alcohol", "wine", "beer", "vodka", "rum", "whiskey", "liquor",
    "coffee", "caffeine", "energy drink",
    "supplement", "baby formula", "medical food",
    "sauce", "dressing", "dip", "gravy", "ketchup",
    "mayonnaise", "mayo", "syrup", "spread",
]

# ─── Quality filter: unhealthy or vague alternative names ─────────────────────

_QUALITY_BLOCKED_TERMS: list[str] = [
    "candy", "cake", "cookie", "cookies", "muffin", "muffins",
    "ice cream", "soda", "cola", "chips", "fries", "french fries",
    "donut", "doughnut", "pastry", "brownie", "cupcake", "waffle",
    "syrup", "chocolate", "chocolate bar",
    "sweetened drink", "sweetened drinks", "energy drink",
    "sauce", "dressing", "dip", "gravy", "ketchup",
    "mayonnaise", "mayo", "spread",
]

_BROAD_CATEGORY_TERMS: frozenset[str] = frozenset({
    "fruit", "fruits", "vegetable", "vegetables", "protein",
    "healthy snack", "drink", "drinks",
})

# Single raw ingredients that are too vague on their own as alternatives
_SINGLE_RAW_INGREDIENTS: frozenset[str] = frozenset({
    "mango", "banana", "apple", "orange", "grapes", "pear", "kiwi",
    "strawberry", "strawberries", "blueberry", "blueberries", "berries",
    "yogurt", "yoghurt", "milk", "cheese", "egg", "eggs",
    "rice", "oats", "bread", "potato", "carrot", "spinach",
    "chicken", "fish", "tofu", "nuts", "almonds", "water",
})

# ─── Generic fallback when rules also produce nothing ─────────────────────────

_GENERIC_FALLBACK: list[dict] = [
    {
        "name": "Yogurt with Berries",
        "description": "Creamy and naturally sweet — great for your tummy and gives you energy to play! 🍓",
    },
    {
        "name": "Fruit Bowl",
        "description": "Full of vitamins and natural sweetness to keep you feeling great all day! 🍊",
    },
]

# ─── Per-food fallback map (used when quality filter removes too many alts) ───
# Items use alternative_reason so they go through the normal shape-output step.

_FALLBACK_MAP: dict[str, list[dict]] = {
    "candy": [
        {"name": "mango slices",  "alternative_reason": "Mango slices are naturally sweet and full of vitamins to keep you energized! 🥭✨"},
        {"name": "fresh berries", "alternative_reason": "Fresh berries are sweet, colorful, and packed with vitamins for a healthy snack! 🍓🌟"},
    ],
    "cake": [
        {"name": "banana bread",        "alternative_reason": "Banana bread is a naturally sweet treat made with real fruit — delicious and nutritious! 🍌😊"},
        {"name": "yogurt with berries", "alternative_reason": "Yogurt with berries is creamy and sweet with less sugar than cake — great for your tummy! 🍓✨"},
    ],
    "ice cream": [
        {"name": "plain yogurt with fruit", "alternative_reason": "Plain yogurt with fruit is creamy and sweet — a cool treat that's great for you! 🍓🥛"},
        {"name": "frozen banana",           "alternative_reason": "Frozen banana is naturally creamy and sweet — like ice cream but full of vitamins! 🍌❄️"},
    ],
    "cola": [
        {"name": "water with fruit slices", "alternative_reason": "Water with fruit slices is refreshing and naturally flavored — great for staying hydrated! 💧🍋"},
        {"name": "fruit smoothie",          "alternative_reason": "A fruit smoothie is sweet, creamy, and full of vitamins to keep you feeling great! 🍓🥤"},
    ],
    "soda": [
        {"name": "water with fruit slices", "alternative_reason": "Water with fruit slices is refreshing and naturally flavored — great for staying hydrated! 💧🍋"},
        {"name": "fruit smoothie",          "alternative_reason": "A fruit smoothie is sweet, creamy, and full of vitamins to keep you feeling great! 🍓🥤"},
    ],
    "chips": [
        {"name": "carrot sticks with hummus", "alternative_reason": "Carrot sticks with hummus give you the same satisfying crunch as chips, with more vitamins and a tasty dip! 🥕😊"},
        {"name": "low-salt roasted nori",     "alternative_reason": "Low-salt roasted nori is light, crispy, and savoury — just like chips but way better for you! 🌊✨"},
    ],
    "fries": [
        {"name": "sweet potato fries",   "alternative_reason": "Sweet potato fries are crispy and naturally sweet — a tastier, healthier choice! 🍠✨"},
        {"name": "baked potato wedges",  "alternative_reason": "Baked potato wedges give you the same crunch without the extra oil! 🥔😊"},
    ],
    "french fries": [
        {"name": "sweet potato fries",   "alternative_reason": "Sweet potato fries are crispy and naturally sweet — a tastier, healthier choice! 🍠✨"},
        {"name": "baked potato wedges",  "alternative_reason": "Baked potato wedges give you the same crunch without the extra oil! 🥔😊"},
    ],
    "burger": [
        {"name": "whole-grain chicken sandwich", "alternative_reason": "A whole-grain chicken sandwich gives you protein and fiber to keep you full and strong! 🐔🌾"},
        {"name": "whole-grain fish sandwich",    "alternative_reason": "A whole-grain fish sandwich is rich in healthy fats and great for your brain! 🐟🌾"},
        {"name": "rice bowl with vegetables",    "alternative_reason": "A rice bowl with veggies is hearty and satisfying — just like a burger but way more nutritious! 🍚🥦"},
        {"name": "tofu rice bowl",               "alternative_reason": "A tofu rice bowl is filling and packed with plant-based protein to keep you going! 🍚✨"},
    ],
    "cheeseburger": [
        {"name": "whole-grain chicken sandwich", "alternative_reason": "A whole-grain chicken sandwich gives you protein and fiber to keep you full and strong! 🐔🌾"},
        {"name": "veggie burger",                "alternative_reason": "A veggie burger is a tasty plant-based option packed with fiber and goodness! 🥦🌾"},
    ],
    "hamburger": [
        {"name": "whole-grain chicken sandwich", "alternative_reason": "A whole-grain chicken sandwich gives you protein and fiber to keep you full and strong! 🐔🌾"},
        {"name": "whole-grain fish sandwich",    "alternative_reason": "A whole-grain fish sandwich is rich in healthy fats and great for your brain! 🐟🌾"},
    ],
    "instant noodles": [
        {"name": "noodle soup with vegetables",   "alternative_reason": "Noodle soup with vegetables is warm, filling, and packed with nutrients! 🍜🥦"},
        {"name": "whole-grain noodles with egg",  "alternative_reason": "Whole-grain noodles with egg give you energy and protein to stay active! 🍝🥚"},
    ],
    "fried chicken": [
        {"name": "grilled chicken wrap",       "alternative_reason": "A grilled chicken wrap has the same great taste with less oil and more veggies! 🌯🥗"},
        {"name": "chicken rice bowl",          "alternative_reason": "A chicken rice bowl is a balanced meal with protein and carbs to keep you going! 🍚🐔"},
        {"name": "tofu stir-fry with vegetables", "alternative_reason": "Tofu stir-fry gives you that satisfying crispy texture with healthy veggies instead of frying! 🥦✨"},
        {"name": "vegetable rice bowl",        "alternative_reason": "A veggie rice bowl is filling, colourful, and packed with vitamins to keep you energised! 🍚🥦"},
    ],
    "chocolate cookie": [
        {"name": "banana bread",        "alternative_reason": "Banana bread satisfies your sweet tooth with natural fruit sweetness — no extra sugar needed! 🍌😊"},
        {"name": "yogurt with berries", "alternative_reason": "Yogurt with berries gives you creamy sweetness plus vitamins for a great snack! 🍓✨"},
    ],
    "cookie": [
        {"name": "banana oat bites",    "alternative_reason": "Banana oat bites are chewy, naturally sweet, and full of energy to keep you going! 🍌🌾"},
        {"name": "yogurt with berries", "alternative_reason": "Yogurt with berries gives you creamy sweetness plus vitamins for a great snack! 🍓✨"},
    ],
    "donut": [
        {"name": "banana bread",           "alternative_reason": "Banana bread is soft, naturally sweet, and made with real fruit — a much better treat! 🍌😊"},
        {"name": "fruit salad with honey", "alternative_reason": "Fruit salad with a drizzle of honey is sweet, fresh, and full of vitamins! 🍓🍯"},
    ],
    "doughnut": [
        {"name": "banana bread",           "alternative_reason": "Banana bread is soft, naturally sweet, and made with real fruit — a much better treat! 🍌😊"},
        {"name": "fruit salad with honey", "alternative_reason": "Fruit salad with a drizzle of honey is sweet, fresh, and full of vitamins! 🍓🍯"},
    ],
    "pastry": [
        {"name": "whole-grain toast with nut butter", "alternative_reason": "Whole-grain toast with nut butter gives you lasting energy and healthy fats to power your day! 🍞🥜"},
        {"name": "banana oat bites",                  "alternative_reason": "Banana oat bites are chewy, naturally sweet, and packed with energy! 🍌🌾"},
    ],
    "milk tea": [
        {"name": "plain milk with a dash of honey", "alternative_reason": "Plain milk with a touch of honey is creamy, naturally sweet, and great for strong bones! 🥛🍯"},
        {"name": "fruit smoothie",                  "alternative_reason": "A fruit smoothie is refreshing, sweet, and packed with vitamins to keep you energized! 🍓🥤"},
    ],
    "bubble tea": [
        {"name": "plain milk with a dash of honey", "alternative_reason": "Plain milk with a touch of honey is creamy, naturally sweet, and great for strong bones! 🥛🍯"},
        {"name": "fruit smoothie",                  "alternative_reason": "A fruit smoothie is refreshing, sweet, and packed with vitamins to keep you energized! 🍓🥤"},
    ],
    "pizza": [
        {"name": "whole-grain veggie flatbread",    "alternative_reason": "A whole-grain veggie flatbread has the same fun pizza feel with more fibre and vegetables! 🫓🥦"},
        {"name": "chicken and vegetable rice bowl", "alternative_reason": "A chicken and veggie rice bowl is a filling, balanced meal with protein and plenty of goodness! 🍚🐔"},
    ],
    "hot dog": [
        {"name": "whole-grain chicken sandwich", "alternative_reason": "A whole-grain chicken sandwich gives you protein and fibre to keep you full and strong! 🐔🌾"},
        {"name": "grilled chicken wrap",         "alternative_reason": "A grilled chicken wrap is a tasty handheld option with lean protein and vegetables! 🌯🥗"},
    ],
}

# ─── Frontend category → alternative name keyword mapper ─────────────────────
# Maps the 8 frontend preference IDs to keywords found in alternative food names.
# Order within each list matters: earlier keywords are more specific.

_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "fish":       ["fish", "salmon", "tuna", "sardine", "mackerel", "seafood", "prawn", "shrimp"],
    "meat":       ["chicken", "beef", "turkey", "lamb", "duck", "pork", "meat"],
    "dairy":      ["yogurt", "yoghurt", "milk", "cheese", "kefir"],
    "fruits":     ["fruit", "apple", "banana", "mango", "berry", "berries", "orange", "grape",
                   "melon", "peach", "pear", "kiwi", "lychee", "watermelon"],
    "vegetables": ["vegetable", "veggie", "carrot", "broccoli", "spinach", "cucumber",
                   "tomato", "lettuce", "celery", "cabbage", "corn", "pea"],
    "noodles":    ["noodle", "pasta", "spaghetti", "vermicelli", "ramen", "udon"],
    "rice":       ["rice", "congee", "porridge", "risotto"],
    "bread":      ["bread", "toast", "wrap", "flatbread", "sandwich", "bun", "roll", "pita"],
}


def infer_alternative_category(name: str) -> str | None:
    """
    Map an alternative food name to one of the 8 frontend preference categories.
    Returns None if no category can be inferred.

    Priority order: fish > meat > dairy > fruits > vegetables > noodles > rice > bread
    (protein-first, since a 'chicken rice bowl' should map to meat not rice)
    """
    lower = name.lower()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return category
    return None


# ─── Scan-specific system prompt ─────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are a child-friendly healthy eating assistant for children aged 7-12.
Your task is to suggest healthier food alternatives when a child scans an unhealthy food.

Output rules:
- Return valid JSON only.
- Output exactly 2 specific food alternatives in the "alternatives" array.
- Each alternative must have "name" (a specific food, NOT a broad category like "fruit", \
"vegetable", "healthy snack", or "drink") and "alternative_reason" (one sentence explaining \
why this food is a good swap, child-friendly, with 1-2 emojis).
- "name" must be a complete, specific food or dish (e.g. "banana oat bites", \
"frozen yogurt with berries", "carrot sticks with hummus") — NOT a single raw ingredient \
like "mango", "banana", "yogurt", "milk", or "apple" alone.
- "alternative_reason" must explain both why this alternative is healthier AND how it \
satisfies a similar craving or eating occasion as the original food (e.g. same crunch, \
same sweetness, same handheld feel, same refreshing quality). Do NOT write a generic \
nutrition statement — make the connection to the original food's appeal obvious.
- Choose alternatives in the same eating context: snack stays snack or fruit, \
drink stays drink or dairy, dessert stays light dessert or fruit, \
meal stays a balanced meal option.
- Do not mention calories.
- Do not use medical jargon.
- Do not recommend pork, bacon, ham, alcohol, caffeine drinks, supplements, baby formula, \
medical foods, sauces, or condiments as alternatives.
- Do not recommend another junk food, candy, cake, cookie, ice cream, donut, or pastry \
as an alternative — even if the original food is also a sweet or junk food.

Context-matching rules:
- Alternatives must be similar in food type, eating occasion, and texture.
- Do not replace a full meal with a single raw ingredient.
- Do not replace noodles or pasta dishes with raw vegetables only.
- Do not replace burgers or sandwiches with plain meat or plain fish only.
- Prefer complete child-friendly alternatives (a dish or a food combination).

Examples of good context-matched alternatives (notice how each reason links back to the original food's appeal):
Food: chips → alternatives: carrot sticks with hummus (reason: "same satisfying crunch as chips, with a tasty dip"), low-salt roasted nori (reason: "light and crispy just like chips but way better for you")
Food: burger → alternatives: whole-grain chicken sandwich (reason: "same handheld, savoury feel as a burger"), veggie burger (reason: "gives you the burger experience with more fibre")
Food: instant noodles → alternatives: noodle soup with vegetables (reason: "warm and slurpy just like noodles, with real veggies added"), whole-grain noodles with egg (reason: "same comforting noodle feel with more protein")
Food: ice cream → alternatives: plain yogurt with fruit (reason: "cold, creamy, and sweet — just like ice cream"), frozen banana (reason: "naturally creamy and sweet when frozen — like ice cream but full of vitamins")
Food: cake → alternatives: banana bread (reason: "soft and sweet like cake but made with real fruit"), yogurt with berries (reason: "satisfies the same sweet craving with less sugar")
Food: fried chicken → alternatives: grilled chicken wrap (reason: "same savoury chicken flavour without the heavy frying"), chicken rice bowl (reason: "filling and satisfying like fried chicken, but lighter")
Food: soda → alternatives: fruit-infused water (reason: "refreshing and fizz-free with real fruit flavour"), plain milk (reason: "cold and satisfying to drink, with calcium instead of sugar")

Output schema:
{
  "original_food": "...",
  "alternatives": [
    {"name": "...", "alternative_reason": "..."},
    {"name": "...", "alternative_reason": "..."}
  ]
}"""


# ─── Burger keyword detection ────────────────────────────────────────────────

_BURGER_KEYWORDS = {"burger", "cheeseburger", "hamburger"}


def _is_burger(food_name: str) -> bool:
    return any(kw in food_name.lower() for kw in _BURGER_KEYWORDS)


# ─── Prompt builder ───────────────────────────────────────────────────────────

_BURGER_GUIDANCE = """\

Item-specific guidance for burger / cheeseburger / hamburger:
- Alternatives must be burger-like or sandwich-like.
- Prefer: whole-grain chicken sandwich, whole-grain fish sandwich, \
lean beef sandwich, veggie burger.
- Do not return plain chicken, plain fish, or unrelated meals.
- Do not recommend turkey burger.
- Do not recommend sauces or condiments."""


def build_alternative_prompt(food_name: str, health_level: str) -> str:
    """
    Build user prompt matching the fine-tuned model's training format.
    Appends item-specific guidance for burger-type foods.
    """
    base = (
        f"Task: alternative_generation\n"
        f"Food: {food_name}\n"
        f"Health level: {health_level}\n"
        f"Question: What is a healthier alternative to this food for a child?"
    )
    if _is_burger(food_name):
        base += _BURGER_GUIDANCE
    return base


# ─── Model call ───────────────────────────────────────────────────────────────

def _build_system_prompt(
    blacklist: list[str],
    likes: list[str],
    dislikes: list[str],
) -> str:
    """Return system prompt with user preference context appended."""
    extra: list[str] = []
    if blacklist:
        extra.append(
            "User blacklist (never suggest any of these, not even as part of a dish name): "
            + ", ".join(blacklist)
        )
    if likes:
        extra.append(
            "User prefers food from these groups: "
            + ", ".join(likes)
            + " — when multiple suitable alternatives exist, prefer these categories."
        )
    if dislikes:
        extra.append(
            "User dislikes food from these groups: "
            + ", ".join(dislikes)
            + " — avoid suggesting alternatives from these categories when possible."
        )
    if not extra:
        return _SYSTEM_PROMPT
    return _SYSTEM_PROMPT + "\n\n" + "\n".join(extra)


def _is_blacklisted(name: str, blacklist: list[str]) -> bool:
    """Return True if the alternative name contains any user blacklist term."""
    lower = name.lower()
    for term in blacklist:
        t = term.lower().strip()
        if not t:
            continue
        if " " in t:
            if t in lower:
                return True
        else:
            if re.search(r"\b" + re.escape(t), lower):
                return True
    return False


def call_alternative_model(
    food_name: str,
    health_level: str,
    blacklist: list[str] | None = None,
    likes: list[str] | None = None,
    dislikes: list[str] | None = None,
) -> str:
    """Call the fine-tuned model synchronously. Returns raw response string."""
    api_key = os.getenv("OPENAI_API_KEY")
    client  = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model       = _MODEL,
        temperature = _TEMPERATURE,
        top_p       = _TOP_P,
        messages    = [
            {"role": "system", "content": _build_system_prompt(blacklist or [], likes or [], dislikes or [])},
            {"role": "user",   "content": build_alternative_prompt(food_name, health_level)},
        ],
    )
    return response.choices[0].message.content or ""


# ─── Parser ───────────────────────────────────────────────────────────────────

def parse_alternative_output(raw: str) -> dict | None:
    """
    Parse model output JSON. Returns dict with "alternatives" list or None.
    Strips markdown fences if present.
    """
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:] if lines[0].startswith("```") else lines
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None

    if not isinstance(parsed, dict):
        return None
    alts = parsed.get("alternatives")
    if not isinstance(alts, list) or len(alts) == 0:
        return None
    # Each item must have name and alternative_reason
    for item in alts:
        if not isinstance(item, dict):
            return None
        if not item.get("name") or not item.get("alternative_reason"):
            return None
    return parsed


# ─── Filter ───────────────────────────────────────────────────────────────────

def _is_banned(name: str) -> bool:
    """Return True if a food name contains a globally banned term."""
    lower = name.lower()
    for term in _SCAN_BANNED_TERMS:
        if " " in term:
            if term in lower:
                return True
        else:
            if re.search(r"\b" + re.escape(term), lower):
                return True
    return False


def filter_alternatives(alternatives: list[dict]) -> list[dict]:
    """Remove alternatives whose name contains a global banned term."""
    return [a for a in alternatives if not _is_banned(a.get("name", ""))]


def _is_single_raw_ingredient(name: str) -> bool:
    """Return True if the name is a single raw ingredient with no preparation context."""
    lower = name.lower().strip()
    # Only flag single-token names (multi-word names like "yogurt with berries" are fine)
    if " " in lower:
        return False
    return lower in _SINGLE_RAW_INGREDIENTS


def _is_quality_blocked(name: str) -> bool:
    """Return True if a name is unhealthy junk food, a broad vague category, or a single raw ingredient."""
    lower = name.lower().strip()
    if lower in _BROAD_CATEGORY_TERMS:
        return True
    if _is_single_raw_ingredient(lower):
        return True
    for term in _QUALITY_BLOCKED_TERMS:
        if " " in term:
            if term in lower:
                return True
        else:
            if re.search(r"\b" + re.escape(term) + r"\b", lower):
                return True
    return False


def filter_quality_alternatives(alternatives: list[dict]) -> list[dict]:
    """Remove alternatives whose name is a junk food or broad category."""
    return [a for a in alternatives if not _is_quality_blocked(a.get("name", ""))]


def _fill_from_fallback_map(
    food_name: str,
    existing_alts: list[dict],
    target: int = 2,
    blacklist: list[str] | None = None,
    likes: list[str] | None = None,
    dislikes: list[str] | None = None,
) -> list[dict]:
    """
    Fill up to `target` items using _FALLBACK_MAP when quality filter leaves
    fewer than needed. Candidates are quality-checked, blacklist-filtered, and
    sorted so liked categories come first.
    """
    if len(existing_alts) >= target:
        return existing_alts[:target]

    food_lower = food_name.lower().strip()
    candidates = _FALLBACK_MAP.get(food_lower, [])

    # Partial-match fallback: e.g. "chocolate chip cookie" -> "cookie" key
    if not candidates:
        for key, items in _FALLBACK_MAP.items():
            if key in food_lower:
                candidates = items
                break

    existing_names = {a.get("name", "").lower() for a in existing_alts}
    bl = blacklist or []
    liked = set(likes or [])
    disliked = set(dislikes or [])

    eligible: list[dict] = []
    for cand in candidates:
        name = cand.get("name", "")
        if name.lower() in existing_names:
            continue
        if _is_quality_blocked(name):
            continue
        if bl and _is_blacklisted(name, bl):
            continue
        cat = infer_alternative_category(name)
        if disliked and cat in disliked:
            continue
        eligible.append(cand)

    # Liked categories first, then neutral
    if liked:
        eligible.sort(key=lambda c: 0 if infer_alternative_category(c.get("name", "")) in liked else 1)

    result = list(existing_alts) + eligible
    return result[:target]


def _filter_dislikes(alts: list[dict], dislikes: list[str]) -> list[dict]:
    """
    Hard-filter alternatives whose inferred category is in the dislikes list.
    If all alternatives are disliked, returns empty list — caller fills from fallback.
    """
    if not dislikes:
        return alts
    disliked = set(dislikes)
    return [a for a in alts if infer_alternative_category(a.get("name", "")) not in disliked]


# ─── Burger post-parse cleanup ───────────────────────────────────────────────

# Maps exact (lowercased) names that the model outputs for burger to better alternatives.
_BURGER_NAME_REPLACEMENTS: dict[str, str] = {
    "chicken":       "whole-grain chicken sandwich",
    "fish":          "whole-grain fish sandwich",
    "turkey burger": "whole-grain chicken sandwich",
}

# Names that are acceptable for burger but only kept if no burger-like alternative exists.
_BURGER_WRAP_ONLY_NAMES = {"chicken wrap"}

# Names considered burger-like (no replacement needed).
_BURGER_LIKE = {"whole-grain chicken sandwich", "whole-grain fish sandwich",
                "lean beef sandwich", "veggie burger"}


def _cleanup_burger_alternatives(
    food_name: str,
    alternatives: list[dict],
) -> list[dict]:
    """
    Post-parse cleanup applied only when the scanned food is burger-type.
    Replaces plain/unwanted names with burger-like equivalents.
    """
    if not _is_burger(food_name):
        return alternatives

    cleaned: list[dict] = []
    has_burger_like = any(
        a.get("name", "").lower() in _BURGER_LIKE for a in alternatives
    )

    for alt in alternatives:
        name       = alt.get("name", "").strip()
        name_lower = name.lower()

        # Direct replacement map
        if name_lower in _BURGER_NAME_REPLACEMENTS:
            replacement = _BURGER_NAME_REPLACEMENTS[name_lower]
            logger.debug(
                "Burger cleanup: replacing %r with %r", name, replacement
            )
            cleaned.append({**alt, "name": replacement})
            continue

        # chicken wrap: keep only if no burger-like alternative already exists
        if name_lower in _BURGER_WRAP_ONLY_NAMES and has_burger_like:
            logger.debug(
                "Burger cleanup: dropping %r (burger-like alternative exists)", name
            )
            continue

        cleaned.append(alt)

    return cleaned


# ─── Fallback ─────────────────────────────────────────────────────────────────

def _fallback_alternatives(food_name: str) -> list[dict]:
    """
    Rule-based fallback when model call or parse fails.
    Uses alternative_rules.get_rule_based_candidates; falls back to generic list.
    """
    try:
        candidates = get_rule_based_candidates(food_name, limit=2)
        if candidates:
            return [
                {
                    "name": c["name"],
                    "description": "A healthier and tasty choice for you! 🌟",
                }
                for c in candidates[:2]
            ]
    except Exception as exc:
        logger.warning("Rule-based fallback failed for %r: %s", food_name, exc)

    return _GENERIC_FALLBACK[:2]


# ─── Public entry point ───────────────────────────────────────────────────────

def get_scan_alternatives(
    food_name: str,
    assessment_score: int,
    blacklist: list[str] | None = None,
    likes: list[str] | None = None,
    dislikes: list[str] | None = None,
) -> list[dict]:
    """
    Return up to 2 healthier alternatives for a scanned food.

    Returns [] for healthy foods (assessment_score >= 3).
    Returns [{name, description}, ...] for unhealthy / moderate foods.
    Falls back to rule-based candidates if the model fails.

    blacklist: hard filter — allergens/ingredients to never suggest.
    dislikes:  hard filter — disliked frontend categories are always excluded.
    likes:     preference hint — liked categories prioritised in fallback ordering.
    """
    if assessment_score >= 3:
        return []

    health_level = _SCORE_TO_HEALTH_LEVEL.get(assessment_score)
    if health_level is None:
        logger.warning("Unexpected assessment_score=%s, returning []", assessment_score)
        return []

    bl = [t.strip() for t in (blacklist or []) if t.strip()]
    lk = [t.strip() for t in (likes or []) if t.strip()]
    dl = [t.strip() for t in (dislikes or []) if t.strip()]

    # ── Model call ──
    try:
        raw    = call_alternative_model(food_name, health_level, blacklist=bl, likes=lk, dislikes=dl)
        parsed = parse_alternative_output(raw)
    except Exception as exc:
        logger.error("Model call failed for scan alternative (%r): %s", food_name, exc)
        parsed = None

    if parsed is None:
        logger.warning("Model output parse/call failed for %r, seeding from fallback map", food_name)
        # Seed alts from fallback map so blacklist/dislikes filters still apply
        alts = list(_fallback_alternatives(food_name))
    else:
        # ── Filter global banned terms ──
        alts = filter_alternatives(parsed["alternatives"])

    # ── Filter user blacklist (hard) ──
    if bl:
        before = len(alts)
        alts = [a for a in alts if not _is_blacklisted(a.get("name", ""), bl)]
        if len(alts) < before:
            logger.info("Blacklist removed %d alt(s) for %r", before - len(alts), food_name)

    # ── Burger-specific cleanup ──
    alts = _cleanup_burger_alternatives(food_name, alts)

    # ── Quality filter (remove junk food / broad-category alternatives) ──
    alts = filter_quality_alternatives(alts)

    # ── Filter user dislikes (hard) ──
    if dl:
        before = len(alts)
        alts = _filter_dislikes(alts, dl)
        if len(alts) < before:
            logger.info("Dislikes filter removed %d alt(s) for %r", before - len(alts), food_name)

    # ── Fill from fallback map if fewer than 2 remain ──
    if len(alts) < 2:
        logger.info(
            "Only %d quality alt(s) for %r after filter, filling from fallback map",
            len(alts), food_name,
        )
        alts = _fill_from_fallback_map(food_name, alts, blacklist=bl, likes=lk, dislikes=dl)

    if not alts:
        logger.warning("All alternatives filtered for %r — no alternatives to return", food_name)
        return []

    # ── Shape output ──
    return [
        {
            "name":        a["name"],
            "description": a.get("alternative_reason") or a.get("description", ""),
        }
        for a in alts[:2]
    ]
