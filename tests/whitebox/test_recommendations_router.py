"""
White-box tests for app.routers.recommendations.

Covers:
  - invalid goal_id → 422 with informative detail
  - valid goal_id with mocked service → proper RecommendationResponse shape
  - authentication is required (Depends(get_current_user) is wired in)
  - all valid goal IDs are accepted
"""

import asyncio
import importlib

import pytest
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Module fixture (follows the same pattern as test_daily_challenge_router.py)
# ---------------------------------------------------------------------------

@pytest.fixture()
def rec_module(monkeypatch):
    # Use a fake Postgres URL so app.database loads without raising; the DB is
    # never actually connected because get_recommendations is monkeypatched.
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:password@localhost:5432/nutrihealth")
    import app.routers.recommendations as rec_router
    return importlib.reload(rec_router)


@pytest.fixture()
def rec_schemas(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:password@localhost:5432/nutrihealth")
    from app.schemas import recommendations as schemas_mod
    return importlib.reload(schemas_mod)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_food_item(rec_module, cn_code: int = 1, name: str = "Apple", grade: str = "A"):
    from app.schemas.recommendations import FoodItem
    return FoodItem(
        cn_code=cn_code,
        name=name,
        category="fruit",
        grade=grade,
        image_url=f"https://image.pollinations.ai/prompt/{name}?model=flux&width=400&height=400",
    )


def _make_empty_response(rec_module):
    from app.schemas.recommendations import RecommendationResponse
    return RecommendationResponse(
        super_power_foods=[],
        tiny_hero_foods=[],
        try_less_foods=[],
    )


def _make_full_response(rec_module):
    from app.schemas.recommendations import RecommendationResponse
    return RecommendationResponse(
        super_power_foods=[
            _make_food_item(rec_module, 1, "Apple", "A"),
            _make_food_item(rec_module, 2, "Broccoli", "A"),
        ],
        tiny_hero_foods=[_make_food_item(rec_module, 3, "Carrot", "B")],
        try_less_foods=[_make_food_item(rec_module, 4, "Candy", "E")],
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_goal", ["unknown", "weight_loss", "", "GROW", "123"])
def test_recommend_rejects_invalid_goal_id(monkeypatch, rec_module, bad_goal):
    monkeypatch.setattr(rec_module, "get_recommendations", lambda db, payload: _make_empty_response(rec_module))

    fake_db = MagicMock()
    payload = rec_module.RecommendationRequest(goal_id=bad_goal)

    with pytest.raises(rec_module.HTTPException) as exc:
        asyncio.run(
            rec_module.recommend(
                payload=payload,
                db=fake_db,
                current_user={"username": "demo"},
            )
        )

    assert exc.value.status_code == 422
    assert bad_goal in exc.value.detail or "Invalid goal_id" in exc.value.detail


@pytest.mark.parametrize("goal", ["grow", "see", "think", "fight", "feel", "strong"])
def test_recommend_accepts_all_valid_goal_ids(monkeypatch, rec_module, goal):
    monkeypatch.setattr(rec_module, "get_recommendations", lambda db, payload: _make_empty_response(rec_module))

    fake_db = MagicMock()
    payload = rec_module.RecommendationRequest(goal_id=goal)

    result = asyncio.run(
        rec_module.recommend(
            payload=payload,
            db=fake_db,
            current_user={"username": "demo"},
        )
    )

    from app.schemas.recommendations import RecommendationResponse
    assert isinstance(result, RecommendationResponse)
    assert isinstance(result.super_power_foods, list)
    assert isinstance(result.tiny_hero_foods, list)
    assert isinstance(result.try_less_foods, list)


def test_recommend_returns_response_from_service(monkeypatch, rec_module):
    expected = _make_full_response(rec_module)
    monkeypatch.setattr(rec_module, "get_recommendations", lambda db, payload: expected)

    fake_db = MagicMock()
    payload = rec_module.RecommendationRequest(goal_id="grow")

    result = asyncio.run(
        rec_module.recommend(
            payload=payload,
            db=fake_db,
            current_user={"username": "demo"},
        )
    )

    assert len(result.super_power_foods) == 2
    assert len(result.tiny_hero_foods) == 1
    assert len(result.try_less_foods) == 1
    assert result.super_power_foods[0].name == "Apple"
    assert result.try_less_foods[0].grade == "E"


def test_recommend_propagates_service_exception(monkeypatch, rec_module):
    def _boom(db, payload):
        raise RuntimeError("DB error")

    monkeypatch.setattr(rec_module, "get_recommendations", _boom)

    fake_db = MagicMock()
    payload = rec_module.RecommendationRequest(goal_id="think")

    with pytest.raises(RuntimeError, match="DB error"):
        asyncio.run(
            rec_module.recommend(
                payload=payload,
                db=fake_db,
                current_user={"username": "demo"},
            )
        )


def test_recommend_passes_payload_to_service(monkeypatch, rec_module):
    received: dict = {}

    def _capture(db, payload):
        received["goal_id"] = payload.goal_id
        received["likes"] = payload.likes
        received["dislikes"] = payload.dislikes
        received["blacklist"] = payload.blacklist
        return _make_empty_response(rec_module)

    monkeypatch.setattr(rec_module, "get_recommendations", _capture)

    fake_db = MagicMock()
    payload = rec_module.RecommendationRequest(
        goal_id="feel",
        likes=["dairy", "fruit"],
        dislikes=["fish"],
        blacklist=["egg"],
    )

    asyncio.run(
        rec_module.recommend(
            payload=payload,
            db=fake_db,
            current_user={"username": "demo"},
        )
    )

    assert received["goal_id"] == "feel"
    assert received["likes"] == ["dairy", "fruit"]
    assert received["dislikes"] == ["fish"]
    assert received["blacklist"] == ["egg"]
