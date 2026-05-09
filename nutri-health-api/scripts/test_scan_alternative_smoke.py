"""
Step 1 — Smoke test: verify the fine-tuned model follows the new
alternative_generation schema (alternatives list + alternative_reason).

Run:
    /usr/bin/python3 scripts/test_scan_alternative_smoke.py

Prints raw model output for each test food so you can judge:
  - Does the model output "alternatives" as a list (not "better_alternative")?
  - Are names specific foods (not broad categories)?
  - Does alternative_reason explain why the alternative is good?

No pass/fail in this step — human review only.
After reviewing, run with --validate to add automated checks.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.load_env import ensure_dotenv_loaded
ensure_dotenv_loaded()

if not os.getenv("OPENAI_API_KEY"):
    _env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(_env):
        with open(_env) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

from app.services.scan_alternative_service import (
    _MODEL as MODEL,
    _TEMPERATURE as TEMP,
    _TOP_P as TOP_P,
    _SCORE_TO_HEALTH_LEVEL,
    call_alternative_model,
    build_alternative_prompt,
)

# (food_name, assessment_score, expected_has_alternatives)
TEST_FOODS = [
    ("chips",            1, True),
    ("cola",             1, True),
    ("cake",             1, True),
    ("ice cream",        1, True),
    ("candy",            1, True),
    ("fried chicken",    1, True),
    ("burger",           2, True),
    ("instant noodles",  2, True),
    ("french fries",     2, True),
    ("chocolate cookie", 1, True),
    ("apple",            3, False),
    ("salmon",           3, False),
]

SEP = "=" * 65

VALIDATE = "--validate" in sys.argv

# Terms that must never appear as candy alternatives (hard FAIL in validate mode)
CANDY_JUNK_TERMS: frozenset[str] = frozenset({
    "cake", "ice cream", "candy", "cookie", "cookies",
    "soda", "chips", "fries", "french fries",
})

# Context checks: if alternative name is exactly one of these single words,
# it is considered too vague for the given food type → WARN (not FAIL).
_CONTEXT_CHECKS: dict[str, dict] = {
    "burger": {
        "bad_single_words": {"chicken", "fish", "beef", "meat", "turkey", "pork"},
        "bad_exact_names": {"turkey burger", "chicken wrap"},
        "good_names": {
            "whole-grain chicken sandwich", "whole-grain fish sandwich",
            "lean beef sandwich", "veggie burger",
        },
        "hint": "should be burger-like e.g. 'whole-grain chicken sandwich', 'veggie burger'",
    },
    "instant noodles": {
        "bad_single_words": {"carrot", "cucumber", "vegetable", "broccoli", "spinach"},
        "hint": "should be a noodle/grain dish e.g. 'noodle soup with vegetables'",
    },
}


_failures: list[str] = []


def run_food(food_name: str, score: int, expect_alternatives: bool) -> None:
    print(SEP)
    print(f"Food: {food_name!r}  score={score}  expect_alternatives={expect_alternatives}")

    if score >= 3:
        print("  → score >= 3, skipping model call (alternatives should be [])")
        return

    health_level = _SCORE_TO_HEALTH_LEVEL.get(score, "sometimes")
    raw = call_alternative_model(food_name, health_level)
    print(f"  RAW OUTPUT:\n  {raw}")

    if VALIDATE:
        # Parse
        try:
            parsed = json.loads(raw.strip())
        except json.JSONDecodeError:
            print("  [FAIL] Cannot parse JSON")
            _failures.append(f"{food_name}: JSON parse failed")
            return

        alts = parsed.get("alternatives", [])

        # Count check
        if len(alts) == 0:
            print("  [FAIL] alternatives is empty")
            _failures.append(f"{food_name}: alternatives empty")
            return

        print(f"  alternatives count: {len(alts)}")

        BROAD_CATEGORIES = {
            "fruit", "fruits", "vegetable", "vegetables",
            "healthy snack", "drink", "drinks", "dairy",
            "snack", "food", "meal",
        }

        context_check = _CONTEXT_CHECKS.get(food_name.lower())

        for i, alt in enumerate(alts):
            name   = alt.get("name", "").strip()
            reason = alt.get("alternative_reason", "").strip()
            print(f"  [{i}] name={name!r}")
            print(f"       reason={reason!r}")

            # FAIL: empty name
            if not name:
                print(f"  [FAIL] alt[{i}] name is empty")
                _failures.append(f"{food_name}: alt[{i}] name empty")
                continue

            # FAIL: name is a broad category word
            if name.lower() in BROAD_CATEGORIES:
                print(f"  [FAIL] alt[{i}] name is a broad category: {name!r}")
                _failures.append(f"{food_name}: alt[{i}] broad category name")

            # FAIL: empty reason
            if not reason:
                print(f"  [FAIL] alt[{i}] alternative_reason is empty")
                _failures.append(f"{food_name}: alt[{i}] reason empty")

            # WARN: single-word name (may be too vague, but not a hard failure)
            if len(name.split()) < 2:
                print(f"  [WARN] alt[{i}] name is a single word — may lack context: {name!r}")

            # WARN / FAIL: context mismatch for specific foods
            if context_check:
                name_lower = name.lower()
                bad_single = context_check.get("bad_single_words", set())
                bad_exact  = context_check.get("bad_exact_names", set())
                good_names = context_check.get("good_names", set())

                if name_lower in bad_single and len(name.split()) < 2:
                    print(
                        f"  [WARN] alt[{i}] {name!r} is too plain for {food_name!r} "
                        f"— {context_check['hint']}"
                    )
                elif name_lower in bad_exact:
                    print(
                        f"  [FAIL] alt[{i}] {name!r} is not accepted for {food_name!r} "
                        f"— {context_check['hint']}"
                    )
                    _failures.append(f"{food_name}: alt[{i}] unaccepted name {name!r}")
                elif good_names and name_lower in good_names:
                    print(f"  [GOOD] alt[{i}] {name!r} is a preferred alternative ✓")

            # Hard FAIL: candy must never return junk food as an alternative
            if food_name.lower() == "candy":
                name_lower = name.lower()
                for junk in CANDY_JUNK_TERMS:
                    if junk in name_lower:
                        print(
                            f"  [FAIL] candy: alt[{i}] {name!r} contains junk term {junk!r}"
                        )
                        _failures.append(
                            f"{food_name}: alt[{i}] junk alternative {name!r} (term={junk!r})"
                        )
                        break

        print("  [OK]")
    print()


def main() -> None:
    print(f"\nModel:       {MODEL}")
    print(f"Temperature: {TEMP}")
    print(f"Top-p:       {TOP_P}")
    print(f"Mode:        {'VALIDATE' if VALIDATE else 'OBSERVE (raw output only)'}\n")

    for food_name, score, expect_alts in TEST_FOODS:
        run_food(food_name, score, expect_alts)

    if VALIDATE:
        print(SEP)
        if _failures:
            print(f"RESULT: FAIL — {len(_failures)} issue(s):")
            for f in _failures:
                print(f"  • {f}")
        else:
            print("RESULT: PASS")
        print(SEP)


if __name__ == "__main__":
    main()
