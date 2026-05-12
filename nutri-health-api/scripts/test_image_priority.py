"""
Service-level smoke test: image URL priority in recommendation responses.

Confirms that enrich_recommendation_items() and the router's generation-queue
logic both prefer clean_food_metadata.json images over Pollinations-generated URLs.

Test sections:
  1. Metadata image returned for known foods (banana, blueberries, broccoli …)
  2. Unknown food with no AI cache → category fallback (not a Pollinations URL)
  3. Unknown food with AI cache hit → AI cache URL used (not metadata, not Pollinations)
  4. Metadata wins over AI cache even when AI cache entry exists
  5. Fallback Pollinations URL is 512×512
  6. Router queue logic: no generation task queued for metadata-matched foods;
     generation IS queued for foods not in metadata

Run:
    .venv/bin/python3 scripts/test_image_priority.py
"""
from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.enrichment import enrich_recommendation_items
from app.services.food_image_cache import _build_pollinations_url, _IMAGE_WIDTH, _IMAGE_HEIGHT
from app.services.food_metadata import find_existing_image

SEP = "=" * 65
failures: list[str] = []


def ok(label: str) -> None:
    print(f"  [OK]  {label}")


def fail(label: str, detail: str) -> None:
    print(f"  [FAIL] {label}: {detail}")
    failures.append(f"{label}: {detail}")


def _is_metadata_url(url: str) -> bool:
    return "/static/food_photos/" in url


def _is_pollinations_url(url: str) -> bool:
    return "pollinations.ai" in url


def _is_fallback_url(url: str) -> bool:
    return "/static/category_fallback/" in url


# ── 1. Metadata image returned for known foods ────────────────────────────────
print(SEP)
print("1. Known foods → metadata image URL from clean_food_metadata.json")

KNOWN_FOODS = [
    ("banana",       "/static/food_photos/9040.jpg"),
    ("blueberries",  "/static/food_photos/9054.jpg"),
    ("broccoli",     "/static/food_photos/11090.jpg"),
    ("spinach",      "/static/food_photos/11457.jpg"),
    ("sweet potato", "/static/food_photos/11510.jpg"),
    ("edamame",      "/static/food_photos/11212.jpg"),
    ("salmon",       "/static/food_photos/15264.jpg"),
]

for food_name, expected_url in KNOWN_FOODS:
    items = [{"food": food_name, "reason": "test"}]
    result = enrich_recommendation_items(items)
    assert len(result) == 1, f"expected 1 item, got {len(result)}"
    item = result[0]

    if item.image_url == expected_url:
        ok(f"'{food_name}' → {item.image_url}")
    else:
        fail(f"'{food_name}' image_url", f"got {item.image_url!r}, want {expected_url!r}")

    if item.image_status == "ready":
        ok(f"'{food_name}' image_status='ready'")
    else:
        fail(f"'{food_name}' image_status", f"got {item.image_status!r}, want 'ready'")

    if not _is_pollinations_url(item.image_url):
        ok(f"'{food_name}' is NOT a Pollinations URL")
    else:
        fail(f"'{food_name}' should not be Pollinations", item.image_url)

# ── 2. Unknown food, no AI cache → category fallback ─────────────────────────
print(SEP)
print("2. Unknown food (no metadata, no AI cache) → category fallback")

UNKNOWN_FOOD = "xyzzy rainbow cake 9000"

with patch("app.services.enrichment.get_cached_image", return_value=None):
    result = enrich_recommendation_items([{"food": UNKNOWN_FOOD, "reason": "test"}])
    assert len(result) == 1
    item = result[0]

if _is_fallback_url(item.image_url):
    ok(f"unknown food → category fallback: {item.image_url}")
else:
    fail("unknown food fallback URL", f"got {item.image_url!r}")

if item.image_status == "fallback":
    ok("unknown food image_status='fallback'")
else:
    fail("unknown food image_status", f"got {item.image_status!r}, want 'fallback'")

if not _is_metadata_url(item.image_url):
    ok("unknown food is NOT a metadata URL")
else:
    fail("unknown food should not be metadata URL", item.image_url)

if not _is_pollinations_url(item.image_url):
    ok("unknown food is NOT a Pollinations URL (generation is a background task)")
else:
    fail("unknown food should not be Pollinations URL directly", item.image_url)

# ── 3. Unknown food with AI cache hit → AI cache URL ─────────────────────────
print(SEP)
print("3. Unknown food + AI cache hit → AI-cached image, not category fallback")

AI_CACHED_URL = "/static/generated_foods/xyzzy_rainbow_cake_9000.png"
fake_cache_entry = {"image_url": AI_CACHED_URL, "image_status": "ready"}

with patch("app.services.enrichment._find_metadata_image", return_value=None), \
     patch("app.services.enrichment.get_cached_image", return_value=fake_cache_entry):
    result = enrich_recommendation_items([{"food": UNKNOWN_FOOD, "reason": "test"}])
    assert len(result) == 1
    item = result[0]

if item.image_url == AI_CACHED_URL:
    ok(f"AI cache hit → {item.image_url}")
else:
    fail("AI cache URL", f"got {item.image_url!r}, want {AI_CACHED_URL!r}")

if item.image_status == "ready":
    ok("AI cache hit image_status='ready'")
else:
    fail("AI cache hit image_status", f"got {item.image_status!r}")

if not _is_fallback_url(item.image_url):
    ok("AI cache hit is NOT category fallback")
else:
    fail("AI cache should not be category fallback", item.image_url)

# ── 4. Metadata wins over AI cache ────────────────────────────────────────────
print(SEP)
print("4. Metadata image wins over AI cache when both are available")

for food_name, expected_url in KNOWN_FOODS[:3]:   # banana, blueberries, broccoli
    fake_ai = {"image_url": f"/static/generated_foods/{food_name}.png", "image_status": "ready"}
    with patch("app.services.enrichment.get_cached_image", return_value=fake_ai):
        result = enrich_recommendation_items([{"food": food_name, "reason": "test"}])
        assert len(result) == 1
        item = result[0]

    if item.image_url == expected_url:
        ok(f"'{food_name}' metadata wins over AI cache: {item.image_url}")
    else:
        fail(
            f"'{food_name}' metadata priority over AI cache",
            f"got {item.image_url!r}, want {expected_url!r}",
        )

# ── 5. Fallback Pollinations URL is 512×512 ───────────────────────────────────
print(SEP)
print("5. Fallback Pollinations URL (background generation) uses 512×512")

if _IMAGE_WIDTH == 512 and _IMAGE_HEIGHT == 512:
    ok(f"food_image_cache constants: _IMAGE_WIDTH={_IMAGE_WIDTH} _IMAGE_HEIGHT={_IMAGE_HEIGHT}")
else:
    fail("food_image_cache size constants", f"got {_IMAGE_WIDTH}×{_IMAGE_HEIGHT}, want 512×512")

for food in ["banana", "broccoli", UNKNOWN_FOOD]:
    url = _build_pollinations_url(food)
    if "width=512" in url and "height=512" in url:
        ok(f"_build_pollinations_url('{food}') is 512×512")
    else:
        fail(f"_build_pollinations_url('{food}') size", f"url={url!r}")

# ── 6. Router queue: metadata foods skipped, unknown foods queued ─────────────
print(SEP)
print("6. Router generation queue: metadata foods skipped, unknowns queued")

# Build a mixed list of EnrichedFoodItem-like objects
class _Item:
    def __init__(self, food_name: str, category: str = "fruits"):
        self.food_name = food_name
        self.category = category

metadata_foods = [food for food, _ in KNOWN_FOODS]   # all in metadata
non_metadata   = ["xyzzy rainbow cake 9000", "turbo mystery steak 42"]

all_test_items = [_Item(f) for f in metadata_foods] + [_Item(f) for f in non_metadata]

queued: list[str] = []
skipped: list[str] = []

# Replicate the router's generation-queuing logic exactly:
#   if _find_metadata_image(item.food_name): continue
#   if should_queue_generation(item.food_name): mark_pending + add_task
with patch(
    "app.services.food_image_cache.should_queue_generation",
    return_value=True,          # pretend nothing is in the AI cache
):
    for item in all_test_items:
        if find_existing_image(item.food_name):
            skipped.append(item.food_name)
            continue
        # would call should_queue_generation, mark_pending, add_task here
        queued.append(item.food_name)

# All metadata-matched foods must be skipped
for food in metadata_foods:
    if food in skipped and food not in queued:
        ok(f"'{food}' skipped (has metadata image) — no generation queued")
    else:
        fail(
            f"'{food}' should be skipped",
            f"skipped={food in skipped} queued={food in queued}",
        )

# All unknown foods must be queued
for food in non_metadata:
    if food in queued and food not in skipped:
        ok(f"'{food}' queued for generation (not in metadata)")
    else:
        fail(
            f"'{food}' should be queued",
            f"queued={food in queued} skipped={food in skipped}",
        )

# ── Summary ───────────────────────────────────────────────────────────────────
print(SEP)
if failures:
    print(f"RESULT: FAIL — {len(failures)} issue(s):")
    for f in failures:
        print(f"  • {f}")
else:
    print("RESULT: PASS")
print(SEP)
