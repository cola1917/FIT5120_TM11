"""
White-box unit tests for:
  - _pick_diverse
  - build_excluded_cn_codes
  - _query_tiny_hero
  - _normalize_name
  - _compute_common_score
  - _sort_pool
  - global name deduplication across sections (via get_recommendations)

Run from nutri-health-api/:
    pytest tests/unit/test_recommendation_service.py -v
"""

import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("RECOMMENDATION_AI_ENRICH_ENABLED", "false")

from app.services.recommendation_service import (
    _compute_common_score,
    _dedupe_pool_by_name,
    _apply_batch_display_rewrite,
    _make_image_url,
    _normalize_name,
    _pick_diverse,
    _to_food_item,
    _query_tiny_hero,
    _sort_pool,
    _query_pool,
    build_excluded_cn_codes,
    clean_display_name,
    get_recommendations,
)
from app.services.food_display import (
    batch_rewrite_display_names,
    contextual_display_name,
    is_challenge_suitable_by_rule,
)
from app.schemas.recommendations import FoodItem, RecommendationRequest, RecommendationResponse

# ── Patch targets ─────────────────────────────────────────────────────────────

PATCH_POOL = "app.services.recommendation_service._query_pool"
PATCH_TO_ITEM = "app.services.recommendation_service._to_food_item"


# ── Test object factories ─────────────────────────────────────────────────────

def _food(cn_code: int, cat_code: int, grade: str = "A", descriptor: str = "") -> MagicMock:
    """Create a mock CnFdes object."""
    f = MagicMock()
    f.cn_code = cn_code
    f.food_category_code = cat_code
    f.health_grade = grade
    f.descriptor = descriptor or f"Food {cn_code}"
    f.hcl_compliant = True
    return f


def _row(cn_code: int) -> MagicMock:
    """Create a mock row with only a cn_code attribute (used for DB scalar queries)."""
    r = MagicMock()
    r.cn_code = cn_code
    return r


# ── clean_display_name / _normalize_name ──────────────────────────────────────

class TestCleanDisplayName:
    def test_removes_package_hash_sizes(self):
        assert clean_display_name("Jalapeno Cheese Sauce 6/5# 30#") == "Jalapeno Cheese Sauce"

    def test_keeps_first_comma_segment(self):
        assert clean_display_name("Chicken, roasted, cooked") == "Chicken"

    def test_removes_comma_nutrition_text(self):
        assert clean_display_name("Milk, whole, 3.25%") == "Milk"

    def test_removes_ratio_and_raw_descriptor(self):
        assert clean_display_name("Beef 80/20 raw") == "Beef"

    def test_removes_weight_units_and_collapses_spaces(self):
        assert clean_display_name("apple   slices 12 oz #") == "Apple Slices"

    def test_to_food_item_uses_clean_display_name(self):
        food = _food(1, 1, descriptor="Milk, whole, 3.25%")
        assert _to_food_item(food).name == "Milk"

    def test_try_less_uses_contextual_display_name(self):
        food = _food(1, 1, descriptor="Milk, whole, 3.25%")
        assert _to_food_item(food, "try_less").name == "Whole Milk"

    def test_image_url_uses_clean_display_name(self):
        url = _make_image_url("Jalapeno Cheese Sauce 6/5# 30#")
        assert "Jalapeno%20Cheese%20Sauce%20food%20photography" in url
        assert "6/5" not in url
        assert "30" not in url

    def test_try_less_image_url_uses_contextual_display_name(self):
        url = _make_image_url("Milk, whole, 3.25%", "try_less")
        assert "Whole%20Milk%20food%20photography" in url

    def test_contextual_name_preserves_fried_modifier(self):
        assert contextual_display_name("Chicken, fried, cooked") == "Fried Chicken"

    def test_contextual_name_preserves_processed_modifier(self):
        assert contextual_display_name("Cheese, pasteurized process, American") == "Processed Cheese"

    def test_challenge_unsuitable_rule_blocks_unusual_foods(self):
        assert is_challenge_suitable_by_rule("Frog legs, raw") is False
        assert is_challenge_suitable_by_rule("Crustaceans, mixed species") is False

class TestNormalizeName:
    def test_basic_lowercase(self):
        assert _normalize_name("Beef") == "beef"

    def test_strips_after_comma(self):
        assert _normalize_name("Beef, raw") == "beef"

    def test_strips_whitespace(self):
        assert _normalize_name("  Beef  ") == "beef"

    def test_removes_punctuation(self):
        assert _normalize_name("Beef.") == "beef"

    def test_collapses_spaces(self):
        assert _normalize_name("Beef  Steak") == "beef steak"

    def test_same_name_different_case_matches(self):
        assert _normalize_name("BEEF") == _normalize_name("beef")

    def test_same_name_with_comma_suffix_matches(self):
        assert _normalize_name("Chicken") == _normalize_name("Chicken, roasted")

    def test_multi_word_name(self):
        assert _normalize_name("Fried chicken wings, battered") == "fried chicken wings"

    def test_noisy_package_text_dedups_to_clean_name(self):
        assert _normalize_name("Jalapeno Cheese Sauce 6/5# 30#") == "jalapeno cheese sauce"


# ── _pick_diverse ─────────────────────────────────────────────────────────────

class TestDedupePoolByName:
    def test_removes_duplicate_names_within_pool(self):
        pool = [
            _food(1, cat_code=15, descriptor="Fish"),
            _food(2, cat_code=15, descriptor="Fish, raw"),
            _food(3, cat_code=15, descriptor="Salmon"),
        ]

        result = _dedupe_pool_by_name(pool, used_names=set())

        assert [f.cn_code for f in result] == [1, 3]

    def test_removes_names_already_used(self):
        pool = [
            _food(1, cat_code=15, descriptor="Fish"),
            _food(2, cat_code=9, descriptor="Apple"),
        ]

        result = _dedupe_pool_by_name(pool, used_names={"fish"})

        assert [f.cn_code for f in result] == [2]

    def test_preserves_sorted_pool_order_for_duplicate_choice(self):
        preferred = _food(1, cat_code=15, descriptor="Fish")
        duplicate = _food(2, cat_code=15, descriptor="Fish, raw")

        result = _dedupe_pool_by_name([preferred, duplicate], used_names=set())

        assert [f.cn_code for f in result] == [1]

class TestPickDiverse:
    def test_empty_pool_returns_empty(self):
        assert _pick_diverse([], 3) == []

    def test_selects_one_per_category_in_round1(self):
        pool = [
            _food(1, cat_code=9),
            _food(2, cat_code=9),   # same cat as food 1 → skipped in round 1
            _food(3, cat_code=11),
            _food(4, cat_code=15),
        ]
        result = _pick_diverse(pool, 3)
        assert len(result) == 3
        selected_codes = {f.cn_code for f in result}
        assert 1 in selected_codes   # first in cat 9
        assert 2 not in selected_codes  # duplicate cat 9 skipped
        assert 3 in selected_codes
        assert 4 in selected_codes

    def test_fills_remainder_without_diversity_constraint(self):
        # Only 2 distinct categories but n=3 → must fill with leftover duplicate cat
        pool = [
            _food(1, cat_code=9),
            _food(2, cat_code=11),
            _food(3, cat_code=9),   # duplicate category, used in round 2
        ]
        result = _pick_diverse(pool, 3)
        assert len(result) == 3
        assert result[0].cn_code == 1
        assert result[1].cn_code == 2
        assert result[2].cn_code == 3

    def test_respects_n_limit(self):
        pool = [_food(i, cat_code=i) for i in range(10)]
        result = _pick_diverse(pool, 4)
        assert len(result) == 4

    def test_pool_smaller_than_n_returns_all(self):
        pool = [_food(1, cat_code=1), _food(2, cat_code=2)]
        result = _pick_diverse(pool, 5)
        assert len(result) == 2

    def test_single_item_pool(self):
        pool = [_food(42, cat_code=9)]
        result = _pick_diverse(pool, 3)
        assert len(result) == 1
        assert result[0].cn_code == 42

    def test_all_same_category_fills_via_round2(self):
        pool = [_food(i, cat_code=9) for i in range(5)]
        result = _pick_diverse(pool, 3)
        assert len(result) == 3
        # Round 1 selects food 0; round 2 fills foods 1, 2
        assert result[0].cn_code == 0
        assert {r.cn_code for r in result[1:]} == {1, 2}


# ── build_excluded_cn_codes ───────────────────────────────────────────────────

class TestBuildExcludedCnCodes:

    def _make_db(self, allergen_rows=None, pork_rows=None) -> MagicMock:
        """
        Build a mock DB where db.query(...).filter(...).all() can be called twice
        in sequence: first for allergen tags, then for pork category.
        Uses side_effect to return different values per call.
        """
        db = MagicMock()
        allergen_result = MagicMock()
        allergen_result.all.return_value = allergen_rows or []
        pork_result = MagicMock()
        pork_result.all.return_value = pork_rows or []

        # Each call to db.query(...).filter(...) returns the relevant result mock.
        # If the service only performs the pork query, the first filter call must
        # return pork rows rather than an unused allergen placeholder.
        filter_mock_allergen = MagicMock()
        filter_mock_allergen.all.return_value = allergen_rows or []
        filter_mock_pork = MagicMock()
        filter_mock_pork.all.return_value = pork_rows or []

        query_mock = MagicMock()
        filter_results = []
        if allergen_rows is not None:
            filter_results.append(filter_mock_allergen)
        if pork_rows is not None:
            filter_results.append(filter_mock_pork)
        query_mock.filter.side_effect = filter_results
        db.query.return_value = query_mock
        return db

    def test_empty_blacklist_returns_empty_set(self):
        db = MagicMock()
        result = build_excluded_cn_codes(db, [])
        assert result == set()
        db.query.assert_not_called()

    def test_allergen_only_no_pork(self):
        db = self._make_db(allergen_rows=[_row(10), _row(20)])
        result = build_excluded_cn_codes(db, ["egg"])
        assert result == {10, 20}
        # Only one query (allergen), no pork query
        db.query.assert_called_once()

    def test_pork_only_no_allergen(self):
        db = self._make_db(pork_rows=[_row(30), _row(40)])
        result = build_excluded_cn_codes(db, ["pork"])
        assert result == {30, 40}
        db.query.assert_called_once()

    def test_allergen_and_pork_combined(self):
        db = self._make_db(
            allergen_rows=[_row(10), _row(20)],
            pork_rows=[_row(30)],
        )
        result = build_excluded_cn_codes(db, ["milk", "pork"])
        assert result == {10, 20, 30}
        assert db.query.call_count == 2

    def test_multiple_allergens_merged(self):
        # nuts → ["TreeNut", "Peanut"]; all allergen_values passed in one query
        db = self._make_db(allergen_rows=[_row(5), _row(6), _row(7)])
        result = build_excluded_cn_codes(db, ["nuts"])
        assert result == {5, 6, 7}
        db.query.assert_called_once()

    def test_unknown_blacklist_item_ignored(self):
        # 'unknown_item' not in BLACKLIST_TO_ALLERGEN, not "pork" → no queries
        db = MagicMock()
        result = build_excluded_cn_codes(db, ["unknown_item"])
        assert result == set()
        db.query.assert_not_called()

    def test_returns_union_no_duplicates(self):
        # Same cn_code in both allergen and pork results → deduplicated in set
        db = self._make_db(
            allergen_rows=[_row(99)],
            pork_rows=[_row(99), _row(100)],
        )
        result = build_excluded_cn_codes(db, ["egg", "pork"])
        assert result == {99, 100}

    def test_empty_allergen_rows_with_allergen_blacklist(self):
        db = self._make_db(allergen_rows=[])
        result = build_excluded_cn_codes(db, ["seafood"])
        assert result == set()


# ── _query_pool ───────────────────────────────────────────────────────────────

class TestQueryPool:
    def test_filters_pork_descriptor_globally(self):
        db = MagicMock()
        query = MagicMock()
        db.query.return_value = query
        query.filter.return_value = query
        query.order_by.return_value = query
        query.limit.return_value = query
        query.all.return_value = []

        _query_pool(
            db=db,
            prefs=["meat"],
            grades=["A", "B"],
            excluded=set(),
            used=set(),
        )

        filter_args = query.filter.call_args_list[0].args
        compiled_filters = " ".join(str(arg) for arg in filter_args)
        bound_values = [
            value
            for arg in filter_args
            for value in getattr(arg.compile(), "params", {}).values()
        ]
        assert "descriptor" in compiled_filters
        assert "NOT LIKE" in compiled_filters
        assert "%pork%" in bound_values

    def test_default_limit_is_thirty(self):
        db = MagicMock()
        query = MagicMock()
        db.query.return_value = query
        query.filter.return_value = query
        query.order_by.return_value = query
        query.limit.return_value = query
        query.all.return_value = []

        _query_pool(
            db=db,
            prefs=["meat"],
            grades=["A", "B"],
            excluded=set(),
            used=set(),
        )

        query.limit.assert_called_once_with(30)


# ── Final batch display rewrite ───────────────────────────────────────────────

class TestBatchDisplayRewrite:
    def test_batch_rewrite_disabled_returns_empty(self):
        assert batch_rewrite_display_names("grow", [{"cn_code": 1}]) == {}

    def test_apply_batch_display_rewrite_updates_names_and_images(self):
        response = RecommendationResponse(
            super_power_foods=[
                FoodItem(
                    cn_code=1,
                    name="Milk",
                    category="dairy",
                    grade="E",
                    image_url="https://example.com/old.jpg",
                )
            ],
            tiny_hero_foods=[],
            try_less_foods=[],
        )
        food = _food(1, 1, grade="E", descriptor="Milk, whole, 3.25%")

        db = MagicMock()
        query = MagicMock()
        db.query.return_value = query
        query.filter.return_value = query
        query.all.return_value = [food]

        with patch(
            "app.services.recommendation_service.batch_rewrite_display_names",
            return_value={1: "Whole Milk"},
        ) as mock_rewrite:
            result = _apply_batch_display_rewrite(db, "grow", response)

        mock_rewrite.assert_called_once()
        assert result.super_power_foods[0].name == "Whole Milk"
        assert "Whole%20Milk%20food%20photography" in result.super_power_foods[0].image_url


# ── _query_tiny_hero ──────────────────────────────────────────────────────────

class TestQueryTinyHero:
    """
    Branches under test:
      TH-A: dislikes ∩ goal_prefs non-empty  → target = intersection
      TH-B: dislikes non-empty, ∩ empty      → target = dislikes
      TH-C: disliked categories unavailable  → target = goal_prefs - likes
      TH-D: dislikes empty                   → target = goal_prefs - likes
      TH-E: TH-D target empty                → target = full goal_prefs
    """

    def _stub_item(self, food: MagicMock, *args):
        """Return a dummy FoodItem-like mock for _to_food_item."""
        item = MagicMock()
        item.cn_code = food.cn_code
        return item

    # ── TH-A ──────────────────────────────────────────────────────────────────

    def test_th_a_dislikes_intersect_goal_prefs(self):
        """
        goal='see', goal_prefs=['vegetables','fruits','fish']
        dislikes=['fruits'], likes=[]
        → target = ['fruits'] (intersection)
        """
        foods = [_food(1, 9), _food(2, 11)]

        with patch(PATCH_POOL, return_value=foods) as mock_pool, \
             patch(PATCH_TO_ITEM, side_effect=self._stub_item):
            _query_tiny_hero(
                db=MagicMock(),
                goal_id="see",
                likes=[],
                dislikes=["fruits"],
                excluded=set(),
                used=set(),
                used_names=set(),
            )

        first_prefs = set(mock_pool.call_args_list[0].args[1])
        assert first_prefs == {"fruits"}

    # ── TH-B ──────────────────────────────────────────────────────────────────

    def test_th_b_dislikes_not_in_goal_prefs_uses_dislikes_first(self):
        """
        goal='see', goal_prefs=['vegetables','fruits','fish']
        dislikes=['bread'], likes=['vegetables']
        dislikes ∩ goal_prefs = [] → TH-B: target = dislikes = {'bread'}
        """
        foods = [_food(10, 18)]

        with patch(PATCH_POOL, return_value=foods) as mock_pool, \
             patch(PATCH_TO_ITEM, side_effect=self._stub_item):
            _query_tiny_hero(
                db=MagicMock(),
                goal_id="see",
                likes=["vegetables"],
                dislikes=["bread"],
                excluded=set(),
                used=set(),
                used_names=set(),
            )

        first_prefs = set(mock_pool.call_args_list[0].args[1])
        assert first_prefs == {"bread"}
        assert "vegetables" not in first_prefs  # excluded by likes

    def test_th_b_prefers_all_dislikes_when_intersection_empty(self):
        """
        Product rule: if dislikes do not overlap the goal, still try disliked
        categories before non-liked goal categories.
        """
        foods = [_food(20, 18)]

        with patch(PATCH_POOL, return_value=foods) as mock_pool, \
             patch(PATCH_TO_ITEM, side_effect=self._stub_item):
            _query_tiny_hero(
                db=MagicMock(),
                goal_id="see",
                likes=[],
                dislikes=["meat", "rice", "bread"],  # none in goal_prefs for 'see'
                excluded=set(),
                used=set(),
                used_names=set(),
            )

        first_prefs = set(mock_pool.call_args_list[0].args[1])
        assert first_prefs == {"meat", "rice", "bread"}

    # ── TH-C ──────────────────────────────────────────────────────────────────

    def test_th_c_disliked_unavailable_falls_back_to_goal_prefs_minus_likes(self):
        """
        goal='see', goal_prefs=['vegetables','fruits','fish']
        dislikes=['bread'], likes=['vegetables']
        disliked query empty → TH-C: target = goal_prefs - likes = {'fruits','fish'}
        """
        foods = [_food(30, 9)]

        with patch(PATCH_POOL, side_effect=[[], foods, []]) as mock_pool, \
             patch(PATCH_TO_ITEM, side_effect=self._stub_item):
            _query_tiny_hero(
                db=MagicMock(),
                goal_id="see",
                likes=["vegetables"],
                dislikes=["bread"],
                excluded=set(),
                used=set(),
                used_names=set(),
            )

        first_prefs = set(mock_pool.call_args_list[0].args[1])
        second_prefs = set(mock_pool.call_args_list[1].args[1])
        assert first_prefs == {"bread"}
        assert second_prefs == {"fruits", "fish"}

    # ── TH-D ──────────────────────────────────────────────────────────────────

    def test_th_d_no_dislikes_uses_goal_prefs_minus_likes(self):
        """
        goal='see', goal_prefs=['vegetables','fruits','fish']
        dislikes=[], likes=['vegetables']
        → target = goal_prefs - likes = {'fruits','fish'}
        """
        foods = [_food(40, 9)]

        with patch(PATCH_POOL, return_value=foods) as mock_pool, \
             patch(PATCH_TO_ITEM, side_effect=self._stub_item):
            _query_tiny_hero(
                db=MagicMock(),
                goal_id="see",
                likes=["vegetables"],
                dislikes=[],
                excluded=set(),
                used=set(),
                used_names=set(),
            )

        first_prefs = set(mock_pool.call_args_list[0].args[1])
        assert first_prefs == {"fruits", "fish"}

    # ── TH-E ──────────────────────────────────────────────────────────────────

    def test_th_e_no_dislikes_all_goal_prefs_liked_uses_full_goal_prefs(self):
        """
        goal='see', goal_prefs=['vegetables','fruits','fish']
        dislikes=[], likes=['vegetables','fruits','fish']
        TH-D target = goal_prefs - likes = [] → TH-E: target = full goal_prefs
        """
        foods = [_food(50, 9)]

        with patch(PATCH_POOL, return_value=foods) as mock_pool, \
             patch(PATCH_TO_ITEM, side_effect=self._stub_item):
            _query_tiny_hero(
                db=MagicMock(),
                goal_id="see",
                likes=["vegetables", "fruits", "fish"],
                dislikes=[],
                excluded=set(),
                used=set(),
                used_names=set(),
            )

        first_prefs = set(mock_pool.call_args_list[0].args[1])
        assert first_prefs == {"vegetables", "fruits", "fish"}

    def test_th_dislikes_non_goal_preferred_over_liked_goal_categories(self):
        """
        Required: goal='grow', dislikes=['fish'], likes include all grow prefs.
        Fish is not grow-relevant, but it is disliked and healthy, so it should
        be chosen before liked grow categories such as meat/dairy/vegetables.
        """
        fish_foods = [_food(70, 15), _food(71, 15), _food(72, 15)]

        with patch(PATCH_POOL, return_value=fish_foods) as mock_pool, \
             patch(PATCH_TO_ITEM, side_effect=self._stub_item):
            result = _query_tiny_hero(
                db=MagicMock(),
                goal_id="grow",
                likes=["meat", "dairy", "vegetables"],
                dislikes=["fish"],
                excluded=set(),
                used=set(),
                used_names=set(),
            )

        first_prefs = set(mock_pool.call_args_list[0].args[1])
        selected_codes = {item.cn_code for item in result}
        assert first_prefs == {"fish"}
        assert selected_codes == {70, 71, 72}

    def test_th_disliked_unavailable_after_allergy_filtering_uses_non_liked_goal(self):
        """
        Required: if disliked foods are unavailable after allergy filtering,
        fall back to goal_prefs - likes before any liked goal categories.
        """
        vegetable_food = _food(80, 11)
        excluded = {55, 66}

        with patch(PATCH_POOL, side_effect=[[], [vegetable_food], []]) as mock_pool, \
             patch(PATCH_TO_ITEM, side_effect=self._stub_item):
            result = _query_tiny_hero(
                db=MagicMock(),
                goal_id="grow",
                likes=["meat", "dairy"],
                dislikes=["fish"],
                excluded=excluded,
                used=set(),
                used_names=set(),
            )

        first_prefs = set(mock_pool.call_args_list[0].args[1])
        second_prefs = set(mock_pool.call_args_list[1].args[1])
        assert first_prefs == {"fish"}
        assert mock_pool.call_args_list[0].args[3] == excluded
        assert second_prefs == {"vegetables"}
        assert [item.cn_code for item in result] == [80]

    def test_th_does_not_choose_liked_categories_until_other_options_exhausted(self):
        """
        Required: disliked and non-liked goal categories should fill Tiny Hero
        before liked goal categories are queried.
        """
        fish_foods = [_food(90, 15), _food(91, 15)]
        vegetable_food = _food(92, 11)

        with patch(PATCH_POOL, side_effect=[fish_foods, [vegetable_food]]) as mock_pool, \
             patch(PATCH_TO_ITEM, side_effect=self._stub_item):
            result = _query_tiny_hero(
                db=MagicMock(),
                goal_id="grow",
                likes=["meat", "dairy"],
                dislikes=["fish"],
                excluded=set(),
                used=set(),
                used_names=set(),
            )

        queried_prefs = [set(c.args[1]) for c in mock_pool.call_args_list]
        selected_codes = {item.cn_code for item in result}
        assert queried_prefs == [{"fish"}, {"vegetables"}]
        assert selected_codes == {90, 91, 92}

    def test_th_dedupes_duplicate_display_names_within_same_pool(self):
        """
        Different cn_codes with the same cleaned display name should not both
        appear in Tiny Hero, and category-like names should be removed.
        """
        fish_1 = _food(500, 15, descriptor="Fish")
        fish_2 = _food(501, 15, descriptor="Fish, raw")
        salmon = _food(502, 15, descriptor="Salmon")

        with patch(PATCH_POOL, return_value=[fish_1, fish_2, salmon]), \
             patch(PATCH_TO_ITEM, side_effect=self._stub_item):
            result = _query_tiny_hero(
                db=MagicMock(),
                goal_id="grow",
                likes=["meat", "dairy", "vegetables"],
                dislikes=["fish"],
                excluded=set(),
                used=set(),
                used_names=set(),
            )

        selected_codes = [item.cn_code for item in result]
        assert selected_codes == [502]

    def test_th_filters_challenge_unsuitable_foods(self):
        frog = _food(510, 15, descriptor="Frog legs, raw")
        crustaceans = _food(511, 15, descriptor="Crustaceans, mixed species")
        salmon = _food(512, 15, descriptor="Salmon")

        with patch(PATCH_POOL, return_value=[frog, crustaceans, salmon]), \
             patch(PATCH_TO_ITEM, side_effect=self._stub_item):
            result = _query_tiny_hero(
                db=MagicMock(),
                goal_id="grow",
                likes=["meat", "dairy", "vegetables"],
                dislikes=["fish"],
                excluded=set(),
                used=set(),
                used_names=set(),
            )

        assert [item.cn_code for item in result] == [512]

    # ── Fallback chain ────────────────────────────────────────────────────────

    def test_fallback_to_goal_prefs_when_initial_query_empty(self):
        """
        When the first _query_pool returns nothing, falls back to full goal_prefs.
        """
        fallback_foods = [_food(60, 11), _food(61, 9)]

        with patch(PATCH_POOL, side_effect=[[], fallback_foods, []]) as mock_pool, \
             patch(PATCH_TO_ITEM, side_effect=self._stub_item):
            _query_tiny_hero(
                db=MagicMock(),
                goal_id="see",
                likes=[],
                dislikes=["fruits"],
                excluded=set(),
                used=set(),
                used_names=set(),
            )

        # Should be called at least twice (initial + goal_prefs fallback)
        assert mock_pool.call_count >= 2
        second_prefs = set(mock_pool.call_args_list[1].args[1])
        assert second_prefs == {"vegetables", "fruits", "fish"}

    def test_grades_are_always_a_and_b(self):
        """All _query_pool calls from _query_tiny_hero use grades=['A','B']."""
        with patch(PATCH_POOL, return_value=[]) as mock_pool, \
             patch(PATCH_TO_ITEM, return_value=MagicMock()):
            _query_tiny_hero(
                db=MagicMock(),
                goal_id="think",
                likes=[],
                dislikes=[],
                excluded=set(),
                used=set(),
                used_names=set(),
            )

        for c in mock_pool.call_args_list:
            grades = list(c.args[2])
            assert set(grades) == {"A", "B"}, f"Expected grades A/B, got {grades}"

    # ── used set mutation ─────────────────────────────────────────────────────

    def test_used_set_mutated_with_selected_cn_codes(self):
        """
        After _query_tiny_hero returns, the caller's `used` set must contain
        the cn_codes of all selected foods.
        """
        foods = [_food(100, 9), _food(101, 11), _food(102, 15)]
        used: set[int] = set()

        with patch(PATCH_POOL, return_value=foods), \
             patch(PATCH_TO_ITEM, side_effect=self._stub_item):
            _query_tiny_hero(
                db=MagicMock(),
                goal_id="see",
                likes=[],
                dislikes=[],
                excluded=set(),
                used=used,
                used_names=set(),
            )

        assert {100, 101, 102}.issubset(used)

    def test_used_set_isolates_intra_section(self):
        """
        Foods already in `used` when entering must NOT appear in output.
        `used` should only grow, never include food from a different call.
        """
        pre_existing = {999}
        # Pool includes cn_code 999 (pre-used) and new ones
        foods = [_food(999, 9), _food(200, 11)]
        used = set(pre_existing)

        with patch(PATCH_POOL, return_value=foods), \
             patch(PATCH_TO_ITEM, side_effect=self._stub_item):
            result = _query_tiny_hero(
                db=MagicMock(),
                goal_id="see",
                likes=[],
                dislikes=[],
                excluded=set(),
                used=used,
                used_names=set(),
            )

        # 999 was already in used → _query_pool received it in internal_used
        # The actual filtering is done inside _query_pool (mocked), but we can
        # verify that used grew to include new selections
        assert 999 in used  # pre-existing preserved
        assert 200 in used  # new selection added

    def test_excluded_set_passed_to_query_pool(self):
        """Excluded allergen codes are forwarded to _query_pool unchanged."""
        excluded = {55, 66}

        with patch(PATCH_POOL, return_value=[]) as mock_pool, \
             patch(PATCH_TO_ITEM, return_value=MagicMock()):
            _query_tiny_hero(
                db=MagicMock(),
                goal_id="think",
                likes=[],
                dislikes=[],
                excluded=excluded,
                used=set(),
                used_names=set(),
            )

        for c in mock_pool.call_args_list:
            passed_excluded = c.args[3]
            assert passed_excluded == excluded

    # ── Name deduplication within _query_tiny_hero ────────────────────────────

    def test_pre_existing_used_name_excluded_from_pool(self):
        """
        If used_names already contains 'beef', a food named 'Beef' (different
        cn_code) must not be selected.
        """
        beef_food = _food(300, 5, descriptor="Beef")
        other_food = _food(301, 9, descriptor="Apple")

        with patch(PATCH_POOL, return_value=[beef_food, other_food]), \
             patch(PATCH_TO_ITEM, side_effect=self._stub_item):
            result = _query_tiny_hero(
                db=MagicMock(),
                goal_id="see",
                likes=[],
                dislikes=[],
                excluded=set(),
                used=set(),
                used_names={"beef"},   # 'Beef' already used in super_power section
            )

        selected_codes = [item.cn_code for item in result]
        assert 300 not in selected_codes   # Beef blocked by name
        assert 301 in selected_codes       # Apple is fine

    def test_used_names_updated_after_selection(self):
        """
        After _query_tiny_hero, used_names must contain the normalized names
        of all selected foods so subsequent sections can exclude them.
        """
        foods = [_food(400, 9, descriptor="Mango"), _food(401, 11, descriptor="Spinach")]
        used_names: set[str] = set()

        with patch(PATCH_POOL, return_value=foods), \
             patch(PATCH_TO_ITEM, side_effect=self._stub_item):
            _query_tiny_hero(
                db=MagicMock(),
                goal_id="see",
                likes=[],
                dislikes=[],
                excluded=set(),
                used=set(),
                used_names=used_names,
            )

        assert "mango" in used_names
        assert "spinach" in used_names


# ── Global name deduplication (cross-section) ─────────────────────────────────

class TestGlobalNameDeduplication:
    """
    Tests that the same visible food name never appears in more than one section,
    even when different cn_codes share the same descriptor.
    """

    def _make_food_item(self, cn_code: int, name: str, grade: str = "A"):
        """Build a real-ish FoodItem for use in to_food_item stubs."""
        from app.schemas.recommendations import FoodItem
        return FoodItem(
            cn_code=cn_code,
            name=name,
            category="other",
            grade=grade,
            image_url="https://example.com/img.jpg",
        )

    def _make_request(self, goal_id="see", likes=None, dislikes=None, blacklist=None):
        return RecommendationRequest(
            goal_id=goal_id,
            likes=likes or [],
            dislikes=dislikes or [],
            blacklist=blacklist or [],
        )

    def test_same_descriptor_different_cn_code_appears_only_once(self):
        """
        Super Power Foods returns cn_code=1 named 'Beef'.
        Try Less Foods pool also contains cn_code=2 named 'Beef, raw'
        (normalizes to 'beef'). The Try Less section must exclude it.
        """
        sp_food = _food(1, 5, grade="A", descriptor="Beef")
        tl_food = _food(2, 5, grade="E", descriptor="Beef, raw")  # same normalized name

        # _query_pool returns SP foods for super_power rounds, TL foods for try_less
        # We use a cycling side_effect: enough empty lists to exhaust super_power
        # then return the try_less food
        pool_responses = [
            [sp_food],   # super_power R1 (or any round that picks it)
            [], [], [], [], [],  # remaining super_power rounds
            [], [], [], [],  # tiny_hero rounds
            [tl_food],   # try_less R1
            [], [], [],  # try_less remaining rounds
        ]

        PATCH_EXCL = "app.services.recommendation_service.build_excluded_cn_codes"

        with patch(PATCH_POOL, side_effect=pool_responses), \
             patch(PATCH_EXCL, return_value=set()):
            response = get_recommendations(MagicMock(), self._make_request())

        sp_names = [f.name for f in response.super_power_foods]
        tl_names = [f.name for f in response.try_less_foods]

        assert "Beef" in sp_names
        assert "Beef" not in tl_names   # same normalized name blocked

    def test_no_duplicate_normalized_names_in_full_response(self):
        """
        The full response must satisfy:
            len(all_normalized_names) == len(set(all_normalized_names))
        regardless of which cn_codes are returned.
        """
        # Simulate three sections each returning one food with unique name
        sp_food = _food(10, 9, grade="A", descriptor="Apple")
        th_food = _food(20, 11, grade="A", descriptor="Broccoli")
        tl_food = _food(30, 5, grade="E", descriptor="Sausage roll")

        pool_responses = [
            [sp_food], [], [], [], [], [],   # super_power
            [th_food], [], [],               # tiny_hero
            [tl_food], [], [], [],           # try_less
        ]

        PATCH_EXCL = "app.services.recommendation_service.build_excluded_cn_codes"

        with patch(PATCH_POOL, side_effect=pool_responses), \
             patch(PATCH_EXCL, return_value=set()):
            response = get_recommendations(MagicMock(), self._make_request())

        all_names = (
            [f.name for f in response.super_power_foods]
            + [f.name for f in response.tiny_hero_foods]
            + [f.name for f in response.try_less_foods]
        )
        normalized = [_normalize_name(n) for n in all_names]
        assert len(normalized) == len(set(normalized)), (
            f"Duplicate normalized names found: {normalized}"
        )

    def test_duplicate_name_blocked_across_super_power_and_tiny_hero(self):
        """
        Super Power: 'Chicken'  →  Tiny Hero: 'Chicken, grilled' must be blocked.
        """
        sp_food = _food(1, 5, grade="A", descriptor="Chicken")
        th_food = _food(2, 5, grade="B", descriptor="Chicken, grilled")

        pool_responses = [
            [sp_food], [], [], [], [], [],  # super_power picks sp_food
            [th_food], [], [],              # tiny_hero gets th_food in pool
            [], [], [], [],                 # try_less empty
        ]

        PATCH_EXCL = "app.services.recommendation_service.build_excluded_cn_codes"

        with patch(PATCH_POOL, side_effect=pool_responses), \
             patch(PATCH_EXCL, return_value=set()):
            response = get_recommendations(MagicMock(), self._make_request())

        sp_names = {_normalize_name(f.name) for f in response.super_power_foods}
        th_names = {_normalize_name(f.name) for f in response.tiny_hero_foods}

        # 'chicken' must not appear in both sections
        assert not (sp_names & th_names), (
            f"Name collision between SP and TH: {sp_names & th_names}"
        )

    def test_duplicate_name_blocked_across_tiny_hero_and_try_less(self):
        """
        Tiny Hero: 'Milk'  →  Try Less: 'Milk, whole' must be blocked.
        """
        th_food = _food(1, 1, grade="A", descriptor="Milk")
        tl_food = _food(2, 1, grade="D", descriptor="Milk, whole")

        pool_responses = [
            [], [], [], [], [], [],   # super_power: nothing
            [th_food], [], [],        # tiny_hero picks Milk
            [tl_food], [], [], [],    # try_less gets Milk, whole
        ]

        PATCH_EXCL = "app.services.recommendation_service.build_excluded_cn_codes"

        with patch(PATCH_POOL, side_effect=pool_responses), \
             patch(PATCH_EXCL, return_value=set()):
            response = get_recommendations(MagicMock(), self._make_request())

        th_names = {_normalize_name(f.name) for f in response.tiny_hero_foods}
        tl_names = {_normalize_name(f.name) for f in response.try_less_foods}

        assert not (th_names & tl_names), (
            f"Name collision between TH and TL: {th_names & tl_names}"
        )


# ── _compute_common_score ─────────────────────────────────────────────────────

class TestComputeCommonScore:
    def test_common_keyword_gives_plus_two(self):
        assert _compute_common_score("Apple") == 2

    def test_rare_keyword_gives_minus_four(self):
        assert _compute_common_score("Liver, raw") == -4

    def test_no_match_gives_zero(self):
        assert _compute_common_score("Xylitol syrup") == 0

    def test_both_common_and_rare_gives_minus_two(self):
        # "beef" matches common (+2), "liver" matches rare (-4) → -2
        assert _compute_common_score("Beef liver") == -2

    def test_case_insensitive(self):
        assert _compute_common_score("APPLE") == _compute_common_score("apple")

    def test_common_match_is_boolean_not_per_keyword(self):
        # "chicken broccoli rice" has 3 common keywords → still just +2
        assert _compute_common_score("Chicken broccoli rice bowl") == 2

    def test_rare_match_is_boolean_not_per_keyword(self):
        # "liver kidney tripe" has 3 rare keywords → still just -4
        assert _compute_common_score("Liver kidney tripe stew") == -4


# ── _sort_pool ────────────────────────────────────────────────────────────────

class TestSortPool:
    """
    _sort_pool is deterministic on all criteria except the random tiebreak.
    We test that the non-random dimensions produce the correct ordering.
    To isolate from randomness, we patch random.random() to return a constant.
    """

    PATCH_RANDOM = "app.services.recommendation_service._random.random"

    def test_goal_relevant_food_sorts_before_irrelevant(self):
        # goal_prefs=['fruits'] (cat 9); cat 11 = vegetables (not in goal_prefs)
        relevant = _food(1, cat_code=9, grade="A", descriptor="Apple")    # fruits = goal
        irrelevant = _food(2, cat_code=11, grade="A", descriptor="Broccoli")  # not goal

        with patch(self.PATCH_RANDOM, return_value=0.5):
            result = _sort_pool([irrelevant, relevant], goal_prefs=["fruits"])

        assert result[0].cn_code == 1  # relevant first

    def test_grade_a_before_grade_b_ascending(self):
        grade_b = _food(1, cat_code=9, grade="B", descriptor="Apple")
        grade_a = _food(2, cat_code=9, grade="A", descriptor="Banana")

        with patch(self.PATCH_RANDOM, return_value=0.5):
            result = _sort_pool([grade_b, grade_a], goal_prefs=[], ascending_grade=True)

        assert result[0].cn_code == 2  # A before B

    def test_grade_e_before_grade_d_descending(self):
        grade_d = _food(1, cat_code=5, grade="D", descriptor="Beef steak")
        grade_e = _food(2, cat_code=5, grade="E", descriptor="Fried chicken")

        with patch(self.PATCH_RANDOM, return_value=0.5):
            result = _sort_pool([grade_d, grade_e], goal_prefs=[], ascending_grade=False)

        assert result[0].cn_code == 2  # E before D

    def test_hcl_compliant_true_before_false(self):
        non_hcl = _food(1, cat_code=9, grade="A", descriptor="Apple")
        non_hcl.hcl_compliant = False
        hcl = _food(2, cat_code=9, grade="A", descriptor="Banana")
        hcl.hcl_compliant = True

        with patch(self.PATCH_RANDOM, return_value=0.5):
            result = _sort_pool([non_hcl, hcl], goal_prefs=[], ascending_grade=True)

        assert result[0].cn_code == 2  # hcl_compliant first

    def test_higher_common_score_sorts_first(self):
        # common food (score=+2) vs rare food (score=-4)
        common = _food(1, cat_code=9, grade="A", descriptor="Apple")    # +2
        rare = _food(2, cat_code=9, grade="A", descriptor="Sea cucumber")  # -4

        with patch(self.PATCH_RANDOM, return_value=0.5):
            result = _sort_pool([rare, common], goal_prefs=[], ascending_grade=True)

        assert result[0].cn_code == 1  # common food first

    def test_sort_priority_goal_over_grade(self):
        # goal-relevant grade B beats non-goal grade A
        goal_b = _food(1, cat_code=9, grade="B", descriptor="Apple")    # fruits = goal, B
        ngoal_a = _food(2, cat_code=11, grade="A", descriptor="Broccoli")  # not goal, A

        with patch(self.PATCH_RANDOM, return_value=0.5):
            result = _sort_pool([ngoal_a, goal_b], goal_prefs=["fruits"], ascending_grade=True)

        assert result[0].cn_code == 1  # goal relevance beats grade

    def test_sort_priority_grade_over_hcl(self):
        # same goal relevance; grade A non-hcl beats grade B hcl
        a_non_hcl = _food(1, cat_code=9, grade="A", descriptor="Apple")
        a_non_hcl.hcl_compliant = False
        b_hcl = _food(2, cat_code=9, grade="B", descriptor="Banana")
        b_hcl.hcl_compliant = True

        with patch(self.PATCH_RANDOM, return_value=0.5):
            result = _sort_pool([b_hcl, a_non_hcl], goal_prefs=[], ascending_grade=True)

        assert result[0].cn_code == 1  # grade beats hcl

    def test_sort_priority_hcl_over_common_score(self):
        # same goal+grade; hcl non-common beats non-hcl common
        hcl_rare = _food(1, cat_code=9, grade="A", descriptor="Sea cucumber")  # hcl, -4
        hcl_rare.hcl_compliant = True
        non_hcl_common = _food(2, cat_code=9, grade="A", descriptor="Apple")  # no hcl, +2
        non_hcl_common.hcl_compliant = False

        with patch(self.PATCH_RANDOM, return_value=0.5):
            result = _sort_pool([non_hcl_common, hcl_rare], goal_prefs=[], ascending_grade=True)

        assert result[0].cn_code == 1  # hcl beats common_score

    def test_empty_pool_returns_empty(self):
        assert _sort_pool([], goal_prefs=["fruits"]) == []

    def test_returns_all_items(self):
        pool = [_food(i, cat_code=9, grade="A") for i in range(5)]
        with patch(self.PATCH_RANDOM, return_value=0.5):
            result = _sort_pool(pool, goal_prefs=[])
        assert len(result) == 5
