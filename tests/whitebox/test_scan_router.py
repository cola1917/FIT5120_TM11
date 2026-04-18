import io
import importlib
import asyncio

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers


def load_scan_module(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:password@localhost:5432/nutrihealth")
    import app.routers.scan as scan_module
    return importlib.reload(scan_module)


def test_is_recognised_logic(monkeypatch):
    scan_module = load_scan_module(monkeypatch)

    assert scan_module._is_recognised({"confidence": 0.8, "food_name": "Apple"}) is True
    assert scan_module._is_recognised({"confidence": 0.0, "food_name": "Apple"}) is False
    assert scan_module._is_recognised({"confidence": 0.8, "food_name": "food item"}) is False


def test_get_food_image_url_encodes_name(monkeypatch):
    scan_module = load_scan_module(monkeypatch)

    url = scan_module.get_food_image_url("Apple Pie")

    assert "Apple%20Pie" in url
    assert url.startswith("https://image.pollinations.ai/prompt/")


def test_scan_food_rejects_invalid_content_type(monkeypatch):
    scan_module = load_scan_module(monkeypatch)

    upload = UploadFile(filename="file.txt", file=io.BytesIO(b"abc"), headers=Headers({"content-type": "text/plain"}))

    with pytest.raises(scan_module.HTTPException) as exc:
        asyncio.run(scan_module.scan_food(file=upload, db=object(), current_user={"username": "demo"}))

    assert exc.value.status_code == 400
    assert "Invalid file type" in exc.value.detail


def test_scan_food_rejects_empty_payload(monkeypatch):
    scan_module = load_scan_module(monkeypatch)

    upload = UploadFile(filename="empty.jpg", file=io.BytesIO(b""), headers=Headers({"content-type": "image/jpeg"}))

    with pytest.raises(scan_module.HTTPException) as exc:
        asyncio.run(scan_module.scan_food(file=upload, db=object(), current_user={"username": "demo"}))

    assert exc.value.status_code == 400
    assert "Empty file uploaded" in exc.value.detail
