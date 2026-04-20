import pytest

from app.services import seed


class FakeResult:
    def __init__(self, row=None):
        self._row = row

    def first(self):
        return self._row


class FakeDB:
    def __init__(self):
        self.calls = []
        self.committed = 0
        self.rolled_back = 0
        self.next_row = None

    def execute(self, stmt, params=None):
        self.calls.append((str(stmt), params))
        return FakeResult(self.next_row)

    def commit(self):
        self.committed += 1

    def rollback(self):
        self.rolled_back += 1


def test_chunk_rows_splits_batches():
    rows = [{"id": i} for i in range(5)]
    chunks = list(seed._chunk_rows(rows, chunk_size=2))

    assert len(chunks) == 3
    assert chunks[0] == [{"id": 0}, {"id": 1}]
    assert chunks[2] == [{"id": 4}]


def test_validate_identifiers_rejects_unknown_table_and_unsafe_column():
    with pytest.raises(ValueError):
        seed._validate_identifiers("unknown_table", ["id"])

    with pytest.raises(ValueError):
        seed._validate_identifiers(seed.TABLE_INSERT_ORDER[0], ["safe", "bad-column!"])


def test_has_seed_been_initialized_true_false(monkeypatch):
    db = FakeDB()
    monkeypatch.setattr(seed, "_ensure_init_state_table", lambda _db: None)

    db.next_row = (1,)
    assert seed.has_seed_been_initialized(db, "key-1") is True

    db.next_row = None
    assert seed.has_seed_been_initialized(db, "key-2") is False


def test_mark_seed_initialized_executes_upsert(monkeypatch):
    db = FakeDB()
    monkeypatch.setattr(seed, "_ensure_init_state_table", lambda _db: None)

    seed.mark_seed_initialized(db, "key-1", init_value="done")

    assert db.committed == 1
    assert any("INSERT INTO app_init_state" in sql for sql, _ in db.calls)


def test_seed_catalog_tables_happy_path(monkeypatch):
    db = FakeDB()

    def fake_load(table_name):
        if table_name == "daily_healthy_challenge":
            return [{"id": 1, "task_name": "Strong Bone Milk", "tips": "Drink your milk today!", "feedback": "Your bones are getting hard as rocks!"}]
        if table_name == "cn_ctgnme":
            return [{"ctgcd": "A", "ctgnm": "Fruit"}]
        return []

    monkeypatch.setattr(seed, "_load_seed_table", fake_load)

    counts = seed.seed_catalog_tables(db, truncate_before_load=False)

    assert counts["daily_healthy_challenge"] == 1
    assert counts["cn_ctgnme"] == 1
    assert counts["cn_gpcnme"] == 0
    assert db.committed == 1
    assert any("INSERT INTO daily_healthy_challenge" in sql for sql, _ in db.calls)
    assert any("INSERT INTO cn_ctgnme" in sql for sql, _ in db.calls)


def test_seed_catalog_tables_rolls_back_on_error(monkeypatch):
    db = FakeDB()

    def bad_load(_table_name):
        raise RuntimeError("boom")

    monkeypatch.setattr(seed, "_load_seed_table", bad_load)

    with pytest.raises(RuntimeError):
        seed.seed_catalog_tables(db, truncate_before_load=False)

    assert db.rolled_back == 1
