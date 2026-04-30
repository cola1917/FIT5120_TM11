"""
API Regression Tests — pytest-based replacement for api_regression_test.sh.

Requires API_USERNAME and API_PASSWORD to be set; all tests are skipped when
credentials are absent (regression tests are typically run only on push / manual
trigger, not on pull requests).

Covers the same assertions as the original shell script:
  - Root and health endpoints
  - Token endpoint: invalid creds → 401, valid creds → 200 + non-empty token
  - Protected story routes (authenticated + unauthenticated boundary)
  - Scan endpoint error paths: unauthenticated, invalid content type, oversized
  - Admin cleanup-cache endpoint
  - Recommendations endpoint: auth boundary + valid response shape
"""

from __future__ import annotations

import os
from typing import Optional

import httpx
import pytest

from metrics_collector import MetricsCollector
from conftest import timed_request

_USERNAME: Optional[str] = os.getenv("API_USERNAME") or os.getenv("DEMO_USERNAME")
_PASSWORD: Optional[str] = os.getenv("API_PASSWORD") or os.getenv("DEMO_PASSWORD")

# Minimum PNG (1×1 pixel, transparent) used for the oversized-file test baseline
_VALID_SMALL_PNG = (
    b"\x89PNG\r\n\x1a\n"                         # signature
    b"\x00\x00\x00\rIHDR"                         # IHDR chunk length + type
    b"\x00\x00\x00\x01\x00\x00\x00\x01"          # 1×1
    b"\x08\x02\x00\x00\x00\x90wS\xde"            # bit depth + colour + CRC
    b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N"  # IDAT
    b"\x00\x00\x00\x00IEND\xaeB`\x82"            # IEND
)


# ---------------------------------------------------------------------------
# Skip the whole module when no credentials are configured
# ---------------------------------------------------------------------------

def _require_credentials() -> None:
    if not _USERNAME or not _PASSWORD:
        pytest.skip(
            "API_USERNAME and API_PASSWORD are required for the regression suite; "
            "set them via environment variables."
        )


# ---------------------------------------------------------------------------
# Root and health
# ---------------------------------------------------------------------------


def test_regression_root_returns_200(
    client: httpx.Client,
    metrics: MetricsCollector,
) -> None:
    _require_credentials()
    response = timed_request(client, "GET", "/", metrics)
    assert response.status_code == 200, response.text
    response.json()  # must be valid JSON
    metrics.mark_check()


def test_regression_health_returns_200(
    client: httpx.Client,
    metrics: MetricsCollector,
) -> None:
    _require_credentials()
    response = timed_request(client, "GET", "/health", metrics)
    assert response.status_code == 200, response.text
    response.json()
    metrics.mark_check()


# ---------------------------------------------------------------------------
# Token endpoint
# ---------------------------------------------------------------------------


def test_invalid_credentials_return_401(
    client: httpx.Client,
    metrics: MetricsCollector,
) -> None:
    _require_credentials()
    response = timed_request(
        client,
        "POST",
        "/token",
        metrics,
        metrics_path="/token[invalid]",
        data={"username": "wrong-user", "password": "wrong-pass"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
    metrics.mark_check()


def test_valid_credentials_return_token(
    client: httpx.Client,
    metrics: MetricsCollector,
    auth_token: Optional[str],
) -> None:
    _require_credentials()
    # auth_token fixture already validated the token endpoint — if auth_token is not
    # None we know it succeeded; record the check.
    assert auth_token, "Expected a non-empty access token"
    metrics.record("/token[valid]", 200, 0.0)
    metrics.mark_check()
    metrics.set_auth_checks_skipped(False)


# ---------------------------------------------------------------------------
# Protected story routes
# ---------------------------------------------------------------------------


def test_stories_list_authenticated_returns_200(
    client: httpx.Client,
    metrics: MetricsCollector,
    auth_token: Optional[str],
) -> None:
    _require_credentials()
    response = timed_request(
        client,
        "GET",
        "/stories",
        metrics,
        metrics_path="/stories(authenticated)",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200, response.text
    response.json()
    metrics.mark_check()


def test_story_text_authenticated_returns_200(
    client: httpx.Client,
    metrics: MetricsCollector,
    auth_token: Optional[str],
) -> None:
    _require_credentials()
    response = timed_request(
        client,
        "GET",
        "/stories/story-1/text",
        metrics,
        metrics_path="/stories/story-1/text(authenticated)",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200, response.text
    response.json()
    metrics.mark_check()


@pytest.mark.parametrize(
    "path",
    [
        "/stories/story-1/cover",
        "/stories/story-1/pages/1/image",
        "/stories/story-1/pages/1/audio",
        "/stories/story-1/pages/2/audio",
        "/stories/story-1/outcome/audio",
    ],
)
def test_story_media_assets_return_200(
    client: httpx.Client,
    metrics: MetricsCollector,
    path: str,
) -> None:
    _require_credentials()
    response = timed_request(client, "GET", path, metrics)
    assert response.status_code == 200, f"{path} → {response.status_code}"
    metrics.mark_check()


def test_story_invalid_page_returns_400(
    client: httpx.Client,
    metrics: MetricsCollector,
) -> None:
    _require_credentials()
    response = timed_request(client, "GET", "/stories/story-1/pages/999/image", metrics)
    assert response.status_code == 400, response.text
    metrics.mark_check()


def test_stories_list_unauthenticated_returns_401(
    client: httpx.Client,
    metrics: MetricsCollector,
) -> None:
    _require_credentials()
    response = timed_request(
        client,
        "GET",
        "/stories",
        metrics,
        metrics_path="/stories[unauthenticated]",
    )
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    metrics.mark_check()


# ---------------------------------------------------------------------------
# Scan endpoint
# ---------------------------------------------------------------------------


def test_scan_unauthenticated_returns_401(
    client: httpx.Client,
    metrics: MetricsCollector,
) -> None:
    _require_credentials()
    response = timed_request(
        client,
        "POST",
        "/scan",
        metrics,
        metrics_path="/scan[unauthenticated]",
        files={"file": ("empty.png", b"", "image/png")},
    )
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    metrics.mark_check()


def test_scan_invalid_content_type_returns_400(
    client: httpx.Client,
    metrics: MetricsCollector,
    auth_token: Optional[str],
) -> None:
    _require_credentials()
    response = timed_request(
        client,
        "POST",
        "/scan",
        metrics,
        metrics_path="/scan[invalid-type]",
        headers={"Authorization": f"Bearer {auth_token}"},
        files={"file": ("sample.txt", b"not-an-image", "text/plain")},
    )
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    metrics.mark_check()


def test_scan_oversized_file_returns_400(
    client: httpx.Client,
    metrics: MetricsCollector,
    auth_token: Optional[str],
) -> None:
    _require_credentials()
    oversized = b"0" * (5 * 1024 * 1024 + 1)
    response = timed_request(
        client,
        "POST",
        "/scan",
        metrics,
        metrics_path="/scan[oversized]",
        headers={"Authorization": f"Bearer {auth_token}"},
        files={"file": ("big.jpg", oversized, "image/jpeg")},
    )
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    metrics.mark_check()


# ---------------------------------------------------------------------------
# Admin endpoint
# ---------------------------------------------------------------------------


def test_admin_cleanup_cache_returns_200(
    client: httpx.Client,
    metrics: MetricsCollector,
) -> None:
    _require_credentials()
    response = timed_request(client, "GET", "/admin/cleanup-cache", metrics)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    response.json()
    metrics.mark_check()


# ---------------------------------------------------------------------------
# Recommendations endpoint
# ---------------------------------------------------------------------------


def test_recommendations_requires_auth(
    client: httpx.Client,
    metrics: MetricsCollector,
) -> None:
    _require_credentials()
    response = timed_request(
        client,
        "POST",
        "/recommendations",
        metrics,
        metrics_path="/recommendations[unauthenticated]",
        json={"goal_id": "grow"},
    )
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    metrics.mark_check()


def test_recommendations_invalid_goal_returns_422(
    client: httpx.Client,
    metrics: MetricsCollector,
    auth_token: Optional[str],
) -> None:
    _require_credentials()
    response = timed_request(
        client,
        "POST",
        "/recommendations",
        metrics,
        metrics_path="/recommendations[invalid-goal]",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"goal_id": "invalid_goal"},
    )
    assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"
    metrics.mark_check()


@pytest.mark.parametrize("goal", ["grow", "see", "think", "fight", "feel", "strong"])
def test_recommendations_valid_goal_returns_response_shape(
    client: httpx.Client,
    metrics: MetricsCollector,
    auth_token: Optional[str],
    goal: str,
) -> None:
    _require_credentials()
    response = timed_request(
        client,
        "POST",
        "/recommendations",
        metrics,
        metrics_path=f"/recommendations[{goal}]",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"goal_id": goal, "likes": [], "dislikes": [], "blacklist": []},
    )
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    payload = response.json()
    assert "super_power_foods" in payload, payload
    assert "tiny_hero_foods" in payload, payload
    assert "try_less_foods" in payload, payload
    assert isinstance(payload["super_power_foods"], list), payload
    assert isinstance(payload["tiny_hero_foods"], list), payload
    assert isinstance(payload["try_less_foods"], list), payload

    # Each food item must have the required fields
    for section in ("super_power_foods", "tiny_hero_foods", "try_less_foods"):
        for item in payload[section]:
            assert "cn_code" in item, f"{section} item missing cn_code: {item}"
            assert "name" in item, f"{section} item missing name: {item}"
            assert "grade" in item, f"{section} item missing grade: {item}"
            assert "image_url" in item, f"{section} item missing image_url: {item}"

    metrics.mark_check()
