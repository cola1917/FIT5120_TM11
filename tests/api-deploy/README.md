# API Deploy & Smoke Tests

Place deployment smoke checks and API integration probes here.

Suites:
- `api_smoke_test.sh`: light checks that keep running without auth creds.
- `api_regression_test.sh`: heavier checks that require auth creds but avoid OpenAI calls.

Recommended order in CI:
1. smoke
2. regression (push/manual only)

Planned checks:
- API starts successfully
- /health returns healthy status
- basic auth-required endpoint behavior is correct
- daily challenge endpoints return tasks, support exclude_id, and return completion feedback

Notes:
- Token and authenticated scan checks run only when API_USERNAME/API_PASSWORD are supplied.
- Health and unauthorized scan checks always run against the configured API base URL.
