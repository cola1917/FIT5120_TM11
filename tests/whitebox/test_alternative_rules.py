from app.services.alternative_rules import (
    clean_food_name_for_image,
    contains_unhealthy_keyword,
    infer_food_category,
    is_compatible_category,
    normalize_food_name,
)


def test_normalize_food_name_strips_symbols_and_whitespace():
    assert normalize_food_name("  🍕  Bubble   Tea!! ") == "bubble tea"


def test_clean_food_name_for_image_keeps_readable_name():
    assert clean_food_name_for_image("  🍩 Sweet Bun!!  ") == "Sweet Bun"


def test_infer_food_category_matches_keywords():
    assert infer_food_category("Chicken Burger") == "fast_food"
    assert infer_food_category("Fresh Apple Juice") == "drink"
    assert infer_food_category("Plain Water") == "drink"
    assert infer_food_category("Unknown Item") == "general"


def test_is_compatible_category_uses_source_rules():
    assert is_compatible_category("drink", "dairy") is True
    assert is_compatible_category("dessert", "meal") is False
    assert is_compatible_category("unknown", "fruit") is True


def test_contains_unhealthy_keyword_detects_risky_items():
    assert contains_unhealthy_keyword("Chocolate bar") is True
    assert contains_unhealthy_keyword("Apple slices") is False