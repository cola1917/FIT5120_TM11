"""
Unit tests for canonical blacklist/allergy filtering.

Proves that resolve_forbidden + is_item_forbidden correctly blocks foods
by category and keyword, not just literal string match.

Run:
    .venv/bin/python3 scripts/test_canonical_blacklist.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.filter import resolve_forbidden, is_item_forbidden, filter_output, filter_candidates

SEP = "=" * 60
failures: list[str] = []


def item(name: str) -> dict:
    return {"food": name, "reason": "test"}


def assert_blocked(food: str, blacklist: list[str]) -> None:
    fc, fk = resolve_forbidden(blacklist)
    blocked = is_item_forbidden(item(food), fc, fk)
    status = "OK" if blocked else "FAIL"
    if not blocked:
        failures.append(f"'{food}' should be blocked by {blacklist}")
    print(f"  [{status}] {blacklist} blocks '{food}'")


def assert_allowed(food: str, blacklist: list[str]) -> None:
    fc, fk = resolve_forbidden(blacklist)
    blocked = is_item_forbidden(item(food), fc, fk)
    status = "OK" if not blocked else "FAIL"
    if blocked:
        failures.append(f"'{food}' should NOT be blocked by {blacklist}")
    print(f"  [{status}] {blacklist} allows '{food}'")


# ── 1. seafood ────────────────────────────────────────────────────────────────
print(SEP)
print("1. seafood — blocks fish and shellfish by category and keyword")

for food in ["salmon", "tuna", "cod", "mackerel", "sardine", "tilapia",
             "shrimp", "prawn", "crab", "lobster", "squid", "clam",
             "fish balls", "fish and chips", "fried fish fillet"]:
    assert_blocked(food, ["seafood"])

print("  --- must NOT block ---")
for food in ["chicken", "broccoli", "banana", "yogurt", "boiled egg"]:
    assert_allowed(food, ["seafood"])

# ── 2. dairy / milk ──────────────────────────────────────────────────────────
print(SEP)
print("2. dairy/milk — blocks dairy products")

for food in ["milk", "yogurt", "cheese", "butter", "cream",
             "cottage cheese", "flavored milk drink"]:
    assert_blocked(food, ["dairy"])
    assert_blocked(food, ["milk"])

print("  --- must NOT block ---")
for food in ["salmon", "broccoli", "orange", "chicken"]:
    assert_allowed(food, ["dairy"])

# ── 3. egg ───────────────────────────────────────────────────────────────────
print(SEP)
print("3. egg — blocks egg-related foods")

for food in ["egg", "eggs", "boiled egg", "scrambled eggs", "egg fried rice"]:
    assert_blocked(food, ["egg"])

print("  --- must NOT block ---")
for food in ["chicken", "tofu", "oatmeal", "yogurt"]:
    assert_allowed(food, ["egg"])

# ── 4. nuts ──────────────────────────────────────────────────────────────────
print(SEP)
print("4. nuts — blocks nut varieties")

for food in ["peanut", "almond", "cashew", "walnut", "pistachio",
             "peanut butter", "almond milk"]:
    assert_blocked(food, ["nuts"])

print("  --- must NOT block ---")
for food in ["banana", "salmon", "rice", "broccoli"]:
    assert_allowed(food, ["nuts"])

# ── 5. meat ──────────────────────────────────────────────────────────────────
print(SEP)
print("5. meat — blocks meat varieties including processed meat")

for food in ["chicken", "beef", "lamb", "turkey", "duck",
             "chicken breast", "fried chicken", "chicken nuggets",
             "sausage", "ham", "bacon", "meatball", "nuggets",
             "pepperoni", "salami",
             "ham sandwich", "bacon fried rice", "turkey wrap",
             "pepperoni pizza"]:
    assert_blocked(food, ["meat"])

print("  --- must NOT block ---")
for food in ["salmon", "yogurt", "broccoli", "tofu", "oatmeal", "banana"]:
    assert_allowed(food, ["meat"])

# ── 6. filter_output end-to-end ──────────────────────────────────────────────
print(SEP)
print("6. filter_output end-to-end — seafood blacklist removes fish/shellfish from all sections")

parsed = {
    "super_power_foods": [item("salmon"), item("broccoli"), item("orange")],
    "tiny_hero_foods":   [item("tuna"),   item("spinach"), item("plain yogurt")],
    "try_less_foods":    [item("shrimp"), item("crab stick"), item("chips")],
}

result = filter_output(parsed, blacklist=["seafood"], allergies=[])
all_items = (
    result["super_power_foods"] +
    result["tiny_hero_foods"] +
    result["try_less_foods"]
)
all_names = {i["food"].lower() for i in all_items}

for food in ["salmon", "tuna", "shrimp", "crab stick"]:
    status = "OK" if food not in all_names else "FAIL"
    if food in all_names:
        failures.append(f"filter_output: '{food}' still present with seafood blacklist")
    print(f"  [{status}] '{food}' removed")

for food in ["broccoli", "orange", "spinach", "plain yogurt", "chips"]:
    status = "OK" if food in all_names else "FAIL"
    if food not in all_names:
        failures.append(f"filter_output: '{food}' incorrectly removed")
    print(f"  [{status}] '{food}' kept")

# ── 7. Raw candidate pool pre-filtering (topup_sections equivalent) ──────────
print(SEP)
print("7. filter_candidates — seafood blacklist pre-filters raw pool before selection")

raw_pool = [
    item("salmon"),
    item("tuna"),
    item("shrimp"),
    item("crab"),
    item("broccoli"),
    item("plain yogurt"),
    item("banana"),
]

fc, fk = resolve_forbidden(["seafood"])
safe_pool = filter_candidates(raw_pool, fc, fk)
safe_names = {i["food"].lower() for i in safe_pool}

for food in ["salmon", "tuna", "shrimp", "crab"]:
    status = "OK" if food not in safe_names else "FAIL"
    if food in safe_names:
        failures.append(f"filter_candidates: '{food}' survived seafood blacklist in pool")
    print(f"  [{status}] '{food}' removed from pool")

for food in ["broccoli", "plain yogurt", "banana"]:
    status = "OK" if food in safe_names else "FAIL"
    if food not in safe_names:
        failures.append(f"filter_candidates: '{food}' incorrectly removed from pool")
    print(f"  [{status}] '{food}' kept in pool")

# ── 8. Compound food names ────────────────────────────────────────────────────
print(SEP)
print("8. Compound food names — blacklist matches embedded keywords")

compound_cases = [
    # (food_name, blacklist_term, should_block)
    ("milkshake",           "dairy",   True),
    ("milkshake",           "milk",    True),
    ("peanut-butter toast", "nuts",    True),
    ("egg-based noodles",   "egg",     True),
    ("seafood pasta",       "seafood", True),
    ("chicken nuggets",     "meat",    True),
    # safe compounds — must not be blocked
    ("oat milkshake",       "seafood", False),
    ("vegetable pasta",     "egg",     False),
    ("tofu stir-fry",       "meat",    False),
]

for food, term, should_block in compound_cases:
    fc, fk = resolve_forbidden([term])
    blocked = is_item_forbidden(item(food), fc, fk)
    ok = blocked == should_block
    status = "OK" if ok else "FAIL"
    if not ok:
        expected = "blocked" if should_block else "allowed"
        failures.append(f"compound: '{food}' with blacklist=['{term}'] should be {expected}")
    action = "blocks" if should_block else "allows"
    print(f"  [{status}] [{term}] {action} '{food}'")

# ── Summary ──────────────────────────────────────────────────────────────────
print(SEP)
if failures:
    print(f"RESULT: FAIL — {len(failures)} issue(s):")
    for f in failures:
        print(f"  • {f}")
else:
    print("RESULT: PASS")
print(SEP)
