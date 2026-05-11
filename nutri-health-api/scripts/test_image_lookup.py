"""
Deterministic unit tests for the food metadata image lookup feature.

Covers:
  1. Existing image match by food_id
  2. Existing image match by clean_name (exact normalized)
  3. Existing image match by display_name (exact normalized)
  4. Case-insensitive / whitespace normalization variants
  5. Fallback to None when no match
  6. Fallback Pollinations URL uses 512×512 (food_image_cache constant)
  7. Fallback Pollinations URL in recommendation_service uses 512×512
  8. enrichment: metadata image takes priority over AI cache
  9. enrichment: AI cache used when no metadata match
  10. enrichment: category fallback used when neither metadata nor AI cache
  11. No regression — EnrichedFoodItem structure unchanged
  12. metadata_entry_count() returns positive value

Run:
    .venv/bin/python3 scripts/test_image_lookup.py
"""
from __future__ import annotations

import os
import sys
import re
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SEP = "=" * 65
failures: list[str] = []


def ok(label: str) -> None:
    print(f"  [OK]  {label}")


def fail(label: str, detail: str) -> None:
    print(f"  [FAIL] {label}: {detail}")
    failures.append(f"{label}: {detail}")


# ── 1. food_metadata module ────────────────────────────────────────────────────
print(SEP)
print("1. food_metadata — find_existing_image()")

from app.services.food_metadata import (
    find_existing_image,
    metadata_entry_count,
    _by_food_id,
    _by_clean_name,
    _by_display_name,
)

# 1a. Entry count is positive (metadata loaded)
count = metadata_entry_count()
if count > 0:
    ok(f"metadata loaded: {count} food_id entries")
else:
    fail("metadata loaded", f"metadata_entry_count()={count}, expected > 0")

# 1b. Lookup by food_id for known entries (banana=9040, broccoli=11090, salmon=15264)
for food_id, expected_fragment in [
    ("9040",  "food_photos/9040"),
    ("11090", "food_photos/11090"),
    ("15264", "food_photos/15264"),
]:
    url = find_existing_image("anything", food_id=food_id)
    if url and expected_fragment in url:
        ok(f"food_id={food_id} → {url}")
    else:
        fail(f"food_id={food_id} lookup", f"got {url!r}, expected fragment '{expected_fragment}'")

# 1c. Lookup by clean_name (lowercase)
for name, expected_fragment in [
    ("banana",       "food_photos/9040"),
    ("broccoli",     "food_photos/11090"),
    ("spinach",      "food_photos/11457"),
    ("sweet potato", "food_photos/11510"),
    ("edamame",      "food_photos/11212"),
    ("blueberries",  "food_photos/9054"),
    ("salmon",       "food_photos/15264"),
]:
    url = find_existing_image(name)
    if url and expected_fragment in url:
        ok(f"clean_name='{name}' → {url}")
    else:
        fail(f"clean_name='{name}' lookup", f"got {url!r}, expected '{expected_fragment}'")

# 1c-extra. food_id takes priority over name — ID matches independently of name
# This protects the DB cn_code → metadata food_id path used by _to_food_item.
for food_id, wrong_name, expected_url in [
    ("9040",  "completely different rewritten name", "/static/food_photos/9040.jpg"),
    ("11090", "totally unrelated string xyz",        "/static/food_photos/11090.jpg"),
    ("15264", "not salmon at all",                   "/static/food_photos/15264.jpg"),
]:
    url = find_existing_image(wrong_name, food_id=food_id)
    if url == expected_url:
        ok(f"food_id={food_id!r} + wrong name {wrong_name!r} → {url}")
    else:
        fail(
            f"food_id priority: id={food_id!r} name={wrong_name!r}",
            f"got {url!r}, want {expected_url!r}",
        )

# 1d. Case-insensitive / whitespace normalization
for variant, base_name in [
    ("Banana",        "banana"),
    ("BROCCOLI",      "broccoli"),
    (" spinach ",     "spinach"),
    ("Sweet  Potato", "sweet potato"),  # collapsed double space
    ("Sweet Potato",  "sweet potato"),
]:
    url_variant = find_existing_image(variant)
    url_base    = find_existing_image(base_name)
    if url_variant and url_variant == url_base:
        ok(f"normalized variant '{variant}' matches '{base_name}'")
    else:
        fail(
            f"normalization '{variant}'",
            f"variant={url_variant!r} base={url_base!r}",
        )

# 1e. No match for unknown food → None
for unknown in ["unicorn steak", "xyzzy food", "turbo carrot 9000"]:
    result = find_existing_image(unknown)
    if result is None:
        ok(f"no match for '{unknown}' → None")
    else:
        fail(f"no match for '{unknown}'", f"unexpectedly got {result!r}")

# 1f. food_id that doesn't exist → falls back to name, or None
url = find_existing_image("unicorn steak", food_id="99999999")
if url is None:
    ok("non-existent food_id + unknown name → None")
else:
    fail("non-existent food_id + unknown name", f"got {url!r}")

# ── 2. Fallback Pollinations URL size ──────────────────────────────────────────
print(SEP)
print("2. Fallback URL size — 512×512")

# 2a. food_image_cache._build_pollinations_url
from app.services.food_image_cache import _build_pollinations_url, _IMAGE_WIDTH, _IMAGE_HEIGHT

if _IMAGE_WIDTH == 512 and _IMAGE_HEIGHT == 512:
    ok(f"food_image_cache constants: width={_IMAGE_WIDTH} height={_IMAGE_HEIGHT}")
else:
    fail("food_image_cache constants", f"width={_IMAGE_WIDTH} height={_IMAGE_HEIGHT}, expected 512×512")

url = _build_pollinations_url("test food")
if "width=512" in url and "height=512" in url:
    ok(f"_build_pollinations_url contains 512×512: {url}")
else:
    fail("_build_pollinations_url size", f"url={url}")

# 2b. recommendation_service._make_image_url_from_name — check source directly
#     (recommendation_service imports sqlalchemy which may not be in all venvs)
_rec_service_src = Path(__file__).resolve().parent.parent / "app" / "services" / "recommendation_service.py"
_src_text = _rec_service_src.read_text(encoding="utf-8")
if "width=512" in _src_text and "height=512" in _src_text:
    ok("recommendation_service._make_image_url_from_name source contains 512×512")
else:
    fail("recommendation_service._make_image_url_from_name size", "512×512 not found in source")

# ── 3. enrichment — image priority logic ──────────────────────────────────────
print(SEP)
print("3. enrichment — image selection priority")

from app.services.enrichment import enrich_recommendation_items

# 3a. Metadata image takes priority for known food
# salmon has a metadata image at /static/food_photos/15264.jpg
items = [{"food": "salmon", "reason": "rich in omega-3"}]
result = enrich_recommendation_items(items)
assert len(result) == 1, "expected 1 item"
item = result[0]
if "food_photos" in item.image_url:
    ok(f"'salmon' uses metadata image: {item.image_url}")
else:
    fail("metadata priority for 'salmon'", f"image_url={item.image_url!r}")

if item.image_status == "ready":
    ok("'salmon' image_status='ready'")
else:
    fail("salmon image_status", f"got {item.image_status!r}, expected 'ready'")

# 3b. Unknown food with no AI cache → category fallback
with patch("app.services.enrichment.get_cached_image", return_value=None), \
     patch("app.services.enrichment._find_metadata_image", return_value=None):
    items = [{"food": "unicorn steak", "reason": "magical protein"}]
    result = enrich_recommendation_items(items)
    assert len(result) == 1
    item = result[0]
    if item.image_status == "fallback":
        ok(f"unknown food → 'fallback' status, url={item.image_url}")
    else:
        fail("unknown food fallback status", f"got {item.image_status!r}")

# 3c. No metadata match but AI cache present → AI cache wins over fallback
fake_cached = {"image_url": "/static/generated_foods/test_food.png", "image_status": "ready"}
with patch("app.services.enrichment._find_metadata_image", return_value=None), \
     patch("app.services.enrichment.get_cached_image", return_value=fake_cached):
    items = [{"food": "test food", "reason": "test"}]
    result = enrich_recommendation_items(items)
    assert len(result) == 1
    item = result[0]
    if "/static/generated_foods/" in item.image_url and item.image_status == "ready":
        ok(f"AI cache used when no metadata match: {item.image_url}")
    else:
        fail("AI cache priority", f"image_url={item.image_url!r} status={item.image_status!r}")

# 3d. Metadata image takes priority over AI cache
fake_cached = {"image_url": "/static/generated_foods/banana.png", "image_status": "ready"}
with patch("app.services.enrichment.get_cached_image", return_value=fake_cached):
    items = [{"food": "banana", "reason": "good energy"}]
    result = enrich_recommendation_items(items)
    assert len(result) == 1
    item = result[0]
    if "food_photos" in item.image_url:
        ok(f"metadata wins over AI cache for 'banana': {item.image_url}")
    else:
        fail("metadata over AI cache", f"got {item.image_url!r}")

# ── 4. EnrichedFoodItem schema unchanged ──────────────────────────────────────
print(SEP)
print("4. No regression — EnrichedFoodItem structure")

items = [
    {"food": "broccoli",  "reason": "vitamins"},
    {"food": "blueberries", "reason": "antioxidants"},
]
result = enrich_recommendation_items(items)
assert len(result) == 2, f"expected 2 items, got {len(result)}"

for item in result:
    for field in ["food_id", "food_name", "category", "image_url", "image_status", "reason"]:
        if not hasattr(item, field):
            fail(f"EnrichedFoodItem missing field '{field}'", "")
        else:
            ok(f"  field '{field}' present: {getattr(item, field)!r}")
    # Computed aliases
    for alias in ["cn_code", "name", "grade"]:
        if not hasattr(item, alias):
            fail(f"EnrichedFoodItem missing alias '{alias}'", "")
        else:
            ok(f"  alias '{alias}' present: {getattr(item, alias)!r}")

# ── Summary ───────────────────────────────────────────────────────────────────
print(SEP)
if failures:
    print(f"RESULT: FAIL — {len(failures)} issue(s):")
    for f in failures:
        print(f"  • {f}")
else:
    print("RESULT: PASS")
print(SEP)
