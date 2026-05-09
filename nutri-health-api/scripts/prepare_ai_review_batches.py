"""
Prepare AI Review Batches
=========================
Reads cleaned food metadata and splits it into batch JSON files
ready to be sent to the AI review step.

Does NOT call the OpenAI API.

Usage:
    python scripts/prepare_ai_review_batches.py
    python scripts/prepare_ai_review_batches.py --limit 50 --batch-size 5
    python scripts/prepare_ai_review_batches.py --overwrite
    python scripts/prepare_ai_review_batches.py --input path/to/file.json --output-dir path/to/dir

Output format (each batch_NNNN.json):
    {
      "batch_id": "batch_0001",
      "record_count": 5,
      "records": [ ... ]
    }
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "data" / "processed" / "clean_food_metadata.json"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "processed" / "ai_review_batches"
DEFAULT_BATCH_SIZE = 5

# ---------------------------------------------------------------------------
# Fields included in each record sent for AI review
# ---------------------------------------------------------------------------
REVIEW_FIELDS = [
    "food_id",
    "source_id",
    "raw_name",
    "clean_name",
    "display_name",
    "clean_category",
    "sub_category",
    "original_category",
    "grade",
    "health_level",
    "goal_tags",
    "taste_profile",
    "replacement_group",
    "recommendation_role",
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
# Helpers
# ---------------------------------------------------------------------------
def build_review_record(record: dict) -> dict:
    """Keep only the fields needed for AI review."""
    return {k: record[k] for k in REVIEW_FIELDS if k in record}


def clear_existing_batches(output_dir: Path) -> int:
    """Delete all batch_*.json files in output_dir. Returns count deleted."""
    deleted = 0
    for f in output_dir.glob("batch_*.json"):
        f.unlink()
        deleted += 1
    return deleted


def existing_batch_count(output_dir: Path) -> int:
    return len(list(output_dir.glob("batch_*.json")))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def run(args: argparse.Namespace) -> None:
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)

    # --- Load input ---
    if not input_path.exists():
        logger.error("Input file not found: %s", input_path)
        sys.exit(1)

    with open(input_path, encoding="utf-8") as f:
        records: list[dict] = json.load(f)

    total_input = len(records)

    # --- Apply offset then limit ---
    offset = args.offset or 0
    if offset:
        records = records[offset:]
    if args.limit is not None:
        records = records[: args.limit]

    selected = len(records)

    # --- Prepare output dir ---
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- Overwrite / collision check ---
    existing = existing_batch_count(output_dir)
    if existing > 0:
        if args.overwrite:
            deleted = clear_existing_batches(output_dir)
            logger.info("--overwrite: removed %d existing batch file(s)", deleted)
        else:
            print(
                f"\n[ERROR] {existing} batch file(s) already exist in:\n"
                f"  {output_dir}\n\n"
                f"Re-run with --overwrite to replace them, or choose a different "
                f"--output-dir.",
                file=sys.stderr,
            )
            sys.exit(1)

    # --- Split and write batches ---
    batch_size = args.batch_size
    total_batches = (selected + batch_size - 1) // batch_size  # ceil division

    for i in range(0, selected, batch_size):
        batch_num = i // batch_size + 1          # 1-based
        batch_id = f"batch_{batch_num:04d}"
        batch_path = output_dir / f"{batch_id}.json"

        chunk = [build_review_record(r) for r in records[i: i + batch_size]]

        payload = {
            "batch_id": batch_id,
            "record_count": len(chunk),
            "records": chunk,
        }

        with open(batch_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    # --- Summary ---
    print("\n" + "=" * 60)
    print("BATCH PREPARATION COMPLETE")
    print("=" * 60)
    print(f"  Input file       : {input_path}")
    print(f"  Output dir       : {output_dir}")
    print(f"  Total input      : {total_input}")
    print(f"  Offset           : {offset}")
    print(f"  Limit            : {args.limit if args.limit is not None else '(none)'}")
    print(f"  Selected records : {selected}")
    print(f"  Batch size       : {batch_size}")
    print(f"  Batches created  : {total_batches}")
    print(f"\n  Files: {output_dir}/batch_0001.json … batch_{total_batches:04d}.json")
    print("=" * 60)
    print("\nNext step:")
    print("  python scripts/run_ai_metadata_review.py")
    print("=" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Split cleaned food metadata into AI review batch files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input", type=str, default=str(DEFAULT_INPUT), metavar="PATH",
        help=f"Path to cleaned metadata JSON (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output-dir", type=str, default=str(DEFAULT_OUTPUT_DIR), metavar="DIR",
        help=f"Directory to write batch files (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--offset", type=int, default=0, metavar="N",
        help="Skip the first N records before applying --limit (default: 0)",
    )
    parser.add_argument(
        "--limit", type=int, default=None, metavar="N",
        help="Process only the first N records after applying --offset",
    )
    parser.add_argument(
        "--batch-size", type=int, default=DEFAULT_BATCH_SIZE, metavar="N",
        help=f"Records per batch file (default: {DEFAULT_BATCH_SIZE})",
    )
    parser.add_argument(
        "--overwrite", action="store_true",
        help="Delete existing batch_*.json files before writing new ones",
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
