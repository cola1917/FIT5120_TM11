"""
Deterministic tests for the reason builder and reason endpoint schema.

Sections:
  1. Non-empty output for every goal × section combination
  2. Sentence count ≤ 3 for every output
  3. Reason changes when goal_id changes (same food, same section)
  4. super_power reason references goal label/benefit
  5. tiny_hero with disliked category → encouraging, no shame
  6. tiny_hero with non-disliked category → still encouraging
  7. try_less avoids all banned words
  8. likes-aware: super_power with liked category mentions it
  9. No LLM call during reason generation (OpenAI patched to raise on use)
  10. ReasonResponse schema has all required fields
  11. Unknown goal_id falls back gracefully (no crash)
  12. Unknown section_name falls back gracefully (no crash)

Run:
    .venv/bin/python3 scripts/test_reason.py
"""
from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.reason_builder import (
    BANNED_WORDS,
    GOAL_INFO,
    build_personalized_reason,
)
from app.schemas.reason import ReasonRequest, ReasonResponse

SEP = "=" * 65
failures: list[str] = []

GOALS    = list(GOAL_INFO.keys())
SECTIONS = ["super_power_foods", "tiny_hero_foods", "try_less_foods"]


def ok(label: str) -> None:
    print(f"  [OK]  {label}")


def fail(label: str, detail: str) -> None:
    print(f"  [FAIL] {label}: {detail}")
    failures.append(f"{label}: {detail}")


def sentence_count(text: str) -> int:
    """Count sentences by splitting on '.', '!', '?'."""
    import re
    parts = re.split(r"[.!?]+", text.strip())
    return len([p for p in parts if p.strip()])


# ── 1. Non-empty for every goal × section ─────────────────────────────────────
print(SEP)
print("1. Non-empty output — every goal × section combination")

for goal_id in GOALS:
    for section in SECTIONS:
        reason = build_personalized_reason(
            food_name="broccoli", category="vegetables",
            section_name=section, goal_id=goal_id,
        )
        if reason and len(reason.strip()) > 0:
            ok(f"goal={goal_id} section={section} → non-empty")
        else:
            fail(f"goal={goal_id} section={section}", "returned empty string")

# ── 2. Sentence count ≤ 3 ─────────────────────────────────────────────────────
print(SEP)
print("2. Sentence count ≤ 3 — all goal × section × food combinations")

test_foods = [
    ("banana",      "fruits"),
    ("broccoli",    "vegetables"),
    ("salmon",      "fish"),
    ("plain yogurt","dairy"),
    ("chips",       "snacks"),
    ("cola",        "drinks"),
]

for goal_id in GOALS:
    for section in SECTIONS:
        for food_name, category in test_foods:
            reason = build_personalized_reason(
                food_name=food_name, category=category,
                section_name=section, goal_id=goal_id,
                likes=["fruits", "dairy"], dislikes=["vegetables"],
            )
            n = sentence_count(reason)
            if n <= 3:
                ok(f"goal={goal_id} section={section} '{food_name}' → {n} sentence(s)")
            else:
                fail(
                    f"sentence count: goal={goal_id} section={section} '{food_name}'",
                    f"got {n} sentences: {reason!r}",
                )

# ── 3. Reason changes when goal_id changes ────────────────────────────────────
print(SEP)
print("3. Reason varies by goal_id")

reasons_by_goal = {
    g: build_personalized_reason(
        food_name="carrot", category="vegetables",
        section_name="super_power_foods", goal_id=g,
    )
    for g in GOALS
}
unique_reasons = set(reasons_by_goal.values())
if len(unique_reasons) == len(GOALS):
    ok(f"all {len(GOALS)} goals produce distinct reasons")
else:
    fail("goal variation", f"only {len(unique_reasons)} unique reasons for {len(GOALS)} goals")

# spot-check that the goal label appears in the reason
for goal_id, reason in reasons_by_goal.items():
    label = GOAL_INFO[goal_id]["label"]
    if label in reason:
        ok(f"goal={goal_id}: label '{label}' appears in reason")
    else:
        fail(f"goal label missing: goal={goal_id}", f"reason={reason!r}")

# ── 4. super_power references goal label ──────────────────────────────────────
print(SEP)
print("4. super_power_foods reason references goal label and benefit")

for goal_id in GOALS:
    reason = build_personalized_reason(
        food_name="blueberries", category="fruits",
        section_name="super_power_foods", goal_id=goal_id,
    )
    label   = GOAL_INFO[goal_id]["label"]
    benefit = GOAL_INFO[goal_id]["benefit"]
    if label in reason:
        ok(f"goal={goal_id}: label '{label}' in super_power reason")
    else:
        fail(f"goal={goal_id} super_power label", f"reason={reason!r}")
    if benefit in reason:
        ok(f"goal={goal_id}: benefit phrase in super_power reason")
    else:
        fail(f"goal={goal_id} super_power benefit", f"reason={reason!r}")

# ── 5. tiny_hero with disliked category → encouraging, no shame ───────────────
print(SEP)
print("5. tiny_hero with disliked category — encouraging, no shame")

SHAME_WORDS = {"shame", "wrong", "bad", "must", "should", "hate", "gross",
               "disgust", "force", "never"}

for goal_id in GOALS:
    reason = build_personalized_reason(
        food_name="spinach", category="vegetables",
        section_name="tiny_hero_foods", goal_id=goal_id,
        dislikes=["vegetables"],
    )
    # Must mention the tiny hero encouragement
    if "tiny hero" in reason.lower():
        ok(f"goal={goal_id} tiny_hero (disliked): contains 'tiny hero'")
    else:
        fail(f"goal={goal_id} tiny_hero (disliked) encouragement", f"reason={reason!r}")

    # Must NOT contain shame words
    found_shame = [w for w in SHAME_WORDS if w in reason.lower()]
    if not found_shame:
        ok(f"goal={goal_id} tiny_hero (disliked): no shame words")
    else:
        fail(f"goal={goal_id} tiny_hero shame words", f"found {found_shame} in {reason!r}")

    # Must mention the disliked category gently
    if "vegetables" in reason.lower():
        ok(f"goal={goal_id} tiny_hero (disliked): mentions category gently")
    else:
        fail(f"goal={goal_id} tiny_hero category mention", f"reason={reason!r}")

# ── 6. tiny_hero with non-disliked category → still encouraging ───────────────
print(SEP)
print("6. tiny_hero with non-disliked category — still encouraging")

for goal_id in GOALS[:3]:  # sample: grow, see, think
    reason = build_personalized_reason(
        food_name="edamame", category="beans",
        section_name="tiny_hero_foods", goal_id=goal_id,
        dislikes=[],
    )
    if "tiny hero" in reason.lower():
        ok(f"goal={goal_id} tiny_hero (not disliked): contains 'tiny hero'")
    else:
        fail(f"goal={goal_id} tiny_hero (not disliked) encouragement", f"reason={reason!r}")

# ── 7. try_less avoids all banned words ───────────────────────────────────────
print(SEP)
print("7. try_less avoids banned words")

for goal_id in GOALS:
    for food_name, category in [("chips", "snacks"), ("cola", "drinks"), ("candy", "snacks")]:
        reason = build_personalized_reason(
            food_name=food_name, category=category,
            section_name="try_less_foods", goal_id=goal_id,
        )
        reason_lower = reason.lower()
        found_banned = [w for w in BANNED_WORDS if w in reason_lower]
        if not found_banned:
            ok(f"goal={goal_id} try_less '{food_name}': no banned words")
        else:
            fail(
                f"goal={goal_id} try_less '{food_name}' banned words",
                f"found {found_banned} in {reason!r}",
            )

# ── 8. likes-aware: liked category mentioned in super_power ───────────────────
print(SEP)
print("8. likes-aware — liked category mentioned in super_power reason")

for goal_id in GOALS[:3]:
    reason_liked = build_personalized_reason(
        food_name="banana", category="fruits",
        section_name="super_power_foods", goal_id=goal_id,
        likes=["fruits"],
    )
    reason_not_liked = build_personalized_reason(
        food_name="banana", category="fruits",
        section_name="super_power_foods", goal_id=goal_id,
        likes=[],
    )
    if "fruits" in reason_liked.lower():
        ok(f"goal={goal_id}: liked category 'fruits' mentioned when in likes")
    else:
        fail(f"goal={goal_id} likes mention", f"reason={reason_liked!r}")

    if reason_liked != reason_not_liked:
        ok(f"goal={goal_id}: reason differs when category is liked vs not liked")
    else:
        fail(f"goal={goal_id} likes variation", "liked and not-liked reasons are identical")

# ── 9. No LLM call during reason generation ───────────────────────────────────
print(SEP)
print("9. No LLM call — OpenAI client raises if instantiated")

class _NoLLMError(Exception):
    pass

class _BoomClient:
    def __init__(self, *a, **kw):
        raise _NoLLMError("OpenAI client was instantiated during reason generation!")

try:
    with patch.dict("sys.modules", {"openai": MagicMock(OpenAI=_BoomClient)}):
        reason = build_personalized_reason(
            food_name="carrot", category="vegetables",
            section_name="super_power_foods", goal_id="grow",
            likes=[], dislikes=[],
        )
    if reason:
        ok(f"build_personalized_reason ran without touching OpenAI: {reason!r}")
    else:
        fail("no-LLM check", "returned empty reason")
except _NoLLMError as e:
    fail("no-LLM check", str(e))

# ── 10. ReasonResponse schema ─────────────────────────────────────────────────
print(SEP)
print("10. ReasonResponse schema — required fields present")

for section in SECTIONS:
    reason_text = build_personalized_reason(
        food_name="mango", category="fruits",
        section_name=section, goal_id="feel",
        likes=["fruits"], dislikes=[],
    )
    resp = ReasonResponse(food_id="mango", food_name="mango", reason=reason_text)
    for field in ("food_id", "food_name", "reason"):
        val = getattr(resp, field, None)
        if val is not None and val != "":
            ok(f"section={section}: ReasonResponse.{field}={val!r}")
        else:
            fail(f"section={section} ReasonResponse.{field}", "missing or empty")

# ── 11. Unknown goal_id falls back gracefully ─────────────────────────────────
print(SEP)
print("11. Unknown goal_id — no crash, sensible fallback")

reason = build_personalized_reason(
    food_name="carrot", category="vegetables",
    section_name="super_power_foods", goal_id="fly_to_moon",
)
if reason and len(reason.strip()) > 0:
    ok(f"unknown goal_id → fallback reason: {reason!r}")
else:
    fail("unknown goal_id fallback", "returned empty or None")

# ── 12. Unknown section_name falls back gracefully ────────────────────────────
print(SEP)
print("12. Unknown section_name — no crash, sensible fallback")

reason = build_personalized_reason(
    food_name="carrot", category="vegetables",
    section_name="mystery_section", goal_id="grow",
)
if reason and len(reason.strip()) > 0:
    ok(f"unknown section_name → fallback reason: {reason!r}")
else:
    fail("unknown section_name fallback", "returned empty or None")

# ── 13. Plural / singular grammar ────────────────────────────────────────────
print(SEP)
print("13. Plural/singular grammar — is/are, it/they, does/do, category agreement")

from app.services.reason_builder import _is_are, _it_they, _does_do, _is_plural  # noqa

# _is_plural helper
for name, expected in [
    ("blueberries", True), ("chips", True), ("noodles", True),
    ("carrots", True), ("oats", True), ("steel-cut oats", True),
    ("chocolate chips", True), ("mixed berries", True),
    ("banana", False), ("salmon", False), ("spinach", False),
    ("broccoli", False), ("sweet potato", False), ("rice", False),
    ("bass", False), ("hummus", False), ("asparagus", False), ("couscous", False),
]:
    got = _is_plural(name)
    if got == expected:
        ok(f"_is_plural({name!r}) = {got}")
    else:
        fail(f"_is_plural({name!r})", f"got {got}, want {expected}")

# Plural food → "are" / "they" / "do" in super_power sentence
PLURAL_FOODS = [
    ("blueberries", "fruits"),
    ("chips",       "snacks"),
    ("noodles",     "noodles"),
    ("carrots",     "vegetables"),
]
SINGULAR_FOODS = [
    ("banana",  "fruits"),
    ("salmon",  "fish"),
    ("spinach", "vegetables"),
]

for food_name, category in PLURAL_FOODS:
    reason = build_personalized_reason(
        food_name=food_name, category=category,
        section_name="super_power_foods", goal_id="think",
    )
    # Sentence 1: "{food} are a great choice … because they can …"
    if f"{food_name} are" in reason:
        ok(f"super_power plural: '{food_name} are' present")
    else:
        fail(f"super_power plural '{food_name}'", f"expected '{food_name} are' in: {reason!r}")
    if "because they can" in reason:
        ok(f"super_power plural: 'because they can' present for '{food_name}'")
    else:
        fail(f"super_power plural 'they' for '{food_name}'", f"reason={reason!r}")

for food_name, category in SINGULAR_FOODS:
    reason = build_personalized_reason(
        food_name=food_name, category=category,
        section_name="super_power_foods", goal_id="think",
    )
    if f"{food_name} is" in reason:
        ok(f"super_power singular: '{food_name} is' present")
    else:
        fail(f"super_power singular '{food_name}'", f"expected '{food_name} is' in: {reason!r}")
    if "because it can" in reason:
        ok(f"super_power singular: 'because it can' present for '{food_name}'")
    else:
        fail(f"super_power singular 'it' for '{food_name}'", f"reason={reason!r}")

# try_less: plural → "they do not", singular → "it does not"
for food_name, category in PLURAL_FOODS:
    reason = build_personalized_reason(
        food_name=food_name, category=category,
        section_name="try_less_foods", goal_id="strong",
    )
    if "they do not" in reason:
        ok(f"try_less plural: 'they do not' for '{food_name}'")
    else:
        fail(f"try_less plural 'they do not' for '{food_name}'", f"reason={reason!r}")

for food_name, category in SINGULAR_FOODS:
    reason = build_personalized_reason(
        food_name=food_name, category=category,
        section_name="try_less_foods", goal_id="strong",
    )
    if "it does not" in reason:
        ok(f"try_less singular: 'it does not' for '{food_name}'")
    else:
        fail(f"try_less singular 'it does not' for '{food_name}'", f"reason={reason!r}")

# tiny_hero disliked: plural category → "are not your favorite", singular → "is not"
for cat_name, is_plural_cat in [
    ("vegetables", True), ("fruits", True), ("noodles", True),
    ("dairy", False), ("fish", False), ("meat", False), ("rice", False),
]:
    reason = build_personalized_reason(
        food_name="broccoli", category=cat_name,
        section_name="tiny_hero_foods", goal_id="grow",
        dislikes=[cat_name],
    )
    expected_verb = "are" if is_plural_cat else "is"
    if f"{cat_name} {expected_verb} not your favorite" in reason:
        ok(f"tiny_hero disliked category='{cat_name}': '{expected_verb}' correct")
    else:
        fail(
            f"tiny_hero disliked '{cat_name}' verb",
            f"expected '{cat_name} {expected_verb} not your favorite' in: {reason!r}",
        )

# liked category in super_power: "they can" for plural, "it can" for singular
for food_name, category in [("blueberries", "fruits"), ("banana", "fruits")]:
    reason = build_personalized_reason(
        food_name=food_name, category=category,
        section_name="super_power_foods", goal_id="feel",
        likes=[category],
    )
    expected_pronoun = "they" if _is_plural(food_name) else "it"
    if f"Since you like {category}, {expected_pronoun} can" in reason:
        ok(f"super_power liked: '{food_name}' → 'Since you like {category}, {expected_pronoun} can'")
    else:
        fail(
            f"super_power liked pronoun for '{food_name}'",
            f"expected 'Since you like {category}, {expected_pronoun} can' in: {reason!r}",
        )

# ── 14. Category benefit pronoun matches food name, not category ──────────────
print(SEP)
print("14. Category benefit pronoun derived from food_name, not category")

# singular food in plural category → "It can add..."
for food_name, category, expected_fragment in [
    ("mango",  "fruits",     "It can add natural sweetness"),
    ("carrot", "vegetables", "It can add color"),
    ("banana", "fruits",     "It can add natural sweetness"),
]:
    reason = build_personalized_reason(
        food_name=food_name, category=category,
        section_name="super_power_foods", goal_id="feel",
    )
    if expected_fragment in reason:
        ok(f"singular '{food_name}' in '{category}': '{expected_fragment}' ✓")
    else:
        fail(
            f"singular '{food_name}' in '{category}' benefit pronoun",
            f"expected '{expected_fragment}' in: {reason!r}",
        )

# plural food in plural category → "They can add..."
for food_name, category, expected_fragment in [
    ("blueberries", "fruits",     "They can add natural sweetness"),
    ("carrots",     "vegetables", "They can add color"),
    ("grapes",      "fruits",     "They can add natural sweetness"),
]:
    reason = build_personalized_reason(
        food_name=food_name, category=category,
        section_name="super_power_foods", goal_id="think",
    )
    if expected_fragment in reason:
        ok(f"plural '{food_name}' in '{category}': '{expected_fragment}' ✓")
    else:
        fail(
            f"plural '{food_name}' in '{category}' benefit pronoun",
            f"expected '{expected_fragment}' in: {reason!r}",
        )

# singular food in singular category → "It can..."
for food_name, category, expected_fragment in [
    ("salmon",  "fish",  "It can give your body helpful protein"),
    ("tofu",    "beans", "It can give your body plant protein"),
]:
    reason = build_personalized_reason(
        food_name=food_name, category=category,
        section_name="super_power_foods", goal_id="strong",
    )
    if expected_fragment in reason:
        ok(f"singular '{food_name}' in '{category}': '{expected_fragment}' ✓")
    else:
        fail(
            f"singular '{food_name}' in '{category}' benefit pronoun",
            f"expected '{expected_fragment}' in: {reason!r}",
        )

# ── Summary ───────────────────────────────────────────────────────────────────
print(SEP)
if failures:
    print(f"RESULT: FAIL — {len(failures)} issue(s):")
    for f in failures:
        print(f"  • {f}")
else:
    print("RESULT: PASS")
print(SEP)
