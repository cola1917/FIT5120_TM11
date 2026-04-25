"""
Food display name helpers.

Converts raw cn_fdes descriptors (e.g. "Chicken, fried, cooked" or
"Jalapeno Cheese Sauce 6/5# 30#") into child-friendly display names.

Public API
----------
simple_display_name(descriptor)           -> basic clean name (title-cased)
contextual_display_name(descriptor)       -> preserves meaningful prep modifiers
display_name_for_section(...)             -> routes to the right function per section
normalize_display_name(descriptor)        -> lowercase + punct-stripped (for dedup)
is_challenge_suitable_by_rule(descriptor) -> False for scary / generic DB labels
is_challenge_suitable(descriptor, category, grade)  -> broader check
batch_rewrite_display_names(goal_id, items)  -> optional AI enrichment
"""

import json
import logging
import os
import re
import string

from app.config.vision_llm import get_dashscope_openai_client, get_dashscope_settings
from app.load_env import ensure_dotenv_loaded

logger = logging.getLogger(__name__)

# ── Noise patterns removed from all display names ─────────────────────────────
# Matches: ratio sizes (80/20, 6/5#), weights (12 oz, 500 g), percentages
# (3.25%), number+hash (30#), and bare # symbols.

_NOISE_RE = re.compile(
    r"\b\d+/\d+#?"                          # ratio: 80/20, 6/5#
    r"|\b\d+\.?\d*\s*(?:oz|g|kg|lb|lbs)\b"  # weight with unit: 12 oz, 500 g
    r"|\b\d+\.?\d*\s*%"                      # percentage: 3.25%
    r"|\b\d+\s*#"                            # number-hash: 30#
    r"|#",                                   # bare hash
    re.IGNORECASE,
)

# Generic processing words stripped from the *first* comma segment.
# These appear routinely in CN2026 descriptors but add no child-facing value.
_DESCRIPTOR_WORDS_RE = re.compile(
    r"\b(?:raw|cooked|dried|frozen|canned|fresh|unspecified|nos)\b",
    re.IGNORECASE,
)

# ── Contextual modifier map (order matters: longer patterns first) ─────────────
# Maps substrings found in the *second* comma segment to a display prefix.

_MODIFIER_MAP: list[tuple[str, str]] = [
    ("pasteurized process", "Processed"),
    ("reduced fat",         "Reduced-Fat"),
    ("low-fat",             "Low-Fat"),
    ("low fat",             "Low-Fat"),
    ("non-fat",             "Non-Fat"),
    ("nonfat",              "Non-Fat"),
    ("process",             "Processed"),
    ("whole",               "Whole"),
    ("fried",               "Fried"),
    ("grilled",             "Grilled"),
    ("roasted",             "Roasted"),
    ("smoked",              "Smoked"),
    ("baked",               "Baked"),
    ("boiled",              "Boiled"),
    ("steamed",             "Steamed"),
    ("dried",               "Dried"),
    ("frozen",              "Frozen"),
    ("canned",              "Canned"),
]

# ── Challenge-suitability blocklist ──────────────────────────────────────────
# Descriptors matching these patterns are excluded from Tiny Hero challenges
# because they are either too unusual for children or are generic DB labels.

_CHALLENGE_UNSUITABLE_RE = re.compile(
    r"\b(?:frog|snail|escargot|tripe|intestine|offal|organ|"
    r"liver|kidney|heart|brain|blood|marrow|thymus|spleen|tongue)\b"
    r"|mixed species|unspecified|crustaceans\b",
    re.IGNORECASE,
)

_GENERIC_NAMES_BY_CATEGORY: dict[str, set[str]] = {
    "fish": {"fish", "seafood", "shellfish", "mollusk", "mollusks", "crustacean", "crustaceans"},
    "dairy": {"dairy", "milk", "cheese"},
    "meat": {"meat", "poultry"},
    "vegetables": {"vegetable", "vegetables"},
    "fruits": {"fruit", "fruits"},
}


# ── Core helpers ──────────────────────────────────────────────────────────────

def _first_segment(descriptor: str) -> str:
    """Return the text before the first comma, stripped."""
    return descriptor.split(",")[0].strip()


def _two_segments(descriptor: str) -> str:
    """Return the first two comma segments joined, stripped."""
    parts = descriptor.split(",")
    return ", ".join(p.strip() for p in parts[:2])


def _clean_segment(text: str) -> str:
    """Remove noise and descriptor words, collapse spaces, title-case."""
    text = _NOISE_RE.sub(" ", text)
    text = _DESCRIPTOR_WORDS_RE.sub(" ", text)
    # Remove balanced parenthetical content (e.g. "(Jicama)" in "Yambean (Jicama)")
    text = re.sub(r"\(.*?\)", "", text)
    # Remove unclosed parentheses to end of string (e.g. "(Jicama" from comma split)
    text = re.sub(r"\([^)]*$", "", text)
    # Remove orphaned closing parenthesis
    text = re.sub(r"^[^(]*\)", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    # Strip leading/trailing punctuation and special characters (e.g. trailing "-")
    text = text.strip(string.punctuation + " ")
    return text.title()


def _noise_only_clean(text: str) -> str:
    """Remove only package/size noise; preserve semantic words like 'fried', 'ground'."""
    text = _NOISE_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = text.strip(string.punctuation + " ")
    return text


# ── Public display-name functions ─────────────────────────────────────────────

def simple_display_name(descriptor: str) -> str:
    """
    Return a clean, title-cased display name with no prep/package noise.

    Keeps only the first comma segment, then strips package sizes, percentages,
    ratio codes, and generic descriptor words (raw, cooked, frozen …).

    Examples
    --------
    "Jalapeno Cheese Sauce 6/5# 30#"  ->  "Jalapeno Cheese Sauce"
    "Chicken, roasted, cooked"         ->  "Chicken"
    "Milk, whole, 3.25%"               ->  "Milk"
    "Beef 80/20 raw"                   ->  "Beef"
    "apple   slices 12 oz #"           ->  "Apple Slices"
    """
    return _clean_segment(_first_segment(descriptor))


def ai_descriptor(descriptor: str) -> str:
    """
    Return a lightly cleaned descriptor for AI input.

    Keeps the first two comma segments (to preserve semantic context like
    'ground', 'fried', 'with meat') and removes only package/size noise.
    Semantic words (raw, cooked, fried…) are intentionally preserved so the
    AI can make informed naming decisions.

    Examples
    --------
    "Chili, with meat, canned"         ->  "Chili, with meat"
    "Chicken, fried, cooked"           ->  "Chicken, fried"
    "Beef, ground, 80/20, raw"         ->  "Beef, ground"
    "Milk, whole, 3.25%"               ->  "Milk, whole"
    "Corn And Edamame Blend Usda ..."  ->  "Corn And Edamame Blend Usda ..."
    """
    return _noise_only_clean(_two_segments(descriptor))


def contextual_display_name(descriptor: str) -> str:
    """
    Like simple_display_name but preserves meaningful preparation modifiers
    found in the second comma segment (e.g. "fried", "whole", "processed").

    Used for Try Less foods to make them more specific and recognisable.

    Examples
    --------
    "Chicken, fried, cooked"                 ->  "Fried Chicken"
    "Cheese, pasteurized process, American"  ->  "Processed Cheese"
    "Milk, whole, 3.25%"                     ->  "Whole Milk"
    "Salmon, smoked"                         ->  "Smoked Salmon"
    """
    segments = descriptor.split(",")
    main = _clean_segment(segments[0].strip())

    if len(segments) >= 2:
        mod_text = segments[1].strip().lower()
        for pattern, prefix in _MODIFIER_MAP:
            if pattern in mod_text:
                return f"{prefix} {main}"

    return main


def display_name_for_section(
    descriptor: str,
    section: str,
    category: str = "",
    grade: str = "",
) -> str:
    """
    Route to the appropriate display-name function based on section.

    - "try_less" -> contextual_display_name (preserves prep modifiers)
    - all others -> simple_display_name
    """
    if section == "try_less":
        return contextual_display_name(descriptor)
    return simple_display_name(descriptor)


def normalize_display_name(descriptor: str) -> str:
    """
    Return a normalized form of the display name for cross-section deduplication.

    Applies simple_display_name first so that package noise does not create
    false uniqueness, then lowercases, strips punctuation, and collapses spaces.

    "Beef, raw" and "Beef 80/20 raw" both normalize to "beef".
    "Jalapeno Cheese Sauce 6/5# 30#" normalizes to "jalapeno cheese sauce".
    """
    name = simple_display_name(descriptor).lower()
    name = name.translate(str.maketrans("", "", string.punctuation))
    name = re.sub(r"\s+", " ", name).strip()
    return name


def normalize_food_name(name: str) -> str:
    """Normalize an already display-ready food name."""
    cleaned = _clean_segment(name).lower()
    cleaned = cleaned.translate(str.maketrans("", "", string.punctuation))
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def is_generic_output_name(name: str, category: str) -> bool:
    """Return True when a display name is too category-like for final output."""
    normalized_name = normalize_food_name(name)
    normalized_category = normalize_food_name(category)
    if not normalized_name:
        return True
    if normalized_name == normalized_category:
        return True
    return normalized_name in _GENERIC_NAMES_BY_CATEGORY.get(normalized_category, set())


# ── Challenge suitability ─────────────────────────────────────────────────────

def is_challenge_suitable_by_rule(descriptor: str) -> bool:
    """
    Return False for descriptors that are too unusual, scary, or generic for
    a child-facing "Tiny Hero Challenge" (e.g. organ meats, "Frog legs",
    "Crustaceans, mixed species").
    """
    return not bool(_CHALLENGE_UNSUITABLE_RE.search(descriptor))


def is_challenge_suitable(descriptor: str, category: str, grade: str) -> bool:
    """
    Full challenge suitability check. Extends the rule-based check with
    category and grade awareness (both currently delegated to the rule check;
    callers already pre-filter the pool to grades A/B).
    """
    return is_challenge_suitable_by_rule(descriptor)


# ── AI batch display rewrite (optional enrichment) ───────────────────────────

def _unwrap_json_markdown(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _build_batch_rewrite_prompt(goal_id: str, items: list[dict]) -> str:
    payload = {"goal_id": goal_id, "items": items}
    return f"""
You rewrite food database descriptors into short, child-friendly display names.

Task:
For each item, return a concise food name for a children's nutrition app.

Rules:
- Return ONLY valid JSON.
- Do not explain.
- Do not analyze nutrition.
- Do not make allergy or safety decisions.
- Do not invent a different food.
- Remove package sizes, database codes, serving sizes, and symbols (e.g. 6/5#, 30#, 12 oz, 3.25%).
- Strip all institutional and administrative labels. These labels never belong in a
  display name and must be completely removed:
    * USDA / USDA Recipe / USDA Commodity
    * Recipe For Schools / School Recipe / School Lunch
    * Standardized Recipe / Standardized
    * WIC / CNP / NSLP or any government programme acronym
    * Any phrase of the form "For Schools", "For Institutions", "For Programs"
  Example: "Broccoli Bites Usda Recipe For Schools" -> "Broccoli Bites"
- Keep display_name 1-4 words.
- Use words a child or parent can understand.
- If section is "try_less", preserve important modifiers such as whole, fried,
  breaded, processed, sweetened, salted, cream, butter.
- If section is "super_power" or "tiny_hero", prefer simple familiar names but
  keep useful specifics like salmon, broccoli, yogurt, lean beef.
- Avoid names that are only category labels when the descriptor contains a more
  specific food.
- root_food_key must be lowercase, 1-2 words, and useful for fuzzy deduplication.

Input JSON:
{json.dumps(payload, ensure_ascii=False)}

Output schema:
{{
  "items": [
    {{
      "cn_code": 123,
      "display_name": "Whole Milk",
      "root_food_key": "milk"
    }}
  ]
}}
""".strip()

def batch_rewrite_display_names(
    goal_id: str,
    items: list[dict],
) -> dict[int, tuple[str, str]]:
    """
    Optionally rewrite up to 9 display names via an AI model for a given goal.

    Enabled by default when DashScope is configured.
    Set RECOMMENDATION_AI_ENRICH_ENABLED=false to disable it.

    Each item dict contains: cn_code, section, category, grade, descriptor.
    Returns: {cn_code: (display_name, root_food_key)}
    """
    if os.environ.get("RECOMMENDATION_AI_ENRICH_ENABLED", "true").lower() != "true":
        return {}

    ensure_dotenv_loaded()
    client = get_dashscope_openai_client()
    print(f"[AI rewrite] client={client}, items_count={len(items)}")
    if not client:
        print("[AI rewrite] client is None — check DASHSCOPE_API_KEY")
        return {}

    compact_items = [
        {
            "cn_code": item.get("cn_code"),
            "section": item.get("section"),
            "category": item.get("category"),
            "grade": item.get("grade"),
            "descriptor": item.get("descriptor"),
        }
        for item in items
    ]

    try:
        settings = get_dashscope_settings()
        completion = client.chat.completions.create(
            model=settings.qwen_text_model,
            messages=[{"role": "user", "content": _build_batch_rewrite_prompt(goal_id, compact_items)}],
            stream=False,
            temperature=0,
            max_tokens=700,
            timeout=15,
        )
        response_text = (completion.choices[0].message.content or "").strip()
        data = json.loads(_unwrap_json_markdown(response_text))
    except Exception as exc:
        logger.warning("DashScope batch display rewrite failed: %s", exc)
        return {}

    rewritten: dict[int, tuple[str, str]] = {}
    for item in data.get("items", []) if isinstance(data, dict) else []:
        try:
            cn_code = int(item.get("cn_code"))
        except (TypeError, ValueError):
            continue
        display_name = _clean_segment(str(item.get("display_name") or ""))
        root_food_key = str(item.get("root_food_key") or "").strip().lower()
        if display_name and len(display_name) <= 48:
            rewritten[cn_code] = (display_name, root_food_key)
    return rewritten
