import asyncio
from types import SimpleNamespace

import pytest

from app.routers import auth as auth_router


def test_login_returns_token_when_credentials_are_valid(monkeypatch):
    monkeypatch.setattr(auth_router, "authenticate_user", lambda username, password: True)
    monkeypatch.setattr(auth_router, "create_access_token", lambda data: "token-123")

    result = asyncio.run(auth_router.login(SimpleNamespace(username="demo", password="demo123")))

    assert result == {"access_token": "token-123", "token_type": "bearer"}


def test_login_rejects_invalid_credentials(monkeypatch):
    monkeypatch.setattr(auth_router, "authenticate_user", lambda username, password: False)

    with pytest.raises(auth_router.HTTPException) as exc_info:
        asyncio.run(auth_router.login(SimpleNamespace(username="demo", password="wrong")))

    assert exc_info.value.status_code == 401