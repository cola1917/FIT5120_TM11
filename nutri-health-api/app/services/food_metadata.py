"""
Metadata image lookup for food recommendation items.

Loads data/processed/clean_food_metadata.json once at module import and
provides fast dictionary-based lookup without re-reading the file per request.

Public API:
    find_existing_image(food_name, food_id=None) -> str | None

Lookup priority:
    1. food_id exact match (string) — most reliable, used when cn_code is known
    2. Normalized clean_name exact match
    3. Normalized display_name exact match
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

_METADATA_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "data" / "processed" / "clean_food_metadata.json"
)

# ─── Indices (populated at module load) ───────────────────────────────────────

_by_food_id:     dict[str, dict] = {}   # str(food_id) → entry
_by_clean_name:  dict[str, dict] = {}   # normalized clean_name → entry
_by_display_name: dict[str, dict] = {}  # normalized display_name → entry


def _normalize(s: str) -> str:
    """Lowercase, strip, collapse internal whitespace."""
    s = s.lower().strip()
    return re.sub(r"\s+", " ", s)


def _load_metadata() -> None:
    """Load and index clean_food_metadata.json. Called once at import time.

    Fail-soft: any problem (missing file, invalid JSON, unexpected structure,
    or unanticipated error during indexing) is logged as a warning and leaves
    the indices empty. find_existing_image() then returns None for every lookup,
    and callers transparently fall back to generated images.
    """
    if not _METADATA_PATH.exists():
        logger.warning(
            "clean_food_metadata.json not found at %s — metadata image lookup disabled",
            _METADATA_PATH,
        )
        return

    try:
        with open(_METADATA_PATH, encoding="utf-8") as f:
            entries = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning(
            "clean_food_metadata.json could not be read (%s) — metadata image lookup disabled",
            exc,
        )
        return

    if not isinstance(entries, list):
        logger.warning(
            "clean_food_metadata.json has unexpected top-level type %s (expected list)"
            " — metadata image lookup disabled",
            type(entries).__name__,
        )
        return

    try:
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if entry.get("removed"):
                continue
            url = entry.get("image_url", "")
            if not url:
                continue

            # Index by food_id (string key for cn_code lookup)
            fid = str(entry.get("food_id", "")).strip()
            if fid:
                _by_food_id.setdefault(fid, entry)

            # Index by clean_name (normalized)
            clean = _normalize(entry.get("clean_name", ""))
            if clean:
                _by_clean_name.setdefault(clean, entry)

            # Index by display_name (normalized) only when different from clean_name
            display = _normalize(entry.get("display_name", ""))
            if display and display != clean:
                _by_display_name.setdefault(display, entry)

    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Unexpected error while indexing food metadata (%s) — clearing partial index,"
            " metadata image lookup disabled",
            exc,
        )
        _by_food_id.clear()
        _by_clean_name.clear()
        _by_display_name.clear()
        return

    logger.info(
        "Food metadata indexed: %d food_id keys, %d clean_name keys, %d display_name keys",
        len(_by_food_id),
        len(_by_clean_name),
        len(_by_display_name),
    )


try:
    _load_metadata()
except Exception as exc:  # noqa: BLE001 — last-resort guard so import never fails
    logger.warning(
        "food_metadata._load_metadata raised unexpectedly (%s) — metadata image lookup disabled",
        exc,
    )


# ─── Public API ───────────────────────────────────────────────────────────────


def find_existing_image(food_name: str, food_id: str | None = None) -> str | None:
    """
    Return an existing image_url from clean_food_metadata.json, or None.

    Lookup priority:
      1. food_id exact match — when the caller knows the database primary key
      2. Normalized clean_name exact match
      3. Normalized display_name exact match

    The returned URL is the raw value from the JSON (e.g. /static/food_photos/11510.jpg).
    Returns None when no match is found or the matched entry has no image_url.
    """
    # 1. food_id lookup
    if food_id is not None:
        entry = _by_food_id.get(str(food_id).strip())
        if entry:
            url = entry.get("image_url", "")
            if url:
                return url

    # 2 & 3. Name-based lookup
    norm = _normalize(food_name)
    entry = _by_clean_name.get(norm) or _by_display_name.get(norm)
    if entry:
        url = entry.get("image_url", "")
        if url:
            return url

    return None


def metadata_entry_count() -> int:
    """Return the number of indexed food_id entries (useful for tests/health checks)."""
    return len(_by_food_id)
