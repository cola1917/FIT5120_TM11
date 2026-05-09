"""
Smoke test for fine-tuned OpenAI food recommendation model.

Usage:
    python scripts/test_finetuned_model_smoke.py
    python scripts/test_finetuned_model_smoke.py --model ft:gpt-4o-mini-2024-07-18:personal::DbryXUZ2
    python scripts/test_finetuned_model_smoke.py --temperature 0.3 --top-p 0.9
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Allow running from project root or scripts/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

import openai

DEFAULT_MODEL = "ft:gpt-4o-mini-2024-07-18:personal::Dcz8w84o"
DEFAULT_TEMPERATURE = 0.25
DEFAULT_TOP_P = 0.85

SYSTEM_PROMPT = (
    "You are a child-friendly healthy eating recommendation assistant for children aged 7-12.\n"
    "Return valid JSON only.\n"
    "Do not mention calories.\n"
    "Do not use medical jargon.\n"
    "Do not recommend pork, alcohol, caffeine drinks, supplements, baby formula, or medical foods.\n"
    "Only use supported goal_id values: grow, see, think, fight, feel, strong."
)

# ─── Prompt builder (kept in sync with evaluate_finetuned_model.py) ───────────

_IMPORTANT_RULES = """\
Important:
- User preferences are broad food categories, not exact foods.
- Choose specific child-friendly foods based on the goal and category preferences.
- super_power_foods should match the goal and align with liked categories when possible.
- tiny_hero_foods should match the goal but come from disliked or not-preferred categories.
- try_less_foods should be less healthy foods related to liked categories when appropriate.
- Do not simply avoid disliked categories. If a disliked category is important for the goal, choose a small challenge food from that category as tiny_hero_foods.
- Do not put unhealthy snacks, candy, cake, cookies, soda, syrup, chips, fries, or ice cream in super_power_foods.
- Sweet fruits can support feel, but sweet snacks should not be treated as feel goal foods.
- Do not recommend sauces or condiments in any section.
- Respect blacklist and allergies strictly.
- Return valid JSON only."""

_GOAL_CATEGORY_LOGIC = """\
Goal-specific category logic:
grow:
- related categories: dairy, meat, vegetables
- if dairy is disliked, a dairy food can still be tiny_hero
- if meat is disliked, a meat/fish food can still be tiny_hero

see:
- related categories: vegetables, fruits, fish
- if vegetables are disliked, a vegetable can still be tiny_hero
- if fish is disliked, a fish can still be tiny_hero

think:
- related categories: fish, dairy, fruits
- if fish or dairy is disliked, it can still appear as tiny_hero

fight:
- Fight means supporting everyday wellness and resistance.
- Primary related categories: fruits and vegetables.
- If fruits or vegetables are disliked, they can still appear as tiny_hero.
- Secondary supporting categories can include dairy, fish, eggs, beans, and simple grains when they are child-friendly and not try_less.
- Good examples include orange, berries, kiwi, broccoli, spinach, tomato, yogurt, egg, fish, beans, and oats.
- Do not use candy, soda, chips, cake, cookies, ice cream, sauces, or sweetened drinks as fight super_power foods.

feel:
- related categories: fruits, vegetables, rice, noodles
- sweet fruits are good feel candidates
- candy, cake, cookies, soda, and ice cream are not feel super_power foods

strong:
- related categories: meat, fish, dairy
- if meat, fish, or dairy is disliked, it can still appear as tiny_hero"""

_OUTPUT_SCHEMA = """\
Output schema:
{
  "goal": "...",
  "super_power_foods": [
    {"food": "...", "reason": "..."}
  ],
  "tiny_hero_foods": [
    {"food": "...", "reason": "..."}
  ],
  "try_less_foods": [
    {"food": "...", "reason": "..."}
  ]
}"""


def build_user_prompt(case_input: dict) -> str:
    goal      = case_input.get("goal", "")
    likes     = case_input.get("likes", [])
    dislikes  = case_input.get("dislikes", [])
    blacklist = case_input.get("blacklist", [])
    allergies = case_input.get("allergies", [])
    blacklist_str = ", ".join(blacklist) if blacklist else "none"
    allergies_str = ", ".join(allergies) if allergies else "none"
    header = (
        "Task: integrated_recommendation\n"
        f"Goal: {goal}\n"
        f"Liked preference categories: {', '.join(likes) if likes else 'none'}\n"
        f"Disliked preference categories: {', '.join(dislikes) if dislikes else 'none'}\n"
        f"Blacklist: {blacklist_str}\n"
        f"Allergies: {allergies_str}\n"
        "\n"
    )
    return header + _IMPORTANT_RULES + "\n\n" + _GOAL_CATEGORY_LOGIC + "\n\n" + _OUTPUT_SCHEMA


# ─── Fixed smoke-test input ───────────────────────────────────────────────────

_SMOKE_INPUT = {
    "goal": "feel",
    "likes": ["snacks"],
    "dislikes": ["vegetables"],
    "blacklist": ["eggs"],
}

USER_PROMPT = build_user_prompt(_SMOKE_INPUT)

# Hard-coded unsafe terms always checked regardless of input
_ALWAYS_BLOCKED_TERMS = ["pork", "alcohol", "peanut", "caffeine"]

# Terms from the actual smoke-test blacklist
_INPUT_BLACKLIST_TERMS = _SMOKE_INPUT["blacklist"]

# Combined deduplicated list used for the check loop
BLOCKED_TERMS = list(dict.fromkeys(_INPUT_BLACKLIST_TERMS + _ALWAYS_BLOCKED_TERMS))


def parse_args():
    parser = argparse.ArgumentParser(description="Smoke test for fine-tuned food recommendation model")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model ID to test")
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE, help="Sampling temperature")
    parser.add_argument("--top-p", type=float, default=DEFAULT_TOP_P, dest="top_p", help="Top-p nucleus sampling")
    return parser.parse_args()


def main():
    args = parse_args()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[ERROR] OPENAI_API_KEY not set in environment or .env file.")
        sys.exit(1)

    client = openai.OpenAI(api_key=api_key)

    print(f"Model      : {args.model}")
    print(f"Temperature: {args.temperature}")
    print(f"Top-p      : {args.top_p}")
    print("-" * 60)

    response = client.chat.completions.create(
        model=args.model,
        temperature=args.temperature,
        top_p=args.top_p,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT},
        ],
    )

    raw_output = response.choices[0].message.content
    print("Raw output:")
    print(raw_output)
    print("-" * 60)

    # JSON parse check
    parsed = None
    try:
        parsed = json.loads(raw_output)
        print("[PASS] JSON parse: success")
    except json.JSONDecodeError as e:
        print(f"[FAIL] JSON parse: {e}")

    # Blocked terms check — input blacklist first, then always-blocked safety terms
    raw_lower = raw_output.lower()
    for term in _INPUT_BLACKLIST_TERMS:
        if term in raw_lower:
            print(f"[FAIL] Input blacklist term found in output: '{term}'")
        else:
            print(f"[PASS] Input blacklist term absent: '{term}'")
    for term in _ALWAYS_BLOCKED_TERMS:
        if term in raw_lower:
            print(f"[FAIL] Always-blocked term found in output: '{term}'")
        else:
            print(f"[PASS] Always-blocked term absent: '{term}'")

    # Save result
    output_dir = PROJECT_ROOT / "data" / "evaluation"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "smoke_test_result.json"

    result = {
        "model": args.model,
        "temperature": args.temperature,
        "top_p": args.top_p,
        "system_prompt": SYSTEM_PROMPT,
        "user_prompt": USER_PROMPT,
        "raw_output": raw_output,
        "json_parse_success": parsed is not None,
        "parsed_output": parsed,
        "blocked_terms_check": {
            "input_blacklist": {
                term: (term not in raw_lower) for term in _INPUT_BLACKLIST_TERMS
            },
            "always_blocked": {
                term: (term not in raw_lower) for term in _ALWAYS_BLOCKED_TERMS
            },
        },
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\nResult saved to: {output_path}")


if __name__ == "__main__":
    main()
