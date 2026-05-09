"""
Check OpenAI Fine-Tuning Job Status
======================================
Retrieves and displays the current status of an OpenAI fine-tuning job.

Usage:
    python scripts/check_openai_finetune_status.py
    python scripts/check_openai_finetune_status.py --job-id ftjob-abc123
    python scripts/check_openai_finetune_status.py --events

Reads job ID from:
    data/finetune/openai_finetune_job.json   (unless --job-id is provided)

Saves latest status to:
    data/finetune/openai_finetune_status.json
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
ROOT        = Path(__file__).resolve().parent.parent
JOB_META    = ROOT / "data" / "finetune" / "openai_finetune_job.json"
STATUS_FILE = ROOT / "data" / "finetune" / "openai_finetune_status.json"

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _ts(unix_ts: int | None) -> str | None:
    if unix_ts is None:
        return None
    return datetime.fromtimestamp(unix_ts, tz=timezone.utc).isoformat()


def _safe(obj, attr: str, default=None):
    """Safely get an attribute that may not exist on older SDK versions."""
    return getattr(obj, attr, default)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def run(args: argparse.Namespace) -> None:
    _load_dotenv(ROOT)

    # --- Resolve job ID ---
    job_id: str | None = args.job_id

    if not job_id:
        if not JOB_META.exists():
            logger.error(
                "No job metadata found at %s. "
                "Run scripts/start_openai_finetune.py first, "
                "or pass --job-id <id>.",
                JOB_META,
            )
            sys.exit(1)
        with open(JOB_META, encoding="utf-8") as f:
            meta = json.load(f)
        job_id = meta.get("job_id")
        if not job_id:
            logger.error("job_id missing in %s", JOB_META)
            sys.exit(1)
        logger.info("Read job_id=%s from %s", job_id, JOB_META.name)

    # --- Load API key ---
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error(
            "OPENAI_API_KEY is not set. Add it to .env at the project root "
            "or export it in your shell."
        )
        sys.exit(1)

    # --- Import OpenAI SDK ---
    try:
        from openai import OpenAI
    except ImportError:
        logger.error("openai package not installed. Run: pip install openai")
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    # --- Retrieve job ---
    logger.info("Retrieving fine-tuning job: %s", job_id)
    try:
        job = client.fine_tuning.jobs.retrieve(job_id)
    except Exception as exc:
        logger.error("Failed to retrieve job %s: %s", job_id, exc)
        sys.exit(1)

    # --- Extract fields ---
    status           = _safe(job, "status")
    model            = _safe(job, "model")
    fine_tuned_model = _safe(job, "fine_tuned_model")
    created_at       = _ts(_safe(job, "created_at"))
    finished_at      = _ts(_safe(job, "finished_at"))
    estimated_finish = _ts(_safe(job, "estimated_finish"))

    # trained_tokens lives inside train_result or directly on the job depending on SDK version
    trained_tokens: int | None = None
    train_result = _safe(job, "train_result") or _safe(job, "training_result")
    if train_result:
        trained_tokens = _safe(train_result, "trained_tokens")
    if trained_tokens is None:
        trained_tokens = _safe(job, "trained_tokens")

    # --- Retrieve recent events (optional) ---
    recent_events: list[dict] = []
    if args.events:
        try:
            events_page = client.fine_tuning.jobs.list_events(fine_tuning_job_id=job_id, limit=20)
            for ev in reversed(list(events_page.data)):
                recent_events.append({
                    "created_at": _ts(_safe(ev, "created_at")),
                    "level":      _safe(ev, "level"),
                    "message":    _safe(ev, "message"),
                })
        except Exception as exc:
            logger.warning("Could not retrieve events: %s", exc)

    # --- Build status dict ---
    status_data = {
        "job_id":           job_id,
        "status":           status,
        "model":            model,
        "fine_tuned_model": fine_tuned_model,
        "trained_tokens":   trained_tokens,
        "created_at":       created_at,
        "finished_at":      finished_at,
        "estimated_finish": estimated_finish,
        "checked_at":       datetime.now(tz=timezone.utc).isoformat(),
    }

    # --- Save status file ---
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(status_data, f, indent=2, ensure_ascii=False)
    logger.info("Status saved -> %s", STATUS_FILE)

    # Also update fine_tuned_model in job meta if it has been set
    if fine_tuned_model and JOB_META.exists():
        try:
            with open(JOB_META, encoding="utf-8") as f:
                meta = json.load(f)
            if meta.get("fine_tuned_model") != fine_tuned_model:
                meta["fine_tuned_model"] = fine_tuned_model
                with open(JOB_META, "w", encoding="utf-8") as f:
                    json.dump(meta, f, indent=2, ensure_ascii=False)
                logger.info("Updated fine_tuned_model in %s", JOB_META.name)
        except Exception as exc:
            logger.warning("Could not update %s: %s", JOB_META.name, exc)

    # --- Print report ---
    print("\n" + "=" * 60)
    print("FINE-TUNING JOB STATUS")
    print("=" * 60)
    print(f"  Job ID              : {job_id}")
    print(f"  Status              : {status}")
    print(f"  Model               : {model}")
    print(f"  Fine-tuned model    : {fine_tuned_model or '(not yet available)'}")
    print(f"  Trained tokens      : {trained_tokens if trained_tokens is not None else '(not yet available)'}")
    print(f"  Created at          : {created_at or 'N/A'}")
    print(f"  Estimated finish    : {estimated_finish or '(not yet available)'}")
    print(f"  Finished at         : {finished_at or '(not yet finished)'}")
    print(f"  Checked at          : {status_data['checked_at']}")
    print(f"\n  Status saved to     : {STATUS_FILE}")

    if recent_events:
        print(f"\n  Recent events (latest {len(recent_events)}):")
        for ev in recent_events:
            level = (ev.get("level") or "info").upper()
            msg   = ev.get("message", "")
            ts    = ev.get("created_at", "")
            print(f"    [{ts}] {level:<8} {msg}")

    if status == "succeeded":
        print(f"\n  Job completed successfully.")
        print(f"  Fine-tuned model: {fine_tuned_model}")
    elif status == "failed":
        print(f"\n  [ERROR] Job failed.")
        error = _safe(job, "error")
        if error:
            print(f"  Error code   : {_safe(error, 'code')}")
            print(f"  Error message: {_safe(error, 'message')}")
    elif status in ("running", "queued", "validating_files"):
        print(f"\n  Job is in progress. Re-run this script to check again.")

    print("=" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check the status of an OpenAI fine-tuning job.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--job-id", default=None, metavar="ID",
        help="Fine-tuning job ID (default: read from openai_finetune_job.json)",
    )
    parser.add_argument(
        "--events", action="store_true",
        help="Also retrieve and print recent job events",
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
