#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
artifacts_dir="$repo_root/tests/reports/artifacts"
mkdir -p "$artifacts_dir"

cov_json="$artifacts_dir/whitebox_coverage.json"
junit_xml="$artifacts_dir/whitebox_junit.xml"
metrics_json="$artifacts_dir/whitebox_metrics.json"

export PYTHONPATH="$repo_root/nutri-health-api${PYTHONPATH:+:$PYTHONPATH}"
pytest "$repo_root/tests/whitebox" -q \
	--cov="$repo_root/nutri-health-api/app" \
  --cov-report="json:$cov_json" \
  --junitxml="$junit_xml"

python3 - <<'PY' "$cov_json" "$junit_xml" "$metrics_json"
import json
import sys
import xml.etree.ElementTree as ET

cov_path, junit_path, metrics_path = sys.argv[1:4]

with open(cov_path, "r", encoding="utf-8") as f:
	cov = json.load(f)

testsuite = ET.parse(junit_path).getroot()
if testsuite.tag == "testsuites":
	suites = testsuite.findall("testsuite")
else:
	suites = [testsuite]

total = sum(int(s.attrib.get("tests", 0)) for s in suites)
failures = sum(int(s.attrib.get("failures", 0)) for s in suites)
errors = sum(int(s.attrib.get("errors", 0)) for s in suites)
skipped = sum(int(s.attrib.get("skipped", 0)) for s in suites)
passed = max(total - failures - errors - skipped, 0)
pass_rate = (passed / total * 100) if total else 0.0
duration = sum(float(s.attrib.get("time", 0.0)) for s in suites)

metrics = {
	"test_scope": "app package (auth, rules, cache, stories, token router)",
	"tooling": "Pytest, Pytest-cov",
	"coverage_percent": cov.get("totals", {}).get("percent_covered", 0.0),
	"coverage_display": cov.get("totals", {}).get("percent_covered_display", "0"),
	"tests_total": total,
	"tests_passed": passed,
	"tests_failed": failures + errors,
	"tests_skipped": skipped,
	"pass_rate_percent": round(pass_rate, 2),
	"duration_seconds": duration,
	"edge_case_logic": "Invalid credentials, JWT failures, cache expiry, and story lookup errors",
}

with open(metrics_path, "w", encoding="utf-8") as f:
	json.dump(metrics, f, ensure_ascii=True, indent=2)
PY
