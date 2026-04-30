"""
Extended white-box tests for app.routers.scan.

Covers the branches that were not exercised in test_scan_router.py:
  - file-too-large validation (400)
  - file read error (400)
  - cache hit (returns cached ScanResponse without AI calls)
  - vision LLM exception → 500 ANALYSIS_FAILED
  - vision LLM returns reject_reason=analysis_failed → 500 ANALYSIS_FAILED
  - not-food result → 400 NOT_FOOD
  - healthy food (assessment_score >= 3) → alternatives forced to []
  - unhealthy food (assessment_score < 3) → RAG + rewrite + image_url injected
  - CACHE_AI_RESPONSE=false → cache_result is NOT called
"""

import asyncio
import io
import importlib
from unittest.mock import MagicMock, AsyncMock

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_upload(content: bytes, content_type: str = "image/jpeg", filename: str = "test.jpg") -> UploadFile:
    return UploadFile(
        filename=filename,
        file=io.BytesIO(content),
        headers=Headers({"content-type": content_type}),
    )


def _valid_ai_result(assessment_score: int = 3) -> dict:
    """Return a minimal valid AI analysis result."""
    return {
        "confidence": 0.95,
        "is_food": True,
        "food_name": "Apple",
        "primary_object": "apple",
        "reject_reason": "none",
        "nutritional_info": {
            "carbohydrates": {"amount": "14g", "description": "Energy!"},
            "protein": {"amount": "0.5g", "description": "Strong muscles!"},
            "fats": {"amount": "0.2g", "description": "Sharp brain!"},
        },
        "assessment_score": assessment_score,
        "assessment": "Great choice!",
        "alternatives": [],
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def scan_module(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:password@localhost:5432/nutrihealth")
    import app.routers.scan as scan_mod
    return importlib.reload(scan_mod)


@pytest.fixture()
def fake_db():
    """Minimal fake db object – unused by the mocked functions."""
    return MagicMock()


@pytest.fixture()
def fake_user():
    return {"username": "demo"}


# ---------------------------------------------------------------------------
# File validation tests
# ---------------------------------------------------------------------------

def test_scan_food_rejects_oversized_file(monkeypatch, scan_module, fake_db, fake_user):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    big_content = b"x" * (scan_module.MAX_FILE_SIZE + 1)
    upload = _make_upload(big_content, content_type="image/jpeg")

    monkeypatch.setattr(scan_module, "get_cached_result", lambda db, h: None)

    with pytest.raises(scan_module.HTTPException) as exc:
        asyncio.run(scan_module.scan_food(file=upload, db=fake_db, current_user=fake_user))

    assert exc.value.status_code == 400
    assert "too large" in exc.value.detail.lower()
    assert exc.value.headers.get("X-Error-Code") == "INVALID_FILE"


def test_scan_food_rejects_read_error(monkeypatch, scan_module, fake_db, fake_user):
    async def bad_read():
        raise OSError("disk error")

    upload = _make_upload(b"", content_type="image/jpeg")
    upload.read = bad_read  # type: ignore[method-assign]

    with pytest.raises(scan_module.HTTPException) as exc:
        asyncio.run(scan_module.scan_food(file=upload, db=fake_db, current_user=fake_user))

    assert exc.value.status_code == 400
    assert exc.value.headers.get("X-Error-Code") == "INVALID_FILE"


# ---------------------------------------------------------------------------
# Cache hit
# ---------------------------------------------------------------------------

def test_scan_food_returns_cached_result(monkeypatch, scan_module, fake_db, fake_user):
    cached_payload = {**_valid_ai_result(3), "recognised": True}
    monkeypatch.setattr(scan_module, "get_cached_result", lambda db, h: cached_payload)

    # If these are called the test should fail because cache hit must short-circuit
    gemini_mock = MagicMock()
    gemini_mock.analyze_food_image = AsyncMock(side_effect=AssertionError("Should not call AI on cache hit"))
    monkeypatch.setattr(scan_module, "gemini_service", gemini_mock)

    upload = _make_upload(b"\xff\xd8\xff" + b"x" * 100, content_type="image/jpeg")
    result = asyncio.run(scan_module.scan_food(file=upload, db=fake_db, current_user=fake_user))

    assert result.food_name == "Apple"
    assert result.recognised is True


# ---------------------------------------------------------------------------
# Vision LLM failure paths
# ---------------------------------------------------------------------------

def test_scan_food_returns_500_when_vision_raises(monkeypatch, scan_module, fake_db, fake_user):
    monkeypatch.setattr(scan_module, "get_cached_result", lambda db, h: None)

    gemini_mock = MagicMock()
    gemini_mock.analyze_food_image = AsyncMock(side_effect=RuntimeError("API unavailable"))
    monkeypatch.setattr(scan_module, "gemini_service", gemini_mock)

    upload = _make_upload(b"\xff\xd8\xff" + b"x" * 100, content_type="image/jpeg")

    with pytest.raises(scan_module.HTTPException) as exc:
        asyncio.run(scan_module.scan_food(file=upload, db=fake_db, current_user=fake_user))

    assert exc.value.status_code == 500
    assert exc.value.headers.get("X-Error-Code") == "ANALYSIS_FAILED"


def test_scan_food_returns_500_when_vision_returns_analysis_failed(monkeypatch, scan_module, fake_db, fake_user):
    monkeypatch.setattr(scan_module, "get_cached_result", lambda db, h: None)

    fallback = {
        "confidence": 0,
        "is_food": False,
        "food_name": "__NOT_FOOD__",
        "primary_object": "unknown",
        "reject_reason": "analysis_failed",
        "nutritional_info": {"carbohydrates": {"amount": "0g", "description": "n/a"},
                             "protein": {"amount": "0g", "description": "n/a"},
                             "fats": {"amount": "0g", "description": "n/a"}},
        "assessment_score": 1,
        "assessment": "failed",
        "alternatives": [],
    }

    gemini_mock = MagicMock()
    gemini_mock.analyze_food_image = AsyncMock(return_value=fallback)
    monkeypatch.setattr(scan_module, "gemini_service", gemini_mock)

    upload = _make_upload(b"\xff\xd8\xff" + b"x" * 100, content_type="image/jpeg")

    with pytest.raises(scan_module.HTTPException) as exc:
        asyncio.run(scan_module.scan_food(file=upload, db=fake_db, current_user=fake_user))

    assert exc.value.status_code == 500
    assert exc.value.headers.get("X-Error-Code") == "ANALYSIS_FAILED"


# ---------------------------------------------------------------------------
# Not-food path
# ---------------------------------------------------------------------------

def test_scan_food_returns_400_for_non_food(monkeypatch, scan_module, fake_db, fake_user):
    monkeypatch.setattr(scan_module, "get_cached_result", lambda db, h: None)

    not_food_result = {
        "confidence": 0.9,
        "is_food": False,
        "food_name": "__NOT_FOOD__",
        "primary_object": "mouse",
        "reject_reason": "not_food",
        "nutritional_info": {"carbohydrates": {"amount": "0g", "description": "n/a"},
                             "protein": {"amount": "0g", "description": "n/a"},
                             "fats": {"amount": "0g", "description": "n/a"}},
        "assessment_score": 1,
        "assessment": "n/a",
        "alternatives": [],
    }

    gemini_mock = MagicMock()
    gemini_mock.analyze_food_image = AsyncMock(return_value=not_food_result)
    monkeypatch.setattr(scan_module, "gemini_service", gemini_mock)

    upload = _make_upload(b"\xff\xd8\xff" + b"x" * 100, content_type="image/jpeg")

    with pytest.raises(scan_module.HTTPException) as exc:
        asyncio.run(scan_module.scan_food(file=upload, db=fake_db, current_user=fake_user))

    assert exc.value.status_code == 400
    assert exc.value.headers.get("X-Error-Code") == "NOT_FOOD"


# ---------------------------------------------------------------------------
# Healthy food path (score >= 3)
# ---------------------------------------------------------------------------

def test_scan_food_healthy_food_returns_empty_alternatives(monkeypatch, scan_module, fake_db, fake_user):
    monkeypatch.setattr(scan_module, "get_cached_result", lambda db, h: None)

    ai_result = _valid_ai_result(assessment_score=3)
    ai_result["alternatives"] = [{"name": "🍊 Orange", "description": "Tasty"}]  # should be cleared

    gemini_mock = MagicMock()
    gemini_mock.analyze_food_image = AsyncMock(return_value=ai_result)
    monkeypatch.setattr(scan_module, "gemini_service", gemini_mock)

    monkeypatch.setattr(
        scan_module,
        "apply_database_first_score",
        lambda result, db: {"assessment_score": 3, "assessment": "Healthy!", "score_source": "mock",
                            "matched_cn_code": None, "health_grade": "A"},
    )

    cache_result_mock = MagicMock()
    monkeypatch.setattr(scan_module, "cache_result", cache_result_mock)
    monkeypatch.setenv("CACHE_AI_RESPONSE", "true")

    upload = _make_upload(b"\xff\xd8\xff" + b"x" * 100, content_type="image/jpeg")
    result = asyncio.run(scan_module.scan_food(file=upload, db=fake_db, current_user=fake_user))

    assert result.alternatives == []
    assert result.assessment_score == 3


# ---------------------------------------------------------------------------
# Unhealthy food path (score < 3)
# ---------------------------------------------------------------------------

def test_scan_food_unhealthy_food_builds_alternatives(monkeypatch, scan_module, fake_db, fake_user):
    monkeypatch.setattr(scan_module, "get_cached_result", lambda db, h: None)

    ai_result = _valid_ai_result(assessment_score=1)
    ai_result["food_name"] = "Chocolate Chip Cookie"

    gemini_mock = MagicMock()
    gemini_mock.analyze_food_image = AsyncMock(return_value=ai_result)
    gemini_mock.rewrite_alternatives = AsyncMock(return_value=[
        {"name": "🍎 Apple Slices", "description": "Crunchy and full of vitamins!"},
    ])
    monkeypatch.setattr(scan_module, "gemini_service", gemini_mock)

    rag_mock = MagicMock()
    rag_mock.get_alternatives = MagicMock(return_value=[
        {"name": "Apple Slices", "description": "Healthy snack"},
    ])
    monkeypatch.setattr(scan_module, "rag_service", rag_mock)

    monkeypatch.setattr(
        scan_module,
        "apply_database_first_score",
        lambda result, db: {"assessment_score": 1, "assessment": "Try a healthier swap!",
                            "score_source": "mock", "matched_cn_code": None, "health_grade": "E"},
    )

    cache_result_mock = MagicMock()
    monkeypatch.setattr(scan_module, "cache_result", cache_result_mock)
    monkeypatch.setenv("CACHE_AI_RESPONSE", "true")

    upload = _make_upload(b"\xff\xd8\xff" + b"x" * 100, content_type="image/jpeg")
    result = asyncio.run(scan_module.scan_food(file=upload, db=fake_db, current_user=fake_user))

    assert len(result.alternatives) >= 1
    # image_url must be injected
    for alt in result.alternatives:
        assert alt.image_url is not None
        assert alt.image_url.startswith("https://")
    assert result.assessment_score == 1


# ---------------------------------------------------------------------------
# Cache disabled path
# ---------------------------------------------------------------------------

def test_scan_food_does_not_cache_when_disabled(monkeypatch, scan_module, fake_db, fake_user):
    monkeypatch.setenv("CACHE_AI_RESPONSE", "false")
    monkeypatch.setattr(scan_module, "get_cached_result", lambda db, h: None)

    ai_result = _valid_ai_result(assessment_score=3)
    gemini_mock = MagicMock()
    gemini_mock.analyze_food_image = AsyncMock(return_value=ai_result)
    monkeypatch.setattr(scan_module, "gemini_service", gemini_mock)

    monkeypatch.setattr(
        scan_module,
        "apply_database_first_score",
        lambda result, db: {"assessment_score": 3, "assessment": "Healthy!", "score_source": "mock",
                            "matched_cn_code": None, "health_grade": "A"},
    )

    cache_result_mock = MagicMock()
    monkeypatch.setattr(scan_module, "cache_result", cache_result_mock)

    upload = _make_upload(b"\xff\xd8\xff" + b"x" * 100, content_type="image/jpeg")
    asyncio.run(scan_module.scan_food(file=upload, db=fake_db, current_user=fake_user))

    cache_result_mock.assert_not_called()
