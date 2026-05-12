"""
End-to-end blacklist safety test for the recommendation pipeline.

Strategy:
- Mock call_model to return controlled JSON that deliberately includes
  forbidden foods in all three sections (super_power, tiny_hero, try_less).
- Run the full service pipeline:
    parse_model_output → filter_output → filter_tiny_hero_by_likes
    → rewrite_try_less_by_likes → topup_sections
- Assert that NO forbidden food appears in ANY output section,
  including foods injected by topup_sections from static fallback pools.

This tests both filter_output (LLM output gate) and topup_sections
(static pool pre-filtering) in one pipeline run.

Mock lists use 4 items per section (matching _CANDIDATES_WITH_FILTER=4
for blacklist/allergy cases).

Run:
    .venv/bin/python3 scripts/test_e2e_blacklist_safety.py
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.recommendation import (
    parse_model_output,
    topup_sections,
    rewrite_try_less_by_likes,
)
from app.services.filter import (
    filter_output,
    filter_tiny_hero_by_likes,
    resolve_forbidden,
    is_item_forbidden,
)

SEP = "=" * 65
failures: list[str] = []


def make_item(food: str) -> dict:
    return {"food": food, "reason": "test injection"}


def make_mock_json(super_foods, tiny_foods, try_less_foods) -> str:
    return json.dumps({
        "goal": "test",
        "super_power_foods": [make_item(f) for f in super_foods],
        "tiny_hero_foods":   [make_item(f) for f in tiny_foods],
        "try_less_foods":    [make_item(f) for f in try_less_foods],
    })


def run_pipeline(mock_json: str, goal: str, blacklist: list[str],
                 allergies: list[str] | None = None, likes: list[str] | None = None):
    allergies = allergies or []
    likes = likes or []
    parsed = parse_model_output(mock_json)
    if parsed is None:
        return None
    forbidden_cats, forbidden_kws = resolve_forbidden(blacklist + allergies)
    filtered = filter_output(parsed, blacklist, allergies,
                             forbidden_cats=forbidden_cats, forbidden_kws=forbidden_kws)
    filtered = filter_tiny_hero_by_likes(filtered, likes)
    filtered = rewrite_try_less_by_likes(filtered, likes)
    filtered = topup_sections(
        filtered, goal=goal, blacklist=blacklist, allergies=allergies, likes=likes,
        forbidden_cats=forbidden_cats, forbidden_kws=forbidden_kws,
    )
    return filtered


def all_output_names(result: dict) -> set[str]:
    names = set()
    for section in ["super_power_foods", "tiny_hero_foods", "try_less_foods"]:
        for item in result.get(section, []):
            names.add(item.get("food", item.get("name", "")).lower().strip())
    return names


TARGET = 3


def check_case(label: str, goal: str, blacklist: list[str],
               mock_super: list[str], mock_tiny: list[str], mock_try: list[str],
               must_not_appear: list[str], likes: list[str] | None = None):
    print(f"\n{'─'*65}")
    print(f"Case: {label}")
    print(f"  blacklist={blacklist}  goal={goal}")
    print(f"  LLM candidates: super={len(mock_super)} tiny={len(mock_tiny)} try={len(mock_try)}")

    mock_json = make_mock_json(mock_super, mock_tiny, mock_try)
    result = run_pipeline(mock_json, goal=goal, blacklist=blacklist, likes=likes)

    if result is None:
        print("  [FAIL] pipeline returned None")
        failures.append(f"{label}: pipeline returned None")
        return

    output_names = all_output_names(result)
    ok = True

    # Print what came out
    for section in ["super_power_foods", "tiny_hero_foods", "try_less_foods"]:
        short = section.replace("_foods", "")
        items = result.get(section, [])
        print(f"  [{short}] ({len(items)} items): "
              f"{[i.get('food','?') for i in items]}")

    # Assert each section has exactly TARGET items
    for section in ["super_power_foods", "tiny_hero_foods", "try_less_foods"]:
        n = len(result.get(section, []))
        if n != TARGET:
            print(f"  [FAIL] {section}: expected {TARGET} items, got {n}")
            failures.append(f"{label}: {section} has {n} items (expected {TARGET})")
            ok = False

    # Assert no duplicate names across sections
    seen_names: set[str] = set()
    for name in output_names:
        if name in seen_names:
            print(f"  [FAIL] duplicate food across sections: '{name}'")
            failures.append(f"{label}: duplicate '{name}' across sections")
            ok = False
        seen_names.add(name)

    # Assert no forbidden food appears in any section
    fc, fk = resolve_forbidden(blacklist)
    for name in output_names:
        if is_item_forbidden({"food": name}, fc, fk):
            print(f"  [FAIL] forbidden food in output: '{name}'")
            failures.append(f"{label}: forbidden '{name}' in output")
            ok = False

    # Assert explicit must_not_appear list
    for food in must_not_appear:
        if food.lower() in output_names:
            print(f"  [FAIL] '{food}' (must_not_appear) found in output")
            failures.append(f"{label}: '{food}' found in output")
            ok = False

    if ok:
        print("  [OK] exactly 3 safe items per section, no forbidden food, no duplicates")


# ── 1. seafood ────────────────────────────────────────────────────────────────
print(SEP)
print("1. blacklist=['seafood'] — salmon, tuna, shrimp, crab, seafood pasta must be absent")

check_case(
    label="seafood — 4 candidates with fish/shellfish + safe foods",
    goal="grow",
    blacklist=["seafood"],
    mock_super=["salmon", "tuna", "broccoli", "orange"],
    mock_tiny= ["shrimp", "crab", "seafood pasta", "spinach"],
    mock_try=  ["fish and chips", "fish balls", "chips", "cola"],
    must_not_appear=["salmon", "tuna", "shrimp", "crab", "seafood pasta",
                     "fish and chips", "fish balls"],
)

check_case(
    label="seafood — all 4 candidates forbidden (topup must fill 3 safe items)",
    goal="grow",
    blacklist=["seafood"],
    mock_super=["salmon", "tuna", "mackerel", "sardine"],
    mock_tiny= ["shrimp", "crab", "lobster", "squid"],
    mock_try=  ["fish balls", "fish and chips", "fried fish fillet", "fish crackers"],
    must_not_appear=["salmon", "tuna", "mackerel", "sardine",
                     "shrimp", "crab", "lobster", "squid",
                     "fish balls", "fish and chips", "fried fish fillet"],
)

# ── 2. dairy ──────────────────────────────────────────────────────────────────
print(SEP)
print("2. blacklist=['dairy'] — milk, yogurt, cheese, milkshake must be absent")

check_case(
    label="dairy — 4 candidates with dairy + safe foods",
    goal="think",
    blacklist=["dairy"],
    mock_super=["milk", "yogurt", "blueberries", "oatmeal"],
    mock_tiny= ["cheese", "milkshake", "avocado", "spinach"],
    mock_try=  ["ice cream", "flavored milk drink", "cola", "chips"],
    must_not_appear=["milk", "yogurt", "cheese", "milkshake",
                     "ice cream", "flavored milk drink", "butter", "cream"],
)

check_case(
    label="dairy — compound milkshake + cottage cheese blocked, safe items fill",
    goal="feel",
    blacklist=["dairy"],
    mock_super=["milkshake", "banana", "mango", "brown rice"],
    mock_tiny= ["cottage cheese", "spinach", "avocado", "carrot"],
    mock_try=  ["sweetened condensed milk", "chips", "cola", "candy"],
    must_not_appear=["milkshake", "cottage cheese", "sweetened condensed milk"],
)

# ── 3. egg ────────────────────────────────────────────────────────────────────
print(SEP)
print("3. blacklist=['egg'] — egg, boiled egg, egg-based noodles must be absent")

check_case(
    label="egg — 4 candidates with egg foods + safe foods",
    goal="strong",
    blacklist=["egg"],
    mock_super=["egg", "boiled egg", "chicken breast", "plain yogurt"],
    mock_tiny= ["scrambled eggs", "egg-based noodles", "edamame", "spinach"],
    mock_try=  ["egg fried rice", "chips", "instant noodles", "fried chicken"],
    must_not_appear=["egg", "boiled egg", "scrambled eggs",
                     "egg-based noodles", "egg fried rice"],
)

# ── 4. nuts ───────────────────────────────────────────────────────────────────
print(SEP)
print("4. blacklist=['nuts'] — peanut, almond, peanut-butter toast must be absent")

check_case(
    label="nuts — 4 candidates with nut foods + safe foods",
    goal="think",
    blacklist=["nuts"],
    mock_super=["walnut", "peanut butter", "blueberries", "oatmeal"],
    mock_tiny= ["almond", "cashew", "chia pudding", "avocado"],
    mock_try=  ["peanut-butter toast", "candy", "chips", "cola"],
    must_not_appear=["walnut", "peanut butter", "almond", "cashew",
                     "peanut-butter toast", "peanut", "pistachio"],
)

# ── 5. meat ───────────────────────────────────────────────────────────────────
print(SEP)
print("5. blacklist=['meat'] — chicken, beef, nuggets, sausage, ham, bacon must be absent")

check_case(
    label="meat — 4 candidates with meat + processed meat + safe foods",
    goal="strong",
    blacklist=["meat"],
    mock_super=["chicken", "beef", "plain yogurt", "tuna"],
    mock_tiny= ["chicken breast", "lamb", "edamame", "spinach"],
    mock_try=  ["chicken nuggets", "fried chicken", "chips", "sausage"],
    must_not_appear=["chicken", "beef", "chicken breast", "lamb",
                     "chicken nuggets", "fried chicken", "sausage", "turkey"],
)

check_case(
    label="meat — sausage/ham/bacon in try_less must all be removed, safe fallback fills",
    goal="strong",
    blacklist=["meat"],
    mock_super=["plain yogurt", "tuna", "broccoli", "tofu"],
    mock_tiny= ["edamame", "spinach", "plain yogurt", "sardine"],
    mock_try=  ["sausage", "ham", "bacon", "pepperoni"],
    must_not_appear=["sausage", "ham", "bacon", "meatball", "pepperoni", "salami"],
)

check_case(
    label="meat — compound: ham sandwich, bacon fried rice, turkey wrap, pepperoni pizza blocked",
    goal="feel",
    blacklist=["meat"],
    mock_super=["ham sandwich", "banana", "mango", "brown rice"],
    mock_tiny= ["bacon fried rice", "spinach", "avocado", "carrot"],
    mock_try=  ["turkey wrap", "pepperoni pizza", "chips", "cola"],
    must_not_appear=["ham sandwich", "bacon fried rice", "turkey wrap", "pepperoni pizza"],
)

# ── 6. Compound names across all blacklists ───────────────────────────────────
print(SEP)
print("6. Compound food names — embedded keywords blocked across all blacklists")

check_case(
    label="seafood — compound 'seafood pasta' and 'salmon fried rice' blocked",
    goal="feel",
    blacklist=["seafood"],
    mock_super=["seafood pasta", "banana", "mango", "brown rice"],
    mock_tiny= ["salmon fried rice", "spinach", "avocado", "carrot"],
    mock_try=  ["fish crackers", "chips", "cola", "candy"],
    must_not_appear=["seafood pasta", "salmon fried rice", "fish crackers"],
)

check_case(
    label="nuts — compound 'peanut-butter toast' and 'almond milk yogurt' blocked",
    goal="think",
    blacklist=["nuts"],
    mock_super=["peanut-butter toast", "oatmeal", "berries", "salmon"],
    mock_tiny= ["almond milk yogurt", "avocado", "chia pudding", "mackerel"],
    mock_try=  ["candy bar with nuts", "chips", "cola", "candy"],
    must_not_appear=["peanut-butter toast", "almond milk yogurt", "candy bar with nuts"],
)

check_case(
    label="egg — compound 'egg-based noodles', 'scrambled egg toast', 'egg tart' blocked",
    goal="feel",
    blacklist=["egg"],
    mock_super=["egg-based noodles", "banana", "brown rice", "mango"],
    mock_tiny= ["scrambled egg toast", "spinach", "avocado", "carrot"],
    mock_try=  ["egg tart", "chips", "cola", "candy"],
    must_not_appear=["egg-based noodles", "scrambled egg toast", "egg tart"],
)

# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n{SEP}")
if failures:
    print(f"RESULT: FAIL — {len(failures)} issue(s):")
    for f in failures:
        print(f"  • {f}")
else:
    print("RESULT: PASS")
print(SEP)
