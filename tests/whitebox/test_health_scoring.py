from types import SimpleNamespace

import pytest


@pytest.fixture()
def health_scoring(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:password@localhost:5432/nutrihealth")
    from app.services import health_scoring as health_scoring_module

    return health_scoring_module


def test_build_query_variants_expands_aliases_and_components(health_scoring):
    variants = health_scoring._build_query_variants("Mango Sticky Rice")

    assert "mango sticky rice" in variants
    assert "mango with tapioca" in variants
    assert "mango rice dessert" in variants
    assert "mango" in variants
    assert "rice" in variants


def test_build_query_variants_removes_stopwords(health_scoring):
    variants = health_scoring._build_query_variants("Stir Fried Squid With Vegetables")

    assert "squid fried" in variants
    assert "squid vegetables" in variants
    assert "squid" in variants


def test_map_health_grade_to_score_prefers_grade_then_hcl_compliance(health_scoring):
    assert health_scoring._map_health_grade_to_score("A", False) == 3
    assert health_scoring._map_health_grade_to_score("B", False) == 3
    assert health_scoring._map_health_grade_to_score("C", False) == 2
    assert health_scoring._map_health_grade_to_score("D", True) == 1
    assert health_scoring._map_health_grade_to_score("E", True) == 1
    assert health_scoring._map_health_grade_to_score(None, True) == 3
    assert health_scoring._map_health_grade_to_score(None, False) is None


def test_score_candidate_rewards_exact_category_match_and_penalizes_brand(health_scoring):
    unbranded = SimpleNamespace(
        descriptor="Apple",
        food_category_code=9,
        brand_name=None,
    )
    branded = SimpleNamespace(
        descriptor="Apple",
        food_category_code=9,
        brand_name="Snack Co",
    )

    variants = ["apple"]
    unbranded_score = health_scoring._score_candidate(unbranded, variants, "fruit", None)
    branded_score = health_scoring._score_candidate(branded, variants, "fruit", None)

    assert unbranded_score > branded_score
    assert unbranded_score > 3


def test_select_best_candidate_returns_none_when_score_is_too_low(health_scoring):
    row = SimpleNamespace(
        descriptor="Chocolate Cookie",
        food_category_code=18,
        brand_name=None,
    )

    result = health_scoring._select_best_candidate(
        candidates={1: {"row": row, "vector_distance": None}},
        variants=["broccoli"],
        preferred_category="vegetable",
    )

    assert result is None


def test_build_database_assessment_changes_message_by_score(health_scoring):
    row = SimpleNamespace(descriptor="Broccoli", cn_code=1)

    assert "nourishing choice" in health_scoring._build_database_assessment("Broccoli", 3, row)
    assert "enjoyed occasionally" in health_scoring._build_database_assessment("Broccoli", 2, row)
    assert "once-in-a-while treat" in health_scoring._build_database_assessment("Broccoli", 1, row)
