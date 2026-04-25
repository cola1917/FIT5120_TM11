"""
Recommendation Service

Queries cn_fdes and cn_food_tags to build three personalised food lists:
  - super_power_foods : healthy foods from liked + goal-relevant categories
  - tiny_hero_foods   : healthy foods from disliked / unexplored goal categories
  - try_less_foods    : unhealthy foods from liked / goal categories

Allergen exclusion is a global hard constraint applied before all queries.
No food cn_code OR normalized food name appears in more than one section.

Pool ranking (all sections):
  1. goal relevance  (food category is in goal_prefs)
  2. health grade    (A→E for healthy sections; E→A for try_less)
  3. hcl_compliant   (True first)
  4. common_score    (higher = more familiar; +2 common keyword, -4 rare keyword)
  5. random          (tiebreak)
"""

import logging
import random as _random
import urllib.parse
from dataclasses import dataclass

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.cn_food import CnFdes, CnFoodTag
from app.schemas.recommendations import FoodItem, RecommendationRequest, RecommendationResponse
from app.services.category_mapping import (
    BLACKLIST_TO_ALLERGEN,
    CAT_CODE_TO_PREF,
    COMMON_FOOD_KEYWORDS,
    GOAL_RELEVANT_PREFS,
    JUNK_FOOD_KEYWORDS,
    NOODLE_KEYWORDS,
    PREFERENCE_TO_CATEGORY,
    RARE_FOOD_KEYWORDS,
    RICE_KEYWORDS,
)
from app.services.food_display import (
    ai_descriptor,
    batch_rewrite_display_names,
    display_name_for_section,
    is_challenge_suitable,
    is_generic_output_name,
    normalize_food_name,
    normalize_display_name,
    simple_display_name,
)

logger = logging.getLogger(__name__)

_GRADE_ORDER: dict[str, int] = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}
_SECTION_SELECTED_COUNT = 3
_SECTION_CANDIDATE_COUNT = 12


@dataclass
class _SectionSelection:
    section: str
    selected: list[CnFdes]
    backups: list[CnFdes]


# ── Helpers ───────────────────────────────────────────────────────────────────

def clean_display_name(descriptor: str) -> str:
    """Backward-compatible alias for the simple recommendation display name."""
    return simple_display_name(descriptor)


def _make_image_url(descriptor: str, section: str = "default") -> str:
    """Generate a Pollinations AI image URL for a food descriptor."""
    clean = display_name_for_section(descriptor, section)
    return _make_image_url_from_name(clean)


def _make_image_url_from_name(name: str) -> str:
    """Generate a Pollinations AI image URL for a display name."""
    clean = name.strip()
    encoded = urllib.parse.quote(f"{clean} food photography white background")
    return (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?model=flux&width=400&height=400&nologo=true"
    )


def _normalize_name(descriptor: str) -> str:
    """
    Normalize a food descriptor for cross-section name deduplication.
    Uses the cleaned display name, then lowercases, strips punctuation, and
    collapses whitespace so noisy package text does not defeat deduplication.
    """
    return normalize_display_name(descriptor)


def _compute_common_score(descriptor: str) -> int:
    """
    Return a familiarity score for the food descriptor:
      +2 if any COMMON_FOOD_KEYWORDS term appears in the name
      -4 if any RARE_FOOD_KEYWORDS term appears in the name

    Used only for pool sorting. Does NOT filter foods out.
    Rare foods are deprioritized, not excluded.
    """
    name = descriptor.lower()
    score = 0
    if any(kw in name for kw in COMMON_FOOD_KEYWORDS):
        score += 2
    if any(kw in name for kw in RARE_FOOD_KEYWORDS):
        score -= 4
    return score


def extract_common_keyword_hits(descriptor: str) -> dict:
    """
    Debug helper only. Returns matched common and rare keywords for a descriptor.
    This function has no effect on filtering or ranking logic.
    """
    name = descriptor.lower()
    return {
        "common": [kw for kw in COMMON_FOOD_KEYWORDS if kw in name],
        "rare":   [kw for kw in RARE_FOOD_KEYWORDS if kw in name],
    }


def _sort_pool(
    pool: list[CnFdes],
    goal_prefs: list[str],
    ascending_grade: bool = True,
) -> list[CnFdes]:
    """
    Sort a food pool by the canonical ranking criteria (Python ascending sort).
    Negative values are used so that "more desirable" always means "smaller key":

      1. -goal_relevance   (-1 = goal-relevant, 0 = other)
      2.  grade_key        (A=0…E=4 for healthy sections; reversed for try_less so E=0)
      3. -hcl_compliant    (-1 = True, 0 = False/None)
      4. -common_score     (higher familiarity score → more negative → sorts first)
      5.  random()         (tiebreak; ensures variety across requests)
    """
    def _key(food: CnFdes) -> tuple:
        food_pref = CAT_CODE_TO_PREF.get(food.food_category_code, "other")

        grade_idx = _GRADE_ORDER.get(food.health_grade or "C", 2)
        grade_key = grade_idx if ascending_grade else (4 - grade_idx)

        # Word count: more specific names (longer) sort before shorter/generic ones
        word_count = len(_normalize_name(food.descriptor).split())

        return (
            -(food_pref in goal_prefs),           # -1 = goal-relevant, 0 = other
            grade_key,                             # lower = better grade for this section
            -int(food.hcl_compliant or False),    # -1 = compliant, 0 = not/None
            -_compute_common_score(food.descriptor),  # higher score → more negative
            -word_count,                           # more specific names first (fewer tiebreaks needed)
            _random.random(),                      # final tiebreak
        )

    return sorted(pool, key=_key)


def _prefs_to_cat_codes(prefs: list[str]) -> list[int]:
    """Convert a list of preference IDs to unique category code integers."""
    codes: set[int] = set()
    for p in prefs:
        codes.update(PREFERENCE_TO_CATEGORY.get(p, []))
    return list(codes)


def _build_name_filter(prefs: list[str]):
    """
    Return a SQLAlchemy OR filter for cat-20 name disambiguation, or None.

    - Both rice and noodles present → no filter (include all cat-20)
    - Only rice → match rice keywords
    - Only noodles → match noodle keywords
    - Neither → no cat-20 at all, so filter is irrelevant
    """
    has_rice = "rice" in prefs
    has_noodles = "noodles" in prefs

    if has_rice and has_noodles:
        return None
    if has_rice:
        return or_(*[CnFdes.descriptor.ilike(kw) for kw in RICE_KEYWORDS])
    if has_noodles:
        return or_(*[CnFdes.descriptor.ilike(kw) for kw in NOODLE_KEYWORDS])
    return None


def _to_food_item(food: CnFdes, section: str = "default") -> FoodItem:
    category = CAT_CODE_TO_PREF.get(food.food_category_code, "other")
    name = display_name_for_section(food.descriptor, section, category, food.health_grade or "")
    return FoodItem(
        cn_code=food.cn_code,
        name=name,
        category=category,
        grade=food.health_grade or "",
        image_url=_make_image_url(food.descriptor, section),
    )


def _name_words(normalized_name: str) -> frozenset[str]:
    """Return the word set of a normalized name, excluding single-letter tokens."""
    return frozenset(w for w in normalized_name.split() if len(w) > 1)


def _dedupe_pool_by_name(pool: list[CnFdes], used_names: set[str]) -> list[CnFdes]:
    """
    Remove foods whose normalized display name is already used, and collapse
    near-duplicate names within the current pool while preserving pool order.

    Two foods are considered near-duplicates when one name's word set is a
    subset of the other's (e.g. "Processed Cheese" ⊆ "Processed Cheese Product").
    The pool must be sorted before calling this function so that the more
    specific (longer) name appears first and is kept; the shorter/generic one
    is then dropped.

    Single-word names are exempt from subset checking to avoid over-filtering
    (e.g. "Beef" must not be dropped just because "Beef Sausage" was kept).
    """
    # Seed seen_words from already-used cross-section names
    seen_exact: set[str] = set(used_names)
    seen_word_sets: list[frozenset[str]] = [
        _name_words(n) for n in used_names if len(n.split()) >= 2
    ]
    deduped: list[CnFdes] = []

    for food in pool:
        name = _normalize_name(food.descriptor)

        # 1. Exact match (existing behaviour)
        if name in seen_exact:
            continue

        # 2. Word-set containment check.
        # A food is subsumed if its word set is a subset of any already-kept
        # multi-word name (≥2 words).  The guard is on the *kept* side, not
        # the current side, so single-word names like "Salmon" are correctly
        # dropped when a more specific name like "Salmon Nuggets" is already kept.
        words = _name_words(name)
        if any(words <= kept for kept in seen_word_sets if len(kept) >= 2):
            continue

        seen_exact.add(name)
        seen_word_sets.append(words)
        deduped.append(food)

    return deduped


def _filter_generic_pool(pool: list[CnFdes], section: str) -> list[CnFdes]:
    """Remove candidates whose display name is too generic for their category."""
    filtered: list[CnFdes] = []
    for food in pool:
        category = CAT_CODE_TO_PREF.get(food.food_category_code, "other")
        name = display_name_for_section(food.descriptor, section, category, food.health_grade or "")
        if not is_generic_output_name(name, category):
            filtered.append(food)
    return filtered


def _selection_to_food_items(selection: _SectionSelection) -> list[FoodItem]:
    return [_to_food_item(food, selection.section) for food in selection.selected]


def _finalize_selection(
    section: str,
    candidates: list[CnFdes],
    used: set[int],
    used_names: set[str],
) -> _SectionSelection:
    selected = candidates[:_SECTION_SELECTED_COUNT]
    backups = candidates[_SECTION_SELECTED_COUNT:]
    used.update(f.cn_code for f in selected)
    used_names.update(_normalize_name(f.descriptor) for f in selected)
    return _SectionSelection(section=section, selected=selected, backups=backups)


# ── Database query helpers ────────────────────────────────────────────────────

def _query_pool(
    db: Session,
    prefs: list[str],
    grades: list[str],
    excluded: set[int],
    used: set[int],
    limit: int = 30,
) -> list[CnFdes]:
    """
    Fetch a random pool of foods matching the given preference categories and
    health grades, after applying allergen exclusion and cross-section dedup.
    """
    if not prefs:
        return []

    cat_codes = _prefs_to_cat_codes(prefs)
    if not cat_codes:
        return []

    blocked = excluded | used

    q = db.query(CnFdes).filter(
        CnFdes.food_category_code.in_(cat_codes),
        CnFdes.health_grade.in_(grades),
        ~CnFdes.descriptor.ilike("%pork%"),
        CnFdes.discontinued_date == None,  # noqa: E711
    )

    if blocked:
        q = q.filter(CnFdes.cn_code.notin_(blocked))

    name_filter = _build_name_filter(prefs)
    if name_filter is not None:
        q = q.filter(name_filter)

    pool = q.order_by(func.random()).limit(limit).all()
    # Hard-filter foods that match any RARE_FOOD_KEYWORDS (applies to all sections)
    pool = [
        f for f in pool
        if not any(kw in f.descriptor.lower() for kw in RARE_FOOD_KEYWORDS)
    ]
    return pool


def _pick_diverse(pool: list[CnFdes], n: int) -> list[CnFdes]:
    """
    Select up to n items from pool ensuring at most one item per category code.
    If fewer unique categories than n exist, fills remaining slots from leftovers.
    Pool order is preserved — callers must sort before calling this function.
    """
    selected: list[CnFdes] = []
    used_cat_codes: set[int] = set()

    for food in pool:
        if len(selected) >= n:
            break
        if food.food_category_code not in used_cat_codes:
            selected.append(food)
            used_cat_codes.add(food.food_category_code)

    # Fill remaining slots without diversity constraint
    if len(selected) < n:
        for food in pool:
            if len(selected) >= n:
                break
            if food not in selected:
                selected.append(food)

    return selected


# ── Global pre-processing ─────────────────────────────────────────────────────

def build_excluded_cn_codes(db: Session, blacklist: list[str]) -> set[int]:
    """
    Build the global allergen exclusion set from the user's blacklist.
    This set is applied as a hard constraint to ALL three sections.
    """
    excluded: set[int] = set()
    allergen_values: list[str] = []
    exclude_pork_cat = False

    for item in blacklist:
        if item == "pork":
            exclude_pork_cat = True
        else:
            tags = BLACKLIST_TO_ALLERGEN.get(item, [])
            allergen_values.extend(tags)

    if allergen_values:
        rows = (
            db.query(CnFoodTag.cn_code)
            .filter(
                CnFoodTag.tag_type == "Allergen",
                CnFoodTag.tag_value.in_(allergen_values),
            )
            .all()
        )
        excluded.update(r.cn_code for r in rows)

    if exclude_pork_cat:
        rows = (
            db.query(CnFdes.cn_code)
            .filter(CnFdes.food_category_code == 10)
            .all()
        )
        excluded.update(r.cn_code for r in rows)

    logger.info("[rec] excluded_food_count=%d", len(excluded))
    return excluded


def _select_super_power(
    db: Session,
    goal_id: str,
    likes: list[str],
    excluded: set[int],
    used: set[int],
    used_names: set[str],
    target_count: int = _SECTION_CANDIDATE_COUNT,
) -> _SectionSelection:
    """
    Healthy (A/B) foods from liked ∩ goal categories, with priority ordering.
    Falls back progressively to secondary likes, then goal_prefs, then global.
    """
    goal_prefs = GOAL_RELEVANT_PREFS.get(goal_id, [])
    priority_prefs = [p for p in likes if p in goal_prefs]
    secondary_prefs = [p for p in likes if p not in goal_prefs]

    result: list[CnFdes] = []
    internal_used = set(used)
    internal_names: set[str] = set(used_names)

    def _extend(prefs: list[str], grades: list[str], hcl_only: bool = False) -> None:
        if not prefs or len(result) >= target_count:
            return
        pool = _query_pool(db, prefs, grades, excluded, internal_used)
        if hcl_only:
            pool = [f for f in pool if f.hcl_compliant]
        pool = [f for f in pool if not any(kw in f.descriptor.lower() for kw in JUNK_FOOD_KEYWORDS)]
        pool = _sort_pool(pool, goal_prefs, ascending_grade=True)
        pool = _filter_generic_pool(pool, "super_power")
        pool = _dedupe_pool_by_name(pool, internal_names)
        picked = _pick_diverse(pool, target_count - len(result))
        result.extend(picked)
        internal_used.update(f.cn_code for f in picked)
        internal_names.update(_normalize_name(f.descriptor) for f in picked)

    _extend(priority_prefs, ["A"], hcl_only=True)   # R1: priority + A + hcl
    _extend(priority_prefs, ["A"])                   # R2: priority + A
    _extend(priority_prefs, ["B"])                   # R3: priority + B
    _extend(secondary_prefs, ["A", "B"])             # R4: secondary likes
    _extend(goal_prefs, ["A", "B"])                  # R5: full goal_prefs fallback
    _extend(list(PREFERENCE_TO_CATEGORY.keys()), ["A", "B"])  # R6: global fallback

    selection = _finalize_selection("super_power", result, used, used_names)
    logger.info("[rec] super_power_cn_codes=%s", [f.cn_code for f in selection.selected])
    return selection


def _select_tiny_hero(
    db: Session,
    goal_id: str,
    likes: list[str],
    dislikes: list[str],
    excluded: set[int],
    used: set[int],
    used_names: set[str],
    target_count: int = _SECTION_CANDIDATE_COUNT,
) -> _SectionSelection:
    """
    Healthy (A/B) foods the child does not like, or has not liked yet.
    Disliked categories are preferred even when they are outside the selected
    goal, then non-liked goal categories, then full goal categories.
    """
    goal_prefs = GOAL_RELEVANT_PREFS.get(goal_id, [])
    disliked_goal_prefs = [p for p in dislikes if p in goal_prefs]
    disliked_other_prefs = [p for p in dislikes if p not in goal_prefs]
    non_liked_goal_prefs = [p for p in goal_prefs if p not in likes]

    result: list[CnFdes] = []
    internal_used = set(used)
    internal_names: set[str] = set(used_names)

    def _extend(prefs: list[str]) -> None:
        if not prefs or len(result) >= target_count:
            return
        pool = _query_pool(db, prefs, ["A", "B"], excluded, internal_used)
        pool = _sort_pool(pool, goal_prefs, ascending_grade=True)
        pool = [f for f in pool if not any(kw in f.descriptor.lower() for kw in JUNK_FOOD_KEYWORDS)]
        pool = [
            f for f in pool
            if is_challenge_suitable(
                f.descriptor,
                CAT_CODE_TO_PREF.get(f.food_category_code, "other"),
                f.health_grade or "",
            )
        ]
        pool = _filter_generic_pool(pool, "tiny_hero")
        pool = _dedupe_pool_by_name(pool, internal_names)
        picked = _pick_diverse(pool, target_count - len(result))
        result.extend(picked)
        internal_used.update(f.cn_code for f in picked)
        internal_names.update(_normalize_name(f.descriptor) for f in picked)

    if disliked_goal_prefs:
        _extend(disliked_goal_prefs)                 # R1: disliked ∩ goal_prefs
        _extend(disliked_other_prefs)                # R2: remaining disliked categories
    else:
        _extend(dislikes)                            # R1: all disliked categories

    _extend(non_liked_goal_prefs)                    # R3: goal_prefs - likes
    _extend(goal_prefs)                              # R4: final goal fallback

    selection = _finalize_selection("tiny_hero", result, used, used_names)
    logger.info("[rec] tiny_hero_cn_codes=%s", [f.cn_code for f in selection.selected])
    return selection


def _select_try_less(
    db: Session,
    goal_id: str,
    likes: list[str],
    excluded: set[int],
    used: set[int],
    used_names: set[str],
    target_count: int = _SECTION_CANDIDATE_COUNT,
) -> _SectionSelection:
    """
    Unhealthy (D/E) foods, preferring liked ∩ goal categories first.
    Allergen filtering still applies (excluded set).
    """
    goal_prefs = GOAL_RELEVANT_PREFS.get(goal_id, [])
    priority_prefs = [p for p in likes if p in goal_prefs]

    result: list[CnFdes] = []
    internal_used = set(used)
    internal_names: set[str] = set(used_names)

    def _extend(prefs: list[str]) -> None:
        if not prefs or len(result) >= target_count:
            return
        pool = _query_pool(db, prefs, ["D", "E"], excluded, internal_used)
        pool = _sort_pool(pool, goal_prefs, ascending_grade=False)  # E before D
        pool = _filter_generic_pool(pool, "try_less")
        pool = _dedupe_pool_by_name(pool, internal_names)
        picked = _pick_diverse(pool, target_count - len(result))
        result.extend(picked)
        internal_used.update(f.cn_code for f in picked)
        internal_names.update(_normalize_name(f.descriptor) for f in picked)

    _extend(priority_prefs)                          # R1: liked ∩ goal + D/E
    _extend(likes)                                   # R2: all likes + D/E
    _extend(goal_prefs)                              # R3: goal_prefs + D/E
    _extend(list(PREFERENCE_TO_CATEGORY.keys()))     # R4: global D/E fallback

    selection = _finalize_selection("try_less", result, used, used_names)
    logger.info("[rec] try_less_cn_codes=%s", [f.cn_code for f in selection.selected])
    return selection


# ── Section query wrappers ───────────────────────────────────────────────────

def _query_super_power(
    db: Session,
    goal_id: str,
    likes: list[str],
    excluded: set[int],
    used: set[int],
    used_names: set[str],
) -> list[FoodItem]:
    return _selection_to_food_items(
        _select_super_power(
            db, goal_id, likes, excluded, used, used_names,
            target_count=_SECTION_SELECTED_COUNT,
        )
    )


def _query_tiny_hero(
    db: Session,
    goal_id: str,
    likes: list[str],
    dislikes: list[str],
    excluded: set[int],
    used: set[int],
    used_names: set[str],
) -> list[FoodItem]:
    return _selection_to_food_items(
        _select_tiny_hero(
            db, goal_id, likes, dislikes, excluded, used, used_names,
            target_count=_SECTION_SELECTED_COUNT,
        )
    )


def _query_try_less(
    db: Session,
    goal_id: str,
    likes: list[str],
    excluded: set[int],
    used: set[int],
    used_names: set[str],
) -> list[FoodItem]:
    return _selection_to_food_items(
        _select_try_less(
            db, goal_id, likes, excluded, used, used_names,
            target_count=_SECTION_SELECTED_COUNT,
        )
    )


def _apply_batch_display_rewrite(
    db: Session,
    goal_id: str,
    response: RecommendationResponse,
    selections=None,
) -> RecommendationResponse:
    """
    Rewrite only the final 9 display names in a single DashScope call.
    Rule-based names remain as fallback if AI is unavailable or incomplete.
    """
    section_items = [
        ("super_power", item)
        for item in response.super_power_foods
    ] + [
        ("tiny_hero", item)
        for item in response.tiny_hero_foods
    ] + [
        ("try_less", item)
        for item in response.try_less_foods
    ]
    cn_codes = [item.cn_code for _, item in section_items]
    if not cn_codes:
        return response

    try:
        foods = (
            db.query(CnFdes)
            .filter(CnFdes.cn_code.in_(cn_codes))
            .all()
        )
    except Exception as exc:
        logger.warning("[rec] descriptor lookup for display rewrite failed: %s", exc)
        return response

    descriptor_by_code = {food.cn_code: food.descriptor for food in foods}
    rewrite_items = [
        {
            "cn_code": item.cn_code,
            "section": section,
            "category": item.category,
            "grade": item.grade,
            "descriptor": ai_descriptor(descriptor_by_code.get(item.cn_code, item.name)),
        }
        for section, item in section_items
    ]
    rewritten = batch_rewrite_display_names(goal_id, rewrite_items)

    root_keys_by_code: dict[int, str] = {}
    for _, item in section_items:
        result = rewritten.get(item.cn_code)
        if result:
            new_name, root_key = result
            if new_name and not is_generic_output_name(new_name, item.category):
                item.name = new_name
                item.image_url = _make_image_url_from_name(new_name)
                if root_key:
                    root_keys_by_code[item.cn_code] = root_key

    if selections:
        _replace_invalid_items_from_backups(response, selections, root_keys_by_code)
    return response


def _replace_invalid_items_from_backups(
    response: RecommendationResponse,
    selections: dict[str, _SectionSelection],
    root_keys_by_code: dict[int, str] | None = None,
) -> None:
    """Drop generic/duplicate final names and refill from same-section backup candidates.

    root_keys_by_code maps cn_code -> root_food_key (from AI rewrite).
    Items sharing the same root_food_key are considered semantic duplicates;
    only the first occurrence (by section priority order) is kept.
    """
    used_codes: set[int] = set()
    used_names: set[str] = set()
    used_root_keys: set[str] = set()
    root_keys_by_code = root_keys_by_code or {}

    section_fields = [
        ("super_power", "super_power_foods"),
        ("tiny_hero", "tiny_hero_foods"),
        ("try_less", "try_less_foods"),
    ]

    for section, field_name in section_fields:
        current_items: list[FoodItem] = getattr(response, field_name)
        kept: list[FoodItem] = []

        for item in current_items:
            name_key = normalize_food_name(item.name)
            root_key = root_keys_by_code.get(item.cn_code, "")
            if (
                item.cn_code in used_codes
                or name_key in used_names
                or is_generic_output_name(item.name, item.category)
                or (root_key and root_key in used_root_keys)
            ):
                continue
            kept.append(item)
            used_codes.add(item.cn_code)
            used_names.add(name_key)
            if root_key:
                used_root_keys.add(root_key)

        selection = selections.get(section)
        backups = selection.backups if selection else []
        for food in backups:
            if len(kept) >= _SECTION_SELECTED_COUNT:
                break
            item = _to_food_item(food, section)
            name_key = normalize_food_name(item.name)
            root_key = root_keys_by_code.get(item.cn_code, "")
            if (
                item.cn_code in used_codes
                or name_key in used_names
                or is_generic_output_name(item.name, item.category)
                or (root_key and root_key in used_root_keys)
            ):
                continue
            kept.append(item)
            used_codes.add(item.cn_code)
            used_names.add(name_key)
            if root_key:
                used_root_keys.add(root_key)

        setattr(response, field_name, kept)


# ── Public entry point ────────────────────────────────────────────────────────

def get_recommendations(db: Session, request: RecommendationRequest) -> RecommendationResponse:
    logger.info("[rec] goal_id=%s", request.goal_id)
    logger.info(
        "[rec] likes=%s dislikes=%s blacklist=%s",
        request.likes,
        request.dislikes,
        request.blacklist,
    )

    # Step 1: build global allergen exclusion set (hard constraint for all sections)
    excluded = build_excluded_cn_codes(db, request.blacklist)

    # Step 2: shared cross-section dedup (grows as each section selects foods)
    used: set[int] = set()
    used_names: set[str] = set()

    # Step 3: query each section in order; both sets accumulate across calls
    super_power_selection = _select_super_power(db, request.goal_id, request.likes, excluded, used, used_names)
    tiny_hero_selection = _select_tiny_hero(db, request.goal_id, request.likes, request.dislikes, excluded, used, used_names)
    try_less_selection = _select_try_less(db, request.goal_id, request.likes, excluded, used, used_names)

    response = RecommendationResponse(
        super_power_foods=_selection_to_food_items(super_power_selection),
        tiny_hero_foods=_selection_to_food_items(tiny_hero_selection),
        try_less_foods=_selection_to_food_items(try_less_selection),
    )
    return _apply_batch_display_rewrite(
        db,
        request.goal_id,
        response,
        {
            "super_power": super_power_selection,
            "tiny_hero": tiny_hero_selection,
            "try_less": try_less_selection,
        },
    )
