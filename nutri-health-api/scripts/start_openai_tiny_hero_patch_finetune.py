#!/usr/bin/env python3
"""
Upload the tiny_hero patch dataset and start a second-round fine-tuning job.

Usage:
    python scripts/start_openai_tiny_hero_patch_finetune.py
    python scripts/start_openai_tiny_hero_patch_finetune.py --dry-run

Outputs:
    data/finetune_patch/openai_tiny_hero_patch_job.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# ─── .env loader (fallback for system Python without python-dotenv) ───────────
def _load_env_file(env_path: Path) -> None:
    try:
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val
    except OSError:
        pass

_env_path = Path(__file__).resolve().parent.parent / ".env"
try:
    from dotenv import load_dotenv
    load_dotenv(_env_path if _env_path.exists() else None)
except ImportError:
    if _env_path.exists():
        _load_env_file(_env_path)

try:
    from openai import OpenAI
except ImportError:
    print("Error: openai package not installed.  Run: pip install openai>=1.40.0")
    sys.exit(1)

# ─── Paths ────────────────────────────────────────────────────────────────────

ROOT           = Path(__file__).resolve().parent.parent
TRAIN_FILE     = ROOT / "data" / "finetune_patch" / "tiny_hero_patch_train.jsonl"
VALID_FILE     = ROOT / "data" / "finetune_patch" / "tiny_hero_patch_valid.jsonl"
JOB_META_PATH  = ROOT / "data" / "finetune_patch" / "openai_tiny_hero_patch_job.json"

BASE_MODEL     = "ft:gpt-4o-mini-2024-07-18:personal::DbryXUZ2"


# ─── Helpers ─────────────────────────────────────────────────────────────────

def upload_file(client: OpenAI, path: Path, label: str, dry_run: bool) -> str:
    if dry_run:
        fake_id = f"file-dry-run-{label}"
        print(f"  [dry-run] Would upload {path.name}  ->  {fake_id}")
        return fake_id
    print(f"  Uploading {path.name} ...", end=" ", flush=True)
    with open(path, "rb") as f:
        response = client.files.create(file=f, purpose="fine-tune")
    print(f"done  ({response.id})")
    return response.id


def create_job(
    client: OpenAI,
    train_id: str,
    valid_id: str,
    dry_run: bool,
) -> dict:
    if dry_run:
        fake_job = {
            "id":     "ftjob-dry-run-000",
            "status": "dry_run",
            "model":  BASE_MODEL,
        }
        print(f"  [dry-run] Would create fine-tuning job  ->  {fake_job['id']}")
        return fake_job

    print("  Creating fine-tuning job ...", end=" ", flush=True)
    job = client.fine_tuning.jobs.create(
        training_file=train_id,
        validation_file=valid_id,
        model=BASE_MODEL,
    )
    print(f"done  ({job.id})")
    return {
        "id":                 job.id,
        "status":             job.status,
        "model":              job.model,
        "fine_tuned_model":   job.fine_tuned_model,
        "created_at":         job.created_at,
        "estimated_finish":   getattr(job, "estimated_finish", None),
        "trained_tokens":     getattr(job, "trained_tokens", None),
        "organization_id":    getattr(job, "organization_id", None),
    }


def save_metadata(
    train_id: str,
    valid_id: str,
    job: dict,
    dry_run: bool,
) -> None:
    meta = {
        "base_model":          BASE_MODEL,
        "training_file_id":    train_id,
        "validation_file_id":  valid_id,
        "training_file_path":  str(TRAIN_FILE),
        "validation_file_path": str(VALID_FILE),
        "job_id":              job["id"],
        "job_status":          job["status"],
        "dry_run":             dry_run,
        "started_at":          datetime.now(timezone.utc).isoformat(),
    }
    JOB_META_PATH.parent.mkdir(parents=True, exist_ok=True)
    JOB_META_PATH.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  Metadata saved  ->  {JOB_META_PATH}")


# ─── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upload tiny_hero patch dataset and start a fine-tuning job.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would happen without making any API calls.",
    )
    args = parser.parse_args()

    # ── Validate inputs ───────────────────────────────────────────────────────
    for path in (TRAIN_FILE, VALID_FILE):
        if not path.exists():
            print(f"Error: required file not found: {path}")
            sys.exit(1)

    train_lines = sum(1 for _ in TRAIN_FILE.open(encoding="utf-8"))
    valid_lines = sum(1 for _ in VALID_FILE.open(encoding="utf-8"))

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key and not args.dry_run:
        print("Error: OPENAI_API_KEY is not set in environment or .env file.")
        sys.exit(1)

    client = OpenAI(api_key=api_key or "dry-run-key")

    # ── Summary ───────────────────────────────────────────────────────────────
    print("=" * 60)
    print("Tiny Hero Patch Fine-Tuning Job")
    print("=" * 60)
    print(f"  Base model      : {BASE_MODEL}")
    print(f"  Training file   : {TRAIN_FILE.name}  ({train_lines} examples)")
    print(f"  Validation file : {VALID_FILE.name}  ({valid_lines} examples)")
    print(f"  Dry run         : {args.dry_run}")
    print("-" * 60)

    # ── Upload files ──────────────────────────────────────────────────────────
    print("Uploading files:")
    train_id = upload_file(client, TRAIN_FILE, "train", args.dry_run)
    valid_id  = upload_file(client, VALID_FILE, "valid", args.dry_run)

    print(f"\n  Training file ID   : {train_id}")
    print(f"  Validation file ID : {valid_id}")

    # ── Create job ────────────────────────────────────────────────────────────
    print("\nCreating fine-tuning job:")
    job = create_job(client, train_id, valid_id, args.dry_run)

    print(f"\n  Job ID     : {job['id']}")
    print(f"  Status     : {job['status']}")
    print(f"  Model      : {job.get('model', BASE_MODEL)}")

    # ── Save metadata ─────────────────────────────────────────────────────────
    save_metadata(train_id, valid_id, job, args.dry_run)

    print("\nDone.")
    if not args.dry_run:
        print(f"\nTo monitor progress, run:")
        print(f"  python scripts/check_tiny_hero_patch_finetune_status.py")


if __name__ == "__main__":
    main()
