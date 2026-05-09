"""
Validate Fine-Tuning JSONL Files
===================================
Validates the JSONL files produced by generate_finetune_jsonl.py.

Checks per line:
  1. Valid JSON
  2. Record has 'messages' key
  3. Messages contain system, user, assistant roles
  4. Assistant content is valid JSON
  5. No unsupported goal_id values in assistant JSON
  6. No calorie mentions in assistant content
  7. No unsafe food terms recommended (pork, alcohol, caffeine, supplements, etc.)

Report:
  - train / valid / test line counts
  - total examples
  - task type distribution (inferred from assistant JSON shape)
  - assistant JSON parse success rate
  - unsupported goal count
  - calorie mention count
  - unsafe recommended food count

Usage:
    python scripts/validate_finetune_jsonl.py
    python scripts/validate_finetune_jsonl.py --input-dir data/finetune
    python scripts/validate_finetune_jsonl.py --verbose
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from collections import Counter
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT_DIR = ROOT / "data" / "finetune"

# ---------------------------------------------------------------------------
# Validation constants
# ---------------------------------------------------------------------------
VALID_GOAL_IDS = {"grow", "see", "think", "fight", "feel", "strong"}

UNSUPPORTED_GOALS = {
    "energy", "immune", "brain", "eyesight", "height",
    "bones", "muscle", "immunity", "vision", "memory",
    "nutrition", "stamina", "endurance", "focus",
}

# Terms that should NOT appear as recommended foods in better_alternative / food fields
UNSAFE_FOOD_TERMS = {
    "pork", "bacon", "ham", "lard", "pork belly", "pork chop", "pork ribs",
    "beer", "wine", "alcohol", "vodka", "whiskey", "whisky", "spirits", "liquor",
    "caffeine", "energy drink", "coffee drink", "caffeinated",
    "supplement", "protein powder", "vitamin supplement", "mineral supplement",
    "baby formula", "infant formula", "medical food", "formula milk",
}

CALORIE_PATTERN = re.compile(r"\bcalori(e|es|ic)\b|\bkcal\b", re.IGNORECASE)

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
# Structural checks
# ---------------------------------------------------------------------------
def check_structure(record: dict) -> tuple[bool, str]:
    """Returns (ok, error_message)."""
    if "messages" not in record:
        return False, "missing 'messages' key"

    messages = record["messages"]
    if not isinstance(messages, list):
        return False, f"'messages' must be a list, got {type(messages).__name__}"
    if len(messages) < 3:
        return False, f"'messages' must have at least 3 items, got {len(messages)}"

    roles = [m.get("role") for m in messages if isinstance(m, dict)]
    for required_role in ("system", "user", "assistant"):
        if required_role not in roles:
            return False, f"missing '{required_role}' message"

    return True, ""


def get_assistant_content(record: dict) -> str | None:
    for msg in record.get("messages", []):
        if isinstance(msg, dict) and msg.get("role") == "assistant":
            return msg.get("content")
    return None


def parse_assistant_json(content: str) -> tuple[dict | None, str]:
    """Returns (parsed_object, error_message)."""
    try:
        obj = json.loads(content)
        if not isinstance(obj, dict):
            return None, f"expected JSON object, got {type(obj).__name__}"
        return obj, ""
    except json.JSONDecodeError as e:
        return None, str(e)


# ---------------------------------------------------------------------------
# Content checks
# ---------------------------------------------------------------------------
def infer_task_type(obj: dict) -> str:
    """Infer task type from assistant JSON shape."""
    if "super_power_foods" in obj and "goal" in obj:
        return "task_e"
    if "original_food" in obj:
        return "task_d"
    if "main_recommendation" in obj:
        return "task_c"
    if "goal_match" in obj and "goal" in obj:
        return "task_b"
    if "recommendation_role" in obj:
        return "task_a"
    return "unknown"


def check_unsupported_goals(obj: dict) -> list[str]:
    """Return list of unsupported goal values found anywhere in the assistant JSON."""
    found: list[str] = []

    def _check_tag(tag: str) -> None:
        if isinstance(tag, str) and tag.lower() in UNSUPPORTED_GOALS:
            found.append(tag)

    # Top-level goal_tags array
    for tag in obj.get("goal_tags") or []:
        _check_tag(tag)

    # Top-level 'goal' string
    goal = obj.get("goal")
    if isinstance(goal, str):
        _check_tag(goal)

    # Nested inside super_power_foods / tiny_hero_foods / try_less_foods
    for key in ("super_power_foods", "tiny_hero_foods", "try_less_foods"):
        for item in obj.get(key) or []:
            if isinstance(item, dict):
                for tag in item.get("goal_tags") or []:
                    _check_tag(tag)

    return found


def extract_advice_texts(obj: dict) -> list[str]:
    """
    Extract only the advice/reason text fields from the assistant JSON.
    Deliberately excludes food name fields (food, original_food, better_alternative)
    because those may legitimately contain product names that include 'calorie'.
    """
    texts: list[str] = []

    for key in ("reason", "similarity"):
        val = obj.get(key)
        if isinstance(val, str):
            texts.append(val)

    for key in ("super_power_foods", "tiny_hero_foods", "try_less_foods"):
        for item in obj.get(key) or []:
            if isinstance(item, dict):
                r = item.get("reason")
                if isinstance(r, str):
                    texts.append(r)

    return texts


def check_calories(obj: dict) -> bool:
    """Check calorie mentions only in advice/reason fields, not food name fields."""
    for text in extract_advice_texts(obj):
        if CALORIE_PATTERN.search(text):
            return True
    return False


def check_unsafe_foods(obj: dict) -> list[str]:
    """
    Return unsafe food terms found in recommendation output fields.
    Checks: better_alternative, food (top-level), and food keys inside list items.
    """
    found: set[str] = set()

    candidate_texts: list[str] = []

    val = obj.get("better_alternative")
    if isinstance(val, str):
        candidate_texts.append(val)

    val = obj.get("food")
    if isinstance(val, str):
        candidate_texts.append(val)

    for key in ("super_power_foods", "tiny_hero_foods"):
        for item in obj.get(key) or []:
            if isinstance(item, dict):
                food_val = item.get("food")
                if isinstance(food_val, str):
                    candidate_texts.append(food_val)

    for text in candidate_texts:
        text_lower = text.lower()
        for term in UNSAFE_FOOD_TERMS:
            if term in text_lower:
                found.add(term)

    return sorted(found)


# ---------------------------------------------------------------------------
# Per-file validation
# ---------------------------------------------------------------------------
def validate_file(path: Path, verbose: bool = False) -> dict:
    stats: dict = {
        "file": path.name,
        "total_lines": 0,
        "valid_json": 0,
        "invalid_json": 0,
        "structure_ok": 0,
        "structure_errors": 0,
        "assistant_json_ok": 0,
        "assistant_json_fail": 0,
        "unsupported_goal_count": 0,
        "calorie_mention_count": 0,
        "unsafe_food_count": 0,
        "task_type_counts": Counter(),
        "errors": [],
    }

    with open(path, encoding="utf-8") as f:
        for line_num, raw_line in enumerate(f, 1):
            line = raw_line.strip()
            if not line:
                continue

            stats["total_lines"] += 1

            # Check 1: valid JSON
            try:
                record = json.loads(line)
                stats["valid_json"] += 1
            except json.JSONDecodeError as e:
                stats["invalid_json"] += 1
                msg = f"Line {line_num}: invalid JSON — {e}"
                stats["errors"].append(msg)
                if verbose:
                    logger.warning(msg)
                continue

            # Check 2: structure
            ok, err = check_structure(record)
            if ok:
                stats["structure_ok"] += 1
            else:
                stats["structure_errors"] += 1
                msg = f"Line {line_num}: structure error — {err}"
                stats["errors"].append(msg)
                if verbose:
                    logger.warning(msg)
                continue

            # Check 3: assistant content is valid JSON
            content = get_assistant_content(record)
            if content is None:
                stats["assistant_json_fail"] += 1
                msg = f"Line {line_num}: no assistant content found"
                stats["errors"].append(msg)
                continue

            obj, parse_err = parse_assistant_json(content)
            if obj is None:
                stats["assistant_json_fail"] += 1
                msg = f"Line {line_num}: assistant JSON parse error — {parse_err}"
                stats["errors"].append(msg)
                if verbose:
                    logger.warning(msg)
                continue

            stats["assistant_json_ok"] += 1
            stats["task_type_counts"][infer_task_type(obj)] += 1

            # Check 4: unsupported goal values
            bad_goals = check_unsupported_goals(obj)
            if bad_goals:
                stats["unsupported_goal_count"] += 1
                msg = f"Line {line_num}: unsupported goal value(s): {bad_goals}"
                stats["errors"].append(msg)
                if verbose:
                    logger.warning(msg)

            # Check 5: calorie mentions in advice/reason fields
            if check_calories(obj):
                stats["calorie_mention_count"] += 1
                msg = f"Line {line_num}: calorie mention detected in advice/reason text"
                stats["errors"].append(msg)
                if verbose:
                    logger.warning(msg)

            # Check 6: unsafe recommended food terms
            unsafe = check_unsafe_foods(obj)
            if unsafe:
                stats["unsafe_food_count"] += 1
                msg = f"Line {line_num}: unsafe food term(s) in recommendation: {unsafe}"
                stats["errors"].append(msg)
                if verbose:
                    logger.warning(msg)

    total_assist = stats["assistant_json_ok"] + stats["assistant_json_fail"]
    stats["assistant_json_parse_rate"] = (
        stats["assistant_json_ok"] / total_assist if total_assist > 0 else 0.0
    )

    return stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def run(args: argparse.Namespace) -> None:
    input_dir = Path(args.input_dir)

    files: dict[str, Path] = {
        "train": input_dir / "food_recommender_train.jsonl",
        "valid": input_dir / "food_recommender_valid.jsonl",
        "test":  input_dir / "food_recommender_test.jsonl",
    }

    missing = [name for name, path in files.items() if not path.exists()]
    if missing:
        logger.error("Missing JSONL file(s): %s", ", ".join(missing))
        sys.exit(1)

    all_stats: dict[str, dict] = {}
    total_task_counts: Counter = Counter()

    for split_name, path in files.items():
        logger.info("Validating %s (%s) …", split_name, path.name)
        stats = validate_file(path, verbose=args.verbose)
        all_stats[split_name] = stats
        total_task_counts += stats["task_type_counts"]

    # --- Aggregate ---
    total_examples      = sum(s["total_lines"]            for s in all_stats.values())
    total_invalid_json  = sum(s["invalid_json"]           for s in all_stats.values())
    total_struct_errors = sum(s["structure_errors"]       for s in all_stats.values())
    total_assist_ok     = sum(s["assistant_json_ok"]      for s in all_stats.values())
    total_assist_fail   = sum(s["assistant_json_fail"]    for s in all_stats.values())
    total_unsupported   = sum(s["unsupported_goal_count"] for s in all_stats.values())
    total_calories      = sum(s["calorie_mention_count"]  for s in all_stats.values())
    total_unsafe        = sum(s["unsafe_food_count"]      for s in all_stats.values())

    total_assist = total_assist_ok + total_assist_fail
    overall_parse_rate = total_assist_ok / total_assist if total_assist > 0 else 0.0

    # --- Report ---
    print("\n" + "=" * 60)
    print("FINETUNE JSONL VALIDATION REPORT")
    print("=" * 60)

    print(f"\n  Split counts:")
    for split_name, stats in all_stats.items():
        print(f"    {split_name:<8}  {stats['total_lines']:>6} examples")
    print(f"    {'TOTAL':<8}  {total_examples:>6} examples")

    print(f"\n  Task type distribution (all splits):")
    for task_type in sorted(total_task_counts.keys()):
        print(f"    {task_type:<45} {total_task_counts[task_type]:>6}")

    print(f"\n  Validation results:")
    print(f"    Invalid JSON lines          : {total_invalid_json}")
    print(f"    Structure errors            : {total_struct_errors}")
    print(f"    Assistant JSON parse rate   : {overall_parse_rate:.1%}"
          f"  ({total_assist_ok}/{total_assist})")
    print(f"    Unsupported goal count      : {total_unsupported}")
    print(f"    Calorie mention count       : {total_calories}")
    print(f"    Unsafe food term count      : {total_unsafe}")

    any_issues = (
        total_invalid_json  > 0 or
        total_struct_errors > 0 or
        total_assist_fail   > 0 or
        total_unsupported   > 0 or
        total_calories      > 0 or
        total_unsafe        > 0
    )

    if any_issues:
        print(f"\n  [WARN] Issues found — re-run with --verbose to see per-line details.")
        if args.verbose:
            for split_name, stats in all_stats.items():
                if stats["errors"]:
                    print(f"\n  Errors in {split_name} ({len(stats['errors'])} total):")
                    for err in stats["errors"][:30]:
                        print(f"    {err}")
                    if len(stats["errors"]) > 30:
                        print(f"    ... and {len(stats['errors']) - 30} more")
    else:
        print(f"\n  All checks passed.")

    print("=" * 60)

    # Exit non-zero on critical failures
    if total_invalid_json > 0 or total_struct_errors > 0 or overall_parse_rate < 0.99:
        sys.exit(1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate fine-tuning JSONL files for OpenAI fine-tuning.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input-dir", default=str(DEFAULT_INPUT_DIR), metavar="DIR",
        help=f"Directory containing JSONL files (default: {DEFAULT_INPUT_DIR})",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Print per-line error messages",
    )

    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
