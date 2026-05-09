"""
File-based image cache for AI-generated food images.

Cache is stored at:
  data/image_cache/food_image_cache.json   — metadata
  static/generated_foods/{food_key}.png    — downloaded image files

Pollinations.ai is used for image generation (no API key required).
All cache writes are protected by a threading lock so that concurrent
background tasks do not corrupt the JSON file.

Public API used by other modules:
  get_cached_image(food_name)          -> cache entry dict | None
  get_image_status(food_name)          -> "ready" | "pending" | "failed" | "missing"
  get_category_fallback_image(category)-> "/static/category_fallback/{category}.png"
  should_queue_generation(food_name)   -> bool
  mark_pending(food_name, category)
  mark_ready(food_name, category, image_url)
  mark_failed(food_name, category, error)
  generate_and_cache_food_image(food_name, category)  — run in background task
"""

from __future__ import annotations

import json
import logging
import re
import threading
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# ─── Paths ────────────────────────────────────────────────────────────────────

_BASE = Path(__file__).resolve().parent.parent.parent   # project root
_CACHE_FILE   = _BASE / "data" / "image_cache" / "food_image_cache.json"
_GEN_DIR      = _BASE / "static" / "generated_foods"
_FALLBACK_DIR = _BASE / "static" / "category_fallback"

_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
_GEN_DIR.mkdir(parents=True, exist_ok=True)

# ─── Lock ─────────────────────────────────────────────────────────────────────

_lock = threading.Lock()

# ─── Constants ────────────────────────────────────────────────────────────────

_RETRY_AFTER_HOURS = 24
_DOWNLOAD_TIMEOUT  = 15   # seconds
_IMAGE_WIDTH       = 400
_IMAGE_HEIGHT      = 400

VALID_STATUSES = {"ready", "pending", "failed", "fallback", "missing"}

# ─── Key normalisation ────────────────────────────────────────────────────────


def normalize_food_key(food_name: str) -> str:
    """
    Produce a filesystem-safe cache key from a food name.
    e.g. "Sweet Potato" -> "sweet_potato"
    """
    key = food_name.lower().strip()
    key = re.sub(r"[^\w\s-]", "", key)          # remove punctuation
    key = re.sub(r"[\s\-]+", "_", key)           # spaces/hyphens -> underscore
    key = re.sub(r"_+", "_", key).strip("_")     # collapse duplicates
    return key


# ─── Cache I/O ────────────────────────────────────────────────────────────────


def load_cache() -> dict:
    """Load cache from disk. Returns empty dict if file missing or corrupt."""
    if not _CACHE_FILE.exists():
        return {}
    try:
        with open(_CACHE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        logger.warning("Image cache file corrupt or unreadable; starting fresh.")
        return {}


def save_cache(cache: dict) -> None:
    """Persist cache to disk (caller must hold _lock)."""
    try:
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except OSError as exc:
        logger.error("Failed to save image cache: %s", exc)


# ─── Read helpers ─────────────────────────────────────────────────────────────


def get_cached_image(food_name: str) -> dict | None:
    """
    Return the cache entry if status == "ready" and the image file exists.
    Otherwise return None.
    """
    key = normalize_food_key(food_name)
    cache = load_cache()
    entry = cache.get(key)
    if not entry:
        return None
    if entry.get("image_status") != "ready":
        return None
    # Verify the file is actually on disk
    image_path = _GEN_DIR / f"{key}.png"
    if not image_path.exists():
        return None
    return entry


def get_image_status(food_name: str) -> str:
    """Return "ready" | "pending" | "failed" | "missing"."""
    key = normalize_food_key(food_name)
    cache = load_cache()
    entry = cache.get(key)
    if not entry:
        return "missing"
    status = entry.get("image_status", "missing")
    # If marked ready but file gone, treat as missing
    if status == "ready" and not (_GEN_DIR / f"{key}.png").exists():
        return "missing"
    return status


def get_category_fallback_image(category: str) -> str:
    """
    Return the static fallback image path for a category.
    Falls back to mixed_dishes if the specific category file is absent.
    """
    path = _FALLBACK_DIR / f"{category}.png"
    if path.exists():
        return f"/static/category_fallback/{category}.png"
    return "/static/category_fallback/mixed_dishes.png"


def should_queue_generation(food_name: str) -> bool:
    """
    Return True if a background generation task should be queued.

    Rules:
      - missing  → True
      - pending  → False  (already in-flight)
      - ready    → False  (already done)
      - failed   → True only if last attempt was > 24 h ago
    """
    key = normalize_food_key(food_name)
    cache = load_cache()
    entry = cache.get(key)

    if not entry:
        return True

    status = entry.get("image_status", "missing")

    if status == "ready":
        if (_GEN_DIR / f"{key}.png").exists():
            return False
        # File gone — re-queue
        return True

    if status == "pending":
        return False

    if status == "failed":
        updated_at_str = entry.get("updated_at")
        if not updated_at_str:
            return True
        try:
            updated_at = datetime.fromisoformat(updated_at_str)
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=timezone.utc)
            age = datetime.now(tz=timezone.utc) - updated_at
            return age > timedelta(hours=_RETRY_AFTER_HOURS)
        except ValueError:
            return True

    # missing or unknown
    return True


# ─── Write helpers ────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def mark_pending(food_name: str, category: str) -> None:
    key = normalize_food_key(food_name)
    with _lock:
        cache = load_cache()
        entry = cache.get(key, {})
        now = _now_iso()
        cache[key] = {
            **entry,
            "food_name":    food_name,
            "category":     category,
            "image_url":    get_category_fallback_image(category),
            "image_status": "pending",
            "created_at":   entry.get("created_at", now),
            "updated_at":   now,
            "error":        None,
        }
        save_cache(cache)


def mark_ready(food_name: str, category: str, image_url: str) -> None:
    key = normalize_food_key(food_name)
    with _lock:
        cache = load_cache()
        entry = cache.get(key, {})
        now = _now_iso()
        cache[key] = {
            **entry,
            "food_name":    food_name,
            "category":     category,
            "image_url":    image_url,
            "image_status": "ready",
            "created_at":   entry.get("created_at", now),
            "updated_at":   now,
            "error":        None,
        }
        save_cache(cache)


def mark_failed(food_name: str, category: str, error: str) -> None:
    key = normalize_food_key(food_name)
    with _lock:
        cache = load_cache()
        entry = cache.get(key, {})
        now = _now_iso()
        cache[key] = {
            **entry,
            "food_name":    food_name,
            "category":     category,
            "image_url":    entry.get("image_url", get_category_fallback_image(category)),
            "image_status": "failed",
            "created_at":   entry.get("created_at", now),
            "updated_at":   now,
            "error":        error,
        }
        save_cache(cache)


# ─── Image generation ─────────────────────────────────────────────────────────


def _build_pollinations_url(food_name: str) -> str:
    prompt = (
        f"{food_name}, food photo, white background, "
        "realistic, child-friendly healthy eating app"
    )
    encoded = urllib.parse.quote(prompt)
    return (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width={_IMAGE_WIDTH}&height={_IMAGE_HEIGHT}&nologo=true"
    )


def generate_and_cache_food_image(food_name: str, category: str) -> None:
    """
    Download a Pollinations image for food_name and save it to
    static/generated_foods/{food_key}.png.

    Intended to be called as a FastAPI BackgroundTask — never awaited directly.
    On success calls mark_ready; on any error calls mark_failed.
    """
    key = normalize_food_key(food_name)
    dest_path = _GEN_DIR / f"{key}.png"
    url = _build_pollinations_url(food_name)

    logger.info("Generating image for '%s' from %s", food_name, url)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "NutriHealthBot/1.0"})
        with urllib.request.urlopen(req, timeout=_DOWNLOAD_TIMEOUT) as resp:
            content_type = resp.headers.get("Content-Type", "")
            if "image" not in content_type:
                raise ValueError(f"Unexpected Content-Type: {content_type}")
            image_bytes = resp.read()

        if len(image_bytes) < 1024:
            raise ValueError(f"Image too small ({len(image_bytes)} bytes) — likely an error page")

        dest_path.write_bytes(image_bytes)
        image_url = f"/static/generated_foods/{key}.png"
        mark_ready(food_name, category, image_url)
        logger.info("Cached generated image for '%s' -> %s", food_name, image_url)

    except Exception as exc:
        error_msg = str(exc)
        logger.warning("Image generation failed for '%s': %s", food_name, error_msg)
        mark_failed(food_name, category, error_msg)
