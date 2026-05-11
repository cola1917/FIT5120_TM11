"""
Deterministic unit tests for parse_model_output and build_user_prompt.

Uses fixed fake LLM strings — no API calls, no network, fully offline.

Tests all 3 parser layers:
  Layer 1: clean JSON
  Layer 2: markdown fence stripped
  Layer 3: regex extraction from text-wrapped JSON

Dynamic candidate count tests:
  - 3-item output  (no blacklist/allergies  → _llm_candidate_count returns 3)
  - 4-item output  (blacklist/allergies present → _llm_candidate_count returns 4)

Run:
    .venv/bin/python3 scripts/test_parser.py
"""
from __future__ import annotations
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.recommendation import (
    parse_model_output,
    build_user_prompt,
    _llm_candidate_count,
)

SEP = "=" * 60
failures: list[str] = []


def ok(label: str) -> None:
    print(f"  [OK]  {label}")


def fail(label: str, detail: str) -> None:
    print(f"  [FAIL] {label}: {detail}")
    failures.append(f"{label}: {detail}")


def assert_parsed(label: str, raw: str, expect_none: bool = False,
                  expected_super_count: int | None = None) -> None:
    result = parse_model_output(raw)
    if expect_none:
        if result is None:
            ok(label)
        else:
            fail(label, f"expected None, got {type(result)}")
        return
    if result is None:
        fail(label, "returned None — should have parsed successfully")
        return
    if not isinstance(result, dict):
        fail(label, f"expected dict, got {type(result)}")
        return
    if expected_super_count is not None:
        n = len(result.get("super_power_foods", []))
        if n != expected_super_count:
            fail(label, f"super_power_foods has {n} items, expected {expected_super_count}")
            return
    ok(label)


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_section(n: int) -> list[dict]:
    return [{"food": f"food_{i}", "reason": f"reason_{i}"} for i in range(n)]


def make_payload(n: int) -> dict:
    return {
        "goal": "grow",
        "super_power_foods": make_section(n),
        "tiny_hero_foods":   make_section(n),
        "try_less_foods":    make_section(n),
    }


# ── Dynamic candidate count ───────────────────────────────────────────────────
print(SEP)
print("Dynamic candidate count — _llm_candidate_count()")

def assert_count(label: str, blacklist: list, allergies: list, expected: int) -> None:
    got = _llm_candidate_count(blacklist, allergies)
    if got == expected:
        ok(label)
    else:
        fail(label, f"expected {expected}, got {got}")

assert_count("no blacklist, no allergies → 3", [], [], 3)
assert_count("blacklist present → 4",          ["seafood"], [], 4)
assert_count("allergies present → 4",          [], ["nuts"], 4)
assert_count("both present → 4",               ["egg"], ["dairy"], 4)

# ── Prompt embeds correct n ───────────────────────────────────────────────────
print(SEP)
print("build_user_prompt — embeds correct candidate count")

for n, label in [(3, "n=3 prompt"), (4, "n=4 prompt")]:
    prompt = build_user_prompt("grow", [], [], [], [], n_candidates=n)
    marker = f"EXACTLY {n} items"
    if marker in prompt:
        ok(f"{label} contains '{marker}'")
    else:
        fail(label, f"'{marker}' not found in prompt")
    # ensure the other count is NOT present
    wrong = 6 if n != 6 else 3
    wrong_marker = f"EXACTLY {wrong} items"
    if wrong_marker in prompt:
        fail(label, f"'{wrong_marker}' should not appear")

# ── Layer 1: clean JSON ───────────────────────────────────────────────────────
print(SEP)
print("Layer 1 — clean JSON direct parse")

assert_parsed("3-item clean JSON (no blacklist → n=3)",
              json.dumps(make_payload(3)),
              expected_super_count=3)

assert_parsed("4-item clean JSON (blacklist present → n=4)",
              json.dumps(make_payload(4)),
              expected_super_count=4)

assert_parsed("clean JSON with unicode",
              json.dumps({"goal": "feel", "super_power_foods": [{"food": "香蕉", "reason": "好吃"}],
                          "tiny_hero_foods": [], "try_less_foods": []}))

assert_parsed("JSON with trailing newline",
              json.dumps(make_payload(4)) + "\n\n",
              expected_super_count=4)

# ── Layer 2: markdown fence ───────────────────────────────────────────────────
print(SEP)
print("Layer 2 — markdown fence stripped")

payload_3 = json.dumps(make_payload(3), indent=2)
payload_4 = json.dumps(make_payload(4), indent=2)

assert_parsed("```json ... ``` fence  (3 items)",
              f"```json\n{payload_3}\n```",
              expected_super_count=3)

assert_parsed("```json ... ``` fence  (4 items)",
              f"```json\n{payload_4}\n```",
              expected_super_count=4)

assert_parsed("``` ... ``` fence (no language tag, 4 items)",
              f"```\n{payload_4}\n```",
              expected_super_count=4)

assert_parsed("fence with extra blank lines inside (4 items)",
              f"```json\n\n{payload_4}\n\n```",
              expected_super_count=4)

# ── Layer 3: JSON embedded in explanation text ────────────────────────────────
print(SEP)
print("Layer 3 — regex extraction from text-wrapped JSON")

assert_parsed("JSON after explanation sentence (4 items)",
              f"Here are the recommendations:\n{payload_4}",
              expected_super_count=4)

assert_parsed("JSON between paragraphs (4 items)",
              f"Sure! Here is your result.\n\n{payload_4}\n\nLet me know if you want changes.",
              expected_super_count=4)

assert_parsed("JSON after markdown heading (3 items)",
              f"## Recommendations\n\n{payload_3}",
              expected_super_count=3)

assert_parsed("JSON on same line as prefix text (3 items)",
              f"Result: {json.dumps(make_payload(3))}",
              expected_super_count=3)

# ── Robustness — None cases ───────────────────────────────────────────────────
print(SEP)
print("Robustness — should return None")

assert_parsed("empty string", "", expect_none=True)
assert_parsed("whitespace only", "   \n\t  ", expect_none=True)
assert_parsed("plain English, no JSON", "I cannot provide food recommendations.", expect_none=True)
assert_parsed("truncated JSON (cut mid-object)",
              '{"goal": "grow", "super_power_foods": [{"food": "milk"',
              expect_none=True)
assert_parsed("JSON array instead of object", json.dumps([1, 2, 3]), expect_none=True)
assert_parsed("markdown fence with no JSON inside", "```\nHello world\n```", expect_none=True)

# ── Schema content checks ─────────────────────────────────────────────────────
print(SEP)
print("Schema content — 3-item (no filter) and 4-item (with blacklist) realistic payloads")

real_3 = {
    "goal": "see",
    "super_power_foods": [
        {"food": "carrot",      "reason": "Vitamin A for eyes"},
        {"food": "spinach",     "reason": "Lutein for eyes"},
        {"food": "blueberries", "reason": "Antioxidants"},
    ],
    "tiny_hero_foods": [
        {"food": "mackerel",    "reason": "DHA for eyes"},
        {"food": "kale",        "reason": "Lutein hero"},
        {"food": "capsicum",    "reason": "Vitamin C"},
    ],
    "try_less_foods": [
        {"food": "chips",  "reason": "High salt"},
        {"food": "cola",   "reason": "High sugar"},
        {"food": "candy",  "reason": "Empty calories"},
    ],
}

real_4 = {
    "goal": "see",
    "super_power_foods": [
        {"food": "carrot",      "reason": "Vitamin A for eyes"},
        {"food": "spinach",     "reason": "Lutein for eyes"},
        {"food": "blueberries", "reason": "Antioxidants"},
        {"food": "sweet potato","reason": "Beta-carotene"},
    ],
    "tiny_hero_foods": [
        {"food": "mackerel",    "reason": "DHA for eyes"},
        {"food": "kale",        "reason": "Lutein hero"},
        {"food": "capsicum",    "reason": "Vitamin C"},
        {"food": "sardine",     "reason": "Omega-3s"},
    ],
    "try_less_foods": [
        {"food": "chips",          "reason": "High salt"},
        {"food": "cola",           "reason": "High sugar"},
        {"food": "instant noodles","reason": "Low vitamins"},
        {"food": "candy",          "reason": "Empty calories"},
    ],
}

for expected_n, payload, label in [
    (3, real_3, "3-item realistic payload (no blacklist)"),
    (4, real_4, "4-item realistic payload (with blacklist)"),
]:
    result = parse_model_output(json.dumps(payload))
    if result is None:
        fail(label, "returned None")
    else:
        for section in ["super_power_foods", "tiny_hero_foods", "try_less_foods"]:
            items = result.get(section, [])
            if len(items) == expected_n:
                ok(f"{label} — {section} has {expected_n} items")
            else:
                fail(f"{label} — {section} item count", f"got {len(items)}, expected {expected_n}")
        for section in ["super_power_foods", "tiny_hero_foods", "try_less_foods"]:
            for item in result.get(section, []):
                if "food" not in item or "reason" not in item:
                    fail(f"{label} — {section} structure", f"missing key in {item}")
                    break
            else:
                ok(f"{label} — {section} items have 'food'+'reason'")

# ── Combined: fence + realistic payloads ─────────────────────────────────────
print(SEP)
print("Combined — fence wrapping around 3-item and 4-item payloads")

assert_parsed("fenced 3-item schema (no blacklist case)",
              "```json\n" + json.dumps(real_3, indent=2) + "\n```",
              expected_super_count=3)

assert_parsed("fenced 4-item schema (blacklist case)",
              "```json\n" + json.dumps(real_4, indent=2) + "\n```",
              expected_super_count=4)

# ── Summary ───────────────────────────────────────────────────────────────────
print(SEP)
if failures:
    print(f"RESULT: FAIL — {len(failures)} issue(s):")
    for f in failures:
        print(f"  • {f}")
else:
    print("RESULT: PASS")
print(SEP)
