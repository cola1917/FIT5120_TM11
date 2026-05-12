"""
Start OpenAI Fine-Tuning Job
==============================
Uploads train/valid JSONL files to OpenAI and creates a fine-tuning job.

Usage:
    python scripts/start_openai_finetune.py
    python scripts/start_openai_finetune.py --model gpt-4o-mini
    python scripts/start_openai_finetune.py --dry-run

Environment:
    OPENAI_API_KEY  (required) — loaded from .env or shell environment

Input:
    data/finetune/food_recommender_train.jsonl
    data/finetune/food_recommender_valid.jsonl

Output:
    data/finetune/openai_finetune_job.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
TRAIN_FILE  = ROOT / "data" / "finetune" / "food_recommender_train.jsonl"
VALID_FILE  = ROOT / "data" / "finetune" / "food_recommender_valid.jsonl"
JOB_META    = ROOT / "data" / "finetune" / "openai_finetune_job.json"

DEFAULT_MODEL = "gpt-4o-mini-2024-07-18"

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
# .env loader
# ---------------------------------------------------------------------------
def _load_dotenv(root: Path) -> None:
    env_path = root / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=env_path, override=False)
        logger.debug(".env loaded via python-dotenv")
        return
    except ImportError:
        pass
    import re
    _re = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$')
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = _re.match(line)
            if not m:
                continue
            key, value = m.group(1), m.group(2)
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            if key not in os.environ:
                os.environ[key] = value
    logger.debug(".env loaded via fallback parser")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def count_lines(path: Path) -> int:
    count = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def upload_file(client, path: Path, purpose: str = "fine-tune") -> str:
    """Upload a file to OpenAI and return the file ID."""
    logger.info("Uploading %s (%d lines) …", path.name, count_lines(path))
    with open(path, "rb") as f:
        response = client.files.create(file=f, purpose=purpose)
    file_id = response.id
    logger.info("Uploaded %s -> file_id=%s (status=%s)", path.name, file_id, response.status)
    return file_id


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def run(args: argparse.Namespace) -> None:
    _load_dotenv(ROOT)

    # --- Validate input files ---
    for path in (TRAIN_FILE, VALID_FILE):
        if not path.exists():
            logger.error("Input file not found: %s", path)
            logger.error("Run scripts/generate_finetune_jsonl.py first.")
            sys.exit(1)

    train_lines = count_lines(TRAIN_FILE)
    valid_lines = count_lines(VALID_FILE)

    print("\n" + "=" * 60)
    print("OPENAI FINE-TUNING SETUP")
    print("=" * 60)
    print(f"  Train file  : {TRAIN_FILE.name}  ({train_lines} examples)")
    print(f"  Valid file  : {VALID_FILE.name}  ({valid_lines} examples)")
    print(f"  Model       : {args.model}")
    print(f"  Output meta : {JOB_META}")

    if args.dry_run:
        print("\n  DRY RUN — no files uploaded, no job created.")
        print("=" * 60)
        return

    # --- Load API key ---
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error(
            "OPENAI_API_KEY is not set. Add it to .env at the project root "
            "or export it in your shell."
        )
        sys.exit(1)
    masked = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
    logger.info("Using API key: %s", masked)

    # --- Import OpenAI SDK ---
    try:
        from openai import OpenAI
    except ImportError:
        logger.error("openai package not installed. Run: pip install openai")
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    # --- Upload files ---
    print()
    train_file_id = upload_file(client, TRAIN_FILE)
    valid_file_id = upload_file(client, VALID_FILE)

    # --- Create fine-tuning job ---
    logger.info(
        "Creating fine-tuning job: model=%s, train=%s, valid=%s",
        args.model, train_file_id, valid_file_id,
    )

    job = client.fine_tuning.jobs.create(
        training_file=train_file_id,
        validation_file=valid_file_id,
        model=args.model,
    )

    job_id     = job.id
    job_status = job.status
    created_at = datetime.fromtimestamp(job.created_at, tz=timezone.utc).isoformat()

    # --- Save metadata ---
    JOB_META.parent.mkdir(parents=True, exist_ok=True)
    meta = {
        "job_id":          job_id,
        "status":          job_status,
        "model":           args.model,
        "train_file_id":   train_file_id,
        "valid_file_id":   valid_file_id,
        "train_file_name": TRAIN_FILE.name,
        "valid_file_name": VALID_FILE.name,
        "train_examples":  train_lines,
        "valid_examples":  valid_lines,
        "created_at":      created_at,
        "fine_tuned_model": None,
    }
    with open(JOB_META, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    logger.info("Job metadata saved -> %s", JOB_META)

    # --- Print summary ---
    print()
    print("=" * 60)
    print("FINE-TUNING JOB CREATED")
    print("=" * 60)
    print(f"  Training file ID   : {train_file_id}")
    print(f"  Validation file ID : {valid_file_id}")
    print(f"  Fine-tuning job ID : {job_id}")
    print(f"  Job status         : {job_status}")
    print(f"  Model              : {args.model}")
    print(f"  Created at         : {created_at}")
    print(f"\n  Metadata saved to  : {JOB_META}")
    print("=" * 60)
    print("\nNext step: python scripts/check_openai_finetune_status.py")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upload JSONL files to OpenAI and create a fine-tuning job.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--model", default=DEFAULT_MODEL,
        help=f"Base model to fine-tune (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Validate inputs and print plan without uploading or creating a job",
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
