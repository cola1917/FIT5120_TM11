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
import re

import openai

# ─── Model config ─────────────────────────────────────────────────────────────

TARGET_PER_SECTION = 3  # final items returned per section

# Candidate counts sent to the LLM.
# Extra candidates give the filter pipeline room to remove blacklisted items
# without falling back to the static pool. When no filtering is needed the
# LLM is asked for exactly TARGET_PER_SECTION to minimise token count / latency.
_CANDIDATES_WITH_FILTER = 4   # blacklist or allergies present
_CANDIDATES_NO_FILTER   = 3   # no blacklist, no allergies


def _llm_candidate_count(blacklist: list[str], allergies: list[str]) -> int:
    return _CANDIDATES_WITH_FILTER if (blacklist or allergies) else _CANDIDATES_NO_FILTER

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
- Return EXACTLY {n} items in each of super_power_foods, tiny_hero_foods, and try_less_foods.
- The {n} items in each section must be diverse — different ingredients, not variations of the same food.
- No food name may appear more than once across all three sections combined.
- User preferences are broad food categories, not exact foods.
- Choose specific child-friendly foods based on the goal and category preferences.
- super_power_foods should match the goal and align with liked categories when possible.
- try_less_foods MUST be unhealthy or heavily processed foods from the same categories as the liked categories.
  - If likes includes fruits → try_less should include fruit gummies, sweetened fruit juice, canned fruit in syrup, or similar.
  - If likes includes meat → try_less should include fried chicken, sausage, hot dog, or similar.
  - If likes includes dairy → try_less should include ice cream, flavored milk drink, or similar.
  - If likes includes vegetables → try_less should include french fries, potato chips, onion rings, or similar.
  - If likes includes fish → try_less should include fish balls, fish and chips, fish crackers, or similar.
  - If likes includes rice → try_less should include fried rice, rice crackers, or similar.
  - If likes includes noodles → try_less should include instant noodles, fried noodles, or similar.
  - If likes includes bread → try_less should include croissant, sweet bun, white toast with jam, or similar.
  - If likes is empty, use unhealthy foods related to the goal category instead.
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

def _build_output_schema(n: int) -> str:
    item = '    {"food": "...", "reason": "..."}'
    items = ",\n".join([item] * n)
    section = f"[\n{items}\n  ]"
    return (
        f'Output schema (EXACTLY {n} items per section, all food names unique across sections):\n'
        f'{{\n'
        f'  "goal": "...",\n'
        f'  "super_power_foods": {section},\n'
        f'  "tiny_hero_foods": {section},\n'
        f'  "try_less_foods": {section}\n'
        f'}}'
    )


# ─── Prompt builder ───────────────────────────────────────────────────────────

def build_user_prompt(
    goal: str,
    likes: list[str],
    dislikes: list[str],
    blacklist: list[str],
    allergies: list[str],
    n_candidates: int = TARGET_PER_SECTION,
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
    rules = _IMPORTANT_RULES.format(n=n_candidates)
    return header + rules + "\n\n" + _GOAL_CATEGORY_LOGIC + "\n\n" + _build_output_schema(n_candidates)


# ─── JSON parser ──────────────────────────────────────────────────────────────

def _try_parse(text: str) -> dict | None:
    """Attempt json.loads; return dict or None."""
    try:
        result = json.loads(text)
        return result if isinstance(result, dict) else None
    except (json.JSONDecodeError, ValueError):
        return None


def parse_model_output(raw: str) -> dict | None:
    """
    Parse model output into a dict using a 3-layer fallback strategy:

    1. Direct parse — handles clean JSON output.
    2. Markdown fence strip — handles ```json ... ``` wrapping.
    3. Regex extraction — finds the first { ... } block in text, handles
       extra explanation text before/after the JSON, partial truncation at
       the top/bottom of the response, or any other wrapping the model adds.

    Returns None only if all three layers fail (truly unparseable output).
    The function is intentionally lenient: the downstream filter pipeline
    validates content; the parser's only job is to extract a dict.
    """
    text = raw.strip()
    if not text:
        return None

    # Layer 1: direct parse
    result = _try_parse(text)
    if result is not None:
        return result

    # Layer 2: strip markdown fences (```json ... ``` or ``` ... ```)
    if text.startswith("```"):
        lines = text.splitlines()
        # drop opening fence line
        lines = lines[1:]
        # drop closing fence line if present
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
        result = _try_parse(stripped)
        if result is not None:
            return result

    # Layer 3: regex — extract first {...} block from anywhere in the text.
    # The pattern matches the outermost braces including nested structures.
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        result = _try_parse(match.group())
        if result is not None:
            return result

    return None


# ─── Static fallback pool ─────────────────────────────────────────────────────
# Used to top-up sections that fall below TARGET_PER_SECTION after filtering.
# Each entry: {"food": "...", "reason": "..."}
# Keys: goal → "super" | "tiny" | "try_less"

_FALLBACK_POOL: dict[str, dict[str, list[dict]]] = {
    "grow": {
        "super": [
            {"food": "milk",          "reason": "Milk is packed with calcium to build strong bones and teeth! 🥛"},
            {"food": "boiled egg",    "reason": "Eggs are full of protein to help your muscles grow! 💪"},
            {"food": "chicken breast","reason": "Chicken is a great protein source to help your body grow strong!"},
            {"food": "plain yogurt",  "reason": "Yogurt gives you calcium and protein for healthy bones and muscles!"},
            {"food": "tofu",          "reason": "Tofu is a plant-based protein that helps your body repair and grow!"},
            {"food": "broccoli",      "reason": "Broccoli has calcium and vitamins that support healthy growth!"},
        ],
        "tiny": [
            {"food": "salmon",        "reason": "Salmon has protein and healthy fats — try it and feel the difference!"},
            {"food": "spinach",       "reason": "Spinach has iron and calcium that help your body grow — give it a go!"},
            {"food": "edamame",       "reason": "Edamame is a fun green snack full of plant protein for growing bodies!"},
            {"food": "cheese",        "reason": "Cheese is rich in calcium — try a small piece for strong bones!"},
        ],
        "try_less": [
            {"food": "fried chicken", "reason": "Fried chicken has lots of oil — grilled chicken is a tastier swap!"},
            {"food": "instant noodles","reason": "Instant noodles are high in salt and low in protein for growing bodies."},
            {"food": "sausage",       "reason": "Sausages are high in salt and fat — enjoy them only once in a while."},
            {"food": "fish balls",    "reason": "Fish balls are heavily processed and high in salt — best as an occasional treat."},
        ],
    },
    "see": {
        "super": [
            {"food": "carrot",        "reason": "Carrots are full of vitamin A to keep your eyes sharp and healthy! 🥕"},
            {"food": "blueberries",   "reason": "Blueberries have antioxidants that protect your eyes and help you see clearly!"},
            {"food": "spinach",       "reason": "Spinach contains lutein which shields your eyes from strain!"},
            {"food": "sweet potato",  "reason": "Sweet potato is rich in beta-carotene to support healthy vision!"},
            {"food": "tuna",          "reason": "Tuna has omega-3 fatty acids that help keep your eyes healthy!"},
            {"food": "mango",         "reason": "Mango is loaded with vitamin A to support clear and healthy eyesight!"},
        ],
        "tiny": [
            {"food": "mackerel",      "reason": "Mackerel has omega-3s that are great for eye health — be brave and try it!"},
            {"food": "kale",          "reason": "Kale has lutein and zeaxanthin that protect your eyes — a real hero veggie!"},
            {"food": "capsicum",      "reason": "Capsicum is packed with vitamin C which supports eye health — try a slice!"},
            {"food": "sardine",       "reason": "Sardines have omega-3s that are fantastic for keeping your eyes strong!"},
            {"food": "boiled egg",    "reason": "Eggs contain lutein and zeaxanthin that help protect your eyes — try one!"},
            {"food": "plain yogurt",  "reason": "Yogurt is rich in zinc which supports healthy vision — give it a try!"},
            {"food": "tuna",          "reason": "Tuna has omega-3s that keep your eyes healthy — a great challenge food!"},
        ],
        "try_less": [
            {"food": "chips",         "reason": "Chips are high in salt and fat with no eye-health benefits."},
            {"food": "cola",          "reason": "Cola has lots of sugar and no vitamins to support your eyes."},
            {"food": "instant noodles","reason": "Instant noodles lack the vitamins your eyes need to stay healthy."},
            {"food": "candy",         "reason": "Candy is all sugar with nothing to help your eyes stay sharp."},
        ],
    },
    "think": {
        "super": [
            {"food": "salmon",        "reason": "Salmon is full of omega-3s that feed your brain and help you focus! 🐟"},
            {"food": "plain yogurt",  "reason": "Yogurt gives your brain protein and probiotics to stay sharp!"},
            {"food": "walnut",        "reason": "Walnuts look like tiny brains — and they're great brain food too!"},
            {"food": "blueberries",   "reason": "Blueberries are brain berries — antioxidants to boost memory and focus!"},
            {"food": "boiled egg",    "reason": "Eggs have choline that helps your brain send messages faster!"},
            {"food": "oatmeal",       "reason": "Oatmeal gives your brain steady energy so you can think all day!"},
        ],
        "tiny": [
            {"food": "mackerel",      "reason": "Mackerel is loaded with DHA for brain power — give it a try!"},
            {"food": "avocado",       "reason": "Avocado has healthy fats that support your brain — a creamy challenge!"},
            {"food": "chia pudding",  "reason": "Chia seeds are tiny but packed with omega-3s for a sharp mind!"},
            {"food": "tofu",          "reason": "Tofu has plant protein that supports brain health — try it stir-fried!"},
        ],
        "try_less": [
            {"food": "cola",          "reason": "Cola is full of sugar that causes energy crashes and makes it hard to focus."},
            {"food": "candy",         "reason": "Candy gives a quick sugar rush but leaves your brain foggy afterwards."},
            {"food": "chips",         "reason": "Chips are high in salt and unhealthy fat with no brain-boosting nutrients."},
            {"food": "instant noodles","reason": "Instant noodles lack the omega-3s and nutrients your brain needs to grow."},
        ],
    },
    "fight": {
        "super": [
            {"food": "orange",        "reason": "Oranges are bursting with vitamin C to power up your immune system! 🍊"},
            {"food": "broccoli",      "reason": "Broccoli is packed with vitamins C and K to help your body fight illness!"},
            {"food": "kiwi",          "reason": "Kiwi has more vitamin C than an orange — a tiny immunity powerhouse!"},
            {"food": "strawberries",  "reason": "Strawberries are full of antioxidants to keep your body strong and healthy!"},
            {"food": "plain yogurt",  "reason": "Yogurt has probiotics that keep your gut healthy and your defences up!"},
            {"food": "spinach",       "reason": "Spinach has iron and vitamins that help your body fight off germs!"},
        ],
        "tiny": [
            {"food": "capsicum",      "reason": "Capsicum has loads of vitamin C to boost immunity — try it raw and crunchy!"},
            {"food": "tomato",        "reason": "Tomatoes have lycopene that helps protect your body — be a fighter!"},
            {"food": "edamame",       "reason": "Edamame has plant protein and zinc to support your immune system!"},
            {"food": "boiled egg",    "reason": "Eggs have zinc and protein to help your body stay strong and resilient!"},
            {"food": "plain yogurt",  "reason": "Yogurt has probiotics that boost your gut health and keep you feeling well!"},
            {"food": "sardine",       "reason": "Sardines have omega-3s and zinc to keep your immune system fighting strong!"},
            {"food": "tofu",          "reason": "Tofu has plant protein and iron to help your body stay strong and healthy!"},
        ],
        "try_less": [
            {"food": "cola",          "reason": "Cola has lots of sugar that can weaken your immune system over time."},
            {"food": "chips",         "reason": "Chips are high in unhealthy fat and salt with no immune-boosting power."},
            {"food": "candy",         "reason": "Too much candy can reduce the vitamins your body needs to fight illness."},
            {"food": "fried chicken", "reason": "Fried chicken is high in fat — grilled versions are much better for your defences."},
        ],
    },
    "feel": {
        "super": [
            {"food": "banana",        "reason": "Bananas have natural sugars and potassium to give you steady happy energy! 🍌"},
            {"food": "brown rice",    "reason": "Brown rice releases energy slowly so you feel good all day long!"},
            {"food": "oatmeal",       "reason": "Oatmeal gives you long-lasting energy and helps you feel calm and focused!"},
            {"food": "mango",         "reason": "Mango is naturally sweet and full of vitamins to brighten your mood!"},
            {"food": "watermelon",    "reason": "Watermelon is refreshing, hydrating, and naturally sweet to lift your spirits!"},
            {"food": "sweet potato",  "reason": "Sweet potato gives you slow-release energy and vitamins to feel great!"},
        ],
        "tiny": [
            {"food": "spinach",       "reason": "Spinach has magnesium that helps your body relax and feel calm — try it!"},
            {"food": "avocado",       "reason": "Avocado has healthy fats that support a steady, happy mood all day!"},
            {"food": "carrot",        "reason": "Carrots are crunchy and full of energy-giving vitamins — give them a try!"},
            {"food": "plain yogurt",  "reason": "Yogurt has probiotics that help your gut — and a happy gut means a happy mood!"},
        ],
        "try_less": [
            {"food": "cola",          "reason": "Cola causes sugar spikes and crashes that leave you feeling tired and grumpy."},
            {"food": "candy",         "reason": "Candy gives a short sugar high followed by a big energy crash."},
            {"food": "chips",         "reason": "Chips are salty and offer no steady energy — not great for feeling your best."},
            {"food": "donut",         "reason": "Donuts are high in sugar and fat that cause energy swings and low moods."},
        ],
    },
    "strong": {
        "super": [
            {"food": "chicken breast","reason": "Chicken breast is lean protein to build strong muscles after activity! 🏋️"},
            {"food": "boiled egg",    "reason": "Eggs are packed with protein and healthy fats for muscle growth!"},
            {"food": "tuna",          "reason": "Tuna is a lean, high-protein fish that helps your muscles repair and grow!"},
            {"food": "milk",          "reason": "Milk gives you calcium and protein — the perfect combo for strong bones!"},
            {"food": "tofu",          "reason": "Tofu is a great plant-based protein source to help muscles recover!"},
            {"food": "plain yogurt",  "reason": "Yogurt has protein and calcium to support strong muscles and bones!"},
        ],
        "tiny": [
            {"food": "salmon",        "reason": "Salmon has protein and omega-3s — great for muscle recovery after exercise!"},
            {"food": "edamame",       "reason": "Edamame is full of plant protein — a fun green snack for strong bodies!"},
            {"food": "sardine",       "reason": "Sardines are small but mighty — packed with protein and calcium!"},
            {"food": "mackerel",      "reason": "Mackerel has protein and healthy fats to help your muscles stay strong!"},
            {"food": "plain yogurt",  "reason": "Yogurt has protein and calcium to keep your bones and muscles strong!"},
            {"food": "tofu",          "reason": "Tofu is a plant-based protein that helps your muscles repair — try it!"},
            {"food": "boiled egg",    "reason": "Eggs are packed with protein for muscle strength — a great challenge food!"},
            {"food": "cheese",        "reason": "Cheese has calcium and protein to support strong bones — give it a go!"},
        ],
        "try_less": [
            {"food": "fried chicken", "reason": "Fried chicken has too much oil — grilled chicken gives the same protein without the fat."},
            {"food": "sausage",       "reason": "Sausages are high in saturated fat and salt — not the best fuel for strong muscles."},
            {"food": "instant noodles","reason": "Instant noodles are low in protein and high in salt — not great for building strength."},
            {"food": "chips",         "reason": "Chips are high in fat and salt with no protein to support your muscles."},
            {"food": "cola",          "reason": "Cola has lots of sugar and no nutrients to help your muscles recover after exercise."},
            {"food": "candy",         "reason": "Candy gives a quick sugar spike but no protein or fuel for strong muscles."},
        ],
    },
}

_SECTION_KEY_MAP = {
    "super_power_foods": "super",
    "tiny_hero_foods":   "tiny",
    "try_less_foods":    "try_less",
}

# try_less fallback keyed by liked category — unhealthy versions of liked foods
_TRY_LESS_BY_CATEGORY: dict[str, list[dict]] = {
    "fruits": [
        {"food": "fruit gummies",             "reason": "Fruit gummies look like fruit but are mostly sugar with no real vitamins."},
        {"food": "sweetened fruit juice",     "reason": "Sweetened juice has as much sugar as soda — whole fruit is a much better choice."},
        {"food": "canned fruit in syrup",     "reason": "Canned fruit in syrup is loaded with added sugar — fresh fruit is tastier and healthier."},
        {"food": "fruit roll-up",             "reason": "Fruit roll-ups are mostly sugar and have very little real fruit inside."},
    ],
    "meat": [
        {"food": "fried chicken",             "reason": "Fried chicken is high in oil and saturated fat — grilled chicken is a much better swap."},
        {"food": "sausage",                   "reason": "Sausages are highly processed and full of salt and fat — enjoy them only occasionally."},
        {"food": "hot dog",                   "reason": "Hot dogs are processed meat with lots of salt and additives — not great for everyday eating."},
        {"food": "chicken nuggets",           "reason": "Chicken nuggets are heavily battered and fried — homemade grilled versions are far healthier."},
    ],
    "dairy": [
        {"food": "ice cream",                 "reason": "Ice cream is high in sugar and saturated fat — plain yogurt with fruit is a better treat."},
        {"food": "flavored milk drink",       "reason": "Flavored milk drinks add lots of sugar to what could be a healthy choice."},
        {"food": "cheese puffs",              "reason": "Cheese puffs are mostly air, salt, and artificial flavoring with very little real dairy."},
        {"food": "sweetened condensed milk",  "reason": "Condensed milk is packed with sugar — a tiny bit goes a long way."},
    ],
    "vegetables": [
        {"food": "french fries",              "reason": "French fries are deep-fried and high in salt — baked potato wedges are a tastier swap."},
        {"food": "potato chips",              "reason": "Potato chips are made from vegetables but lose all their goodness in frying and salting."},
        {"food": "onion rings",               "reason": "Onion rings are battered and deep-fried — raw or roasted onions are much better for you."},
        {"food": "vegetable crisps",          "reason": "Vegetable crisps sound healthy but are still high in oil and salt like regular chips."},
    ],
    "fish": [
        {"food": "fish balls",                "reason": "Fish balls are heavily processed and high in salt with little of the goodness of real fish."},
        {"food": "fish and chips",            "reason": "Fish and chips adds lots of oil and salt to what could be a healthy fish dish."},
        {"food": "fish crackers",             "reason": "Fish crackers are mostly starch and salt — not much real fish nutrition inside."},
        {"food": "fried fish fillet",         "reason": "Fried fish loses its healthy fats in the frying process — steamed or baked is much better."},
    ],
    "rice": [
        {"food": "fried rice",                "reason": "Fried rice uses lots of oil and salt — plain steamed rice is a much lighter choice."},
        {"food": "rice crackers",             "reason": "Rice crackers are high in salt and have very little of the nutrition of whole rice."},
        {"food": "instant rice porridge",     "reason": "Instant rice porridge is high in sodium and low in nutrients compared to homemade."},
        {"food": "rice pudding with sugar",   "reason": "Rice pudding with added sugar turns a simple grain into a high-sugar dessert."},
    ],
    "noodles": [
        {"food": "instant noodles",           "reason": "Instant noodles are high in salt and low in protein — fresh noodle soup is far better."},
        {"food": "fried noodles",             "reason": "Fried noodles soak up a lot of oil during cooking — steamed or soup noodles are healthier."},
        {"food": "cup noodles",               "reason": "Cup noodles have very high sodium and few real nutrients — not great for growing bodies."},
        {"food": "crispy noodle snack",       "reason": "Crispy noodle snacks are deep-fried and salty with no nutritional benefit."},
    ],
    "bread": [
        {"food": "croissant",                 "reason": "Croissants are made with lots of butter and refined flour — a once-in-a-while treat."},
        {"food": "sweet bun",                 "reason": "Sweet buns are high in sugar and fat — wholegrain bread is a much better everyday choice."},
        {"food": "white toast with jam",      "reason": "White toast with jam is mostly refined carbs and added sugar with little nutrition."},
        {"food": "doughnut",                  "reason": "Doughnuts are deep-fried dough with lots of sugar — enjoy them only as a special treat."},
    ],
}


def rewrite_try_less_by_likes(filtered: dict, likes: list[str]) -> dict:
    """
    When the user has liked categories, replace model-generated try_less items
    that don't belong to any liked category with items from _TRY_LESS_BY_CATEGORY.
    Items already in a liked category are kept; unrelated generic junk is dropped
    so topup_sections can fill the gap with category-relevant foods.
    """
    from app.services.enrichment import infer_category

    if not likes:
        return filtered

    liked_set = {c.lower().strip() for c in likes}
    current   = filtered.get("try_less_foods", [])

    # Keep only items whose inferred category is in liked categories
    kept = [
        item for item in current
        if infer_category(str(item.get("food", item.get("name", "")))) in liked_set
    ]

    return {**filtered, "try_less_foods": kept}


def topup_sections(
    filtered: dict,
    goal: str,
    blacklist: list[str],
    allergies: list[str],
    likes: list[str] | None = None,
    target: int = TARGET_PER_SECTION,
    forbidden_cats: "set[str] | None" = None,
    forbidden_kws: "set[str] | None" = None,
) -> dict:
    """
    Fill each section up to `target` items using _FALLBACK_POOL when the model
    + filter pipeline left fewer than needed. Respects blacklist, allergies, and
    likes (tiny_hero candidates must not come from liked categories).
    Deduplicates across all sections.

    Pass pre-resolved forbidden_cats / forbidden_kws (from resolve_forbidden) to
    reuse the same forbidden sets across the whole request pipeline.
    Candidate pools are pre-filtered before the selection loop so no blacklisted
    food can ever be introduced from a static pool.
    """
    from app.services.filter import resolve_forbidden, filter_candidates
    from app.services.enrichment import infer_category

    liked_set = {c.lower().strip() for c in (likes or [])}
    result = dict(filtered)

    if forbidden_cats is None or forbidden_kws is None:
        forbidden_cats, forbidden_kws = resolve_forbidden(blacklist + allergies)

    raw_pool = _FALLBACK_POOL.get(goal, {})

    # ── Pre-filter all static pools before any selection loop ─────────────────
    safe_pool: dict[str, list[dict]] = {
        key: filter_candidates(items, forbidden_cats, forbidden_kws)
        for key, items in raw_pool.items()
    }
    safe_try_less_by_cat: dict[str, list[dict]] = {
        cat: filter_candidates(items, forbidden_cats, forbidden_kws)
        for cat, items in _TRY_LESS_BY_CATEGORY.items()
    }

    # ── Process sections in priority order, building `seen` progressively ─────
    # This ensures cross-section deduplication works correctly even when the LLM
    # returns more than `target` items per section (e.g. 6 candidates).
    # Higher-priority sections (super > tiny > try_less) claim their names first;
    # lower-priority sections skip anything already committed.
    seen: set[str] = set()

    for section, pool_key in _SECTION_KEY_MAP.items():
        raw_items = list(result.get(section, []))

        # Deduplicate against already-committed sections, preserving order
        items: list[dict] = []
        for item in raw_items:
            name = item.get("food", "").lower().strip()
            if name and name not in seen:
                seen.add(name)
                items.append(item)

        # Fill from safe pool if we still have fewer than target after dedup
        if len(items) < target:
            if section == "try_less_foods" and liked_set:
                per_cat = [safe_try_less_by_cat.get(cat, []) for cat in sorted(liked_set)]
                candidates: list[dict] = []
                max_len = max((len(c) for c in per_cat), default=0)
                for i in range(max_len):
                    for cat_list in per_cat:
                        if i < len(cat_list):
                            candidates.append(cat_list[i])
            else:
                candidates = safe_pool.get(pool_key, [])

            for cand in candidates:
                if len(items) >= target:
                    break
                name = cand["food"].lower().strip()
                if name in seen:
                    continue
                if section == "tiny_hero_foods" and liked_set:
                    if infer_category(cand["food"]) in liked_set:
                        continue
                seen.add(name)
                items.append(cand)

            # try_less second-pass: fall back to goal pool if still short
            if section == "try_less_foods" and len(items) < target:
                for cand in safe_pool.get("try_less", []):
                    if len(items) >= target:
                        break
                    name = cand["food"].lower().strip()
                    if name in seen:
                        continue
                    seen.add(name)
                    items.append(cand)

        # Trim to exactly target — do NOT trim before this point
        result[section] = items[:target]

    return result


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
    n_candidates = _llm_candidate_count(blacklist, allergies)
    api_key = os.getenv("OPENAI_API_KEY")
    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        top_p=top_p,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": build_user_prompt(
                goal, likes, dislikes, blacklist, allergies, n_candidates=n_candidates,
            )},
        ],
    )
    return response.choices[0].message.content or ""
