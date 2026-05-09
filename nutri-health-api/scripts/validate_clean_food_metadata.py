"""
Validation Script for Cleaned Food Metadata
============================================
Reads:  data/processed/clean_food_metadata.json
        data/processed/removed_food_records.json  (optional)
        data/processed/cleaning_summary.json       (optional)

Run from project root:
    python scripts/validate_clean_food_metadata.py

Exit codes:
    0 = all hard checks pass (warnings may be printed)
    1 = one or more hard checks failed
"""

from __future__ import annotations

import json
import random
import sys
from collections import Counter
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
CLEAN_JSON = ROOT / "data" / "processed" / "clean_food_metadata.json"
REMOVED_JSON = ROOT / "data" / "processed" / "removed_food_records.json"
SUMMARY_JSON = ROOT / "data" / "processed" / "cleaning_summary.json"

# ---------------------------------------------------------------------------
# Allowed value sets (must match clean_food_metadata.py exactly)
# ---------------------------------------------------------------------------
SUPPORTED_GOALS = {"grow", "see", "think", "fight", "feel", "strong"}

ALLOWED_CATEGORIES = {
    "dairy", "meat", "fish", "vegetables", "fruits",
    "rice", "noodles", "grains", "beans", "eggs",
    "snacks", "drinks", "mixed_dishes", "sauces", "other",
}

ALLOWED_HEALTH_LEVELS = {"healthy", "sometimes", "try_less"}

ALLOWED_SUB_CATEGORIES = {
    "plain_milk", "flavored_milk", "yogurt", "cheese", "cheese_spread",
    "butter_fat", "cream", "egg_drink",
    "lean_meat", "processed_meat", "fish", "fruit", "vegetable",
    "rice", "noodles", "grains", "beans",
    "snack_sweet", "sugary_drink", "sauce", "mixed_dish", "other",
}

ALLOWED_RECOMMENDATION_ROLES = {
    "super_power_candidate", "tiny_hero_candidate", "alternative_candidate",
    "try_less_candidate", "avoid_training_only",
}

# Bad patterns that should NOT appear in kept records
BAD_PATTERNS_IN_KEPT = [
    "pork", "bacon", "ham", "pepperoni", "salami", "lard", "spareribs",
    "beer", "wine", "alcohol", "vodka", "rum", "whiskey", "cocktail",
    "energy drink", "espresso",
    "babyfood", "infant formula", "toddler",
    "protein powder", "meal replacement",
    "brain", "tripe", "gizzard",
]

# Thresholds for warnings (not hard failures)
MIN_KEPT_RECORDS = 1000
MIN_TRY_LESS_FRACTION = 0.10   # 10% of kept should be try_less
MIN_GOAL_EXAMPLES = 100
MIN_CATEGORY_EXAMPLES = 30
CORE_CATEGORIES = {
    "dairy", "meat", "fish", "vegetables", "fruits",
    "rice", "noodles", "grains", "beans", "eggs",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _fail(message: str) -> None:
    print(f"\n[FAIL] {message}", file=sys.stderr)


def _warn(message: str) -> None:
    print(f"[WARN] {message}")


def _ok(message: str) -> None:
    print(f"[ OK ] {message}")


# ---------------------------------------------------------------------------
# Main validation
# ---------------------------------------------------------------------------
def validate() -> int:
    """Run all checks. Returns exit code (0 = pass, 1 = fail)."""
    errors = 0

    # ------------------------------------------------------------------
    # 1. Load clean file
    # ------------------------------------------------------------------
    if not CLEAN_JSON.exists():
        _fail(f"Clean metadata file not found: {CLEAN_JSON}")
        print("Run 'python scripts/clean_food_metadata.py' first.", file=sys.stderr)
        return 1

    print(f"Loading: {CLEAN_JSON}")
    with open(CLEAN_JSON, encoding="utf-8") as f:
        records: list[dict] = json.load(f)

    total_kept = len(records)
    print(f"  -> {total_kept} kept records loaded\n")

    # ------------------------------------------------------------------
    # 2. Load optional removed file
    # ------------------------------------------------------------------
    total_removed = 0
    if REMOVED_JSON.exists():
        with open(REMOVED_JSON, encoding="utf-8") as f:
            removed_records: list[dict] = json.load(f)
        total_removed = len(removed_records)
        print(f"Removed records file: {REMOVED_JSON}  ({total_removed} records)")
    else:
        print(f"[INFO] Removed records file not found (skipping): {REMOVED_JSON}")

    # ------------------------------------------------------------------
    # 3. Load optional summary
    # ------------------------------------------------------------------
    if SUMMARY_JSON.exists():
        with open(SUMMARY_JSON, encoding="utf-8") as f:
            summary = json.load(f)
        print(f"Summary file: {SUMMARY_JSON}")
        print(f"  Input total:   {summary.get('total_input', 'n/a')}")
        print(f"  Kept:          {summary.get('total_kept', 'n/a')}")
        print(f"  Removed:       {summary.get('total_removed', 'n/a')}")
    print()

    # ------------------------------------------------------------------
    # 4. Field-level checks on every kept record
    # ------------------------------------------------------------------
    print("=" * 60)
    print("FIELD-LEVEL CHECKS")
    print("=" * 60)

    bad_goal_tags: list[tuple[str, str]] = []
    bad_categories: list[tuple[str, str]] = []
    bad_health_levels: list[tuple[str, str]] = []
    bad_sub_categories: list[tuple[str, str]] = []
    bad_rec_roles: list[tuple[str, str]] = []
    missing_food_id: int = 0
    missing_clean_name: int = 0

    for rec in records:
        fid = rec.get("food_id", "?")

        # goal_tags
        for tag in rec.get("goal_tags") or []:
            if tag not in SUPPORTED_GOALS:
                bad_goal_tags.append((str(fid), tag))

        # clean_category
        cat = rec.get("clean_category")
        if cat not in ALLOWED_CATEGORIES:
            bad_categories.append((str(fid), str(cat)))

        # health_level
        hl = rec.get("health_level")
        if hl not in ALLOWED_HEALTH_LEVELS:
            bad_health_levels.append((str(fid), str(hl)))

        # sub_category
        sc = rec.get("sub_category")
        if sc and sc not in ALLOWED_SUB_CATEGORIES:
            bad_sub_categories.append((str(fid), str(sc)))

        # recommendation_role
        rr = rec.get("recommendation_role")
        if rr and rr not in ALLOWED_RECOMMENDATION_ROLES:
            bad_rec_roles.append((str(fid), str(rr)))

        # required fields
        if not rec.get("food_id"):
            missing_food_id += 1
        if not rec.get("clean_name"):
            missing_clean_name += 1

    if bad_goal_tags:
        _fail(f"Unsupported goal_tags found in {len(bad_goal_tags)} records:")
        for fid, tag in bad_goal_tags[:10]:
            print(f"      food_id={fid}  tag='{tag}'")
        if len(bad_goal_tags) > 10:
            print(f"      ... and {len(bad_goal_tags) - 10} more")
        errors += 1
    else:
        _ok("All goal_tags are valid (only supported backend goal_ids used)")

    if bad_categories:
        _fail(f"Invalid clean_category found in {len(bad_categories)} records:")
        for fid, cat in bad_categories[:10]:
            print(f"      food_id={fid}  category='{cat}'")
        errors += 1
    else:
        _ok("All clean_category values are valid")

    if bad_health_levels:
        _fail(f"Invalid health_level found in {len(bad_health_levels)} records:")
        for fid, hl in bad_health_levels[:10]:
            print(f"      food_id={fid}  health_level='{hl}'")
        errors += 1
    else:
        _ok("All health_level values are valid")

    if bad_sub_categories:
        _fail(f"Invalid sub_category found in {len(bad_sub_categories)} records:")
        for fid, sc in bad_sub_categories[:5]:
            print(f"      food_id={fid}  sub_category='{sc}'")
        errors += 1
    else:
        _ok("All sub_category values are valid")

    if bad_rec_roles:
        _fail(f"Invalid recommendation_role found in {len(bad_rec_roles)} records:")
        for fid, rr in bad_rec_roles[:5]:
            print(f"      food_id={fid}  recommendation_role='{rr}'")
        errors += 1
    else:
        _ok("All recommendation_role values are valid")

    if missing_food_id:
        _fail(f"{missing_food_id} records are missing food_id")
        errors += 1
    else:
        _ok("All records have food_id")

    if missing_clean_name:
        _fail(f"{missing_clean_name} records are missing clean_name")
        errors += 1
    else:
        _ok("All records have clean_name")

    # ------------------------------------------------------------------
    # 5. Bad-pattern leakage check (filtered items should not appear)
    # ------------------------------------------------------------------
    print()
    print("=" * 60)
    print("BAD-PATTERN LEAKAGE CHECKS")
    print("=" * 60)

    leaked: dict[str, list[str]] = {}
    for rec in records:
        name_lower = (rec.get("raw_name") or "").lower()
        for pattern in BAD_PATTERNS_IN_KEPT:
            if pattern in name_lower:
                leaked.setdefault(pattern, []).append(
                    f"  food_id={rec.get('food_id')}  raw='{rec.get('raw_name')}'"
                )

    if leaked:
        _fail(f"Filtered content leaked into kept records for {len(leaked)} patterns:")
        for pattern, examples in leaked.items():
            print(f"  Pattern '{pattern}' ({len(examples)} records):")
            for ex in examples[:3]:
                print(ex)
            if len(examples) > 3:
                print(f"    ... and {len(examples) - 3} more")
        errors += 1
    else:
        _ok("No bad patterns (alcohol/pork/caffeine/supplements/organs) leaked into kept records")

    # ------------------------------------------------------------------
    # 6. Distribution counts
    # ------------------------------------------------------------------
    print()
    print("=" * 60)
    print("DISTRIBUTION COUNTS")
    print("=" * 60)

    category_counts = Counter(r.get("clean_category") for r in records)
    sub_cat_counts = Counter(r.get("sub_category") for r in records)
    goal_counts: Counter = Counter()
    for r in records:
        for g in r.get("goal_tags") or []:
            goal_counts[g] += 1
    health_level_counts = Counter(r.get("health_level") for r in records)
    replacement_group_counts = Counter(r.get("replacement_group") for r in records)
    rec_role_counts = Counter(r.get("recommendation_role") for r in records)
    grade_counts = Counter(r.get("grade") or "Unknown" for r in records)

    print(f"\n  Category distribution ({len(category_counts)} distinct):")
    for cat, count in category_counts.most_common():
        bar = "#" * min(40, count // 5)
        print(f"    {cat:<20} {count:>5}  {bar}")

    print(f"\n  Sub-category distribution (dairy detail):")
    dairy_subs = {
        "plain_milk", "flavored_milk", "yogurt", "cheese",
        "cheese_spread", "butter_fat", "cream", "egg_drink",
    }
    for sc in sorted(dairy_subs):
        count = sub_cat_counts.get(sc, 0)
        if count:
            print(f"    {sc:<20} {count:>5}")

    print(f"\n  Goal tag distribution:")
    for goal in sorted(SUPPORTED_GOALS):
        count = goal_counts.get(goal, 0)
        bar = "#" * min(40, count // 5)
        print(f"    {goal:<10} {count:>5}  {bar}")

    print(f"\n  Health level distribution:")
    for level in ("healthy", "sometimes", "try_less"):
        count = health_level_counts.get(level, 0)
        pct = count / total_kept * 100 if total_kept else 0
        print(f"    {level:<15} {count:>5}  ({pct:.1f}%)")

    print(f"\n  Recommendation role distribution:")
    for role, count in rec_role_counts.most_common():
        print(f"    {role:<30} {count:>5}")

    print(f"\n  Replacement group distribution:")
    for group, count in replacement_group_counts.most_common():
        print(f"    {group:<25} {count:>5}")

    print(f"\n  Grade distribution:")
    for grade, count in grade_counts.most_common():
        print(f"    {grade:<10} {count:>5}")

    # ------------------------------------------------------------------
    # 7. Threshold warnings
    # ------------------------------------------------------------------
    print()
    print("=" * 60)
    print("THRESHOLD WARNINGS")
    print("=" * 60)
    warnings_issued = 0

    if total_kept < MIN_KEPT_RECORDS:
        _warn(f"Only {total_kept} kept records (threshold: {MIN_KEPT_RECORDS}). Dataset may be too small.")
        warnings_issued += 1
    else:
        _ok(f"Kept record count OK: {total_kept} >= {MIN_KEPT_RECORDS}")

    try_less_count = health_level_counts.get("try_less", 0)
    try_less_frac = try_less_count / total_kept if total_kept else 0
    if try_less_frac < MIN_TRY_LESS_FRACTION:
        _warn(
            f"try_less foods = {try_less_count} ({try_less_frac:.1%}) — "
            f"below threshold {MIN_TRY_LESS_FRACTION:.0%}. "
            "Health level inference may be overly generous."
        )
        warnings_issued += 1
    else:
        _ok(f"try_less fraction OK: {try_less_frac:.1%} >= {MIN_TRY_LESS_FRACTION:.0%}")

    for goal in sorted(SUPPORTED_GOALS):
        count = goal_counts.get(goal, 0)
        if count < MIN_GOAL_EXAMPLES:
            _warn(f"Goal '{goal}' has only {count} examples (threshold: {MIN_GOAL_EXAMPLES})")
            warnings_issued += 1
        else:
            _ok(f"Goal '{goal}': {count} examples (>= {MIN_GOAL_EXAMPLES})")

    for cat in sorted(CORE_CATEGORIES):
        count = category_counts.get(cat, 0)
        if count < MIN_CATEGORY_EXAMPLES:
            _warn(f"Core category '{cat}' has only {count} examples (threshold: {MIN_CATEGORY_EXAMPLES})")
            warnings_issued += 1
        else:
            _ok(f"Category '{cat}': {count} examples (>= {MIN_CATEGORY_EXAMPLES})")

    # ------------------------------------------------------------------
    # 8. Random sample
    # ------------------------------------------------------------------
    print()
    print("=" * 60)
    print("RANDOM SAMPLE (20 kept records)")
    print("=" * 60)

    sample_size = min(20, total_kept)
    sample = random.sample(records, sample_size)
    for rec in sample:
        goals = ",".join(rec.get("goal_tags") or []) or "(none)"
        print(
            f"  [{rec.get('clean_category', '?'):<15}|{rec.get('sub_category', '?'):<15}] "
            f"{rec.get('clean_name', '?'):<35}  "
            f"grade={rec.get('grade') or '?'}  "
            f"level={rec.get('health_level', '?'):<10}  "
            f"role={rec.get('recommendation_role', '?'):<25}  "
            f"goals=[{goals}]"
        )

    # ------------------------------------------------------------------
    # 9. Final verdict
    # ------------------------------------------------------------------
    print()
    print("=" * 60)
    print("FINAL RESULT")
    print("=" * 60)
    print(f"  Hard errors : {errors}")
    print(f"  Warnings    : {warnings_issued}")

    if errors == 0:
        print("\n  VALIDATION PASSED")
        if warnings_issued:
            print(f"  (with {warnings_issued} warning(s) — review above)")
    else:
        print(f"\n  VALIDATION FAILED — {errors} error(s) found", file=sys.stderr)

    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(validate())
