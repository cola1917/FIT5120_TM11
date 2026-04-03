"""Generate anomaly report files from seeded PostgreSQL data."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import text

from app.database import engine

BASE_DIR = Path(__file__).resolve().parents[2]
STAGING_DIR = BASE_DIR / "data" / "staging"


def fetch_one(sql: str) -> dict:
    with engine.connect() as conn:
        row = conn.execute(text(sql)).mappings().first()
        return dict(row) if row else {}


def fetch_many(sql: str) -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(text(sql)).mappings().all()
        return [dict(r) for r in rows]


def build_report() -> dict:
    summary = fetch_one(
        """
        SELECT
          (SELECT COUNT(*) FROM cn_fdes) AS total_foods,
          (SELECT COUNT(*) FROM cn_nutval) AS total_nutvals,
          (SELECT COUNT(*) FROM cn_wght) AS total_weights,
          (SELECT COUNT(*) FROM remote_alternative) AS total_alternatives,
          (SELECT COUNT(*) FROM cn_nutval WHERE nutrient_value < 0) AS negative_nutrient_values,
          (SELECT COUNT(*) FROM cn_nutval WHERE nutrient_code IN (203,204,205,269,291,605,606) AND nutrient_value > 100) AS gram_over_100,
          (SELECT COUNT(*) FROM cn_nutval WHERE nutrient_code = 208 AND nutrient_value > 900) AS energy_over_900_kcal,
          (SELECT COUNT(*) FROM cn_nutval WHERE nutrient_code = 307 AND nutrient_value > 5000) AS sodium_over_5000_mg,
          (SELECT COUNT(*) FROM cn_wght WHERE amount <= 0 OR unit_amount <= 0) AS non_positive_weight_rows,
          (SELECT COUNT(*) FROM cn_fdes WHERE gtin IS NOT NULL AND NOT (gtin ~ '^[0-9]+$')) AS gtin_non_numeric,
          (SELECT COUNT(*) FROM cn_fdes WHERE gtin IS NOT NULL AND length(gtin) NOT IN (8,12,13,14)) AS gtin_unusual_length,
          (SELECT COUNT(*) FROM remote_alternative r JOIN cn_fdes o ON o.cn_code=r.original_cn_code JOIN cn_fdes s ON s.cn_code=r.suggested_cn_code
             WHERE (CASE s.health_grade WHEN 'A' THEN 1 WHEN 'B' THEN 2 WHEN 'C' THEN 3 WHEN 'D' THEN 4 ELSE 5 END)
               >= (CASE o.health_grade WHEN 'A' THEN 1 WHEN 'B' THEN 2 WHEN 'C' THEN 3 WHEN 'D' THEN 4 ELSE 5 END)
          ) AS non_improving_alternatives
        """
    )

    details = {
        "gram_over_100_samples": fetch_many(
            """
            SELECT n.cn_code, n.nutrient_code, n.nutrient_value, f.descriptor
            FROM cn_nutval n
            JOIN cn_fdes f ON f.cn_code = n.cn_code
            WHERE n.nutrient_code IN (203,204,205,269,291,605,606)
              AND n.nutrient_value > 100
            ORDER BY n.nutrient_value DESC
            LIMIT 20
            """
        ),
        "energy_over_900_samples": fetch_many(
            """
            SELECT n.cn_code, n.nutrient_value AS kcal_per_100g, f.descriptor
            FROM cn_nutval n
            JOIN cn_fdes f ON f.cn_code = n.cn_code
            WHERE n.nutrient_code = 208
              AND n.nutrient_value > 900
            ORDER BY n.nutrient_value DESC
            LIMIT 20
            """
        ),
        "sodium_over_5000_samples": fetch_many(
            """
            SELECT n.cn_code, n.nutrient_value AS sodium_mg_per_100g, f.descriptor
            FROM cn_nutval n
            JOIN cn_fdes f ON f.cn_code = n.cn_code
            WHERE n.nutrient_code = 307
              AND n.nutrient_value > 5000
            ORDER BY n.nutrient_value DESC
            LIMIT 20
            """
        ),
        "non_positive_weight_samples": fetch_many(
            """
            SELECT cn_code, sequence_num, amount, unit_amount, measure_description
            FROM cn_wght
            WHERE amount <= 0 OR unit_amount <= 0
            ORDER BY cn_code
            LIMIT 30
            """
        ),
    }

    return {"summary": summary, "details": details}


def write_report(report: dict) -> None:
    STAGING_DIR.mkdir(parents=True, exist_ok=True)

    json_path = STAGING_DIR / "anomaly_report.json"
    md_path = STAGING_DIR / "anomaly_report.md"

    with json_path.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=True)

    s = report["summary"]
    lines = [
        "# Seed Anomaly Report",
        "",
        "## Summary",
        "",
        f"- total_foods: {s['total_foods']}",
        f"- total_nutvals: {s['total_nutvals']}",
        f"- total_weights: {s['total_weights']}",
        f"- total_alternatives: {s['total_alternatives']}",
        f"- negative_nutrient_values: {s['negative_nutrient_values']}",
        f"- gram_over_100: {s['gram_over_100']}",
        f"- energy_over_900_kcal: {s['energy_over_900_kcal']}",
        f"- sodium_over_5000_mg: {s['sodium_over_5000_mg']}",
        f"- non_positive_weight_rows: {s['non_positive_weight_rows']}",
        f"- gtin_non_numeric: {s['gtin_non_numeric']}",
        f"- gtin_unusual_length: {s['gtin_unusual_length']}",
        f"- non_improving_alternatives: {s['non_improving_alternatives']}",
        "",
        "## Note",
        "",
        "Outliers are retained from source data for traceability."
    ]

    with md_path.open("w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def main() -> None:
    report = build_report()
    write_report(report)
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
