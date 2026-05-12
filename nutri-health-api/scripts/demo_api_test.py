"""
Demo test for the AI recommendation pipeline.

Runs 15 real user scenarios directly through the service layer
(no HTTP server required) and prints raw model output + final
filtered/enriched response for each case.

Usage:
    python scripts/demo_api_test.py
"""

from __future__ import annotations

import json
import os
import sys

# Allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.load_env import ensure_dotenv_loaded

ensure_dotenv_loaded()

# Fallback: if dotenv is unavailable, parse .env manually
if not os.getenv("OPENAI_API_KEY"):
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        with open(env_path) as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _k, _v = _line.split("=", 1)
                    os.environ.setdefault(_k.strip(), _v.strip())

from app.services.enrichment import enrich_recommendation_items
from app.services.filter import filter_output, filter_tiny_hero_by_likes
from app.services.recommendation import call_model, parse_model_output

# ─── Test scenarios ───────────────────────────────────────────────────────────

SCENARIOS: list[dict] = [
    # 1. grow — likes dairy, dislikes vegetables
    dict(goal="grow", likes=["dairy"], dislikes=["vegetables"], blacklist=[], allergies=[]),
    # 2. grow — likes meat and dairy, dislikes nothing
    dict(goal="grow", likes=["meat", "dairy"], dislikes=[], blacklist=[], allergies=[]),
    # 3. see — likes fruits, dislikes fish
    dict(goal="see", likes=["fruits"], dislikes=["fish"], blacklist=[], allergies=[]),
    # 4. see — likes vegetables and fruits, blacklists carrots
    dict(goal="see", likes=["vegetables", "fruits"], dislikes=[], blacklist=["carrot"], allergies=[]),
    # 5. think — likes dairy, dislikes fish and beans
    dict(goal="think", likes=["dairy"], dislikes=["fish", "beans"], blacklist=[], allergies=[]),
    # 6. think — no likes or dislikes
    dict(goal="think", likes=[], dislikes=[], blacklist=[], allergies=[]),
    # 7. fight — likes fruits and vegetables
    dict(goal="fight", likes=["fruits", "vegetables"], dislikes=[], blacklist=[], allergies=[]),
    # 8. fight — likes snacks, dislikes fruits and vegetables
    dict(goal="fight", likes=["snacks"], dislikes=["fruits", "vegetables"], blacklist=[], allergies=[]),
    # 9. feel — likes fruits and noodles
    dict(goal="feel", likes=["fruits", "noodles"], dislikes=[], blacklist=[], allergies=[]),
    # 10. feel — likes snacks, dislikes everything healthy
    dict(goal="feel", likes=["snacks"], dislikes=["fruits", "vegetables", "dairy"], blacklist=[], allergies=[]),
    # 11. strong — likes meat, dislikes dairy and fish
    dict(goal="strong", likes=["meat"], dislikes=["dairy", "fish"], blacklist=[], allergies=[]),
    # 12. strong — no preferences, nut allergy
    dict(goal="strong", likes=[], dislikes=[], blacklist=[], allergies=["peanut", "nut"]),
    # 13. grow — egg allergy, blacklists milk
    dict(goal="grow", likes=["dairy", "meat"], dislikes=[], blacklist=["milk"], allergies=["egg"]),
    # 14. fight — likes beans and grains, dislikes meat
    dict(goal="fight", likes=["beans", "grains"], dislikes=["meat"], blacklist=[], allergies=[]),
    # 15. strong — likes fish, dislikes dairy, blacklists tuna
    dict(goal="strong", likes=["fish"], dislikes=["dairy"], blacklist=["tuna"], allergies=[]),
]

# ─── Runner ───────────────────────────────────────────────────────────────────

SEP = "=" * 70


def _print_items(label: str, items: list) -> None:
    print(f"  [{label}]")
    if not items:
        print("    (none)")
        return
    for it in items:
        if hasattr(it, "food_name"):
            print(f"    • {it.food_name} ({it.category}) — {it.reason}")
        else:
            print(f"    • {it.get('food', '?')} — {it.get('reason', '')}")


def run_scenario(idx: int, scenario: dict) -> None:
    print(SEP)
    print(f"Scenario {idx:02d} | goal={scenario['goal']}")
    print(
        f"  likes={scenario['likes']}  dislikes={scenario['dislikes']}"
        f"  blacklist={scenario['blacklist']}  allergies={scenario['allergies']}"
    )
    print()

    # 1. Call model
    raw = call_model(
        goal=scenario["goal"],
        likes=scenario["likes"],
        dislikes=scenario["dislikes"],
        blacklist=scenario["blacklist"],
        allergies=scenario["allergies"],
    )

    # 2. Parse
    parsed = parse_model_output(raw)

    print("  RAW MODEL OUTPUT:")
    if parsed:
        for section in ("super_power_foods", "tiny_hero_foods", "try_less_foods"):
            items = parsed.get(section, [])
            short = [i.get("food", "?") for i in items]
            print(f"    {section}: {short}")
    else:
        print("    [PARSE FAILED]")
        print(f"    {raw[:300]}")

    # 3. Filter
    filtered = filter_output(parsed, scenario["blacklist"], scenario["allergies"])
    filtered = filter_tiny_hero_by_likes(filtered, scenario["likes"])

    # 4. Enrich
    if filtered:
        enriched = {
            "super_power_foods": enrich_recommendation_items(
                filtered.get("super_power_foods", [])
            ),
            "tiny_hero_foods": enrich_recommendation_items(
                filtered.get("tiny_hero_foods", [])
            ),
            "try_less_foods": enrich_recommendation_items(
                filtered.get("try_less_foods", [])
            ),
        }
    else:
        enriched = None

    print()
    print("  ENRICHED RESPONSE:")
    if enriched:
        _print_items("super_power_foods", enriched["super_power_foods"])
        _print_items("tiny_hero_foods",   enriched["tiny_hero_foods"])
        _print_items("try_less_foods",    enriched["try_less_foods"])
    else:
        print("    [ENRICHMENT FAILED]")

    print()


def main() -> None:
    print(f"\nRunning {len(SCENARIOS)} demo scenarios...\n")
    for idx, scenario in enumerate(SCENARIOS, start=1):
        run_scenario(idx, scenario)
    print(SEP)
    print("Done.")


if __name__ == "__main__":
    main()
