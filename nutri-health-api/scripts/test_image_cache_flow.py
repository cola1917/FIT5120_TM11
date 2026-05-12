"""
Image cache flow test.

Validates the image caching pipeline without making a full API request.

Usage:
    /usr/bin/python3 scripts/test_image_cache_flow.py
    /usr/bin/python3 scripts/test_image_cache_flow.py --run-generation
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RUN_GENERATION = "--run-generation" in sys.argv

SAMPLE_FOODS = [
    ("mango",  "fruits"),
    ("yogurt", "dairy"),
    ("carrot", "vegetables"),
]

SEP   = "=" * 60
PASS  = "PASS"
FAIL  = "FAIL"

# ── helpers ───────────────────────────────────────────────────────────────────

_failures: list[str] = []

def check(label: str, condition: bool, detail: str = "") -> None:
    status = PASS if condition else FAIL
    suffix = f"  ({detail})" if detail else ""
    print(f"  [{status}] {label}{suffix}")
    if not condition:
        _failures.append(label)

# ── import cache module ───────────────────────────────────────────────────────

from app.services.food_image_cache import (
    _CACHE_FILE,
    _GEN_DIR,
    generate_and_cache_food_image,
    get_cached_image,
    get_category_fallback_image,
    get_image_status,
    mark_failed,
    mark_pending,
    mark_ready,
    normalize_food_key,
    should_queue_generation,
)
from app.services.enrichment import enrich_recommendation_items

# ── Test 1: normalize_food_key ────────────────────────────────────────────────

print(f"\n{SEP}")
print("Test 1: normalize_food_key")
check("'mango' -> 'mango'",           normalize_food_key("mango")        == "mango")
check("'Sweet Potato' -> 'sweet_potato'", normalize_food_key("Sweet Potato") == "sweet_potato")
check("'Ice Cream!' -> 'ice_cream'",  normalize_food_key("Ice Cream!")   == "ice_cream")
check("'  oats  ' -> 'oats'",         normalize_food_key("  oats  ")     == "oats")

# ── Test 2: category fallback image ──────────────────────────────────────────

print(f"\n{SEP}")
print("Test 2: get_category_fallback_image")
for food_name, category in SAMPLE_FOODS:
    url = get_category_fallback_image(category)
    check(
        f"{category} fallback URL non-empty",
        bool(url) and url.startswith("/static/category_fallback/"),
        url,
    )

unknown_url = get_category_fallback_image("nonexistent_category_xyz")
check(
    "Unknown category falls back to mixed_dishes",
    "mixed_dishes" in unknown_url,
    unknown_url,
)

# ── Test 3: enrichment uses fallback for uncached foods ───────────────────────

print(f"\n{SEP}")
print("Test 3: enrichment returns fallback for uncached foods")

# Ensure test foods are NOT in the cache (skip if already cached)
for food_name, category in SAMPLE_FOODS:
    if get_image_status(food_name) != "ready":
        items = [{"food": food_name, "reason": f"Test reason for {food_name}"}]
        enriched = enrich_recommendation_items(items)
        check(
            f"{food_name}: image_url uses category fallback",
            "/static/category_fallback/" in enriched[0].image_url,
            enriched[0].image_url,
        )
        check(
            f"{food_name}: image_status is 'fallback'",
            enriched[0].image_status == "fallback",
            enriched[0].image_status,
        )
    else:
        print(f"  [SKIP] {food_name} already cached as ready — fallback test skipped")

# ── Test 4: should_queue_generation for missing foods ────────────────────────

print(f"\n{SEP}")
print("Test 4: should_queue_generation")

for food_name, _ in SAMPLE_FOODS:
    status = get_image_status(food_name)
    if status in ("missing", "failed"):
        check(
            f"{food_name} (status={status}): should_queue == True",
            should_queue_generation(food_name) is True,
        )
    elif status == "pending":
        check(
            f"{food_name} (status=pending): should_queue == False",
            should_queue_generation(food_name) is False,
        )
    elif status == "ready":
        check(
            f"{food_name} (status=ready): should_queue == False",
            should_queue_generation(food_name) is False,
        )

# ── Test 5: mark_pending / mark_failed / mark_ready round-trip ───────────────

print(f"\n{SEP}")
print("Test 5: cache state transitions")

_test_food = "__test_cache_food__"
_test_cat  = "fruits"

mark_pending(_test_food, _test_cat)
check("mark_pending: status becomes 'pending'",
      get_image_status(_test_food) == "pending")
check("mark_pending: should_queue returns False",
      should_queue_generation(_test_food) is False)
check("mark_pending: get_cached_image returns None",
      get_cached_image(_test_food) is None)

mark_failed(_test_food, _test_cat, "test error")
check("mark_failed: status becomes 'failed'",
      get_image_status(_test_food) == "failed")

# Fake a ready entry with a real file so get_cached_image works
_fake_img_path = _GEN_DIR / f"{normalize_food_key(_test_food)}.png"
_fake_img_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
mark_ready(_test_food, _test_cat, f"/static/generated_foods/{normalize_food_key(_test_food)}.png")
check("mark_ready: status becomes 'ready'",
      get_image_status(_test_food) == "ready")
check("mark_ready: should_queue returns False",
      should_queue_generation(_test_food) is False)
check("mark_ready: get_cached_image returns entry",
      get_cached_image(_test_food) is not None)

# Cleanup test entry
_fake_img_path.unlink(missing_ok=True)

# ── Test 6: enrichment uses ready cached image ────────────────────────────────

print(f"\n{SEP}")
print("Test 6: enrichment uses cached image when ready")

_test_food2    = "__test_cache_food2__"
_test_food2_key = normalize_food_key(_test_food2)
_fake_img2 = _GEN_DIR / f"{_test_food2_key}.png"
_fake_img2.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
mark_ready(_test_food2, "fruits", f"/static/generated_foods/{_test_food2_key}.png")

items = [{"food": _test_food2, "reason": "Cached food test"}]
enriched2 = enrich_recommendation_items(items)
check(
    "Cached food: image_url uses generated path",
    "/static/generated_foods/" in enriched2[0].image_url,
    enriched2[0].image_url,
)
check(
    "Cached food: image_status is 'ready'",
    enriched2[0].image_status == "ready",
    enriched2[0].image_status,
)
_fake_img2.unlink(missing_ok=True)

# ── Test 7 (optional): real image generation ──────────────────────────────────

if RUN_GENERATION:
    print(f"\n{SEP}")
    print("Test 7: generate_and_cache_food_image (live, may take ~15s)")
    _gen_food = "mango"
    _gen_cat  = "fruits"
    _gen_key  = normalize_food_key(_gen_food)
    # Clear any existing entry so we start fresh
    from app.services.food_image_cache import load_cache, save_cache
    cache = load_cache()
    cache.pop(_gen_key, None)
    save_cache(cache)
    (_GEN_DIR / f"{_gen_key}.png").unlink(missing_ok=True)

    print(f"  Generating image for '{_gen_food}'...")
    generate_and_cache_food_image(_gen_food, _gen_cat)

    final_status = get_image_status(_gen_food)
    check(
        f"After generation: status is 'ready'",
        final_status == "ready",
        final_status,
    )
    check(
        "After generation: image file exists on disk",
        (_GEN_DIR / f"{_gen_key}.png").exists(),
    )
    entry = get_cached_image(_gen_food)
    check(
        "After generation: get_cached_image returns entry",
        entry is not None,
    )
    if entry:
        check(
            "After generation: image_url points to generated_foods",
            "/static/generated_foods/" in entry["image_url"],
            entry["image_url"],
        )

# ── Summary ───────────────────────────────────────────────────────────────────

print(f"\n{SEP}")
if _failures:
    print(f"RESULT: FAIL — {len(_failures)} check(s) failed:")
    for f in _failures:
        print(f"  • {f}")
else:
    print("RESULT: PASS — all checks passed")
print(SEP)
