"""
Post-generation output filter for food recommendations.

Responsibilities:
- Remove items containing global banned terms (non-child-friendly / non-halal).
- Remove items containing user blacklist or allergy terms.
- Deduplicate across sections (super_power > tiny_hero > try_less priority).

Global banned terms cover only categories that are universally unsafe for
children in this app: pork/derivatives, alcohol, caffeine/stimulants,
supplements/medical foods, and condiments/sauces.
User-specific blacklist and allergies are kept separate so the API caller
can audit which filter removed an item.
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


def _hit(term: str, text: str) -> bool:
    """
    Case-insensitive match with a leading word boundary.
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


def _is_user_filtered(item: dict, blacklist: list[str], allergies: list[str]) -> bool:
    name = _item_food_name(item)
    return any(_hit(term, name) for term in blacklist + allergies)


def _food_key(item: dict) -> str:
    return _item_food_name(item).strip()


def filter_output(
    parsed: dict | None,
    blacklist: list[str],
    allergies: list[str],
) -> dict | None:
    """
    Apply global banned terms, user blacklist, and allergy filters to parsed
    model output. Deduplicate across sections in priority order.

    Returns a new dict with the same structure; each section is always a list.
    Returns None if parsed is None.
    """
    if parsed is None:
        return None

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
            if _is_user_filtered(item, blacklist, allergies):
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
