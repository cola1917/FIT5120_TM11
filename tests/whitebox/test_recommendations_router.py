"""
White-box tests for app.routers.recommendations.

Covers the fine-tuned model recommendation pipeline:
  - invalid goal_id is rejected by request validation
  - all supported goal IDs run through the mocked model/filter/enrichment path
  - parse failures become a 502 response
  - payload fields are forwarded to the model call and filters
"""

import asyncio
import importlib

import pytest
from fastapi import BackgroundTasks
from pydantic import ValidationError


@pytest.fixture()
def rec_module(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:password@localhost:5432/nutrihealth")
    import app.routers.recommendations as rec_router
    return importlib.reload(rec_router)


def _model_payload():
    return {
        "goal": "grow",
        "super_power_foods": [
            {"food": "Apple", "reason": "Helps you feel ready to play."},
            {"food": "Broccoli", "reason": "A strong green choice."},
        ],
        "tiny_hero_foods": [
            {"food": "Carrot", "reason": "A brave crunchy try."},
        ],
        "try_less_foods": [
            {"food": "Candy", "reason": "Best as a sometimes food."},
        ],
    }


def _enriched_item(food_name: str, reason: str, category: str = "fruits"):
    from app.schemas.recommendation import EnrichedFoodItem

    food_id = food_name.lower().replace(" ", "_")
    return EnrichedFoodItem(
        food_id=food_id,
        food_name=food_name,
        category=category,
        image_url=f"/static/category_fallback/{category}.png",
        image_status="fallback",
        reason=reason,
    )


def _patch_successful_pipeline(monkeypatch, rec_module, parsed=None):
    parsed_payload = parsed or _model_payload()

    monkeypatch.setattr(rec_module, "call_model", lambda **kwargs: '{"ok": true}')
    monkeypatch.setattr(rec_module, "parse_model_output", lambda raw: parsed_payload)
    monkeypatch.setattr(rec_module, "filter_output", lambda parsed, blacklist, allergies: parsed)
    monkeypatch.setattr(rec_module, "filter_tiny_hero_by_likes", lambda filtered, likes: filtered)
    monkeypatch.setattr(rec_module, "should_queue_generation", lambda food_name: False)

    def _enrich(items):
        return [
            _enriched_item(item["food"], item.get("reason", ""), category="fruits")
            for item in items
        ]

    monkeypatch.setattr(rec_module, "enrich_recommendation_items", _enrich)


@pytest.mark.parametrize("bad_goal", ["unknown", "weight_loss", "", "GROW", "123"])
def test_recommend_rejects_invalid_goal_id(rec_module, bad_goal):
    with pytest.raises(ValidationError) as exc:
        rec_module.RecommendationRequest(goal_id=bad_goal)

    assert "goal_id" in str(exc.value)
    assert "grow" in str(exc.value)


@pytest.mark.parametrize("goal", ["grow", "see", "think", "fight", "feel", "strong"])
def test_recommend_accepts_all_valid_goal_ids(monkeypatch, rec_module, goal):
    _patch_successful_pipeline(monkeypatch, rec_module)

    payload = rec_module.RecommendationRequest(goal_id=goal)
    result = asyncio.run(
        rec_module.recommend(
            payload=payload,
            background_tasks=BackgroundTasks(),
            current_user={"username": "demo"},
        )
    )

    from app.schemas.recommendation import RecommendationResponse

    assert isinstance(result, RecommendationResponse)
    assert isinstance(result.super_power_foods, list)
    assert isinstance(result.tiny_hero_foods, list)
    assert isinstance(result.try_less_foods, list)


def test_recommend_returns_enriched_response(monkeypatch, rec_module):
    _patch_successful_pipeline(monkeypatch, rec_module)

    payload = rec_module.RecommendationRequest(goal_id="grow")
    result = asyncio.run(
        rec_module.recommend(
            payload=payload,
            background_tasks=BackgroundTasks(),
            current_user={"username": "demo"},
        )
    )

    assert len(result.super_power_foods) == 2
    assert len(result.tiny_hero_foods) == 1
    assert len(result.try_less_foods) == 1
    assert result.super_power_foods[0].food_name == "Apple"
    assert result.super_power_foods[0].name == "Apple"
    assert result.try_less_foods[0].reason == "Best as a sometimes food."


def test_recommend_raises_502_when_model_output_cannot_parse(monkeypatch, rec_module):
    monkeypatch.setattr(rec_module, "call_model", lambda **kwargs: "not json")
    monkeypatch.setattr(rec_module, "parse_model_output", lambda raw: None)

    payload = rec_module.RecommendationRequest(goal_id="think")

    with pytest.raises(rec_module.HTTPException) as exc:
        asyncio.run(
            rec_module.recommend(
                payload=payload,
                background_tasks=BackgroundTasks(),
                current_user={"username": "demo"},
            )
        )

    assert exc.value.status_code == 502
    assert "invalid output" in exc.value.detail


def test_recommend_passes_payload_to_model_and_filters(monkeypatch, rec_module):
    received: dict = {}
    parsed_payload = _model_payload()

    def _capture_model(**kwargs):
        received["model_kwargs"] = kwargs
        return '{"ok": true}'

    def _capture_filter(parsed, blacklist, allergies):
        received["filter_blacklist"] = blacklist
        received["filter_allergies"] = allergies
        return parsed

    def _capture_tiny_hero_filter(filtered, likes):
        received["tiny_hero_likes"] = likes
        return filtered

    monkeypatch.setattr(rec_module, "call_model", _capture_model)
    monkeypatch.setattr(rec_module, "parse_model_output", lambda raw: parsed_payload)
    monkeypatch.setattr(rec_module, "filter_output", _capture_filter)
    monkeypatch.setattr(rec_module, "filter_tiny_hero_by_likes", _capture_tiny_hero_filter)
    monkeypatch.setattr(rec_module, "should_queue_generation", lambda food_name: False)
    monkeypatch.setattr(
        rec_module,
        "enrich_recommendation_items",
        lambda items: [_enriched_item(item["food"], item.get("reason", "")) for item in items],
    )

    payload = rec_module.RecommendationRequest(
        goal_id="feel",
        likes=["dairy", "fruits"],
        dislikes=["fish"],
        blacklist=["egg"],
        allergies=["nuts"],
    )

    asyncio.run(
        rec_module.recommend(
            payload=payload,
            background_tasks=BackgroundTasks(),
            current_user={"username": "demo"},
        )
    )

    assert received["model_kwargs"] == {
        "goal": "feel",
        "likes": ["dairy", "fruits"],
        "dislikes": ["fish"],
        "blacklist": ["egg"],
        "allergies": ["nuts"],
    }
    assert received["filter_blacklist"] == ["egg"]
    assert received["filter_allergies"] == ["nuts"]
    assert received["tiny_hero_likes"] == ["dairy", "fruits"]
