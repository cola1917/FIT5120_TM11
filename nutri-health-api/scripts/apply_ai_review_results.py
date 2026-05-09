"""
Apply AI Review Results
=======================
Merges AI-reviewed metadata back into the original cleaned records.

Reads:
    data/processed/ai_review_results/result_*.json   – per-batch AI outputs
    data/processed/clean_food_metadata.json          – original cleaned records

Writes:
    data/processed/ai_reviewed_food_metadata.json    – final merged output (kept)
    data/processed/ai_reviewed_food_metadata.csv     – same, CSV
    data/processed/ai_rejected_food_records.json     – AI-rejected records
    data/processed/ai_apply_summary.json             – run statistics

Usage:
    python scripts/apply_ai_review_results.py
    python scripts/apply_ai_review_results.py --strict   # fail on any validation error
    python scripts/apply_ai_review_results.py --dry-run  # validate only, no writes

Fine-tuning filter (safe subset):
    records where ai_review_status == "reviewed" and "_ai_validation_errors" not in record
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from collections import Counter
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "data" / "processed" / "ai_review_results"
CLEAN_DATA_PATH = ROOT / "data" / "processed" / "clean_food_metadata.json"
OUTPUT_JSON = ROOT / "data" / "processed" / "ai_reviewed_food_metadata.json"
OUTPUT_CSV = ROOT / "data" / "processed" / "ai_reviewed_food_metadata.csv"
REJECTED_JSON = ROOT / "data" / "processed" / "ai_rejected_food_records.json"
SUMMARY_JSON = ROOT / "data" / "processed" / "ai_apply_summary.json"

# ---------------------------------------------------------------------------
# Allowed value sets (must stay in sync with run_ai_metadata_review.py)
# ---------------------------------------------------------------------------
VALID_GOAL_TAGS = {"grow", "see", "think", "fight", "feel", "strong"}
VALID_HEALTH_LEVELS = {"healthy", "sometimes", "try_less"}
VALID_CATEGORIES = {
    "dairy", "meat", "fish", "vegetables", "fruits", "rice", "noodles",
    "grains", "beans", "eggs", "snacks", "drinks", "mixed_dishes", "sauces", "other",
}
VALID_RECOMMENDATION_ROLES = {
    "super_power_candidate", "tiny_hero_candidate", "alternative_candidate",
    "try_less_candidate", "avoid_training_only",
}

# Limits for text fields
CHILD_FRIENDLY_REASON_MAX = 240
REVIEW_NOTE_MAX = 200
ALTERNATIVE_FOR_MAX_ITEMS = 5
ALTERNATIVE_FOR_ITEM_MAX_LEN = 40

# Fields the AI is allowed to update on the original record
AI_UPDATABLE_FIELDS = [
    "clean_name", "display_name", "clean_category", "sub_category",
    "health_level", "goal_tags", "goal_reason", "taste_profile",
    "replacement_group", "recommendation_role",
    "alternative_for", "child_friendly_reason", "review_note",
]

# Fields that come exclusively from the original record (AI must not overwrite)
PRESERVE_FIELDS = [
    "food_id", "source_id", "raw_name",
    "original_category", "grade", "child_friendly",
    "hcl_compliant", "image_url", "removed", "remove_reason",
]

# CSV column order for output
CSV_COLUMNS = [
    "food_id", "source_id", "raw_name", "clean_name", "display_name",
    "clean_category", "sub_category", "original_category", "grade",
    "health_level", "goal_tags", "taste_profile",
    "replacement_group", "recommendation_role",
    "alternative_for", "child_friendly_reason", "review_note",
    "child_friendly", "hcl_compliant", "image_url",
    "ai_review_status", "ai_review_model",
]

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
# Validation helpers
# ---------------------------------------------------------------------------
def _validate_goal_reason(rec: dict, errors: list[str], warnings: list[str]) -> bool:
    """
    Validate goal_reason field:
    - Must be a dict for kept records.
    - No unsupported goal keys allowed.
    - If goal_tags has keys absent from goal_reason, auto-trim goal_tags (warning, not error).
    - If goal_reason has extra keys not in goal_tags, that is a schema error.
    Returns True if a mismatch was found (for counter tracking).
    """
    goal_tags = set(rec.get("goal_tags") or [])
    goal_reason = rec.get("goal_reason")

    if goal_reason is None:
        # Treat missing as empty dict; only an error if goal_tags is non-empty
        if goal_tags:
            errors.append(
                f"goal_reason missing but goal_tags={sorted(goal_tags)}"
            )
            return True
        return False

    if not isinstance(goal_reason, dict):
        errors.append(
            f"goal_reason must be a dict, got {type(goal_reason).__name__}"
        )
        return True

    reason_keys = set(goal_reason.keys())

    # Check for unsupported keys
    unsupported = reason_keys - VALID_GOAL_TAGS
    if unsupported:
        errors.append(f"goal_reason contains unsupported keys: {sorted(unsupported)}")

    # Keys must exactly match goal_tags
    if reason_keys != goal_tags:
        missing_keys = goal_tags - reason_keys   # goal_tags has keys goal_reason lacks
        extra_keys = reason_keys - goal_tags     # goal_reason has keys not in goal_tags

        if missing_keys:
            # Auto-reconcile: trim goal_tags to match goal_reason keys.
            # goal_reason text is treated as authoritative; missing entries = AI omission.
            reconciled = sorted(reason_keys & VALID_GOAL_TAGS)
            rec["goal_tags"] = reconciled
            warnings.append(
                f"goal_reason missing keys {sorted(missing_keys)}; "
                f"goal_tags auto-trimmed to {reconciled}"
            )

        if extra_keys:
            # goal_reason has entries for goals absent from goal_tags — schema error
            errors.append(
                f"goal_reason keys mismatch goal_tags: extra keys not in goal_tags {sorted(extra_keys)}"
            )
            return True

        # Only missing_keys (no extra_keys): warn only, still count as mismatch
        if missing_keys:
            return True

    # If goal_tags is empty, goal_reason must also be empty
    if not goal_tags and goal_reason:
        errors.append("goal_tags is empty but goal_reason is non-empty")
        return True

    return False


def _validate_and_clean_alternative_for(
    rec: dict,
    errors: list[str],
    warnings: list[str],
    strict: bool,
) -> bool:
    """
    Validate and clean alternative_for in-place on rec.
    Returns True if the field had any issues.
    """
    val = rec.get("alternative_for")
    if val is None:
        return False

    had_issues = False

    if not isinstance(val, list):
        msg = f"alternative_for must be a list, got {type(val).__name__}"
        if strict:
            errors.append(msg)
        else:
            warnings.append(msg)
            rec["alternative_for"] = []
        return True

    # Clean: remove non-strings, empty strings, duplicates, enforce max length
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in val:
        if not isinstance(item, str):
            warnings.append(
                f"alternative_for item {item!r} is not a string — removed"
            )
            had_issues = True
            continue
        item = item.strip()
        if not item:
            had_issues = True
            continue
        if item in seen:
            had_issues = True
            continue
        if len(item) > ALTERNATIVE_FOR_ITEM_MAX_LEN:
            warnings.append(
                f"alternative_for item '{item[:30]}...' exceeds {ALTERNATIVE_FOR_ITEM_MAX_LEN} "
                f"chars — truncated"
            )
            item = item[:ALTERNATIVE_FOR_ITEM_MAX_LEN]
            had_issues = True
        seen.add(item)
        cleaned.append(item)

    if len(cleaned) > ALTERNATIVE_FOR_MAX_ITEMS:
        warnings.append(
            f"alternative_for has {len(cleaned)} items (max {ALTERNATIVE_FOR_MAX_ITEMS}) — "
            f"truncated to first {ALTERNATIVE_FOR_MAX_ITEMS}"
        )
        cleaned = cleaned[:ALTERNATIVE_FOR_MAX_ITEMS]
        had_issues = True

    rec["alternative_for"] = cleaned
    return had_issues


def _validate_text_fields(
    rec: dict,
    errors: list[str],
    warnings: list[str],
) -> bool:
    """
    Validate child_friendly_reason and review_note.
    Trims whitespace in-place.
    Returns True if any long-reason warning was issued.
    """
    had_long = False

    # child_friendly_reason
    cfr = rec.get("child_friendly_reason")
    if cfr is None or (isinstance(cfr, str) and not cfr.strip()):
        errors.append("child_friendly_reason must be a non-empty string for kept records")
    elif not isinstance(cfr, str):
        errors.append(
            f"child_friendly_reason must be a string, got {type(cfr).__name__}"
        )
    else:
        rec["child_friendly_reason"] = cfr.strip()
        if len(rec["child_friendly_reason"]) > CHILD_FRIENDLY_REASON_MAX:
            warnings.append(
                f"child_friendly_reason is {len(rec['child_friendly_reason'])} chars "
                f"(max recommended {CHILD_FRIENDLY_REASON_MAX})"
            )
            had_long = True

    # review_note (optional — may be absent or null)
    rn = rec.get("review_note")
    if rn is not None:
        if not isinstance(rn, str):
            errors.append(
                f"review_note must be a string, got {type(rn).__name__}"
            )
        else:
            rec["review_note"] = rn.strip()
            if len(rec["review_note"]) > REVIEW_NOTE_MAX:
                warnings.append(
                    f"review_note is {len(rec['review_note'])} chars "
                    f"(max recommended {REVIEW_NOTE_MAX})"
                )
                had_long = True

    return had_long


# ---------------------------------------------------------------------------
# Main per-record validation
# ---------------------------------------------------------------------------
def validate_ai_record(
    rec: dict,
    strict: bool = False,
) -> tuple[bool, list[str], list[str], dict[str, bool]]:
    """
    Validate a single AI-reviewed record for schema correctness.

    Returns:
        (is_valid, errors, warnings, flags)
        flags keys: goal_reason_mismatch, long_reason, invalid_alternative_for
    """
    errors: list[str] = []
    warnings: list[str] = []
    flags: dict[str, bool] = {
        "goal_reason_mismatch": False,
        "long_reason": False,
        "invalid_alternative_for": False,
    }

    if "keep" not in rec:
        errors.append("missing 'keep' field")
        return False, errors, warnings, flags

    if not rec["keep"]:
        if not rec.get("reject_reason"):
            errors.append("keep=false but no reject_reason")
        return len(errors) == 0, errors, warnings, flags

    # --- Required fields ---
    required = ["food_id", "clean_name", "clean_category", "health_level",
                "goal_tags", "recommendation_role"]
    for field in required:
        if field not in rec:
            errors.append(f"missing required field: {field}")

    if errors:
        return False, errors, warnings, flags

    # --- Value set checks ---
    for tag in rec.get("goal_tags") or []:
        if tag not in VALID_GOAL_TAGS:
            errors.append(f"invalid goal_tag: '{tag}'")

    if rec.get("health_level") not in VALID_HEALTH_LEVELS:
        errors.append(f"invalid health_level: '{rec.get('health_level')}'")

    if rec.get("clean_category") not in VALID_CATEGORIES:
        errors.append(f"invalid clean_category: '{rec.get('clean_category')}'")

    if rec.get("recommendation_role") not in VALID_RECOMMENDATION_ROLES:
        errors.append(f"invalid recommendation_role: '{rec.get('recommendation_role')}'")

    # --- Logical consistency ---
    if rec.get("health_level") == "try_less" and rec.get("goal_tags"):
        errors.append("try_less food should have empty goal_tags")

    # --- goal_reason ---
    flags["goal_reason_mismatch"] = _validate_goal_reason(rec, errors, warnings)

    # --- alternative_for ---
    flags["invalid_alternative_for"] = _validate_and_clean_alternative_for(
        rec, errors, warnings, strict
    )

    # --- child_friendly_reason + review_note ---
    flags["long_reason"] = _validate_text_fields(rec, errors, warnings)

    return len(errors) == 0, errors, warnings, flags


# ---------------------------------------------------------------------------
# Result loading
# ---------------------------------------------------------------------------
def load_all_results(results_dir: Path) -> tuple[list[dict], int, str | None]:
    """
    Load all result_*.json files from results_dir.
    Returns (flat list of AI records, count of files loaded, model name or None).

    Model name is taken from the first result file that contains a top-level
    "model" key in its metadata wrapper.
    """
    result_files = sorted(results_dir.glob("result_*.json"))
    if not result_files:
        return [], 0, None

    all_records: list[dict] = []
    detected_model: str | None = None

    for path in result_files:
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, dict):
                # Capture model from wrapper metadata (first occurrence wins)
                if detected_model is None and isinstance(data.get("model"), str):
                    detected_model = data["model"]

                batch_results = data.get("results")
            else:
                batch_results = data

            if isinstance(batch_results, list):
                all_records.extend(batch_results)
            else:
                logger.warning("Unexpected format in %s — skipping", path.name)

        except Exception as exc:
            logger.error("Failed to load %s: %s", path.name, exc)

    logger.info(
        "Loaded %d AI records from %d result files (model=%s)",
        len(all_records), len(result_files), detected_model or "unknown",
    )
    return all_records, len(result_files), detected_model


# ---------------------------------------------------------------------------
# Merge logic
# ---------------------------------------------------------------------------
def merge_record(
    original: dict,
    ai_rec: dict,
    ai_review_model: str | None,
) -> dict:
    """
    Merge AI-updated fields into the original record.
    Preserves all non-updatable fields from original.
    Stamps ai_review_status and ai_review_model.
    Returns a new merged dict.
    """
    merged = dict(original)  # start from original (preserves all source fields)

    for field in AI_UPDATABLE_FIELDS:
        if field in ai_rec:
            merged[field] = ai_rec[field]

    # Ensure display_name stays consistent with clean_name if AI only updated clean_name
    if "clean_name" in ai_rec and "display_name" not in ai_rec:
        merged["display_name"] = ai_rec["clean_name"].title()

    # Stamp review provenance
    merged["ai_review_status"] = "reviewed"
    merged["ai_review_model"] = ai_review_model

    # Carry validation/warning flags for audit trail
    if "_validation_errors" in ai_rec:
        merged["_ai_validation_errors"] = ai_rec["_validation_errors"]
    if "_validation_warnings" in ai_rec:
        merged["_ai_validation_warnings"] = ai_rec["_validation_warnings"]

    return merged


# ---------------------------------------------------------------------------
# CSV writing
# ---------------------------------------------------------------------------
def write_csv(records: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for rec in records:
            row = dict(rec)
            # Flatten list fields
            for list_field in ("goal_tags", "taste_profile", "alternative_for"):
                val = row.get(list_field)
                if isinstance(val, list):
                    row[list_field] = ",".join(str(v) for v in val)
            # Flatten dict fields
            gr = row.get("goal_reason")
            if isinstance(gr, dict):
                row["goal_reason"] = json.dumps(gr, ensure_ascii=False)
            writer.writerow(row)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
def run(args: argparse.Namespace) -> None:
    # ------------------------------------------------------------------
    # 1. Load original clean records (indexed by food_id)
    # ------------------------------------------------------------------
    if not CLEAN_DATA_PATH.exists():
        logger.error("Original clean metadata not found: %s", CLEAN_DATA_PATH)
        logger.error("Run scripts/clean_food_metadata.py first.")
        sys.exit(1)

    with open(CLEAN_DATA_PATH, encoding="utf-8") as f:
        original_records: list[dict] = json.load(f)

    original_by_id: dict[str, dict] = {
        str(r["food_id"]): r for r in original_records
    }
    logger.info("Loaded %d original records", len(original_records))

    # ------------------------------------------------------------------
    # 2. Load AI review results
    # ------------------------------------------------------------------
    if not RESULTS_DIR.exists():
        logger.error("AI review results directory not found: %s", RESULTS_DIR)
        logger.error("Run scripts/run_ai_metadata_review.py first.")
        sys.exit(1)

    ai_records, num_files, ai_review_model = load_all_results(RESULTS_DIR)
    if not ai_records:
        logger.error("No AI review results found in %s", RESULTS_DIR)
        sys.exit(1)

    # ------------------------------------------------------------------
    # 3. Validate + categorize each AI record
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("VALIDATING AI REVIEW OUTPUT")
    print("=" * 60)

    validation_error_count: int = 0
    records_with_goal_reason_mismatch: int = 0
    records_with_long_reason: int = 0
    records_with_invalid_alternative_for: int = 0

    ai_by_id: dict[str, dict] = {}
    duplicate_food_ids: dict[str, int] = {}   # food_id → occurrence count

    for ai_rec in ai_records:
        food_id = str(ai_rec.get("food_id", ""))

        ok, errors, warnings, flags = validate_ai_record(ai_rec, strict=args.strict)

        # Update counters from flags (even on otherwise-valid records)
        if flags["goal_reason_mismatch"]:
            records_with_goal_reason_mismatch += 1
        if flags["long_reason"]:
            records_with_long_reason += 1
        if flags["invalid_alternative_for"]:
            records_with_invalid_alternative_for += 1

        if not ok:
            logger.warning("food_id=%s failed validation: %s", food_id or "?", errors)
            validation_error_count += 1
            if args.strict:
                logger.error("--strict mode: aborting due to validation error")
                sys.exit(1)
            ai_rec["_validation_errors"] = errors

        if warnings:
            logger.debug("food_id=%s warnings: %s", food_id or "?", warnings)
            ai_rec["_validation_warnings"] = warnings

        # Duplicate detection: track food_ids seen more than once
        if food_id in ai_by_id:
            duplicate_food_ids[food_id] = duplicate_food_ids.get(food_id, 1) + 1
            logger.debug("Duplicate food_id=%s — last occurrence wins", food_id)

        # Deduplicate: if multiple batches contain the same food_id, last wins
        ai_by_id[food_id] = ai_rec

    logger.info("Parsed %d unique food_ids from AI results", len(ai_by_id))
    if duplicate_food_ids:
        logger.warning(
            "%d food_id(s) appeared more than once across result files (last-wins applied): %s%s",
            len(duplicate_food_ids),
            ", ".join(list(duplicate_food_ids.keys())[:5]),
            f" … and {len(duplicate_food_ids) - 5} more" if len(duplicate_food_ids) > 5 else "",
        )
    if validation_error_count:
        logger.warning(
            "%d records had validation errors (kept with _ai_validation_errors flag)",
            validation_error_count,
        )

    # ------------------------------------------------------------------
    # 4. Merge AI records with originals
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("MERGING WITH ORIGINAL RECORDS")
    print("=" * 60)

    kept_merged: list[dict] = []
    rejected_records: list[dict] = []
    unmatched_ids: list[str] = []

    for food_id, ai_rec in ai_by_id.items():
        original = original_by_id.get(food_id)

        if original is None:
            logger.warning("food_id=%s in AI results not found in original data", food_id)
            unmatched_ids.append(food_id)
            continue

        keep = ai_rec.get("keep", True)

        if not keep:
            rejected = dict(original)
            rejected["ai_reject_reason"] = ai_rec.get("reject_reason", "")
            rejected["ai_review_status"] = "rejected"
            rejected["ai_review_model"] = ai_review_model
            rejected_records.append(rejected)
        else:
            merged = merge_record(original, ai_rec, ai_review_model)
            kept_merged.append(merged)

    # Records in original that AI never reviewed — pass through with status flag
    reviewed_ids = set(ai_by_id.keys())
    unreviewed: list[dict] = []
    for r in original_records:
        if str(r["food_id"]) not in reviewed_ids:
            rec = dict(r)
            rec["ai_review_status"] = "not_reviewed"
            rec["ai_review_model"] = None
            unreviewed.append(rec)

    if unreviewed:
        logger.warning(
            "%d original records were not covered by AI review — "
            "included in output with ai_review_status='not_reviewed'",
            len(unreviewed),
        )
        kept_merged.extend(unreviewed)

    # Stable sort: by food_id (numeric where possible)
    def sort_key(r: dict) -> tuple:
        fid = r.get("food_id", "")
        try:
            return (0, int(fid))
        except (ValueError, TypeError):
            return (1, str(fid))

    kept_merged.sort(key=sort_key)
    rejected_records.sort(key=sort_key)

    reviewed_count = len(kept_merged) - len(unreviewed)
    not_reviewed_count = len(unreviewed)
    rejected_count = len(rejected_records)

    # ------------------------------------------------------------------
    # 5. Print distribution summary
    # ------------------------------------------------------------------
    category_counts = Counter(r.get("clean_category") for r in kept_merged)
    health_counts = Counter(r.get("health_level") for r in kept_merged)
    role_counts = Counter(r.get("recommendation_role") for r in kept_merged)
    goal_counts: Counter = Counter()
    for r in kept_merged:
        for g in r.get("goal_tags") or []:
            goal_counts[g] += 1

    total = len(kept_merged)

    print(f"\n  Records kept       : {total}")
    print(f"    reviewed         : {reviewed_count}")
    print(f"    not_reviewed     : {not_reviewed_count}")
    print(f"  Records rejected   : {rejected_count}")
    print(f"  Unmatched IDs      : {len(unmatched_ids)}")
    print(f"  Duplicate food_ids : {len(duplicate_food_ids)}"
          + (f"  ({', '.join(list(duplicate_food_ids.keys())[:3])}"
             + ("…" if len(duplicate_food_ids) > 3 else "") + ")"
             if duplicate_food_ids else ""))
    print(f"  Validation errors  : {validation_error_count}")
    print(f"  Goal reason mismatches       : {records_with_goal_reason_mismatch}")
    print(f"  Long reason warnings         : {records_with_long_reason}")
    print(f"  Invalid alternative_for      : {records_with_invalid_alternative_for}")
    print(f"  AI model           : {ai_review_model or 'unknown'}")

    print(f"\n  Category distribution:")
    for cat, count in category_counts.most_common():
        print(f"    {cat:<20} {count:>5}")

    print(f"\n  Health level distribution:")
    for level in ("healthy", "sometimes", "try_less"):
        count = health_counts.get(level, 0)
        pct = count / total * 100 if total else 0
        print(f"    {level:<15} {count:>5}  ({pct:.1f}%)")

    print(f"\n  Recommendation role distribution:")
    for role, count in role_counts.most_common():
        print(f"    {role:<30} {count:>5}")

    print(f"\n  Goal tag distribution:")
    for goal in sorted(VALID_GOAL_TAGS):
        count = goal_counts.get(goal, 0)
        print(f"    {goal:<10} {count:>5}")

    if unmatched_ids:
        print(f"\n  [WARN] Unmatched food_ids from AI: {unmatched_ids[:10]}")
        if len(unmatched_ids) > 10:
            print(f"         ... and {len(unmatched_ids) - 10} more")

    # Fine-tuning safe subset size
    ft_safe = sum(
        1 for r in kept_merged
        if r.get("ai_review_status") == "reviewed"
        and "_ai_validation_errors" not in r
    )
    print(f"\n  Fine-tuning safe subset        : {ft_safe}")
    print(f"  (ai_review_status='reviewed' and no _ai_validation_errors)")

    # ------------------------------------------------------------------
    # 6. Write outputs (unless dry-run)
    # ------------------------------------------------------------------
    if args.dry_run:
        print("\n" + "=" * 60)
        print("DRY RUN — no files written.")
        print("=" * 60)
        return

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)

    # Atomic JSON write
    tmp = OUTPUT_JSON.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(kept_merged, f, indent=2, ensure_ascii=False)
    tmp.rename(OUTPUT_JSON)
    logger.info("Wrote %d records -> %s", len(kept_merged), OUTPUT_JSON)

    # CSV
    write_csv(kept_merged, OUTPUT_CSV)
    logger.info("Wrote CSV -> %s", OUTPUT_CSV)

    # Rejected
    tmp_rej = REJECTED_JSON.with_suffix(".tmp")
    with open(tmp_rej, "w", encoding="utf-8") as f:
        json.dump(rejected_records, f, indent=2, ensure_ascii=False)
    tmp_rej.rename(REJECTED_JSON)
    logger.info("Wrote %d rejected records -> %s", len(rejected_records), REJECTED_JSON)

    # Summary
    summary = {
        "total_original": len(original_records),
        "ai_result_files": num_files,
        "ai_records_loaded": len(ai_records),
        "ai_unique_ids": len(ai_by_id),
        "ai_review_model": ai_review_model,
        "strict_mode": args.strict,
        # Status counts
        "reviewed_count": reviewed_count,
        "not_reviewed_count": not_reviewed_count,
        "rejected_count": rejected_count,
        "total_kept": len(kept_merged),
        "unmatched_ids": len(unmatched_ids),
        "duplicate_ai_result_food_ids": len(duplicate_food_ids),
        "duplicate_ai_result_examples": list(duplicate_food_ids.keys())[:10],
        # Validation counts
        "validation_error_count": validation_error_count,
        "records_with_goal_reason_mismatch": records_with_goal_reason_mismatch,
        "records_with_long_reason": records_with_long_reason,
        "records_with_invalid_alternative_for": records_with_invalid_alternative_for,
        "fine_tuning_safe_count": ft_safe,
        # Distributions
        "category_distribution": dict(category_counts),
        "health_level_distribution": dict(health_counts),
        "recommendation_role_distribution": dict(role_counts),
        "goal_tag_distribution": dict(goal_counts),
    }
    with open(SUMMARY_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    logger.info("Wrote summary -> %s", SUMMARY_JSON)

    # ------------------------------------------------------------------
    # 7. Final result
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("APPLY COMPLETE")
    print("=" * 60)
    print(f"  Final kept records : {len(kept_merged)}")
    print(f"    reviewed         : {reviewed_count}")
    print(f"    not_reviewed     : {not_reviewed_count}")
    print(f"  AI rejected        : {rejected_count}")
    print(f"  Fine-tuning safe   : {ft_safe}")
    if validation_error_count:
        print(f"  [WARN] {validation_error_count} records had schema errors "
              f"(flagged with _ai_validation_errors)")
    if records_with_goal_reason_mismatch:
        print(f"  [WARN] {records_with_goal_reason_mismatch} records had goal_reason mismatches")
    if records_with_long_reason:
        print(f"  [WARN] {records_with_long_reason} records had long reason strings")
    if records_with_invalid_alternative_for:
        print(f"  [WARN] {records_with_invalid_alternative_for} records had "
              f"alternative_for issues (cleaned in output)")
    print(f"\n  Output JSON        : {OUTPUT_JSON}")
    print(f"  Output CSV         : {OUTPUT_CSV}")
    print(f"  Rejected records   : {REJECTED_JSON}")
    print(f"  Summary            : {SUMMARY_JSON}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Merge AI review results into final food metadata.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Validate and summarize without writing any output files",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Abort immediately if any AI record fails schema validation",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    run(args)


if __name__ == "__main__":
    main()
