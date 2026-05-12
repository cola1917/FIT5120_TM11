#!/usr/bin/env python3
"""
Check the status of the tiny_hero patch fine-tuning job.

Usage:
    python scripts/check_tiny_hero_patch_finetune_status.py
    python scripts/check_tiny_hero_patch_finetune_status.py --job-id ftjob-abc123
    python scripts/check_tiny_hero_patch_finetune_status.py --events
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

ROOT            = Path(__file__).resolve().parent.parent
JOB_META_PATH   = ROOT / "data" / "finetune_patch" / "openai_tiny_hero_patch_job.json"
STATUS_OUT_PATH = ROOT / "data" / "finetune_patch" / "openai_tiny_hero_patch_status.json"


# ─── Helpers ─────────────────────────────────────────────────────────────────

def load_job_id(cli_job_id: str | None) -> str:
    if cli_job_id:
        return cli_job_id
    if not JOB_META_PATH.exists():
        print(f"Error: job metadata not found at {JOB_META_PATH}")
        print("       Run start_openai_tiny_hero_patch_finetune.py first, or pass --job-id.")
        sys.exit(1)
    meta = json.loads(JOB_META_PATH.read_text(encoding="utf-8"))
    job_id = meta.get("job_id")
    if not job_id or job_id.startswith("ftjob-dry-run"):
        print(f"Error: stored job_id '{job_id}' is from a dry-run.  Pass --job-id with the real ID.")
        sys.exit(1)
    return job_id


def fmt_ts(ts) -> str:
    """Format a Unix timestamp or ISO string for display."""
    if ts is None:
        return "—"
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    except (TypeError, ValueError):
        return str(ts)


def print_job(job) -> None:
    print("=" * 60)
    print("Tiny Hero Patch Fine-Tuning Job Status")
    print("=" * 60)
    print(f"  Job ID              : {job.id}")
    print(f"  Status              : {job.status}")
    print(f"  Base model          : {job.model}")
    print(f"  Fine-tuned model    : {job.fine_tuned_model or '—  (not ready yet)'}")
    print(f"  Trained tokens      : {getattr(job, 'trained_tokens', None) or '—'}")
    print(f"  Created at          : {fmt_ts(job.created_at)}")
    est = getattr(job, "estimated_finish", None)
    print(f"  Estimated finish    : {fmt_ts(est)}")
    err = getattr(job, "error", None)
    if err:
        print(f"  Error               : {err}")
    print("-" * 60)


def print_events(client: OpenAI, job_id: str) -> None:
    print("\nRecent events:")
    events = client.fine_tuning.jobs.list_events(fine_tuning_job_id=job_id, limit=10)
    if not events.data:
        print("  (no events yet)")
        return
    for ev in reversed(events.data):
        ts = fmt_ts(getattr(ev, "created_at", None))
        msg = getattr(ev, "message", str(ev))
        print(f"  [{ts}]  {msg}")


def _serialize_error(err) -> dict | None:
    """Convert an OpenAI Error object to a plain dict, or None if empty."""
    if err is None:
        return None
    code    = getattr(err, "code",    None)
    message = getattr(err, "message", None)
    param   = getattr(err, "param",   None)
    if code is None and message is None and param is None:
        return None
    return {"code": code, "message": message, "param": param}


def save_status(job) -> None:
    status = {
        "job_id":            job.id,
        "status":            job.status,
        "model":             job.model,
        "fine_tuned_model":  job.fine_tuned_model,
        "trained_tokens":    getattr(job, "trained_tokens", None),
        "created_at":        getattr(job, "created_at", None),
        "estimated_finish":  getattr(job, "estimated_finish", None),
        "error":             _serialize_error(getattr(job, "error", None)),
        "checked_at":        datetime.now(timezone.utc).isoformat(),
    }
    STATUS_OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_OUT_PATH.write_text(json.dumps(status, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  Status saved  ->  {STATUS_OUT_PATH}")


# ─── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check status of the tiny_hero patch fine-tuning job.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--job-id",
        default=None,
        help="Fine-tuning job ID. If omitted, read from openai_tiny_hero_patch_job.json.",
    )
    parser.add_argument(
        "--events",
        action="store_true",
        help="Show recent fine-tuning events from OpenAI.",
    )
    args = parser.parse_args()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY is not set in environment or .env file.")
        sys.exit(1)

    client = OpenAI(api_key=api_key)
    job_id = load_job_id(args.job_id)

    print(f"Fetching status for job: {job_id} ...\n")
    job = client.fine_tuning.jobs.retrieve(job_id)

    print_job(job)

    if args.events:
        print_events(client, job_id)

    save_status(job)

    # Friendly next-step hint
    if job.status in ("succeeded", "failed", "cancelled"):
        print(f"\nFinal status: {job.status.upper()}")
        if job.fine_tuned_model:
            print(f"Fine-tuned model ID: {job.fine_tuned_model}")
            print("Update DEFAULT_MODEL in evaluate_finetuned_model.py and test_finetuned_model_smoke.py.")
    elif job.status in ("running", "queued", "validating_files"):
        print("\nJob is still in progress.  Run this script again to refresh.")


if __name__ == "__main__":
    main()
