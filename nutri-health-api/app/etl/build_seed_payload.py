"""
Build staging and seed payloads from CN.2026.03 raw JSON files.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = BASE_DIR / "data" / "raw"
STAGING_DIR = BASE_DIR / "data" / "staging"
SEED_DIR = BASE_DIR / "data" / "seed"
MAPPING_FILE = BASE_DIR / "data" / "mapping" / "nutrition_rules.json"


def _parse_int(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def _parse_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_date(value: Any):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _read_cn_rows(file_name: str, table_key: str) -> list[dict[str, Any]]:
    path = RAW_DIR / file_name
    with path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)

    records = payload.get(table_key, [])
    result: list[dict[str, Any]] = []
    for item in records:
        row = item.get("row", {})
        if isinstance(row, dict):
            result.append(row)
    return result


def _load_rules() -> dict[str, Any]:
    with MAPPING_FILE.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _nutri_points(value: float | None, thresholds: list[float]) -> int:
    if value is None:
        return 0
    score = 0
    for threshold in thresholds:
        if value > threshold:
            score += 1
    return score


def _normalize_form(value: str | None) -> str | None:
    if not value:
        return None
    token = value.strip().upper().replace(" ", "_")
    replacements = {
        "AS_PURCHASED": "UNPREPARED",
        "AS_SERVED": "READY_TO_EAT",
    }
    return replacements.get(token, token)


def _build_nutrient_lookup(nutvals: list[dict[str, Any]]) -> dict[int, dict[int, float]]:
    by_food: dict[int, dict[int, float]] = defaultdict(dict)
    for row in nutvals:
        cn_code = _parse_int(row.get("Cn code"))
        nutrient_code = _parse_int(row.get("Nutrient code"))
        value = _parse_float(row.get("Nutrient value"))
        if cn_code is None or nutrient_code is None or value is None:
            continue
        if nutrient_code not in by_food[cn_code]:
            by_food[cn_code][nutrient_code] = value
    return by_food


def _calc_health_grade(nutrients: dict[int, float], rules: dict[str, Any]) -> tuple[str, bool]:
    code_map = rules["nutrient_codes"]
    energy_kcal = nutrients.get(code_map["energy_kcal"])
    energy_kj = (energy_kcal * 4.184) if energy_kcal is not None else None
    sugar = nutrients.get(code_map["sugar_g"])
    sat_fat = nutrients.get(code_map["saturated_fat_g"])
    sodium = nutrients.get(code_map["sodium_mg"])
    fiber = nutrients.get(code_map["fiber_g"])
    protein = nutrients.get(code_map["protein_g"])

    nutri = rules["nutri_score"]
    neg = (
        _nutri_points(energy_kj, nutri["negative"]["energy_kj"])
        + _nutri_points(sugar, nutri["negative"]["sugars_g"])
        + _nutri_points(sat_fat, nutri["negative"]["sat_fat_g"])
        + _nutri_points(sodium, nutri["negative"]["sodium_mg"])
    )

    pos = _nutri_points(fiber, nutri["positive"]["fiber_g"]) + _nutri_points(protein, nutri["positive"]["protein_g"])
    score = neg - pos

    if score <= -1:
        grade = "A"
    elif score <= 2:
        grade = "B"
    elif score <= 10:
        grade = "C"
    elif score <= 18:
        grade = "D"
    else:
        grade = "E"

    hcl = rules["hcl_default_thresholds"]
    hcl_compliant = all(
        [
            sugar is not None and sugar <= hcl["sugar_g"],
            sodium is not None and sodium <= hcl["sodium_mg"],
            sat_fat is not None and sat_fat <= hcl["saturated_fat_g"],
            (energy_kcal is not None and energy_kcal <= hcl["energy_kcal"]),
        ]
    )

    return grade, hcl_compliant


def _detect_halal(text: str, rules: dict[str, Any]) -> bool:
    low = text.lower()
    for keyword in rules["halal_non_compliant_keywords"]:
        if keyword in low:
            return False
    return True


def _build_food_tags(food_rows: list[dict[str, Any]], nutrients_by_food: dict[int, dict[int, float]], rules: dict[str, Any]) -> list[dict[str, Any]]:
    code_map = rules["nutrient_codes"]
    tags: list[dict[str, Any]] = []
    next_id = 1

    allergen_patterns = {
        "Peanut": r"\bpeanut\b",
        "TreeNut": r"\b(almond|cashew|walnut|pistachio|hazelnut)\b",
        "Milk": r"\b(milk|cheese|whey|casein)\b",
        "Egg": r"\begg\b",
        "Gluten": r"\b(wheat|barley|rye|gluten)\b",
        "Shellfish": r"\b(shrimp|prawn|crab|lobster)\b",
    }

    for food in food_rows:
        cn_code = food["cn_code"]
        text_blob = " ".join(
            [
                food.get("descriptor", "") or "",
                food.get("brand_name", "") or "",
            ]
        ).lower()

        for label, pattern in allergen_patterns.items():
            if re.search(pattern, text_blob):
                tags.append({"tag_id": next_id, "cn_code": cn_code, "tag_type": "Allergen", "tag_value": label})
                next_id += 1

        nutrients = nutrients_by_food.get(cn_code, {})
        sodium = nutrients.get(code_map["sodium_mg"])
        protein = nutrients.get(code_map["protein_g"])
        sugar = nutrients.get(code_map["sugar_g"])

        if sodium is not None and sodium <= 120:
            tags.append({"tag_id": next_id, "cn_code": cn_code, "tag_type": "Feature", "tag_value": "Low-Sodium"})
            next_id += 1
        if protein is not None and protein >= 10:
            tags.append({"tag_id": next_id, "cn_code": cn_code, "tag_type": "Feature", "tag_value": "High-Protein"})
            next_id += 1
        if sugar is not None and sugar <= 5:
            tags.append({"tag_id": next_id, "cn_code": cn_code, "tag_type": "Feature", "tag_value": "Low-Sugar"})
            next_id += 1

    return tags


def _build_alternatives(food_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_category: dict[int, list[dict[str, Any]]] = defaultdict(list)
    grade_rank = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5}

    for row in food_rows:
        cat = row.get("food_category_code")
        if cat is not None:
            by_category[cat].append(row)

    for cat_rows in by_category.values():
        cat_rows.sort(key=lambda r: (grade_rank.get(r.get("health_grade", "E"), 5), r.get("cn_code", 0)))

    alternatives: list[dict[str, Any]] = []
    next_alt_id = 1

    for row in food_rows:
        cat = row.get("food_category_code")
        if cat is None:
            continue
        source_rank = grade_rank.get(row.get("health_grade", "E"), 5)
        candidates = by_category.get(cat, [])
        picked = 0

        for candidate in candidates:
            if candidate["cn_code"] == row["cn_code"]:
                continue
            cand_rank = grade_rank.get(candidate.get("health_grade", "E"), 5)
            if cand_rank >= source_rank:
                continue

            alternatives.append(
                {
                    "alt_id": next_alt_id,
                    "original_cn_code": row["cn_code"],
                    "suggested_cn_code": candidate["cn_code"],
                    "swap_reason_en": "Better nutrition profile within same category",
                    "swap_score": 100 - (cand_rank * 10),
                }
            )
            next_alt_id += 1
            picked += 1
            if picked >= 3:
                break

    return alternatives


def build_payloads(write_staging: bool = True) -> dict[str, int]:
    rules = _load_rules()

    ctgnme_raw = _read_cn_rows("CN.2026.03_CTGNME.json", "CTGNME")
    fdes_raw = _read_cn_rows("CN.2026.03_FDES.json", "FDES")
    gpcnme_raw = _read_cn_rows("CN.2026.03_GPCNME.json", "GPCNME")
    nutdes_raw = _read_cn_rows("CN.2026.03_NUTDES.json", "NUTDES")
    nutval_raw = _read_cn_rows("CN.2026.03_NUTVAL.json", "NUTVAL")
    wght_raw = _read_cn_rows("CN.2026.03_WGHT.json", "WGHT")

    cn_ctgnme = [
        {
            "food_category_code": _parse_int(row.get("Food category code")),
            "category_description": (row.get("Category description") or "").strip(),
        }
        for row in ctgnme_raw
        if _parse_int(row.get("Food category code")) is not None
    ]

    cn_gpcnme = [
        {
            "gpc_code": (row.get("Gpc code") or "").strip(),
            "gpc_description": (row.get("Gpc description") or "").strip(),
        }
        for row in gpcnme_raw
        if (row.get("Gpc code") or "").strip()
    ]

    cn_nutdes = [
        {
            "nutrient_code": _parse_int(row.get("Nutrient code")),
            "nutrient_description": (row.get("Nutrient description") or "").strip(),
            "nutrient_unit": (row.get("Nutrient unit") or "").strip() or None,
        }
        for row in nutdes_raw
        if _parse_int(row.get("Nutrient code")) is not None
    ]

    cn_nutval = [
        {
            "cn_code": _parse_int(row.get("Cn code")),
            "nutrient_code": _parse_int(row.get("Nutrient code")),
            "nutrient_value": _parse_float(row.get("Nutrient value")),
            "source_code": _parse_int(row.get("Source code")),
            "value_type_code": _parse_int(row.get("Value type code")),
            "per_unit": (row.get("Per unit") or "").strip() or None,
        }
        for row in nutval_raw
        if _parse_int(row.get("Cn code")) is not None and _parse_int(row.get("Nutrient code")) is not None
    ]

    nutrients_by_food = _build_nutrient_lookup(nutval_raw)

    cn_fdes: list[dict[str, Any]] = []
    for row in fdes_raw:
        cn_code = _parse_int(row.get("Cn code"))
        if cn_code is None:
            continue

        descriptor = (row.get("Descriptor") or "").strip()
        brand_name = (row.get("Brand name") or "").strip() or None
        brand_owner_name = (row.get("Brand owner name") or "").strip() or None
        combined_text = " ".join([descriptor, brand_name or "", brand_owner_name or ""])
        health_grade, hcl_compliant = _calc_health_grade(nutrients_by_food.get(cn_code, {}), rules)

        cn_fdes.append(
            {
                "cn_code": cn_code,
                "gtin": (row.get("Gtin") or "").strip() or None,
                "food_category_code": _parse_int(row.get("Food category code")),
                "gpc_product_code": (row.get("Gpc product code") or "").strip() or None,
                "descriptor": descriptor,
                "brand_name": brand_name,
                "brand_owner_name": brand_owner_name,
                "form_of_food": _normalize_form((row.get("Form of food") or "").strip() or None),
                "health_grade": health_grade,
                "hcl_compliant": hcl_compliant,
                "is_halal_auto": _detect_halal(combined_text, rules),
                "discontinued_date": _parse_date(row.get("Discontinued date")),
            }
        )

    cn_wght: list[dict[str, Any]] = []
    for row in wght_raw:
        cn_code = _parse_int(row.get("Cn code"))
        if cn_code is None:
            continue

        sequence_num = _parse_int(row.get("Sequence num"))
        if sequence_num is None:
            continue

        cn_wght.append(
            {
                "cn_code": cn_code,
                "sequence_num": sequence_num,
                "measure_description": (row.get("Measure description") or "").strip() or None,
                "amount": _parse_float(row.get("Amount")),
                "unit_amount": _parse_float(row.get("Unit amount")),
                "type_of_unit": ((row.get("Type of unit") or "").strip().lower() or None),
                "source_code": _parse_int(row.get("Source code")),
            }
        )

    cn_food_tags = _build_food_tags(cn_fdes, nutrients_by_food, rules)
    remote_alternative = _build_alternatives(cn_fdes)

    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    SEED_DIR.mkdir(parents=True, exist_ok=True)

    tables = {
        "cn_ctgnme": cn_ctgnme,
        "cn_gpcnme": cn_gpcnme,
        "cn_nutdes": cn_nutdes,
        "cn_fdes": cn_fdes,
        "cn_nutval": cn_nutval,
        "cn_wght": cn_wght,
        "cn_food_tags": cn_food_tags,
        "remote_alternative": remote_alternative,
    }

    if write_staging:
        with (STAGING_DIR / "staging_summary.json").open("w", encoding="utf-8") as fh:
            json.dump({k: len(v) for k, v in tables.items()}, fh, indent=2)

    for table_name, rows in tables.items():
        with (SEED_DIR / f"{table_name}.json").open("w", encoding="utf-8") as fh:
            json.dump(rows, fh, ensure_ascii=True)

    return {k: len(v) for k, v in tables.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build DB-ready seed payloads from CN raw JSON")
    parser.add_argument("--no-staging", action="store_true", help="Skip writing staging summary")
    args = parser.parse_args()

    counts = build_payloads(write_staging=not args.no_staging)
    print(json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()
