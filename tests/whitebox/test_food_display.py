from app.services import food_display


def test_simple_display_name_removes_package_noise_and_descriptor_words():
    assert food_display.simple_display_name("Jalapeno Cheese Sauce 6/5# 30#") == "Jalapeno Cheese Sauce"
    assert food_display.simple_display_name("Beef 80/20 raw") == "Beef"


def test_contextual_display_name_preserves_meaningful_modifier():
    assert food_display.contextual_display_name("Chicken, fried, cooked") == "Fried Chicken"
    assert food_display.contextual_display_name("Milk, whole, 3.25%") == "Whole Milk"


def test_display_name_for_section_uses_context_for_try_less_only():
    descriptor = "Cheese, pasteurized process, American"

    assert food_display.display_name_for_section(descriptor, "try_less") == "Processed Cheese"
    assert food_display.display_name_for_section(descriptor, "super_power") == "Cheese"


def test_normalize_display_name_deduplicates_noisy_variants():
    assert food_display.normalize_display_name("Beef, raw") == "beef"
    assert food_display.normalize_display_name("Beef 80/20 raw") == "beef"


def test_challenge_suitability_filters_unusual_or_generic_descriptors():
    assert food_display.is_challenge_suitable_by_rule("Apple, raw") is True
    assert food_display.is_challenge_suitable_by_rule("Frog legs, cooked") is False
    assert food_display.is_challenge_suitable_by_rule("Crustaceans, mixed species") is False


def test_generic_output_name_detects_category_labels():
    assert food_display.is_generic_output_name("Fish", "fish") is True
    assert food_display.is_generic_output_name("Salmon", "fish") is False
