import importlib
import asyncio
from jose import jwt as jose_jwt
import pytest


def load_auth_module(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret")
    monkeypatch.setenv("ALGORITHM", "HS256")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_HOURS", "1")
    monkeypatch.setenv("DEMO_USERNAME", "demo")
    monkeypatch.setenv("DEMO_PASSWORD", "demo123")

    import app.auth as auth_module

    return importlib.reload(auth_module)


def test_authenticate_user_accepts_demo_credentials(monkeypatch):
    auth_module = load_auth_module(monkeypatch)

    assert auth_module.authenticate_user("demo", "demo123") is True


def test_authenticate_user_rejects_invalid_credentials(monkeypatch):
    auth_module = load_auth_module(monkeypatch)

    assert auth_module.authenticate_user("demo", "wrong") is False
    assert auth_module.authenticate_user("other", "demo123") is False


def test_create_and_decode_access_token_round_trip(monkeypatch):
    auth_module = load_auth_module(monkeypatch)

    token = auth_module.create_access_token({"sub": "demo"})
    decoded = auth_module.decode_access_token(token)

    assert decoded == {"username": "demo"}


def test_get_password_hash_and_verify_password(monkeypatch):
    auth_module = load_auth_module(monkeypatch)

    monkeypatch.setattr(auth_module.pwd_context, "hash", lambda password: f"hashed:{password}")
    monkeypatch.setattr(auth_module.pwd_context, "verify", lambda plain, hashed: hashed == f"hashed:{plain}")

    hashed = auth_module.get_password_hash("secret-pass")

    assert auth_module.verify_password("secret-pass", hashed) is True
    assert auth_module.verify_password("wrong-password", hashed) is False


def test_decode_access_token_rejects_missing_subject(monkeypatch):
    auth_module = load_auth_module(monkeypatch)

    token = jose_jwt.encode({"role": "guest"}, auth_module.SECRET_KEY, algorithm=auth_module.ALGORITHM)

    assert auth_module.decode_access_token(token) is None


def test_get_current_user_rejects_invalid_token(monkeypatch):
    auth_module = load_auth_module(monkeypatch)

    with pytest.raises(auth_module.HTTPException) as exc_info:
        asyncio.run(auth_module.get_current_user(token="not-a-valid-token"))

    assert exc_info.value.status_code == 401
