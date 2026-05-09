"""
Generate Fine-Tuning JSONL Dataset
====================================
Generates OpenAI fine-tuning JSONL from AI-reviewed food metadata.

Tasks generated:
  A - health_judgement          : one per safe record
  B - goal_matching             : one per (record, goal_tag) where goal_tags non-empty
  C - try_less_judgement        : one per try_less record
  D - alternative_generation    : for try_less and sometimes records
  E - integrated_recommendation : --integrated-count examples (default 400)

Usage:
    python scripts/generate_finetune_jsonl.py
    python scripts/generate_finetune_jsonl.py --seed 42 --integrated-count 400
    python scripts/generate_finetune_jsonl.py --dry-run

Output:
    data/finetune/food_recommender_train.jsonl
    data/finetune/food_recommender_valid.jsonl
    data/finetune/food_recommender_test.jsonl
    data/finetune/finetune_generation_summary.json
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "data" / "processed" / "ai_reviewed_food_metadata.json"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "finetune"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
VALID_GOAL_TAGS = {"grow", "see", "think", "fight", "feel", "strong"}

SYSTEM_PROMPT = (
    "You are a child-friendly healthy eating recommendation assistant for children aged 7-12. "
    "Return valid JSON only. Do not mention calories. Do not use medical jargon. "
    "Do not recommend pork, alcohol, caffeine drinks, supplements, baby formula, or medical foods. "
    "Only use supported goal_id values: grow, see, think, fight, feel, strong."
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Replacement group → healthier alternative mapping
# ---------------------------------------------------------------------------
_REPLACEMENT_ALT: dict[str, dict[str, Any]] = {
    "sugary_drink": {
        "alternative": "water with fresh fruit slices or a fruit smoothie",
        "similarity": "refreshing and lightly sweet",
        "goal_tags": ["feel"],
    },
    "sweet_drink": {
        "alternative": "fruit-infused water or plain milk",
        "similarity": "refreshing and naturally flavoured",
        "goal_tags": ["feel", "grow"],
    },
    "sweet_snack": {
        "alternative": "fresh mango or banana slices",
        "similarity": "naturally sweet and satisfying",
        "goal_tags": ["feel", "fight"],
    },
    "crunchy_snack": {
        "alternative": "carrot sticks with hummus",
        "similarity": "crunchy and satisfying",
        "goal_tags": ["see", "feel"],
    },
    "creamy_snack": {
        "alternative": "plain yogurt with fresh fruit",
        "similarity": "creamy and naturally sweet",
        "goal_tags": ["grow", "feel"],
    },
    "salty_snack": {
        "alternative": "lightly salted whole-grain crackers",
        "similarity": "salty and crunchy",
        "goal_tags": ["think"],
    },
    "dairy_food": {
        "alternative": "low-fat plain yogurt",
        "similarity": "creamy and mild",
        "goal_tags": ["grow", "strong"],
    },
    "full_fat_dairy": {
        "alternative": "low-fat milk or plain yogurt",
        "similarity": "creamy and nourishing",
        "goal_tags": ["grow", "strong"],
    },
    "main_meal": {
        "alternative": "balanced meal with vegetables and a fruit side",
        "similarity": "hearty and filling",
        "goal_tags": ["grow", "strong"],
    },
    "fast_food": {
        "alternative": "home-cooked rice with vegetables and lean protein",
        "similarity": "filling and satisfying",
        "goal_tags": ["grow", "strong"],
    },
    "fried_food": {
        "alternative": "oven-baked or steamed version of the same food",
        "similarity": "similar texture and flavour with less oil",
        "goal_tags": ["feel", "strong"],
    },
    "sauce_condiment": {
        "alternative": "yogurt-based dip or a smaller serving of sauce",
        "similarity": "flavourful and creamy",
        "goal_tags": ["grow"],
    },
    "high_sugar_condiment": {
        "alternative": "fresh herbs, lemon juice, or a small amount of sauce",
        "similarity": "flavourful and colourful",
        "goal_tags": ["fight"],
    },
    "sweet_dessert": {
        "alternative": "a fresh fruit bowl or frozen yogurt bark",
        "similarity": "sweet and satisfying",
        "goal_tags": ["feel", "fight"],
    },
    "cake_pastry": {
        "alternative": "banana oat bites or fruit with plain yogurt",
        "similarity": "sweet and soft",
        "goal_tags": ["grow", "feel"],
    },
    "candy_sweets": {
        "alternative": "dried fruit or a small piece of dark chocolate",
        "similarity": "sweet and enjoyable",
        "goal_tags": ["feel"],
    },
    "processed_meat": {
        "alternative": "grilled chicken breast or boiled eggs",
        "similarity": "savoury and protein-rich",
        "goal_tags": ["grow", "strong"],
    },
}

_CATEGORY_FALLBACK_ALT: dict[str, dict[str, Any]] = {
    "snacks": {
        "alternative": "fruit slices or plain whole-grain crackers",
        "similarity": "light and satisfying",
        "goal_tags": ["feel"],
    },
    "drinks": {
        "alternative": "water with lemon or a fruit smoothie",
        "similarity": "refreshing and hydrating",
        "goal_tags": ["feel"],
    },
    "dairy": {
        "alternative": "low-fat plain yogurt with berries",
        "similarity": "creamy and naturally sweet",
        "goal_tags": ["grow", "feel"],
    },
    "mixed_dishes": {
        "alternative": "a home-cooked version with more vegetables and less oil",
        "similarity": "hearty and filling",
        "goal_tags": ["grow", "strong"],
    },
    "sauces": {
        "alternative": "yogurt-based dip or fresh herbs",
        "similarity": "flavourful and lighter",
        "goal_tags": ["grow"],
    },
    "grains": {
        "alternative": "whole grain version with less added salt or sugar",
        "similarity": "filling and nutritious",
        "goal_tags": ["think", "strong"],
    },
    "meat": {
        "alternative": "grilled or steamed version with vegetables on the side",
        "similarity": "savoury and satisfying",
        "goal_tags": ["grow", "strong"],
    },
    "eggs": {
        "alternative": "boiled or poached egg with steamed vegetables",
        "similarity": "protein-rich and filling",
        "goal_tags": ["grow", "strong"],
    },
    "noodles": {
        "alternative": "whole-grain noodles with vegetables and light sauce",
        "similarity": "filling and satisfying",
        "goal_tags": ["think", "strong"],
    },
    "fruits": {
        "alternative": "a different fresh seasonal fruit",
        "similarity": "naturally sweet and refreshing",
        "goal_tags": ["feel", "fight"],
    },
    "vegetables": {
        "alternative": "a colourful mix of raw or lightly cooked vegetables",
        "similarity": "crunchy and fresh",
        "goal_tags": ["see", "fight"],
    },
    "beans": {
        "alternative": "lightly seasoned chickpeas or edamame",
        "similarity": "mild and filling",
        "goal_tags": ["grow", "strong"],
    },
    "fish": {
        "alternative": "lightly pan-fried or steamed fish with herbs",
        "similarity": "light and protein-rich",
        "goal_tags": ["think", "grow"],
    },
    "rice": {
        "alternative": "brown rice or cauliflower rice",
        "similarity": "mild and filling",
        "goal_tags": ["think", "strong"],
    },
}

_DEFAULT_ALT: dict[str, Any] = {
    "alternative": "a fresh fruit or vegetable option",
    "similarity": "naturally nutritious and colourful",
    "goal_tags": ["feel", "fight"],
}

# ---------------------------------------------------------------------------
# Preference profiles for Task E (liked_categories, disliked_categories)
# ---------------------------------------------------------------------------
_PREFERENCE_PROFILES: list[tuple[list[str], list[str]]] = [
    (["fruits", "dairy"],          ["vegetables", "fish"]),
    (["fruits", "grains"],         ["vegetables", "beans"]),
    (["meat", "grains"],           ["vegetables", "fish"]),
    (["dairy", "eggs"],            ["vegetables", "beans"]),
    (["snacks", "fruits"],         ["vegetables", "fish"]),
    (["mixed_dishes", "grains"],   ["vegetables", "beans"]),
    (["fruits", "vegetables"],     ["dairy", "fish"]),
    (["dairy", "fruits"],          ["meat", "fish"]),
    (["grains", "beans"],          ["meat", "dairy"]),
    (["eggs", "dairy"],            ["vegetables", "noodles"]),
    (["fruits", "snacks"],         ["meat", "fish"]),
    (["meat", "eggs"],             ["dairy", "vegetables"]),
    (["dairy", "grains"],          ["vegetables", "snacks"]),
    (["fruits", "beans"],          ["meat", "dairy"]),
    (["mixed_dishes", "meat"],     ["fruits", "vegetables"]),
    (["snacks", "dairy"],          ["vegetables", "beans"]),
    (["grains", "eggs"],           ["fish", "snacks"]),
    (["fruits", "dairy"],          ["meat", "noodles"]),
    (["vegetables", "grains"],     ["snacks", "dairy"]),
    (["meat", "dairy"],            ["vegetables", "fruits"]),
]

_TINY_HERO_REASON_TEMPLATES = [
    "{food} supports the {goal} goal, but it belongs to {category}, which this child finds tricky to enjoy.",
    "{food} is good for {goal}, but since {category} is not a favourite, it is a tiny hero food to try a little at a time.",
    "{food} helps with {goal}, but it can be a small challenge because {category} is disliked.",
    "{food} supports {goal}, but it takes a little courage to try because {category} is not usually enjoyed.",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def make_example(user_content: str, assistant_obj: dict, task_type: str) -> dict:
    """Build a single training example with internal _task_type tag (stripped before writing)."""
    return {
        "_task_type": task_type,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": json.dumps(assistant_obj, ensure_ascii=False)},
        ],
    }


def is_safe_record(record: dict) -> bool:
    if record.get("ai_review_status") != "reviewed":
        return False
    if "_ai_validation_errors" in record:
        return False
    if not record.get("clean_name"):
        return False
    if not record.get("health_level"):
        return False
    if not record.get("child_friendly_reason"):
        return False
    for tag in record.get("goal_tags") or []:
        if tag not in VALID_GOAL_TAGS:
            return False
    return True


_CALORIE_PATTERN = re.compile(r"\b(lower in calories|fewer calories|less calories|high.calori\w*|calori\w+|kcal)\b", re.IGNORECASE)

_CALORIE_REPLACEMENTS = [
    (re.compile(r"\blower in calories\b", re.IGNORECASE), "a better everyday choice"),
    (re.compile(r"\bfewer calories\b", re.IGNORECASE), "a lighter option"),
    (re.compile(r"\bless calories\b", re.IGNORECASE), "a lighter choice"),
    (re.compile(r"\bhigh[- ]calori\w*\b", re.IGNORECASE), "energy-dense"),
    (re.compile(r"\bcalori\w+\b", re.IGNORECASE), "filling"),
    (re.compile(r"\bkcal\b", re.IGNORECASE), ""),
]


def clean_reason(text: str) -> str:
    """Replace calorie language in reason/advice text with child-friendly alternatives."""
    if not text:
        return text
    for pattern, replacement in _CALORIE_REPLACEMENTS:
        text = pattern.sub(replacement, text)
    # Collapse any double spaces left by empty replacements
    text = re.sub(r"  +", " ", text).strip()
    return text


def get_alt_info(record: dict) -> dict[str, Any]:
    rg = (record.get("replacement_group") or "").strip()
    cat = record.get("clean_category", "")
    return (
        _REPLACEMENT_ALT.get(rg)
        or _CATEGORY_FALLBACK_ALT.get(cat)
        or _DEFAULT_ALT
    )


# ---------------------------------------------------------------------------
# Task A: health_judgement
# ---------------------------------------------------------------------------
def gen_task_a(record: dict) -> dict:
    name = record["clean_name"]
    category = record.get("clean_category", "food")
    health_level = record["health_level"]
    goal_tags = record.get("goal_tags") or []
    role = record.get("recommendation_role", "alternative_candidate")
    reason = clean_reason(record["child_friendly_reason"])

    user = (
        f"Task: health_judgement\n"
        f"Food: {name}\n"
        f"Category: {category}\n"
        f"Health level from metadata: {health_level}\n"
        f"Question: Is this food suitable for everyday healthy eating for a child?"
    )
    assistant: dict[str, Any] = {
        "food": name,
        "health_level": health_level,
        "goal_tags": goal_tags,
        "recommendation_role": role,
        "reason": reason,
    }
    return make_example(user, assistant, "task_a_health_judgement")


# ---------------------------------------------------------------------------
# Task B: goal_matching
# ---------------------------------------------------------------------------
def gen_task_b(record: dict, goal: str) -> dict:
    name = record["clean_name"]
    health_level = record["health_level"]

    goal_reason = record.get("goal_reason")
    if isinstance(goal_reason, dict) and goal_reason.get(goal):
        reason = clean_reason(goal_reason[goal])
    else:
        reason = clean_reason(record["child_friendly_reason"])

    user = (
        f"Task: goal_matching\n"
        f"Food: {name}\n"
        f"Goal: {goal}\n"
        f"Question: Does this food support this child goal?"
    )
    assistant: dict[str, Any] = {
        "food": name,
        "goal": goal,
        "goal_match": True,
        "health_level": health_level,
        "reason": reason,
    }
    return make_example(user, assistant, "task_b_goal_matching")


# ---------------------------------------------------------------------------
# Task C: try_less_judgement
# ---------------------------------------------------------------------------
def gen_task_c(record: dict) -> dict:
    name = record["clean_name"]
    reason = clean_reason(record["child_friendly_reason"])

    user = (
        f"Task: try_less_judgement\n"
        f"Food: {name}\n"
        f"Question: Should this food be a main recommendation for a child?"
    )
    assistant: dict[str, Any] = {
        "food": name,
        "main_recommendation": False,
        "health_level": "try_less",
        "goal_tags": [],
        "reason": reason,
    }
    return make_example(user, assistant, "task_c_try_less_judgement")


# ---------------------------------------------------------------------------
# Task D: alternative_generation
# ---------------------------------------------------------------------------
def gen_task_d(record: dict) -> dict:
    name = record["clean_name"]
    health_level = record["health_level"]
    taste_profile = record.get("taste_profile") or []

    alt = get_alt_info(record)
    alternative = alt["alternative"]
    alt_goal_tags: list[str] = list(alt["goal_tags"])

    if isinstance(taste_profile, list) and len(taste_profile) >= 2:
        similarity = f"{taste_profile[0]} and {taste_profile[1]}"
    elif isinstance(taste_profile, list) and len(taste_profile) == 1:
        similarity = str(taste_profile[0])
    else:
        similarity = str(alt["similarity"])

    user = (
        f"Task: alternative_generation\n"
        f"Food: {name}\n"
        f"Health level: {health_level}\n"
        f"Question: What is a healthier alternative to this food for a child?"
    )
    assistant: dict[str, Any] = {
        "original_food": name,
        "better_alternative": alternative,
        "similarity": similarity,
        "goal_match": len(alt_goal_tags) > 0,
        "goal_tags": alt_goal_tags,
        "reason": clean_reason(record["child_friendly_reason"]),
    }
    return make_example(user, assistant, "task_d_alternative_generation")


# ---------------------------------------------------------------------------
# Task E: integrated_recommendation
# ---------------------------------------------------------------------------
def gen_task_e_batch(
    rng: random.Random,
    safe_records: list[dict],
    try_less_records: list[dict],
    count: int,
) -> list[dict]:
    # Index records with goal_tags by goal
    by_goal: dict[str, list[dict]] = defaultdict(list)
    for r in safe_records:
        for g in r.get("goal_tags") or []:
            if g in VALID_GOAL_TAGS:
                by_goal[g].append(r)

    goals = sorted(VALID_GOAL_TAGS)
    examples: list[dict] = []
    attempts = 0
    max_attempts = count * 10

    while len(examples) < count and attempts < max_attempts:
        attempts += 1

        goal = rng.choice(goals)
        liked_cats, disliked_cats = rng.choice(_PREFERENCE_PROFILES)

        goal_recs = by_goal.get(goal, [])
        if not goal_recs:
            continue

        # super_power: match goal, liked category, healthy or sometimes (prefer healthy)
        super_healthy = [
            r for r in goal_recs
            if r.get("clean_category") in liked_cats
            and r.get("health_level") == "healthy"
        ]
        super_sometimes = [
            r for r in goal_recs
            if r.get("clean_category") in liked_cats
            and r.get("health_level") == "sometimes"
        ]
        super_pool = super_healthy + super_sometimes

        if not super_pool:
            continue  # Can't build a meaningful example without super_power foods

        # tiny_hero: match goal, disliked category, healthy or sometimes (never try_less)
        tiny_pool = [
            r for r in goal_recs
            if r.get("clean_category") in disliked_cats
            and r.get("health_level") in ("healthy", "sometimes")
        ]

        # try_less: prefer liked categories, fall back to all try_less
        try_pool = [r for r in try_less_records if r.get("clean_category") in liked_cats]
        if not try_pool:
            try_pool = list(try_less_records)

        n_super = rng.randint(1, min(3, len(super_pool)))
        n_tiny = rng.randint(0, min(2, len(tiny_pool)))
        n_try = rng.randint(0, min(2, len(try_pool))) if try_pool else 0

        selected_super = rng.sample(super_pool, n_super)
        selected_tiny = rng.sample(tiny_pool, n_tiny) if n_tiny > 0 else []
        selected_try = rng.sample(try_pool, n_try) if n_try > 0 else []

        liked_str = ", ".join(liked_cats)
        disliked_str = ", ".join(disliked_cats)

        user = (
            f"Task: integrated_recommendation\n"
            f"Goal: {goal}\n"
            f"Child likes: {liked_str}\n"
            f"Child dislikes: {disliked_str}\n"
            f"Question: Suggest foods for a child with this goal, likes, and dislikes."
        )

        tiny_hero_list = []
        for r in selected_tiny:
            tmpl = rng.choice(_TINY_HERO_REASON_TEMPLATES)
            reason = tmpl.format(
                food=r["clean_name"],
                goal=goal,
                category=r.get("clean_category", "this type of food"),
            )
            tiny_hero_list.append({"food": r["clean_name"], "reason": reason})

        assistant: dict[str, Any] = {
            "goal": goal,
            "super_power_foods": [
                {"food": r["clean_name"], "reason": clean_reason(r["child_friendly_reason"])}
                for r in selected_super
            ],
            "tiny_hero_foods": tiny_hero_list,
            "try_less_foods": [
                {"food": r["clean_name"], "reason": clean_reason(r["child_friendly_reason"])}
                for r in selected_try
            ],
        }

        examples.append(make_example(user, assistant, "task_e_integrated_recommendation"))

    if len(examples) < count:
        logger.warning(
            "Generated %d/%d Task E examples after %d attempts",
            len(examples), count, attempts,
        )

    return examples


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
def run(args: argparse.Namespace) -> None:
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)

    # --- Load records ---
    if not input_path.exists():
        logger.error("Input file not found: %s", input_path)
        sys.exit(1)

    logger.info("Loading records from: %s", input_path)
    with open(input_path, encoding="utf-8") as f:
        all_records: list[dict] = json.load(f)
    logger.info("Loaded %d records", len(all_records))

    # --- Filter safe records ---
    safe_records = [r for r in all_records if is_safe_record(r)]
    logger.info("Safe records after filtering: %d / %d", len(safe_records), len(all_records))

    if args.max_examples and len(safe_records) > args.max_examples:
        safe_records = safe_records[: args.max_examples]
        logger.info("Capped to %d records via --max-examples", len(safe_records))

    try_less_records = [r for r in safe_records if r.get("health_level") == "try_less"]
    sometimes_records = [r for r in safe_records if r.get("health_level") == "sometimes"]
    healthy_records = [r for r in safe_records if r.get("health_level") == "healthy"]
    logger.info(
        "Health breakdown — healthy: %d, sometimes: %d, try_less: %d",
        len(healthy_records), len(sometimes_records), len(try_less_records),
    )

    # --- Generate examples ---
    rng = random.Random(args.seed)
    all_examples: list[dict] = []

    # Task A: health_judgement — one per safe record
    for r in safe_records:
        all_examples.append(gen_task_a(r))
    logger.info("Task A (health_judgement)          : %d examples", len(all_examples))

    # Task B: goal_matching — one per (record, goal_tag)
    task_b_start = len(all_examples)
    for r in safe_records:
        for goal in (r.get("goal_tags") or []):
            if goal in VALID_GOAL_TAGS:
                all_examples.append(gen_task_b(r, goal))
    logger.info("Task B (goal_matching)             : %d examples", len(all_examples) - task_b_start)

    # Task C: try_less_judgement — one per try_less record
    task_c_start = len(all_examples)
    for r in try_less_records:
        all_examples.append(gen_task_c(r))
    logger.info("Task C (try_less_judgement)        : %d examples", len(all_examples) - task_c_start)

    # Task D: alternative_generation — try_less + sometimes records
    task_d_start = len(all_examples)
    for r in try_less_records + sometimes_records:
        all_examples.append(gen_task_d(r))
    logger.info("Task D (alternative_generation)    : %d examples", len(all_examples) - task_d_start)

    # Task E: integrated_recommendation — fixed count
    task_e_start = len(all_examples)
    task_e_examples = gen_task_e_batch(rng, safe_records, try_less_records, args.integrated_count)
    all_examples.extend(task_e_examples)
    logger.info("Task E (integrated_recommendation) : %d examples", len(all_examples) - task_e_start)

    total = len(all_examples)
    logger.info("Total examples before split: %d", total)

    # --- Shuffle and split (seed-reproducible) ---
    rng.shuffle(all_examples)

    n_train = int(total * args.train_ratio)
    n_valid = int(total * args.valid_ratio)
    n_test = total - n_train - n_valid  # remainder avoids rounding loss

    train_examples = all_examples[:n_train]
    valid_examples = all_examples[n_train: n_train + n_valid]
    test_examples  = all_examples[n_train + n_valid:]

    logger.info(
        "Split — train: %d, valid: %d, test: %d",
        len(train_examples), len(valid_examples), len(test_examples),
    )

    # --- Task type counts ---
    def count_tasks(examples: list[dict]) -> dict[str, int]:
        c: Counter = Counter(ex.get("_task_type", "unknown") for ex in examples)
        return dict(sorted(c.items()))

    total_task_counts = count_tasks(all_examples)
    train_task_counts = count_tasks(train_examples)
    valid_task_counts = count_tasks(valid_examples)
    test_task_counts  = count_tasks(test_examples)

    # --- Dry run ---
    if args.dry_run:
        print("\n" + "=" * 60)
        print("DRY RUN — no files written")
        print("=" * 60)
        print(f"  Input records     : {len(all_records)} total / {len(safe_records)} safe")
        print(f"  Total examples    : {total}")
        print(f"  Train             : {len(train_examples)}")
        print(f"  Valid             : {len(valid_examples)}")
        print(f"  Test              : {len(test_examples)}")
        print(f"\n  Task type distribution (total):")
        for task, cnt in total_task_counts.items():
            print(f"    {task:<45} {cnt:>6}")
        print("=" * 60)
        return

    # --- Write JSONL files ---
    output_dir.mkdir(parents=True, exist_ok=True)

    splits: dict[str, tuple[Path, list[dict]]] = {
        "train": (output_dir / "food_recommender_train.jsonl", train_examples),
        "valid": (output_dir / "food_recommender_valid.jsonl", valid_examples),
        "test":  (output_dir / "food_recommender_test.jsonl",  test_examples),
    }

    for split_name, (path, examples) in splits.items():
        with open(path, "w", encoding="utf-8") as f:
            for ex in examples:
                record = {k: v for k, v in ex.items() if not k.startswith("_")}
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        logger.info("Wrote %d examples -> %s", len(examples), path)

    # --- Write summary ---
    summary: dict[str, Any] = {
        "input_file": str(input_path),
        "output_dir": str(output_dir),
        "seed": args.seed,
        "total_input_records": len(all_records),
        "total_safe_records": len(safe_records),
        "total_examples": total,
        "train_count": len(train_examples),
        "valid_count": len(valid_examples),
        "test_count": len(test_examples),
        "train_ratio": args.train_ratio,
        "valid_ratio": args.valid_ratio,
        "test_ratio": args.test_ratio,
        "integrated_count_requested": args.integrated_count,
        "integrated_count_generated": len(task_e_examples),
        "task_type_distribution": {
            "total": total_task_counts,
            "train": train_task_counts,
            "valid": valid_task_counts,
            "test":  test_task_counts,
        },
    }

    summary_path = output_dir / "finetune_generation_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    logger.info("Wrote summary -> %s", summary_path)

    # --- Final summary print ---
    print("\n" + "=" * 60)
    print("FINETUNE JSONL GENERATION COMPLETE")
    print("=" * 60)
    print(f"  Input records     : {len(all_records)} total / {len(safe_records)} safe")
    print(f"  Total examples    : {total}")
    print(f"  Train             : {len(train_examples)}")
    print(f"  Valid             : {len(valid_examples)}")
    print(f"  Test              : {len(test_examples)}")
    print(f"\n  Task type distribution (total):")
    for task, cnt in total_task_counts.items():
        print(f"    {task:<45} {cnt:>6}")
    print(f"\n  Output dir        : {output_dir}")
    print("=" * 60)
    print("\nNext step: python scripts/validate_finetune_jsonl.py")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate OpenAI fine-tuning JSONL from AI-reviewed food metadata.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input", default=str(DEFAULT_INPUT), metavar="PATH",
        help=f"Input JSON file (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output-dir", default=str(DEFAULT_OUTPUT_DIR), metavar="DIR",
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--max-examples", type=int, default=None, metavar="N",
        help="Limit input to first N safe records (default: use all)",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducible shuffle and split (default: 42)",
    )
    parser.add_argument(
        "--train-ratio", type=float, default=0.8,
        help="Fraction of examples for training (default: 0.8)",
    )
    parser.add_argument(
        "--valid-ratio", type=float, default=0.1,
        help="Fraction of examples for validation (default: 0.1)",
    )
    parser.add_argument(
        "--test-ratio", type=float, default=0.1,
        help="Fraction of examples for testing (default: 0.1)",
    )
    parser.add_argument(
        "--integrated-count", type=int, default=400, metavar="N",
        help="Number of Task E integrated_recommendation examples to generate (default: 400)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print statistics without writing any files",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    total_ratio = args.train_ratio + args.valid_ratio + args.test_ratio
    if abs(total_ratio - 1.0) > 0.001:
        print(
            f"[ERROR] --train-ratio + --valid-ratio + --test-ratio must sum to 1.0, "
            f"got {total_ratio:.3f}",
            file=sys.stderr,
        )
        sys.exit(1)

    run(args)


if __name__ == "__main__":
    main()
