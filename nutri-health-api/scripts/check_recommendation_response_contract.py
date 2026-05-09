"""
Backend response compatibility contract checker.

Calls the recommendation service directly and checks every item in
super_power_foods / tiny_hero_foods / try_less_foods against:

  Old frontend-compatible fields : cn_code, name, category, grade, image_url
  New fields                     : food_id, food_name, image_status, reason

Alias consistency checks:
  cn_code     == food_id
  name        == food_name
  grade       == reason
  image_url   is not empty
  image_status in {fallback, ready, pending, failed}

Prints a pass/fail summary per scenario and an overall result.

Usage:
    /usr/bin/python3 scripts/check_recommendation_response_contract.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── env loading ──────────────────────────────────────────────────────────────
from app.load_env import ensure_dotenv_loaded

ensure_dotenv_loaded()

if not os.getenv("OPENAI_API_KEY"):
    _env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(_env_path):
        with open(_env_path) as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _k, _v = _line.split("=", 1)
                    os.environ.setdefault(_k.strip(), _v.strip())

from app.services.enrichment import enrich_recommendation_items
from app.services.filter import filter_output, filter_tiny_hero_by_likes
from app.services.recommendation import call_model, parse_model_output

# ── contract definition ───────────────────────────────────────────────────────

OLD_REQUIRED_FIELDS = ["cn_code", "name", "category", "grade", "image_url"]
NEW_REQUIRED_FIELDS = ["food_id", "food_name", "image_status", "reason"]
VALID_IMAGE_STATUSES = {"fallback", "ready", "pending", "failed"}

SECTIONS = ["super_power_foods", "tiny_hero_foods", "try_less_foods"]

SCENARIOS = [
    dict(goal="grow",   likes=["dairy", "meat"],        dislikes=[],                    blacklist=[],       allergies=[]),
    dict(goal="see",    likes=["fruits"],               dislikes=["fish"],              blacklist=[],       allergies=[]),
    dict(goal="think",  likes=[],                       dislikes=[],                    blacklist=[],       allergies=[]),
    dict(goal="fight",  likes=["snacks"],               dislikes=["fruits", "vegetables"], blacklist=[],    allergies=[]),
    dict(goal="feel",   likes=["fruits", "noodles"],    dislikes=[],                    blacklist=[],       allergies=[]),
    dict(goal="strong", likes=["meat"],                 dislikes=["dairy", "fish"],     blacklist=[],       allergies=[]),
]

# ── helpers ───────────────────────────────────────────────────────────────────

def _check_item(item: dict, section: str, idx: int) -> list[str]:
    """Return list of failure messages for a single item dict."""
    failures: list[str] = []
    prefix = f"  [{section}][{idx}] '{item.get('food_name') or item.get('name', '?')}'"

    # Old fields
    for field in OLD_REQUIRED_FIELDS:
        if field not in item:
            failures.append(f"{prefix} MISSING old field: {field}")

    # New fields
    for field in NEW_REQUIRED_FIELDS:
        if field not in item:
            failures.append(f"{prefix} MISSING new field: {field}")

    # Alias consistency (only if both sides present)
    if "cn_code" in item and "food_id" in item:
        if item["cn_code"] != item["food_id"]:
            failures.append(
                f"{prefix} MISMATCH cn_code={item['cn_code']!r} != food_id={item['food_id']!r}"
            )
    if "name" in item and "food_name" in item:
        if item["name"] != item["food_name"]:
            failures.append(
                f"{prefix} MISMATCH name={item['name']!r} != food_name={item['food_name']!r}"
            )
    if "grade" in item and "reason" in item:
        if item["grade"] != item["reason"]:
            failures.append(
                f"{prefix} MISMATCH grade={item['grade']!r} != reason={item['reason']!r}"
            )

    # image_url not empty
    if "image_url" in item and not str(item["image_url"]).strip():
        failures.append(f"{prefix} image_url is empty")

    # image_status valid
    if "image_status" in item:
        if item["image_status"] not in VALID_IMAGE_STATUSES:
            failures.append(
                f"{prefix} image_status={item['image_status']!r} not in {VALID_IMAGE_STATUSES}"
            )

    return failures


def run_scenario(idx: int, scenario: dict) -> tuple[bool, list[str]]:
    """Run one scenario through the pipeline and check the response contract.

    Returns (passed: bool, failure_messages: list[str]).
    """
    raw     = call_model(**scenario)
    parsed  = parse_model_output(raw)
    filtered = filter_output(parsed, scenario["blacklist"], scenario["allergies"])
    filtered = filter_tiny_hero_by_likes(filtered, scenario["likes"])

    if filtered is None:
        return False, [f"  Scenario {idx:02d}: pipeline returned None"]

    # Build response dict mirroring what the router returns
    response: dict[str, list[dict]] = {}
    for section in SECTIONS:
        enriched_items = enrich_recommendation_items(filtered.get(section, []))
        # Convert each EnrichedFoodItem to dict
        response[section] = [item.model_dump() for item in enriched_items]

    all_failures: list[str] = []
    for section in SECTIONS:
        for i, item in enumerate(response[section]):
            all_failures.extend(_check_item(item, section, i))

    return len(all_failures) == 0, all_failures


# ── main ──────────────────────────────────────────────────────────────────────

SEP = "=" * 70

def main() -> None:
    print(f"\nRunning contract check on {len(SCENARIOS)} scenarios...\n")

    total_pass = 0
    total_fail = 0
    all_failures: list[str] = []

    for idx, scenario in enumerate(SCENARIOS, start=1):
        label = (
            f"S{idx:02d} goal={scenario['goal']} "
            f"likes={scenario['likes']} dislikes={scenario['dislikes']}"
        )
        passed, failures = run_scenario(idx, scenario)

        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {label}")
        for msg in failures:
            print(f"        {msg}")
        if passed:
            total_pass += 1
        else:
            total_fail += 1
            all_failures.extend(failures)

    print()
    print(SEP)
    print(f"  Scenarios passed : {total_pass}/{len(SCENARIOS)}")
    print(f"  Scenarios failed : {total_fail}/{len(SCENARIOS)}")
    print()

    if all_failures:
        print("  FAILURES SUMMARY:")
        for msg in all_failures:
            print(f"    {msg}")
        print()

        # Identify which field groups are systematically missing
        missing_old = sorted({
            f.split("old field: ")[-1]
            for f in all_failures if "MISSING old field" in f
        })
        missing_new = sorted({
            f.split("new field: ")[-1]
            for f in all_failures if "MISSING new field" in f
        })
        if missing_old:
            print(f"  Old fields missing from all responses : {missing_old}")
            print("  → To fix: add computed aliases (cn_code=food_id, name=food_name,")
            print("             grade=reason) to EnrichedFoodItem in app/schemas/recommendation.py")
        if missing_new:
            print(f"  New fields missing from all responses : {missing_new}")
        print()
        print("  OVERALL RESULT: FAIL")
    else:
        print("  OVERALL RESULT: PASS")

    print(SEP)


if __name__ == "__main__":
    main()
