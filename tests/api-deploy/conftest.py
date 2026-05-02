"""
Shared pytest fixtures for API deploy integration tests.

Configuration environment variables
------------------------------------
API_BASE_URL        Base URL of the deployed API (default: http://127.0.0.1:8000)
API_USERNAME        Username for obtaining a JWT bearer token (optional)
API_PASSWORD        Password for obtaining a JWT bearer token (optional)
API_TEST_TIMEOUT_SECONDS  Per-request timeout in seconds (default: 60)
API_TEST_RETRIES  Retry count for transient network timeouts/errors (default: 2)
MOCK_AI             Set to "true" or "1" to enable deterministic AI mock on the
                    server side (the server must support this flag).
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Iterator, Optional

import httpx
import pytest

# ---------------------------------------------------------------------------
# Ensure the api-deploy directory is importable regardless of how pytest is
# invoked so that metrics_collector.py can be imported without a package name.
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from metrics_collector import MetricsCollector  # noqa: E402

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL: str = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
TIMEOUT: float = float(os.getenv("API_TEST_TIMEOUT_SECONDS", "60"))
RETRIES: int = int(os.getenv("API_TEST_RETRIES", "2"))
_USERNAME: Optional[str] = os.getenv("API_USERNAME") or os.getenv("DEMO_USERNAME")
_PASSWORD: Optional[str] = os.getenv("API_PASSWORD") or os.getenv("DEMO_PASSWORD")

# ---------------------------------------------------------------------------
# Session-scoped HTTP client
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL


@pytest.fixture(scope="session")
def client() -> Iterator[httpx.Client]:
    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as session:
        yield session


# ---------------------------------------------------------------------------
# Auth token (skipped gracefully when no credentials are configured)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def auth_token(client: httpx.Client) -> Optional[str]:
    """
    Obtain a JWT bearer token using the configured credentials.

    Returns ``None`` (and marks no test as skipped) when credentials are absent;
    tests that need a token should call ``pytest.skip`` themselves if the token
    is ``None``.
    """
    if not _USERNAME or not _PASSWORD:
        return None

    response = request_with_retries(
        client,
        "POST",
        "/token",
        data={"username": _USERNAME, "password": _PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200, (
        f"Token request failed ({response.status_code}): {response.text}"
    )
    return response.json()["access_token"]


@pytest.fixture(scope="session")
def auth_headers(auth_token: Optional[str]) -> dict:
    """Return Authorization headers ready to pass to httpx requests."""
    if auth_token:
        return {"Authorization": f"Bearer {auth_token}"}
    return {}


# ---------------------------------------------------------------------------
# Metrics collector (session-scoped so all tests share one instance)
# ---------------------------------------------------------------------------

_session_metrics: Optional[MetricsCollector] = None


@pytest.fixture(scope="session")
def metrics() -> MetricsCollector:
    global _session_metrics
    _session_metrics = MetricsCollector()
    return _session_metrics


# ---------------------------------------------------------------------------
# Write metrics JSON after the whole session completes
# ---------------------------------------------------------------------------


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """
    Hook called by pytest after all tests finish.

    Writes ``tests/reports/artifacts/api_metrics.json`` with the accumulated
    probe telemetry so that CI can upload it as an artifact.
    """
    if _session_metrics is not None:
        _session_metrics.write_json(BASE_URL)


# ---------------------------------------------------------------------------
# Helper used by both smoke and regression tests
# ---------------------------------------------------------------------------


def request_with_retries(
    client: httpx.Client,
    method: str,
    url: str,
    **kwargs,
) -> httpx.Response:
    """
    Send an HTTP request with small retries for transient deploy/network issues.

    The deployed API can occasionally cold-start or hit a short network stall in
    CI. Retrying only when no response is received keeps status-code assertions
    meaningful while reducing flaky failures.
    """
    last_error: httpx.HTTPError | None = None

    for attempt in range(RETRIES + 1):
        try:
            return client.request(method, url, **kwargs)
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            last_error = exc
            if attempt >= RETRIES:
                raise
            time.sleep(2**attempt)

    raise RuntimeError("Request retry loop exited unexpectedly") from last_error


def timed_request(
    client: httpx.Client,
    method: str,
    url: str,
    collector: MetricsCollector,
    *,
    metrics_path: Optional[str] = None,
    **kwargs,
) -> httpx.Response:
    """Send an HTTP request, record its latency in the collector, and return it.

    ``metrics_path`` overrides the path recorded in the collector (useful for
    labelling authenticated vs unauthenticated probes of the same endpoint).
    """
    path = metrics_path if metrics_path is not None else url
    start = time.perf_counter()
    response = request_with_retries(client, method, url, **kwargs)
    elapsed_ms = (time.perf_counter() - start) * 1000
    collector.record(path, response.status_code, elapsed_ms)
    return response

