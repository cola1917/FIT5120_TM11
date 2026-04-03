"""
Load generated seed JSON files into PostgreSQL.
"""

from __future__ import annotations

import argparse
import json

from app.database import SessionLocal, init_db
from app.services.seed import seed_catalog_tables


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed catalog tables from data/seed JSON files")
    parser.add_argument(
        "--no-truncate",
        action="store_true",
        help="Do not truncate tables before loading",
    )
    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    try:
        counts = seed_catalog_tables(db, truncate_before_load=not args.no_truncate)
    finally:
        db.close()

    print(json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()
