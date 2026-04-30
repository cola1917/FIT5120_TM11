# API Deploy & Smoke Tests

Integration tests that run against a deployed or locally started NutriHealth API.

## Test suites

| File | Purpose | Auth required |
|---|---|---|
| `test_smoke.py` | Light checks that keep passing without auth credentials. Mirrors `api_smoke_test.sh`. | No (authenticated checks skipped gracefully) |
| `test_regression.py` | Heavier checks: full auth flow, protected story routes, scan error paths, recommendations shape. Mirrors `api_regression_test.sh`. | Yes (`API_USERNAME` + `API_PASSWORD`) |
| `test_daily_challenge_api.py` | Daily healthy challenge endpoint integration tests. | No |

## Configuration

| Variable | Default | Description |
|---|---|---|
| `API_BASE_URL` | `http://127.0.0.1:8000` | Base URL of the NutriHealth API |
| `API_USERNAME` | — | Username for token auth (optional for smoke, required for regression) |
| `API_PASSWORD` | — | Password for token auth |
| `API_TEST_TIMEOUT_SECONDS` | `30` | Per-request timeout in seconds |
| `MOCK_AI` | `false` | Set to `true` / `1` to enable deterministic AI mock on the server (no paid API calls) |

## Running locally

```bash
# Install dependencies
pip install -r tests/api-deploy/requirements.txt

# Smoke tests (no credentials needed)
API_BASE_URL=https://fit5120-tm11.onrender.com \
  python -m pytest tests/api-deploy/test_smoke.py tests/api-deploy/test_daily_challenge_api.py -v

# Regression tests (credentials required)
API_BASE_URL=https://fit5120-tm11.onrender.com \
API_USERNAME=demo \
API_PASSWORD=secret \
  python -m pytest tests/api-deploy/test_regression.py -v
```

## Metrics artifact

After a test session the shared conftest writes
`tests/reports/artifacts/api_metrics.json` containing:
- `endpoint_coverage` – sorted list of all probed paths
- `status_distribution` – HTTP status code counts
- `avg_latency_ms` / `p95_latency_ms` – latency statistics
- `checks_total` / `checks_passed` / `pass_rate_percent`
- `auth_checks_skipped` – whether authenticated paths were exercised

This file is uploaded as a CI artifact and referenced in the generated markdown report.

## CI recommended order

1. `api-smoke` (push, PR, manual)
2. `api-regression` (push / manual only, not on PRs)

## Shell scripts (legacy)

`scripts/api_smoke_test.sh` and `scripts/api_regression_test.sh` are retained
for reference but are no longer used by CI. The pytest suites above are the
canonical test runner.
