import importlib
import sys
from datetime import datetime, timedelta


class FakeQuery:
    def __init__(self, entry=None, entries=None):
        self.entry = entry
        self.entries = entries or []

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.entry

    def all(self):
        return list(self.entries)


class FakeDB:
    def __init__(self, entry=None, entries=None):
        self.entry = entry
        self.entries = entries or []
        self.added = []
        self.deleted = []
        self.committed = False
        self.rolled_back = False

    def query(self, model):
        return FakeQuery(entry=self.entry, entries=self.entries)

    def add(self, item):
        self.added.append(item)

    def delete(self, item):
        self.deleted.append(item)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


def load_cache_module(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:password@localhost:5432/nutrihealth")

    for module_name in ["app.services.cache", "app.models.cache", "app.database"]:
        sys.modules.pop(module_name, None)

    import app.database as database_module
    import app.models.cache as cache_model
    import app.services.cache as cache_module
    return cache_module


def test_hash_image_is_deterministic(monkeypatch):
    cache_module = load_cache_module(monkeypatch)

    assert cache_module.hash_image(b"abc") == cache_module.hash_image(b"abc")
    assert cache_module.hash_image(b"abc") != cache_module.hash_image(b"abcd")


def test_get_cached_result_returns_cached_payload(monkeypatch):
    cache_module = load_cache_module(monkeypatch)
    entry = cache_module.ScanCache(image_hash="hash", response_data={"foo": "bar"}, ttl_days=1)
    db = FakeDB(entry=entry)

    assert cache_module.get_cached_result(db, "hash") == {"foo": "bar"}


def test_get_cached_result_deletes_expired_entry(monkeypatch):
    cache_module = load_cache_module(monkeypatch)
    entry = cache_module.ScanCache(image_hash="hash", response_data={"foo": "bar"}, ttl_days=1)
    entry.expires_at = datetime.utcnow() - timedelta(minutes=1)
    db = FakeDB(entry=entry)

    assert cache_module.get_cached_result(db, "hash") is None
    assert db.deleted == [entry]
    assert db.committed is True


def test_cache_result_creates_and_updates_entries(monkeypatch):
    cache_module = load_cache_module(monkeypatch)

    create_db = FakeDB(entry=None)
    assert cache_module.cache_result(create_db, "hash-1", {"ok": True}, ttl_days=2) is True
    assert len(create_db.added) == 1

    existing = cache_module.ScanCache(image_hash="hash-1", response_data={"ok": False}, ttl_days=1)
    update_db = FakeDB(entry=existing)
    assert cache_module.cache_result(update_db, "hash-1", {"ok": True}, ttl_days=2) is True
    assert existing.response_data == {"ok": True}
    assert update_db.committed is True


def test_cleanup_expired_cache_removes_only_expired_rows(monkeypatch):
    cache_module = load_cache_module(monkeypatch)
    expired = cache_module.ScanCache(image_hash="expired", response_data={"ok": False}, ttl_days=1)
    expired.expires_at = datetime.utcnow() - timedelta(minutes=1)

    db = FakeDB(entries=[expired])
    assert cache_module.cleanup_expired_cache(db) == 1
    assert db.deleted == [expired]
    assert db.committed is True