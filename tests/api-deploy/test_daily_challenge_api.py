"""
Daily Healthy Challenge API integration tests.

These tests are meant to run against a locally started NutriHealth API service.
Set API_BASE_URL if the service is not on the default localhost port.
"""

from __future__ import annotations

import os

import httpx
import pytest

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
TIMEOUT_SECONDS = float(os.getenv("API_TEST_TIMEOUT_SECONDS", "10"))


@pytest.fixture(scope="module")
def client() -> httpx.Client:
    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT_SECONDS) as session:
        yield session


@pytest.fixture(scope="module")
def first_task(client: httpx.Client) -> dict:
    response = client.get("/daily-challenge/next")
    assert response.status_code == 200, response.text

    payload = response.json()
    assert payload["id"] > 0
    assert payload["task_name"]
    assert payload["tips"]
    return payload


def test_health_endpoint_is_up(client: httpx.Client) -> None:
    response = client.get("/health")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["service"] == "nutrihealth-api"


def test_next_challenge_returns_task(client: httpx.Client) -> None:
    response = client.get("/daily-challenge/next")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert isinstance(payload["id"], int)
    assert payload["task_name"]
    assert payload["tips"]


def test_try_another_excludes_current_task(client: httpx.Client, first_task: dict) -> None:
    response = client.get("/daily-challenge/next", params={"exclude_id": first_task["id"]})

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["id"] != first_task["id"]
    assert payload["task_name"]
    assert payload["tips"]


def test_complete_returns_feedback(client: httpx.Client, first_task: dict) -> None:
    response = client.post("/daily-challenge/complete", json={"id": first_task["id"]})

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["id"] == first_task["id"]
    assert payload["task_name"] == first_task["task_name"]
    assert payload["feedback"]


def test_complete_returns_404_for_missing_task(client: httpx.Client) -> None:
    response = client.post("/daily-challenge/complete", json={"id": 999999})

    assert response.status_code == 404
    payload = response.json()
    assert "not found" in payload["detail"].lower()
