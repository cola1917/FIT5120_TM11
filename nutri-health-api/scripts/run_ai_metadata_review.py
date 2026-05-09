"""
AI Metadata Review Runner
=========================
Sends cleaned food metadata to OpenAI for few-shot AI review.
Reads the system prompt from prompts/food_metadata_ai_review_prompt.md.
Reads batch inputs from data/processed/ai_review_batches/  (prepared by
  prepare_ai_review_batches.py, or auto-prepared if none exist).
Saves API results to data/processed/ai_review_results/.

Usage:
    python scripts/run_ai_metadata_review.py
    python scripts/run_ai_metadata_review.py --limit 50
    python scripts/run_ai_metadata_review.py --dry-run
    python scripts/run_ai_metadata_review.py --batch-size 5 --model gpt-4o
    python scripts/run_ai_metadata_review.py --provider openai --model gpt-4o-mini
    python scripts/run_ai_metadata_review.py --overwrite-results

Environment variables (loaded from .env at project root, then shell env):
    OPENAI_API_KEY     – your OpenAI API key  (required)
    OPENAI_MODEL       – optional model override (default: gpt-4o-mini)
    AI_REVIEW_PROVIDER – optional provider override (default: openai)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Load .env from project root (before any os.getenv calls)
# Priority: CLI args > shell env > .env file > defaults
# ---------------------------------------------------------------------------
def _load_dotenv(root: Path) -> None:
    """
    Load KEY=VALUE pairs from <root>/.env into os.environ.
    Existing environment variables are NOT overwritten (shell env wins over .env).
    Uses python-dotenv if available; falls back to a simple built-in parser.
    """
    env_path = root / ".env"
    if not env_path.exists():
        return

    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=env_path, override=False)
        logging.getLogger(__name__).debug(".env loaded via python-dotenv: %s", env_path)
        return
    except ImportError:
        pass

    # Fallback: minimal KEY=VALUE parser (no dotenv dependency required)
    import re
    _re_line = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$')
    with open(env_path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            m = _re_line.match(line)
            if not m:
                continue
            key, value = m.group(1), m.group(2)
            # Strip surrounding quotes (single or double)
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            # Only set if not already present in the environment
            if key not in os.environ:
                os.environ[key] = value
    logging.getLogger(__name__).debug(".env loaded via fallback parser: %s", env_path)


_load_dotenv(ROOT)

PROMPT_PATH = ROOT / "prompts" / "food_metadata_ai_review_prompt.md"
CLEAN_DATA_PATH = ROOT / "data" / "processed" / "clean_food_metadata.json"
BATCHES_DIR = ROOT / "data" / "processed" / "ai_review_batches"
RESULTS_DIR = ROOT / "data" / "processed" / "ai_review_results"
ERROR_LOG_PATH = ROOT / "data" / "processed" / "ai_review_errors.jsonl"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_BATCH_SIZE = 10
TEMPERATURE = 0.1
TOP_P = 0.8
MAX_RETRIES = 4
RETRY_BASE_DELAY = 2.0   # seconds; doubles on each retry

# ---------------------------------------------------------------------------
# Allowed value sets for output validation
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

# Fields to include in AI review input (strips internal/irrelevant fields)
REVIEW_INPUT_FIELDS = [
    "food_id", "raw_name", "clean_name", "display_name",
    "clean_category", "sub_category", "grade",
    "health_level", "goal_tags", "taste_profile",
    "replacement_group", "recommendation_role",
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
# Prompt loading
# ---------------------------------------------------------------------------
def load_prompt(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Batch discovery and preparation (1-based, batch_0001 … batch_NNNN)
# ---------------------------------------------------------------------------
def discover_batch_files(batches_dir: Path) -> list[Path]:
    """Return sorted list of existing batch_*.json files."""
    return sorted(batches_dir.glob("batch_*.json"))


def build_review_input(record: dict) -> dict:
    """Strip internal fields; keep only what the AI needs to review."""
    return {k: record[k] for k in REVIEW_INPUT_FIELDS if k in record}


def prepare_batches_1based(
    records: list[dict],
    batch_size: int,
    batches_dir: Path,
) -> list[Path]:
    """
    Split records into 1-based numbered batch JSON files (batch_0001, batch_0002, …).
    Writes plain JSON arrays (compatible with load_batch_records).
    Skips files that already exist (resume-safe).
    Returns list of batch file paths.
    """
    batches_dir.mkdir(parents=True, exist_ok=True)
    batch_paths: list[Path] = []

    for i in range(0, len(records), batch_size):
        batch_num = i // batch_size + 1   # 1-based
        batch_path = batches_dir / f"batch_{batch_num:04d}.json"
        batch_paths.append(batch_path)

        if batch_path.exists():
            logger.debug("Batch file already exists, skipping: %s", batch_path.name)
            continue

        chunk = [build_review_input(r) for r in records[i: i + batch_size]]
        with open(batch_path, "w", encoding="utf-8") as f:
            json.dump(chunk, f, indent=2, ensure_ascii=False)

    logger.info("Auto-prepared %d batch files in %s", len(batch_paths), batches_dir)
    return batch_paths


def load_batch_records(path: Path) -> list[dict]:
    """
    Load records from a batch file.
    Handles both formats:
      - Plain array:                  [{...}, {...}, ...]
      - Wrapper (prepare_ai_review_batches.py): {"batch_id": ..., "records": [...]}
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        records = data.get("records")
        if isinstance(records, list):
            return records
        logger.warning("Batch file %s has unexpected dict shape (no 'records' key)", path.name)
        return []

    logger.warning("Batch file %s has unexpected type: %s", path.name, type(data).__name__)
    return []


def result_path_for_batch(batch_path: Path, results_dir: Path) -> Path:
    """Derive result file path from batch file name: batch_0001.json → result_0001.json."""
    return results_dir / batch_path.name.replace("batch_", "result_")


# ---------------------------------------------------------------------------
# Duplicate food_id detection across batches
# ---------------------------------------------------------------------------
def scan_for_duplicates(batch_paths: list[Path]) -> dict[str, list[str]]:
    """
    Scan all batch files and return a dict of food_id → [batch_file_names]
    for any food_id that appears in more than one batch.
    """
    seen: dict[str, str] = {}          # food_id → first batch filename
    duplicates: dict[str, list[str]] = {}  # food_id → [batch filenames]

    for path in batch_paths:
        try:
            records = load_batch_records(path)
        except Exception as exc:
            logger.warning("Could not scan %s for duplicates: %s", path.name, exc)
            continue
        for rec in records:
            fid = str(rec.get("food_id", ""))
            if not fid:
                continue
            if fid in seen:
                if fid not in duplicates:
                    duplicates[fid] = [seen[fid]]
                duplicates[fid].append(path.name)
            else:
                seen[fid] = path.name

    return duplicates


# ---------------------------------------------------------------------------
# API call with retry
# ---------------------------------------------------------------------------
def call_openai(
    client,
    model: str,
    system_prompt: str,
    user_message: str,
) -> str:
    """
    Call OpenAI chat completions with exponential backoff on failure.
    Returns the raw response content string.
    """
    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=TEMPERATURE,
                top_p=TOP_P,
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content

        except Exception as exc:
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning(
                    "API call failed (attempt %d/%d): %s — retrying in %.1fs",
                    attempt + 1, MAX_RETRIES, exc, delay,
                )
                time.sleep(delay)
            else:
                logger.error("API call failed after %d attempts: %s", MAX_RETRIES, exc)
                raise


# ---------------------------------------------------------------------------
# Response parsing and validation
# ---------------------------------------------------------------------------
def parse_response(raw: str, batch_id: str) -> list[dict] | None:
    """
    Parse the raw JSON string from the API.
    Expected shape: {"results": [...]}
    Returns the list, or None on failure.
    """
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Batch %s: JSON parse error — %s", batch_id, exc)
        return None

    if isinstance(obj, list):
        return obj   # model returned array directly

    if isinstance(obj, dict):
        for key in ("results", "data", "records", "items"):
            if key in obj and isinstance(obj[key], list):
                return obj[key]
        if "food_id" in obj:
            return [obj]   # single record

    logger.error(
        "Batch %s: unexpected response shape — keys: %s",
        batch_id,
        list(obj.keys()) if isinstance(obj, dict) else type(obj),
    )
    return None


def validate_record(rec: dict) -> tuple[bool, list[str]]:
    """
    Validate a single AI-reviewed record.
    Returns (is_valid, list_of_errors).
    """
    errors: list[str] = []

    if "keep" not in rec:
        errors.append("missing 'keep' field")
        return False, errors

    if not rec["keep"]:
        if "reject_reason" not in rec or not rec["reject_reason"]:
            errors.append("keep=false but no reject_reason")
        return len(errors) == 0, errors

    required = ["food_id", "clean_name", "clean_category", "health_level",
                "goal_tags", "recommendation_role"]
    for field in required:
        if field not in rec:
            errors.append(f"missing field: {field}")

    if errors:
        return False, errors

    for tag in rec.get("goal_tags") or []:
        if tag not in VALID_GOAL_TAGS:
            errors.append(f"invalid goal_tag: '{tag}'")

    if rec.get("health_level") not in VALID_HEALTH_LEVELS:
        errors.append(f"invalid health_level: '{rec.get('health_level')}'")

    if rec.get("clean_category") not in VALID_CATEGORIES:
        errors.append(f"invalid clean_category: '{rec.get('clean_category')}'")

    if rec.get("recommendation_role") not in VALID_RECOMMENDATION_ROLES:
        errors.append(f"invalid recommendation_role: '{rec.get('recommendation_role')}'")

    if rec.get("health_level") == "try_less" and rec.get("goal_tags"):
        errors.append("try_less food should have empty goal_tags")

    return len(errors) == 0, errors


def log_error(batch_id: str, record_id: str, errors: list[str], raw_record: dict) -> None:
    entry = {
        "batch_id": batch_id,
        "food_id": record_id,
        "errors": errors,
        "raw_record": raw_record,
    }
    with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Dry-run output
# ---------------------------------------------------------------------------
def dry_run_print(system_prompt: str, first_batch_path: Path) -> None:
    records = load_batch_records(first_batch_path)
    print("\n" + "=" * 70)
    print("DRY RUN — SYSTEM PROMPT (first 3000 chars)")
    print("=" * 70)
    print(system_prompt[:3000])
    if len(system_prompt) > 3000:
        print(f"\n... [{len(system_prompt) - 3000} more chars] ...")

    print("\n" + "=" * 70)
    print(f"DRY RUN — USER MESSAGE (batch {first_batch_path.name}, {len(records)} records)")
    print("=" * 70)
    user_msg = json.dumps(records, indent=2, ensure_ascii=False)
    print(user_msg[:2000])
    if len(user_msg) > 2000:
        print(f"\n... [{len(user_msg) - 2000} more chars] ...")

    print("\n" + "=" * 70)
    print("DRY RUN complete — no API calls made.")
    print("=" * 70)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
def run(args: argparse.Namespace) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # --- Load prompt ---
    logger.info("Loading prompt from: %s", PROMPT_PATH)
    system_prompt = load_prompt(PROMPT_PATH)
    logger.info("Prompt loaded (%d chars)", len(system_prompt))

    # --- Resolve batch files ---
    existing_batches = discover_batch_files(BATCHES_DIR)

    if existing_batches:
        logger.info(
            "Found %d existing batch file(s) in %s — using them directly.",
            len(existing_batches), BATCHES_DIR,
        )
        batch_paths = existing_batches
        if args.limit:
            logger.info(
                "--limit %d ignored when batch files already exist "
                "(re-run prepare_ai_review_batches.py with --limit to change selection).",
                args.limit,
            )
    else:
        # No batch files — load records and auto-prepare
        logger.info("No batch files found. Loading records from: %s", CLEAN_DATA_PATH)
        if not CLEAN_DATA_PATH.exists():
            logger.error("Clean data not found. Run clean_food_metadata.py first.")
            sys.exit(1)
        with open(CLEAN_DATA_PATH, encoding="utf-8") as f:
            records: list[dict] = json.load(f)
        logger.info("Loaded %d records", len(records))
        if args.limit:
            records = records[: args.limit]
            logger.info("--limit applied: using first %d records", len(records))
        batch_paths = prepare_batches_1based(records, args.batch_size, BATCHES_DIR)

    logger.info("Batch files to process (%d):", len(batch_paths))
    for p in batch_paths:
        logger.info("  %s", p.name)

    if not batch_paths:
        logger.error("No batch files to process.")
        sys.exit(1)

    # --- Duplicate food_id scan ---
    duplicates = scan_for_duplicates(batch_paths)
    if duplicates:
        logger.warning(
            "%d food_id(s) appear in multiple batch files (will be deduplicated by apply step):",
            len(duplicates),
        )
        for fid, files in list(duplicates.items())[:5]:
            logger.warning("  food_id=%s in: %s", fid, ", ".join(files))
        if len(duplicates) > 5:
            logger.warning("  ... and %d more", len(duplicates) - 5)
    else:
        logger.info("No duplicate food_ids across batch files.")

    # --- Dry run ---
    if args.dry_run:
        dry_run_print(system_prompt, batch_paths[0])
        return

    # --- Set up OpenAI client ---
    provider = (args.provider or os.getenv("AI_REVIEW_PROVIDER", "openai")).lower()
    if provider != "openai":
        logger.error("Only 'openai' provider is currently supported.")
        sys.exit(1)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error(
            "OPENAI_API_KEY is not set. Add it to .env at the project root "
            "or export it in your shell."
        )
        sys.exit(1)

    model = args.model or os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
    masked = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
    logger.info("Provider: %s | Model: %s | Temperature: %s | Key: %s",
                provider, model, TEMPERATURE, masked)

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
    except ImportError:
        logger.error("openai package not installed. Run: pip install openai")
        sys.exit(1)

    # --- Clear existing results if requested ---
    if args.overwrite_results:
        cleared = 0
        for f in RESULTS_DIR.glob("result_*.json"):
            f.unlink()
            cleared += 1
        if cleared:
            logger.info("--overwrite-results: removed %d existing result file(s)", cleared)

    # --- Process batches ---
    total_kept = 0
    total_rejected = 0
    total_errors = 0
    total_skipped = 0

    for batch_path in batch_paths:
        batch_id = batch_path.stem          # e.g. "batch_0001"
        result_path = result_path_for_batch(batch_path, RESULTS_DIR)

        # Skip already-processed batches (resume-safe)
        if result_path.exists():
            logger.info("Skipping %s (result exists: %s)", batch_id, result_path.name)
            total_skipped += 1
            continue

        records_in_batch = load_batch_records(batch_path)
        logger.info("Processing %s (%d records) -> %s …",
                    batch_id, len(records_in_batch), result_path.name)

        user_message = json.dumps(records_in_batch, ensure_ascii=False)

        # API call
        try:
            raw_response = call_openai(client, model, system_prompt, user_message)
        except Exception as exc:
            logger.error("%s: API call failed permanently: %s", batch_id, exc)
            log_error(batch_id, "BATCH_LEVEL", [str(exc)], {"batch_path": str(batch_path)})
            total_errors += 1
            continue

        # Parse response
        reviewed = parse_response(raw_response, batch_id)
        if reviewed is None:
            log_error(batch_id, "PARSE_ERROR", ["response could not be parsed"],
                      {"raw_response": raw_response[:500]})
            total_errors += 1
            continue

        # Validate each record
        validated: list[dict] = []
        for rec in reviewed:
            rec_id = rec.get("food_id", "unknown")
            ok, errors = validate_record(rec)
            if ok:
                validated.append(rec)
                if rec.get("keep"):
                    total_kept += 1
                else:
                    total_rejected += 1
            else:
                logger.warning("%s record %s: validation errors: %s", batch_id, rec_id, errors)
                log_error(batch_id, rec_id, errors, rec)
                total_errors += 1
                rec["_validation_errors"] = errors
                validated.append(rec)

        # Save result with full metadata wrapper (atomic write)
        wrapper = {
            "batch_id": batch_id,
            "model": model,
            "provider": provider,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "record_count": len(validated),
            "results": validated,
        }
        tmp_path = result_path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(wrapper, f, indent=2, ensure_ascii=False)
        tmp_path.rename(result_path)

        logger.info("  Saved %d reviewed records -> %s", len(validated), result_path.name)
        time.sleep(0.3)   # small courtesy delay between batches

    # --- Final summary ---
    print("\n" + "=" * 60)
    print("AI REVIEW COMPLETE")
    print("=" * 60)
    print(f"  Batches processed : {len(batch_paths) - total_skipped}")
    print(f"  Batches skipped   : {total_skipped}")
    print(f"  Records kept      : {total_kept}")
    print(f"  Records rejected  : {total_rejected}")
    print(f"  Parse/API errors  : {total_errors}")
    if duplicates:
        print(f"  Duplicate food_ids: {len(duplicates)} (across batch files)")
    if total_errors:
        print(f"  Error log         : {ERROR_LOG_PATH}")
    print(f"\n  Results saved to  : {RESULTS_DIR}")
    print("=" * 60)
    print("\nNext step: python scripts/apply_ai_review_results.py")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Send cleaned food metadata to OpenAI for few-shot AI review.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--limit", type=int, default=None, metavar="N",
        help="Auto-prepare only the first N records (ignored if batch files already exist)",
    )
    parser.add_argument(
        "--batch-size", type=int, default=DEFAULT_BATCH_SIZE, metavar="N",
        help=f"Records per API call when auto-preparing batches (default: {DEFAULT_BATCH_SIZE})",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print the prompt and first batch without calling the API",
    )
    parser.add_argument(
        "--overwrite-results", action="store_true",
        help="Delete existing result_*.json files before running",
    )
    parser.add_argument(
        "--provider", type=str, default=None,
        help="AI provider to use (default: openai)",
    )
    parser.add_argument(
        "--model", type=str, default=None,
        help=f"Model name (default: {DEFAULT_MODEL})",
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
