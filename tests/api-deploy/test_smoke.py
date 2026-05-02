"""
API Smoke Tests — pytest-based replacement for api_smoke_test.sh.

These tests run against a deployed or locally running NutriHealth API.
No authentication credentials are required for most checks; authenticated
checks are skipped gracefully when API_USERNAME / API_PASSWORD are absent.

Assertions mirror those in the original shell script:
  - / returns 200 with {name, status}
  - /health returns 200 with {status, service}
  - Public story media assets return 200
  - Protected story endpoints return 401 without a token
  - /scan without auth returns 401
  - With a valid token: /stories returns 200, /scan empty-file returns 400

Metrics (endpoint paths, status distribution, latency) are collected via the
session-scoped ``metrics`` fixture defined in conftest.py and written to
``tests/reports/artifacts/api_metrics.json`` after the session finishes.
"""

from __future__ import annotations

from typing import Optional

import httpx
import pytest

from metrics_collector import MetricsCollector
from conftest import timed_request

# ---------------------------------------------------------------------------
# Root and health
# ---------------------------------------------------------------------------


def test_root_returns_api_info(client: httpx.Client, metrics: MetricsCollector) -> None:
    response = timed_request(client, "GET", "/", metrics)
    assert response.status_code == 200, response.text

    payload = response.json()
    assert payload.get("name") == "NutriHealth API", payload
    assert payload.get("status") == "running", payload

    metrics.mark_check()


def test_health_endpoint_returns_healthy(client: httpx.Client, metrics: MetricsCollector) -> None:
    response = timed_request(client, "GET", "/health", metrics)
    assert response.status_code == 200, response.text

    payload = response.json()
    assert payload.get("status") == "healthy", payload
    assert payload.get("service") == "nutrihealth-api", payload

    metrics.mark_check()


# ---------------------------------------------------------------------------
# Public story media assets (no auth required)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "/stories/story-1/cover",
        "/stories/story-1/pages/1/image",
        "/stories/story-1/pages/1/audio",
        "/stories/story-1/outcome/audio",
    ],
)
def test_public_story_asset_returns_200(
    client: httpx.Client,
    metrics: MetricsCollector,
    path: str,
) -> None:
    response = timed_request(client, "GET", path, metrics)
    assert response.status_code == 200, f"{path} → {response.status_code}: {response.text}"
    metrics.mark_check()


# ---------------------------------------------------------------------------
# Error / auth-required story paths
# ---------------------------------------------------------------------------


def test_invalid_story_page_returns_400(client: httpx.Client, metrics: MetricsCollector) -> None:
    response = timed_request(client, "GET", "/stories/story-1/pages/999/image", metrics)
    assert response.status_code == 400, response.text
    metrics.mark_check()


def test_stories_list_requires_auth(client: httpx.Client, metrics: MetricsCollector) -> None:
    response = timed_request(client, "GET", "/stories", metrics)
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    metrics.mark_check()


def test_story_text_requires_auth(client: httpx.Client, metrics: MetricsCollector) -> None:
    response = timed_request(client, "GET", "/stories/story-1/text", metrics)
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    metrics.mark_check()


def test_scan_requires_auth(client: httpx.Client, metrics: MetricsCollector) -> None:
    response = timed_request(
        client,
        "POST",
        "/scan",
        metrics,
        files={"file": ("empty.png", b"", "image/png")},
    )
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    metrics.mark_check()


# ---------------------------------------------------------------------------
# Authenticated checks (skipped when no credentials are configured)
# ---------------------------------------------------------------------------


def test_authenticated_stories_list_returns_200(
    client: httpx.Client,
    metrics: MetricsCollector,
    auth_token: Optional[str],
) -> None:
    if not auth_token:
        pytest.skip("API_USERNAME / API_PASSWORD not configured; skipping authenticated check")

    metrics.set_auth_checks_skipped(False)
    response = timed_request(
        client,
        "GET",
        "/stories",
        metrics,
        metrics_path="/stories(authenticated)",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200, response.text
    assert response.json().get("stories"), response.json()
    metrics.mark_check()


def test_authenticated_scan_empty_file_returns_400(
    client: httpx.Client,
    metrics: MetricsCollector,
    auth_token: Optional[str],
) -> None:
    if not auth_token:
        pytest.skip("API_USERNAME / API_PASSWORD not configured; skipping authenticated check")

    metrics.set_auth_checks_skipped(False)
    response = timed_request(
        client,
        "POST",
        "/scan",
        metrics,
        metrics_path="/scan(authenticated)",
        headers={"Authorization": f"Bearer {auth_token}"},
        files={"file": ("empty.png", b"", "image/png")},
    )
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    metrics.mark_check()

