"""
Database-first health scoring with prompt fallback.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.cn_food import CnFdes
from app.services.alternative_rules import infer_food_category, normalize_food_name
from app.services.rag_service import rag_service

logger = logging.getLogger(__name__)

_MIN_RECOGNITION_CONFIDENCE = 0.6
_MIN_ACCEPT_SCORE = 1.4
_STOPWORDS = {
    "with", "and", "in", "on", "of", "the", "a", "an", "style", "flavor", "flavoured",
    "flavored", "prepared", "cooked", "raw", "fresh", "frozen", "canned", "bottled",
    "stir", "fried", "stir-fried", "grilled", "roasted", "steamed", "plate", "bowl",
    "dish", "mixed", "served", "vegetables", "veggies",
}
_ALIAS_VARIANTS = {
    "bubble tea": ["milk tea", "tea beverage", "tea"],
    "milk tea": ["bubble tea", "tea beverage", "tea"],
    "french fries": ["fries", "potato fries", "potatoes french fried"],
    "chips": ["potato chips", "chips"],
    "mango sticky rice": ["mango with tapioca", "mango rice dessert"],
    "papaya salad": ["papaya", "fruit salad papaya"],
    "stir fried squid with vegetables": ["squid fried", "squid vegetables", "squid"],
    "stir-fried squid with vegetables": ["squid fried", "squid vegetables", "squid"],
}
_COMPOSITE_COMPONENTS = {
    "mango sticky rice": ["mango", "rice"],
    "papaya salad": ["papaya"],
    "stir fried squid with vegetables": ["squid", "vegetables"],
    "stir-fried squid with vegetables": ["squid", "vegetables"],
    "bubble tea": ["tea"],
    "milk tea": ["tea"],
}


def apply_database_first_score(result: dict[str, Any], db: Session) -> dict[str, Any]:
    """
    Prefer DB-backed catalog scoring, falling back to the vision model score when matching fails.
    """
    food_name = (result.get("food_name") or "").strip()
    fallback_score = int(result.get("assessment_score", 2) or 2)
    fallback_assessment = (result.get("assessment") or "").strip()
    confidence = float(result.get("confidence", 0) or 0)

    if confidence < _MIN_RECOGNITION_CONFIDENCE or not food_name:
        logger.info(
            "Using fallback score for %r because recognition confidence is low (%.2f).",
            food_name,
            confidence,
        )
        return {
            "assessment_score": fallback_score,
            "assessment": fallback_assessment,
            "score_source": "fallback_prompt",
            "matched_cn_code": None,
            "health_grade": None,
        }

    catalog_row = _resolve_catalog_row(db, food_name)
    if catalog_row is None:
        logger.info("Using fallback score for %r because no reliable catalog match was found.", food_name)
        return {
            "assessment_score": fallback_score,
            "assessment": fallback_assessment,
            "score_source": "fallback_prompt",
            "matched_cn_code": None,
            "health_grade": None,
        }

    mapped_score = _map_health_grade_to_score(catalog_row.health_grade, catalog_row.hcl_compliant)
    if mapped_score is None:
        logger.info(
            "Using fallback score for %r because matched cn_code=%s has no usable health grade.",
            food_name,
            catalog_row.cn_code,
        )
        return {
            "assessment_score": fallback_score,
            "assessment": fallback_assessment,
            "score_source": "fallback_prompt",
            "matched_cn_code": catalog_row.cn_code,
            "health_grade": catalog_row.health_grade,
        }

    logger.info(
        "Database score override for %r: fallback=%s final=%s cn_code=%s grade=%s",
        food_name,
        fallback_score,
        mapped_score,
        catalog_row.cn_code,
        catalog_row.health_grade,
    )
    return {
        "assessment_score": mapped_score,
        "assessment": _build_database_assessment(food_name, mapped_score, catalog_row),
        "score_source": "database",
        "matched_cn_code": catalog_row.cn_code,
        "health_grade": catalog_row.health_grade,
    }


def _resolve_catalog_row(db: Session, food_name: str) -> CnFdes | None:
    variants = _build_query_variants(food_name)
    preferred_category = infer_food_category(food_name)
    exact_match = _exact_match(db, variants)
    if exact_match is not None:
        return exact_match

    candidates = _collect_catalog_candidates(db, variants)
    if rag_service.is_ready and rag_service.vectorstore is not None:
        _merge_vector_candidates(db, candidates, variants)

    best_row = _select_best_candidate(candidates, variants, preferred_category)
    if best_row is None:
        return None
    return best_row


def _exact_match(db: Session, variants: list[str]) -> CnFdes | None:
    lowered = [variant.lower() for variant in variants]
    if not lowered:
        return None
    return db.query(CnFdes).filter(func.lower(CnFdes.descriptor).in_(lowered)).first()


def _build_query_variants(food_name: str) -> list[str]:
    variants: list[str] = []
    normalized = normalize_food_name(food_name)
    if not normalized:
        return variants
    variants.append(normalized)

    for alias in _ALIAS_VARIANTS.get(normalized, []):
        variants.append(normalize_food_name(alias))

    stripped_tokens = [token for token in normalized.split() if token not in _STOPWORDS]
    stripped = " ".join(stripped_tokens).strip()
    if stripped and stripped != normalized:
        variants.append(stripped)

    for component in _COMPOSITE_COMPONENTS.get(normalized, []):
        component_normalized = normalize_food_name(component)
        if component_normalized:
            variants.append(component_normalized)

    unique: list[str] = []
    seen = set()
    for variant in variants:
        if variant and variant not in seen:
            unique.append(variant)
            seen.add(variant)
    return unique


def _collect_catalog_candidates(db: Session, variants: list[str]) -> dict[int, dict[str, Any]]:
    candidates: dict[int, dict[str, Any]] = {}
    important_tokens = _important_tokens_from_variants(variants)
    if not important_tokens:
        return candidates

    filters = [func.lower(CnFdes.descriptor).contains(token) for token in important_tokens[:6]]
    rows = db.query(CnFdes).filter(or_(*filters)).limit(80).all()
    for row in rows:
        candidates[row.cn_code] = {"row": row, "vector_distance": None}
    return candidates


def _merge_vector_candidates(db: Session, candidates: dict[int, dict[str, Any]], variants: list[str]) -> None:
    for variant in variants[:5]:
        try:
            matches = rag_service.vectorstore.similarity_search_with_score(variant, k=6)
        except Exception as exc:
            logger.warning("Vector match failed for %r: %s", variant, exc)
            continue

        for doc, score in matches:
            metadata = doc.metadata or {}
            cn_code = metadata.get("cn_code")
            if cn_code is None:
                continue
            row = db.get(CnFdes, cn_code)
            if row is None:
                continue
            entry = candidates.setdefault(cn_code, {"row": row, "vector_distance": None})
            distance = float(score)
            if entry["vector_distance"] is None or distance < entry["vector_distance"]:
                entry["vector_distance"] = distance


def _select_best_candidate(
    candidates: dict[int, dict[str, Any]],
    variants: list[str],
    preferred_category: str,
) -> CnFdes | None:
    best_row: CnFdes | None = None
    best_score = float("-inf")

    for candidate in candidates.values():
        row = candidate["row"]
        score = _score_candidate(row, variants, preferred_category, candidate.get("vector_distance"))
        if score > best_score:
            best_score = score
            best_row = row

    if best_row is None or best_score < _MIN_ACCEPT_SCORE:
        return None
    return best_row


def _score_candidate(
    row: CnFdes,
    variants: list[str],
    preferred_category: str,
    vector_distance: float | None,
) -> float:
    normalized_descriptor = normalize_food_name(row.descriptor or "")
    descriptor_tokens = set(_important_tokens(normalized_descriptor))
    best_lexical = 0.0
    exact_bonus = 0.0
    component_bonus = 0.0

    for variant in variants:
        variant_tokens = set(_important_tokens(variant))
        if not variant_tokens or not descriptor_tokens:
            continue

        if variant == normalized_descriptor:
            exact_bonus = max(exact_bonus, 2.0)
        elif variant in normalized_descriptor or normalized_descriptor in variant:
            exact_bonus = max(exact_bonus, 1.4)

        overlap = len(variant_tokens & descriptor_tokens) / min(len(variant_tokens), len(descriptor_tokens))
        best_lexical = max(best_lexical, overlap)

        if len(variant_tokens) == 1 and overlap > 0:
            component_bonus = max(component_bonus, 0.3)

    score = exact_bonus + (best_lexical * 1.6) + component_bonus

    candidate_category = _catalog_category(row)
    if preferred_category != "general" and candidate_category == preferred_category:
        score += 0.35

    if vector_distance is not None:
        score += max(0.0, 1.05 - min(vector_distance, 1.05))

    if row.brand_name:
        score -= 0.05

    return score


def _token_overlap(left: str, right: str) -> float:
    left_tokens = {token for token in left.split() if token and token not in _STOPWORDS}
    right_tokens = {token for token in right.split() if token and token not in _STOPWORDS}
    if not left_tokens or not right_tokens:
        return 0.0
    shared = left_tokens & right_tokens
    return len(shared) / min(len(left_tokens), len(right_tokens))


def _important_tokens_from_variants(variants: list[str]) -> list[str]:
    tokens: list[str] = []
    for variant in variants:
        tokens.extend(_important_tokens(variant))
    unique: list[str] = []
    seen = set()
    for token in tokens:
        if token not in seen:
            unique.append(token)
            seen.add(token)
    return unique


def _important_tokens(text: str) -> list[str]:
    return [token for token in text.split() if token and token not in _STOPWORDS and len(token) > 2]


def _catalog_category(row: CnFdes) -> str:
    descriptor = normalize_food_name(row.descriptor or "")
    category_code = row.food_category_code
    if category_code == 14:
        return "drink"
    if category_code == 25:
        return "snack"
    if category_code in {18, 19}:
        return "dessert"
    if category_code in {21, 22, 36}:
        return "meal"
    if category_code == 9:
        return "fruit"
    if category_code == 11:
        return "vegetable"
    if category_code == 1:
        return "dairy"
    return infer_food_category(descriptor)


def _map_health_grade_to_score(health_grade: str | None, hcl_compliant: bool | None) -> int | None:
    grade = (health_grade or "").strip().upper()
    if grade in {"A", "B"}:
        return 3
    if grade == "C":
        return 2
    if grade in {"D", "E"}:
        return 1
    if hcl_compliant is True:
        return 3
    return None


def _build_database_assessment(food_name: str, score: int, row: CnFdes) -> str:
    display_name = (row.descriptor or food_name or "This food").strip()
    if score >= 3:
        return (
            f"{display_name} is a nourishing choice with a strong nutrition profile. "
            "It's great for everyday eating and helps your body feel strong and energised! 🌟"
        )
    if score == 2:
        return (
            f"{display_name} has some good nutrients but is higher in fat, sugar, or salt. "
            "It's best enjoyed occasionally rather than every day. 😊"
        )
    return (
        f"{display_name} is high in sugar, salt, or unhealthy fats with limited nutritional value. "
        "It's best saved as a once-in-a-while treat. 💪"
    )
