# Seed and ETL Input Layout

Put files in the following folders.

## 1) Raw source JSON (your original data)
- Path: data/raw/
- Keep the original filename from source systems.
- Do not manually rename keys yet.

## 2) Mapping and transform rules
- Path: data/mapping/
- Put lookup tables, key mapping, enum mapping, and value normalization rules here.

## 3) Staging outputs (cleaned intermediate data)
- Path: data/staging/
- ETL scripts write normalized intermediate JSON here.

## 4) Final seed payloads (database-ready)
- Path: data/seed/
- ETL scripts write final JSON for DB initialization here.

## 5) ETL code
- Path: app/etl/
- Put transform scripts here, for example:
  - app/etl/transform_raw_to_staging.py
  - app/etl/build_seed_payload.py

## Commands
Run from nutri-health-api/:

1. Build seed payloads from raw files
```bash
python -m app.etl.build_seed_payload
```

2. Load generated seed files into PostgreSQL
```bash
export DATABASE_URL='postgresql+psycopg2://USER:PASSWORD@HOST:5432/DBNAME'
python -m app.etl.seed_db
```

3. Run SQL verification check
```bash
docker compose exec -T db psql -U nutrihealth -d nutrihealth -f - < app/etl/sql/check_seed_counts.sql
```

4. Generate anomaly report files for PR
```bash
export DATABASE_URL='postgresql+psycopg2://USER:PASSWORD@HOST:5432/DBNAME'
python -m app.etl.generate_anomaly_report
```

Outputs:
- `data/staging/anomaly_report.json`
- `data/staging/anomaly_report.md`

5. Default startup init behavior
- On startup, service always runs table init (`create_all`).
- By default, startup does not import seed data (`SEED_ON_STARTUP=false`).
- After first successful seed, marker `app_init_state.init_key=cn2026_v1` is stored.
- Next startups skip seed automatically if marker exists.
- If no seed data is loaded, change the startup config and restart the service to trigger a one-time import.

Relevant env vars:
- `SEED_ON_STARTUP` default `false`
- `SEED_KEY` default `cn2026_v1`
- `SEED_TRUNCATE_BEFORE_LOAD` default `false`
- `SEED_FORCE_RELOAD` default `false` (set `true` to force reseed)

## Suggested next input from you
1. Database design (tables, columns, types, constraints, unique keys, foreign keys).
2. One or more sample raw JSON files in data/raw/.
3. Business rules for computed keys and derived fields.
