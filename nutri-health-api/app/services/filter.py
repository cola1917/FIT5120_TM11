"""
Post-generation output filter for food recommendations.

Responsibilities:
- Remove items containing global banned terms (non-child-friendly / non-halal).
- Remove items matching user blacklist or allergy terms via canonical expansion.
- Deduplicate across sections (super_power > tiny_hero > try_less priority).

Blacklist filtering uses a three-layer approach:
  1. Infer the food item's category (via enrichment.infer_category).
  2. Check if the category is in the term's forbidden categories.
  3. Check if the food name contains any of the term's forbidden keywords.

This ensures category-level terms like "seafood" correctly block specific foods
like salmon, tuna, shrimp, crab even when those words don't contain "seafood".
"""

from __future__ import annotations

import re

from app.services.enrichment import infer_category

# ─── Global banned terms ─────────────────────────────────────────────────────
# Only non-child-friendly or non-halal categories.
# Do NOT add healthy foods here — the model decides what is healthy.

GLOBAL_BANNED_TERMS: list[str] = [
    # pork and derivatives
    "pork", "bacon", "ham", "pepperoni", "salami", "prosciutto", "lard",
    # alcohol
    "alcohol", "wine", "beer", "vodka", "rum", "whiskey", "liquor",
    # caffeine / stimulants
    "coffee", "caffeine", "energy drink",
    # medical / special foods not suitable for children
    "supplement", "baby formula", "medical food",
    # condiments and sauces (not food recommendations)
    "sauce", "dressing", "dip", "gravy", "ketchup", "mayonnaise", "mayo",
    "syrup", "spread",
]

_SECTION_ORDER = ["super_power_foods", "tiny_hero_foods", "try_less_foods"]

# Generic category-level names that are not specific foods.
_GENERIC_FOOD_NAMES: frozenset[str] = frozenset({
    "fish", "meat", "dairy", "vegetables", "vegetable", "fruits", "fruit",
    "grains", "grain", "protein", "seafood", "legumes",
    "food", "meal", "dish",
})

# ─── Canonical blacklist expansion ───────────────────────────────────────────
# Each user-facing blacklist/allergy term maps to:
#   categories: set of infer_category() labels to block
#   keywords:   set of food-name keywords to block (word-boundary matched)
#
# Unknown terms not listed here fall back to raw keyword matching.

_BLACKLIST_CANONICAL: dict[str, dict[str, set[str]]] = {
    "seafood": {
        "categories": {"fish", "shellfish"},
        "keywords": {
            "seafood",
            "fish", "salmon", "tuna", "cod", "mackerel", "sardine", "tilapia",
            "trout", "herring", "anchovy", "snapper", "halibut", "seabass", "carp",
            "shrimp", "prawn", "crab", "lobster", "squid", "octopus", "clam",
            "oyster", "mussel", "scallop",
        },
    },
    "meat": {
        "categories": {"meat"},
        "keywords": {
            "chicken", "beef", "lamb", "turkey", "duck", "venison",
            "bison", "veal", "meat", "poultry",
            "sausage", "ham", "bacon", "meatball", "nugget", "nuggets",
            "pepperoni", "salami",
        },
    },
    "dairy": {
        "categories": {"dairy"},
        "keywords": {
            "milk", "cheese", "yogurt", "yoghurt", "cream", "butter",
            "ghee", "kefir", "whey", "cottage",
        },
    },
    "milk": {
        "categories": {"dairy"},
        "keywords": {
            "milk", "cheese", "yogurt", "yoghurt", "cream", "butter",
            "ghee", "kefir", "whey", "cottage",
        },
    },
    "egg": {
        "categories": {"eggs"},
        "keywords": {"egg", "eggs"},
    },
    "nuts": {
        "categories": {"nuts"},
        "keywords": {
            "nut", "peanut", "almond", "cashew", "walnut", "pistachio",
            "hazelnut", "pecan", "macadamia", "chestnut",
        },
    },
    "pork": {
        "categories": set(),
        "keywords": {
            "pork", "bacon", "ham", "pepperoni", "salami", "prosciutto", "lard",
        },
    },
    "bread": {
        "categories": {"grains"},
        "keywords": {
            "bread", "toast", "bun", "baguette", "roll", "croissant", "bagel",
        },
    },
}


def resolve_forbidden(terms: list[str]) -> tuple[set[str], set[str]]:
    """
    Expand a list of blacklist/allergy terms into:
      - forbidden_categories: infer_category() labels to block
      - forbidden_keywords:   food-name keywords to block (word-boundary matched)

    Unknown terms (not in _BLACKLIST_CANONICAL) are treated as raw keywords.
    Call this once per request and pass the result to is_item_forbidden().
    """
    forbidden_cats: set[str] = set()
    forbidden_kws: set[str] = set()
    for term in terms:
        t = term.lower().strip()
        entry = _BLACKLIST_CANONICAL.get(t)
        if entry:
            forbidden_cats.update(entry["categories"])
            forbidden_kws.update(entry["keywords"])
        else:
            forbidden_kws.add(t)
    return forbidden_cats, forbidden_kws


def _hit(term: str, text: str) -> bool:
    """
    Case-insensitive word-boundary match.
    - 'cake'   does NOT match 'pancake'
    - 'cookie' DOES    match 'cookies'
    Multi-word terms use plain substring match.
    """
    t = term.lower()
    if " " in t:
        return t in text
    return bool(re.search(r"\b" + re.escape(t), text))


def _item_food_name(item: dict) -> str:
    """Extract lowercase food name from a model output item."""
    return str(item.get("food", item.get("name", ""))).lower()


def _is_globally_banned(item: dict) -> bool:
    name = _item_food_name(item)
    return any(_hit(term, name) for term in GLOBAL_BANNED_TERMS)


def _is_generic_name(item: dict) -> bool:
    """Return True if the food name is a vague category word, not a specific food."""
    return _item_food_name(item).strip() in _GENERIC_FOOD_NAMES


def is_item_forbidden(
    item: dict,
    forbidden_cats: set[str],
    forbidden_kws: set[str],
) -> bool:
    """
    Return True if item should be excluded based on pre-resolved forbidden sets.

    Priority:
      1. infer_category(food_name) in forbidden_cats
      2. any forbidden keyword word-boundary matches the food name
    """
    if not forbidden_cats and not forbidden_kws:
        return False
    name = _item_food_name(item).strip()
    if infer_category(name) in forbidden_cats:
        return True
    return any(_hit(kw, name) for kw in forbidden_kws)


def filter_candidates(
    candidates: list[dict],
    forbidden_cats: set[str],
    forbidden_kws: set[str],
) -> list[dict]:
    """
    Return only candidates that pass the forbidden sets check.
    Call this to pre-filter a pool before selection so no individual
    is_item_forbidden check is needed in the selection loop.
    """
    if not forbidden_cats and not forbidden_kws:
        return candidates
    return [c for c in candidates if not is_item_forbidden(c, forbidden_cats, forbidden_kws)]


def _is_user_filtered(item: dict, blacklist: list[str], allergies: list[str]) -> bool:
    """Convenience wrapper — resolves terms on every call. Use is_item_forbidden
    with pre-resolved sets when filtering many items in a loop."""
    forbidden_cats, forbidden_kws = resolve_forbidden(blacklist + allergies)
    return is_item_forbidden(item, forbidden_cats, forbidden_kws)


def _food_key(item: dict) -> str:
    return _item_food_name(item).strip()


def filter_output(
    parsed: dict | None,
    blacklist: list[str],
    allergies: list[str],
    forbidden_cats: set[str] | None = None,
    forbidden_kws: set[str] | None = None,
) -> dict | None:
    """
    Apply global banned terms, user blacklist, and allergy filters to parsed
    model output. Deduplicate across sections in priority order.

    Pass pre-resolved forbidden_cats / forbidden_kws to avoid resolving them
    again when the caller has already called resolve_forbidden() for this request.

    Returns a new dict with the same structure; each section is always a list.
    Returns None if parsed is None.
    """
    if parsed is None:
        return None

    if forbidden_cats is None or forbidden_kws is None:
        forbidden_cats, forbidden_kws = resolve_forbidden(blacklist + allergies)

    seen: set[str] = set()
    result: dict = {k: v for k, v in parsed.items() if k not in _SECTION_ORDER}

    for section in _SECTION_ORDER:
        items = parsed.get(section, [])
        if not isinstance(items, list):
            result[section] = []
            continue

        kept = []
        for item in items:
            if _is_globally_banned(item):
                continue
            if _is_generic_name(item):
                continue
            if is_item_forbidden(item, forbidden_cats, forbidden_kws):
                continue
            key = _food_key(item)
            if key in seen:
                continue
            seen.add(key)
            kept.append(item)

        result[section] = kept

    return result


def filter_tiny_hero_by_likes(filtered: dict | None, likes: list[str]) -> dict | None:
    """
    Remove tiny_hero_foods items whose inferred category is in the likes list.

    This is a consistency filter only — no replacement foods are generated.
    Returns the same dict (mutated copy) or None if input is None.
    """
    if filtered is None or not likes:
        return filtered

    liked_set = {c.lower().strip() for c in likes}
    kept = []
    for item in filtered.get("tiny_hero_foods", []):
        food_name = str(item.get("food", item.get("name", ""))).strip()
        category = infer_category(food_name)
        if category not in liked_set:
            kept.append(item)

    return {**filtered, "tiny_hero_foods": kept}
