"""
Recommendation service — prompt construction and model call.

The fine-tuned model is responsible for choosing specific foods.
This module handles:
  - system + user prompt construction
  - OpenAI API call
  - raw JSON parsing
"""

from __future__ import annotations

import json
import os

import openai

# ─── Model config ─────────────────────────────────────────────────────────────

DEFAULT_MODEL       = os.getenv("OPENAI_FOOD_MODEL", "ft:gpt-4o-mini-2024-07-18:personal::Dcz8w84o")
DEFAULT_TEMPERATURE = 0.25
DEFAULT_TOP_P       = 0.85

# ─── System prompt ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are a child-friendly healthy eating recommendation assistant for children aged 7-12.\n"
    "Return valid JSON only.\n"
    "Do not mention calories.\n"
    "Do not use medical jargon.\n"
    "Do not recommend pork, alcohol, caffeine drinks, supplements, baby formula, or medical foods.\n"
    "Only use supported goal_id values: grow, see, think, fight, feel, strong."
)

# ─── User prompt constants ────────────────────────────────────────────────────

_IMPORTANT_RULES = """\
Important:
- User preferences are broad food categories, not exact foods.
- Choose specific child-friendly foods based on the goal and category preferences.
- super_power_foods should match the goal and align with liked categories when possible.
- try_less_foods should be less healthy foods related to liked categories when appropriate.
- Do not put unhealthy snacks, candy, cake, cookies, soda, syrup, chips, fries, or ice cream in super_power_foods.
- Sweet fruits can support feel, but sweet snacks should not be treated as feel goal foods.
- Do not recommend sauces or condiments in any section.
- Respect blacklist and allergies strictly.
- Return valid JSON only.

tiny_hero_foods rules:
- tiny_hero_foods should match the selected goal.
- tiny_hero_foods should come from disliked categories or not-preferred categories.
- tiny_hero_foods should NOT come from liked categories.
- If dislikes is empty, tiny_hero_foods may come from goal-related categories that are not in likes.
- If no suitable challenge food exists, tiny_hero_foods can be an empty list."""

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


# ─── Prompt builder ───────────────────────────────────────────────────────────

def build_user_prompt(
    goal: str,
    likes: list[str],
    dislikes: list[str],
    blacklist: list[str],
    allergies: list[str],
) -> str:
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


# ─── JSON parser ──────────────────────────────────────────────────────────────

def parse_model_output(raw: str) -> dict | None:
    """Parse model output, stripping markdown fences if present."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        result = json.loads(text)
        return result if isinstance(result, dict) else None
    except (json.JSONDecodeError, ValueError):
        return None


# ─── Model call ───────────────────────────────────────────────────────────────

def call_model(
    goal: str,
    likes: list[str],
    dislikes: list[str],
    blacklist: list[str],
    allergies: list[str],
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    top_p: float = DEFAULT_TOP_P,
) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        top_p=top_p,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": build_user_prompt(goal, likes, dislikes, blacklist, allergies)},
        ],
    )
    return response.choices[0].message.content or ""
