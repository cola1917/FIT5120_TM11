# Test Report - {{REPORT_ID}}

## Meta

- Report Time: {{REPORT_TIME}}
- Commit SHA: {{COMMIT_SHA}}
- Branch: {{BRANCH_NAME}}
- Trigger Source: {{TRIGGER_SOURCE}}
- Execution Environment: {{EXECUTION_ENVIRONMENT}}
- API Base URL: {{API_BASE_URL}}

## White-box Summary

| Summary Item | Description | Example |
| --- | --- | --- |
| Test Scope | Which core modules or functions were tested. | Nutrient calculation, XP conversion, Persona filtering. |
| Tooling | Tools used for testing. | Pytest, Pytest-cov. |
| Code Coverage | Primary coverage indicator. | 87% Line Coverage (showing that most code paths were exercised). |
| Execution Environment | Environment where tests were run. | GitHub Actions (Ubuntu-latest) / Local Dev Server. |
| Edge Case Logic | How boundary and edge cases were handled. | Null inputs, Zero values, Out-of-range nutrient data. |

## API Test Summary

| Summary Item | Description | Example |
| --- | --- | --- |
| Endpoint Coverage | Which endpoints were tested. | /auth/login, /food/scan, /goals/recommend. |
| Status Code Distribution | Distribution of response statuses. | 100% 200/201 Success Rate. |
| Performance (P95) | User-perceived latency. | Avg: 180ms / P95: 320ms (measured from Android Client). |
| Data Integrity | Data consistency validation. | JSON schema matches the design; no missing fields. |
| Resilience (Weak Net) | Behavior under poor network conditions. | Simulated 3G: 100% sync success with retry logic. |

## Additional Quality Metrics

| Metric | Description | Example |
| --- | --- | --- |
| Test Pass Rate | Overall test pass rate. | 132/135 (97.8%). |
| Flaky Test Count | Number of recently unstable test cases. | 2 flaky tests in last 10 runs. |
| Regression Count | Number of regressions introduced in this run. | 0 known regressions. |
| Security Gate | Summary of dependency and image security checks. | 0 Critical, 1 High vulnerability. |
| Contract Drift | API contract deviation status. | 0 schema drift in 24 endpoints. |
| Retry Success Rate | Effectiveness of retry mechanisms. | 98.6% recovered after retry. |
| Error Budget Consumption | Error budget usage. | 18% of monthly budget consumed. |

## Risks and Next Actions

- Risks:
- Blockers:
- Next actions:
