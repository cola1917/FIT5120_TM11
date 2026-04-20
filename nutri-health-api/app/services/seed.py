"""
Seed service for loading prepared catalog data into PostgreSQL.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

SEED_DIR = Path(__file__).resolve().parents[2] / "data" / "seed"

TABLE_INSERT_ORDER = [
    "daily_healthy_challenge",
    "cn_ctgnme",
    "cn_gpcnme",
    "cn_nutdes",
    "cn_fdes",
    "cn_nutval",
    "cn_wght",
    "cn_food_tags",
    "remote_alternative",
]

TABLE_TRUNCATE_ORDER = [
    "remote_alternative",
    "cn_food_tags",
    "cn_wght",
    "cn_nutval",
    "cn_fdes",
    "cn_nutdes",
    "cn_gpcnme",
    "cn_ctgnme",
    "daily_healthy_challenge",
]

INIT_STATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS app_init_state (
    init_key TEXT PRIMARY KEY,
    init_value TEXT NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
)
"""


def _load_seed_table(table_name: str) -> list[dict[str, Any]]:
    file_path = SEED_DIR / f"{table_name}.json"
    if not file_path.exists():
        logger.warning("Seed file not found for table %s at %s", table_name, file_path)
        return []

    with file_path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)

    if not isinstance(payload, list):
        raise ValueError(f"Seed file for {table_name} must contain a JSON array")

    return payload


def _chunk_rows(rows: list[dict[str, Any]], chunk_size: int = 2000):
    for i in range(0, len(rows), chunk_size):
        yield rows[i : i + chunk_size]


_SAFE_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def _validate_identifiers(table_name: str, columns: list[str]) -> None:
    """Raise ValueError if table or column names contain unsafe characters."""
    if table_name not in TABLE_INSERT_ORDER:
        raise ValueError(f"Unknown seed table: {table_name!r}")
    for col in columns:
        if not _SAFE_IDENTIFIER_RE.match(col):
            raise ValueError(f"Unsafe column identifier {col!r} in table {table_name!r}")


def _ensure_init_state_table(db: Session) -> None:
    db.execute(text(INIT_STATE_TABLE_SQL))
    db.commit()


def has_seed_been_initialized(db: Session, seed_key: str) -> bool:
    """Check whether a seed key has already been marked as completed."""
    _ensure_init_state_table(db)
    result = db.execute(
        text("SELECT 1 FROM app_init_state WHERE init_key = :seed_key LIMIT 1"),
        {"seed_key": seed_key},
    ).first()
    return result is not None


def mark_seed_initialized(db: Session, seed_key: str, init_value: str = "completed") -> None:
    """Persist a marker so startup seeding can be skipped after first success."""
    _ensure_init_state_table(db)
    db.execute(
        text(
            """
            INSERT INTO app_init_state (init_key, init_value, updated_at)
            VALUES (:seed_key, :init_value, NOW())
            ON CONFLICT (init_key)
            DO UPDATE SET init_value = EXCLUDED.init_value, updated_at = NOW()
            """
        ),
        {"seed_key": seed_key, "init_value": init_value},
    )
    db.commit()


def seed_catalog_tables(db: Session, truncate_before_load: bool = True) -> dict[str, int]:
    """
    Load generated JSON seed files into remote catalog tables.
    """
    table_counts: dict[str, int] = {}

    try:
        if truncate_before_load:
            for table in TABLE_TRUNCATE_ORDER:
                db.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))

        for table in TABLE_INSERT_ORDER:
            rows = _load_seed_table(table)
            table_counts[table] = len(rows)

            if not rows:
                continue

            columns = list(rows[0].keys())
            _validate_identifiers(table, columns)
            columns_sql = ", ".join(columns)
            values_sql = ", ".join(f":{col}" for col in columns)
            insert_sql = text(f"INSERT INTO {table} ({columns_sql}) VALUES ({values_sql})")

            for chunk in _chunk_rows(rows):
                db.execute(insert_sql, chunk)

        db.commit()
        logger.info("Catalog seed completed: %s", table_counts)
        return table_counts

    except Exception:
        db.rollback()
        raise
