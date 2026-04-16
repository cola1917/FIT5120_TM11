import asyncio
from fastapi import HTTPException

from app.routers import stories


def test_load_stories_manifest_reads_catalog():
    manifest = stories.load_stories_manifest()

    assert {item["id"] for item in manifest["stories"]} == {"story-1", "story-2", "story-3"}


def test_validate_story_exists_and_page_count():
    assert stories.validate_story_exists("story-1") is True
    assert stories.validate_story_exists("missing-story") is False
    assert stories.get_story_page_count("story-1") == 8


def test_get_story_page_count_raises_for_missing_story():
    try:
        stories.get_story_page_count("missing-story")
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("Expected HTTPException")


def test_get_stories_returns_manifest():
    result = asyncio.run(stories.get_stories(current_user={"sub": "demo"}))

    assert "stories" in result
    assert len(result["stories"]) == 3


def test_get_story_text_and_assets_resolve_real_files():
    text = asyncio.run(stories.get_story_text("story-1", current_user={"sub": "demo"}))
    cover = asyncio.run(stories.get_story_cover("story-1"))
    page_image = asyncio.run(stories.get_story_page_image("story-1", 1))
    page_audio = asyncio.run(stories.get_story_page_audio("story-1", 1))
    outcome_audio = asyncio.run(stories.get_story_outcome_audio("story-1"))

    assert isinstance(text, dict)
    assert "pages" in text
    assert cover.path.endswith("story-1/cover.jpg")
    assert page_image.path.endswith("story-1/pages/page-1.jpg")
    assert page_audio.path.endswith("story-1/pages/page-1.wav")
    assert outcome_audio.path.endswith("story-1/pages/outcome.wav")


def test_story_audio_fallback_supports_uppercase_wav():
    page_audio = asyncio.run(stories.get_story_page_audio("story-1", 2))

    assert page_audio.path.endswith("story-1/pages/page-2.WAV")


def test_story_asset_endpoints_validate_errors():
    try:
        asyncio.run(stories.get_story_page_image("story-1", 999))
    except HTTPException as exc:
        assert exc.status_code == 400
    else:
        raise AssertionError("Expected HTTPException")

    try:
        asyncio.run(stories.get_story_cover("missing-story"))
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("Expected HTTPException")