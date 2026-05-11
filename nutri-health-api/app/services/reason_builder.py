"""
Deterministic reason builder for food recommendation items.

Generates a child-friendly, goal-aware, section-aware reason string
without any LLM, database, or network call.

Public API:
    build_personalized_reason(
        food_name, category, section_name, goal_id,
        likes=None, dislikes=None,
    ) -> str
"""

from __future__ import annotations

# ─── Goal catalogue ───────────────────────────────────────────────────────────

GOAL_INFO: dict[str, dict[str, str]] = {
    "grow":   {"label": "Grow Up",      "benefit": "support strong and steady growth"},
    "see":    {"label": "See Clear",    "benefit": "support bright eyes and clear vision"},
    "think":  {"label": "Think Fast",   "benefit": "support focus, learning, and brain power"},
    "fight":  {"label": "Fight Germs",  "benefit": "support your body's natural defenses"},
    "feel":   {"label": "Feel Good",    "benefit": "support steady energy and a balanced mood"},
    "strong": {"label": "Be Strong",    "benefit": "support muscles, strength, and active play"},
}

_DEFAULT_GOAL = GOAL_INFO["grow"]

# ─── Per-category extra benefit sentence ──────────────────────────────────────
# Store only the predicate fragment (no pronoun).
# _category_benefit(category, food_name) injects the food-level pronoun so
# "mango" (singular) in "fruits" gets "It can add..." and
# "blueberries" (plural) in "fruits" gets "They can add...".

_CATEGORY_BENEFIT: dict[str, str] = {
    "fruits":       "add natural sweetness and helpful vitamins",
    "vegetables":   "add color, crunch, and helpful nutrients",
    "fish":         "give your body helpful protein and healthy fats",
    "shellfish":    "give your body helpful protein and healthy fats",
    "dairy":        "help support strong bones and steady growth",
    "eggs":         "give your body helpful protein to keep you going",
    "meat":         "give your body protein for strength and active play",
    "beans":        "give your body plant protein and lasting energy",
    "grains":       "give you steady energy for the day",
    "rice":         "give you steady energy for the day",
    "noodles":      "give you energy, especially when paired with colorful foods",
    "snacks":       "be a fun treat to enjoy sometimes",
    "mixed_dishes": "bring together different foods in one tasty meal",
}

# Fixed sentences for categories where the "{pronoun} can {predicate}" pattern
# does not apply (the sentence stands alone regardless of food plurality).
_CATEGORY_BENEFIT_FIXED: dict[str, str] = {
    "drinks": "Staying hydrated is a great way to keep your body feeling good.",
}

# ─── Banned words guard (used in tests) ───────────────────────────────────────

BANNED_WORDS: frozenset[str] = frozenset({
    "bad", "junk", "dangerous", "unhealthy",
    "diet", "fattening", "calories",
})


# ─── Grammar helpers ──────────────────────────────────────────────────────────
#
# Plural detection rule:
#   A food name is treated as plural when its LAST WORD ends with "s"
#   but NOT "ss" (catches bass, hummus, couscous, asparagus …).
#   A small force-singular set handles remaining irregular cases.

_FORCE_SINGULAR: frozenset[str] = frozenset({
    "hummus", "asparagus", "couscous",
})


def _is_plural(name: str) -> bool:
    """
    Return True if the food name or category should use plural agreement.

    Uses the last word of the name so compound names like "steel-cut oats"
    or "chocolate chips" are handled correctly.
    """
    last = name.lower().strip().split()[-1] if name.strip() else ""
    if last in _FORCE_SINGULAR:
        return False
    return last.endswith("s") and not last.endswith("ss")


def _is_are(name: str) -> str:
    """'are' for plural names, 'is' for singular."""
    return "are" if _is_plural(name) else "is"


def _it_they(name: str) -> str:
    """'they' for plural names, 'it' for singular (lowercase)."""
    return "they" if _is_plural(name) else "it"


def _does_do(name: str) -> str:
    """'do' for plural names, 'does' for singular."""
    return "do" if _is_plural(name) else "does"


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _normalize_set(values: list[str] | None) -> set[str]:
    return {str(v).lower().strip() for v in (values or [])}


def _category_benefit(category: str, food_name: str) -> str:
    """
    Build the category benefit sentence using the food-level pronoun.

    The pronoun is derived from food_name (not category) so that
    "mango" in "fruits" → "It can add..." and
    "blueberries" in "fruits" → "They can add...".
    """
    cat = category.lower().strip()
    if cat in _CATEGORY_BENEFIT_FIXED:
        return _CATEGORY_BENEFIT_FIXED[cat]
    pronoun = _it_they(food_name).capitalize()
    predicate = _CATEGORY_BENEFIT.get(cat)
    if predicate:
        return f"{pronoun} can {predicate}."
    return f"{pronoun} can be a helpful part of your food choices."


# ─── Public API ───────────────────────────────────────────────────────────────

def build_personalized_reason(
    food_name: str,
    category: str,
    section_name: str,
    goal_id: str,
    likes: list[str] | None = None,
    dislikes: list[str] | None = None,
) -> str:
    """
    Return a deterministic, child-friendly reason string (max 3 sentences).

    section_name must be one of:
        "super_power_foods" | "tiny_hero_foods" | "try_less_foods"

    Unknown section_name values fall back to a safe generic sentence.
    Unknown goal_id values fall back to "grow".
    """
    goal      = GOAL_INFO.get(goal_id, _DEFAULT_GOAL)
    food      = food_name.strip()
    cat       = (category or "food").lower().strip()
    liked     = _normalize_set(likes)
    disliked  = _normalize_set(dislikes)

    goal_label   = goal["label"]
    goal_benefit = goal["benefit"]
    cat_sentence = _category_benefit(cat, food)

    # Grammar tokens derived from the food name
    is_are   = _is_are(food)
    it_they  = _it_they(food)
    does_do  = _does_do(food)

    # ── Super power ───────────────────────────────────────────────────────────
    if section_name == "super_power_foods":
        sentence_1 = (
            f"{food} {is_are} a great choice for {goal_label} "
            f"because {it_they} can {goal_benefit}."
        )
        sentence_2 = cat_sentence
        if cat in liked:
            sentence_3 = (
                f"Since you like {cat}, {it_they} can be an easy food to enjoy."
            )
        else:
            sentence_3 = (
                f"{it_they.capitalize()} {is_are} a strong choice for your goal."
            )
        return f"{sentence_1} {sentence_2} {sentence_3}"

    # ── Tiny hero ─────────────────────────────────────────────────────────────
    if section_name == "tiny_hero_foods":
        sentence_1 = (
            f"{food} can help with {goal_label} "
            f"because {it_they} can {goal_benefit}."
        )
        if cat in disliked:
            cat_is_are = _is_are(cat)
            sentence_2 = (
                f"Even if {cat} {cat_is_are} not your favorite, "
                f"trying a small bite is a tiny hero step."
            )
        else:
            sentence_2 = "Trying it in a fun way can be a tiny hero step."
        return f"{sentence_1} {sentence_2}"

    # ── Try less ──────────────────────────────────────────────────────────────
    if section_name == "try_less_foods":
        return (
            f"{food} can be fun sometimes, but {it_they} {does_do} not give much "
            f"steady fuel for {goal_label}. "
            f"Try choosing a Super Power food more often."
        )

    # ── Fallback (unknown section) ────────────────────────────────────────────
    return (
        f"{food} can be part of your food choices for {goal_label}. "
        f"Try it in a way that feels easy and fun."
    )
