#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
reports_dir="$(cd "$script_dir/.." && pwd)"
history_dir="$reports_dir/history"
repo_root="$(cd "$reports_dir/../.." && pwd)"
artifacts_dir="$reports_dir/artifacts"
whitebox_metrics_json="$artifacts_dir/whitebox_metrics.json"
api_metrics_json="$artifacts_dir/api_metrics.json"

mkdir -p "$history_dir"

report_id="${TEST_REPORT_ID:-$(date -u +%Y-%m-%d_%H-%M-%S)}"
report_time="${TEST_REPORT_TIME:-$(date -u '+%Y-%m-%d %H:%M:%S UTC')}"
commit_sha="${TEST_COMMIT_SHA:-$(git -C "$repo_root" rev-parse --short HEAD 2>/dev/null || echo unknown)}"
branch_name="${TEST_BRANCH_NAME:-$(git -C "$repo_root" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)}"
trigger_source="${TEST_TRIGGER_SOURCE:-manual}"
execution_environment="${TEST_EXECUTION_ENVIRONMENT:-Local Dev Server}"
api_base_url="${TEST_API_BASE_URL:-}"
if [[ -z "$api_base_url" ]]; then
  api_base_url="https://fit5120-tm11.onrender.com"
fi

output_file="$history_dir/${report_id}.md"
if [[ -e "$output_file" ]]; then
  suffix=2
  while [[ -e "$history_dir/${report_id}_$suffix.md" ]]; do
    suffix=$((suffix + 1))
  done
  output_file="$history_dir/${report_id}_$suffix.md"
fi

python3 - <<'PY' "$output_file" "$report_id" "$report_time" "$commit_sha" "$branch_name" "$trigger_source" "$execution_environment" "$api_base_url" "$whitebox_metrics_json" "$api_metrics_json"
import json
import os
import sys

(
    output_file,
    report_id,
    report_time,
    commit_sha,
    branch_name,
    trigger_source,
    execution_environment,
    api_base_url,
    whitebox_metrics_json,
    api_metrics_json,
) = sys.argv[1:11]


def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


wb = load_json(whitebox_metrics_json)
api = load_json(api_metrics_json)

coverage = wb.get("coverage_percent")
if isinstance(coverage, (int, float)):
    coverage_text = f"{coverage:.2f}% Line Coverage (app package)."
else:
    coverage_text = "N/A (run whitebox script first)."

wb_pass_rate = wb.get("pass_rate_percent")
wb_pass_rate_text = (
    f"{wb.get('tests_passed', 0)}/{wb.get('tests_total', 0)} ({wb_pass_rate:.2f}%)"
    if isinstance(wb_pass_rate, (int, float))
    else "N/A"
)

endpoint_coverage = api.get("endpoint_coverage", [])
endpoint_text = ", ".join(endpoint_coverage) if endpoint_coverage else "N/A (run api smoke script first)."

status_distribution = api.get("status_distribution", {})
if status_distribution:
    status_text = ", ".join([f"{k}: {v}" for k, v in status_distribution.items()])
else:
    status_text = "N/A"

success_rate = api.get("status_success_2xx_rate_percent")
success_rate_text = f"{success_rate:.2f}% 2xx responses" if isinstance(success_rate, (int, float)) else "N/A"

avg_ms = api.get("avg_latency_ms")
p95_ms = api.get("p95_latency_ms")
perf_text = (
    f"Avg: {avg_ms}ms / P95: {p95_ms}ms (current run)."
    if isinstance(avg_ms, (int, float)) and isinstance(p95_ms, (int, float))
    else "N/A"
)

api_pass_rate = api.get("pass_rate_percent")
api_pass_rate_text = (
    f"{api.get('checks_passed', 0)}/{api.get('checks_total', 0)} ({api_pass_rate:.2f}%)"
    if isinstance(api_pass_rate, (int, float))
    else "N/A"
)

lines = [
    f"# Test Report - {report_id}",
    "",
    "## Meta",
    "",
    f"- Report Time: {report_time}",
    f"- Commit SHA: {commit_sha}",
    f"- Branch: {branch_name}",
    f"- Trigger Source: {trigger_source}",
    f"- Execution Environment: {execution_environment}",
    f"- API Base URL: {api_base_url}",
    "",
    "## White-box Summary",
    "",
    "| Metric | Description | Current Run |",
    "| --- | --- | --- |",
    f"| Test Scope | Core modules/functions under test. | {wb.get('test_scope', 'N/A')} |",
    f"| Tooling | Testing framework and tools. | {wb.get('tooling', 'N/A')} |",
    f"| Code Coverage | Line coverage of app package. | {coverage_text} |",
    f"| Execution Environment | Runtime environment. | {execution_environment} |",
    f"| Edge Case Logic | Boundary value handling. | {wb.get('edge_case_logic', 'N/A')} |",
    "",
    "## API Test Summary",
    "",
    "| Metric | Description | Current Run |",
    "| --- | --- | --- |",
    f"| Endpoint Coverage | Endpoints under test. | {endpoint_text} |",
    f"| Status Code Distribution | HTTP response distribution. | {status_text} ({success_rate_text}) |",
    f"| Performance (P95) | P95 latency percentile. | {perf_text} |",
    f"| Data Integrity | Data consistency validation. | {api.get('data_integrity', 'N/A')} |",
    f"| Resilience (Weak Net) | Weak network resilience. | {api.get('resilience', 'N/A')} |",
    "",
    "## Additional Quality Metrics",
    "",
    "| Metric | Description | Current Run |",
    "| --- | --- | --- |",
    f"| Test Pass Rate (White-box) | White-box test pass rate. | {wb_pass_rate_text} |",
    f"| Test Pass Rate (API) | API smoke test pass rate. | {api_pass_rate_text} |",
    f"| White-box Runtime | White-box execution time. | {wb.get('duration_seconds', 'N/A')} seconds |",
    "| Flaky Test Count | Unstable test count. | N/A (not tracked in this run) |",
    "| Regression Count | Regressions introduced. | N/A (not tracked in this run) |",
    "",
    "## Risks and Next Actions",
    "",
    "- Risks:",
    "- Blockers:",
    "- Next actions:",
]

with open(output_file, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
PY

echo "Generated report: $output_file"