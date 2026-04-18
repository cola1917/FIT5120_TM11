#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
artifacts_dir="$repo_root/tests/reports/artifacts"
mkdir -p "$artifacts_dir"
metrics_json="$artifacts_dir/api_metrics.json"

base_url="${API_BASE_URL:-https://fit5120-tm11.onrender.com}"
username="${API_USERNAME:-}"
password="${API_PASSWORD:-}"

if [[ -z "$username" || -z "$password" ]]; then
  echo "API_USERNAME and API_PASSWORD are required for the regression suite." >&2
  exit 1
fi

declare -a endpoint_paths=()
declare -a latency_ms=()
declare -A status_counts=()
checks_total=0
checks_passed=0

response_body=""
response_status=""
response_time_ms="0"

record_probe() {
  local path="$1"
  local status="$2"
  local time_ms="$3"
  endpoint_paths+=("$path")
  latency_ms+=("$time_ms")
  status_counts["$status"]=$(( ${status_counts["$status"]:-0} + 1 ))
}

mark_check() {
  checks_total=$((checks_total + 1))
  checks_passed=$((checks_passed + 1))
}

request_json() {
  local method="$1"
  local url="$2"
  shift 2

  local output
  output="$(curl -sS -w '\n%{http_code}\n%{time_total}' -X "$method" "$url" "$@")"
  response_body="$(printf '%s\n' "$output" | sed '$d' | sed '$d')"
  response_status="$(printf '%s\n' "$output" | tail -n 2 | head -n 1)"
  response_time_ms="$(python3 - <<'PY' "$output"
import sys
text = sys.argv[1].splitlines()
print(int(float(text[-1]) * 1000))
PY
)"
}

probe_request() {
  local method="$1"
  local url="$2"
  shift 2

  local output
  output="$(curl -sS -o /dev/null -w '%{http_code}\n%{time_total}' -X "$method" "$url" "$@")"
  response_status="$(printf '%s\n' "$output" | tail -n 2 | head -n 1)"
  response_time_ms="$(python3 - <<'PY' "$output"
import sys
text = sys.argv[1].splitlines()
print(int(float(text[-1]) * 1000))
PY
)"
}

check_json_body() {
  python3 - <<'PY' "$1"
import json, sys
json.loads(sys.argv[1])
PY
}

check_root_and_health() {
  request_json GET "$base_url/"
  record_probe "/" "$response_status" "$response_time_ms"
  if [[ "$response_status" != "200" ]]; then
    echo "Root check failed with status $response_status" >&2
    echo "$response_body" >&2
    exit 1
  fi
  check_json_body "$response_body"
  mark_check

  request_json GET "$base_url/health"
  record_probe "/health" "$response_status" "$response_time_ms"
  if [[ "$response_status" != "200" ]]; then
    echo "Health check failed with status $response_status" >&2
    echo "$response_body" >&2
    exit 1
  fi
  check_json_body "$response_body"
  mark_check
}

check_token_endpoints() {
  request_json POST "$base_url/token" -H 'Content-Type: application/x-www-form-urlencoded' -d 'username=wrong-user&password=wrong-pass'
  record_probe "/token[invalid]" "$response_status" "$response_time_ms"
  if [[ "$response_status" != "401" ]]; then
    echo "Invalid token request should return 401, got $response_status" >&2
    echo "$response_body" >&2
    exit 1
  fi
  mark_check

  request_json POST "$base_url/token" -H 'Content-Type: application/x-www-form-urlencoded' -d "username=$username&password=$password"
  record_probe "/token[valid]" "$response_status" "$response_time_ms"
  if [[ "$response_status" != "200" ]]; then
    echo "Valid token request failed with status $response_status" >&2
    echo "$response_body" >&2
    exit 1
  fi
  check_json_body "$response_body"
  token="$(python3 - <<'PY' "$response_body"
import json, sys
print(json.loads(sys.argv[1])["access_token"])
PY
)"
  if [[ -z "$token" ]]; then
    echo "Access token was empty" >&2
    exit 1
  fi
  mark_check
}

check_protected_story_routes() {
  local token="$1"

  request_json GET "$base_url/stories" -H "Authorization: Bearer $token"
  record_probe "/stories(authenticated)" "$response_status" "$response_time_ms"
  if [[ "$response_status" != "200" ]]; then
    echo "Authenticated stories list failed with status $response_status" >&2
    echo "$response_body" >&2
    exit 1
  fi
  check_json_body "$response_body"
  mark_check

  request_json GET "$base_url/stories/story-1/text" -H "Authorization: Bearer $token"
  record_probe "/stories/story-1/text(authenticated)" "$response_status" "$response_time_ms"
  if [[ "$response_status" != "200" ]]; then
    echo "Authenticated story text failed with status $response_status" >&2
    echo "$response_body" >&2
    exit 1
  fi
  check_json_body "$response_body"
  mark_check

  probe_request GET "$base_url/stories/story-1/cover"
  record_probe "/stories/story-1/cover" "$response_status" "$response_time_ms"
  if [[ "$response_status" != "200" ]]; then
    echo "Story cover failed with status $response_status" >&2
    exit 1
  fi
  mark_check

  probe_request GET "$base_url/stories/story-1/pages/1/image"
  record_probe "/stories/story-1/pages/1/image" "$response_status" "$response_time_ms"
  if [[ "$response_status" != "200" ]]; then
    echo "Story page image failed with status $response_status" >&2
    exit 1
  fi
  mark_check

  probe_request GET "$base_url/stories/story-1/pages/1/audio"
  record_probe "/stories/story-1/pages/1/audio" "$response_status" "$response_time_ms"
  if [[ "$response_status" != "200" ]]; then
    echo "Story page-1 audio failed with status $response_status" >&2
    exit 1
  fi
  mark_check

  probe_request GET "$base_url/stories/story-1/pages/2/audio"
  record_probe "/stories/story-1/pages/2/audio" "$response_status" "$response_time_ms"
  if [[ "$response_status" != "200" ]]; then
    echo "Story page-2 audio fallback failed with status $response_status" >&2
    exit 1
  fi
  mark_check

  probe_request GET "$base_url/stories/story-1/outcome/audio"
  record_probe "/stories/story-1/outcome/audio" "$response_status" "$response_time_ms"
  if [[ "$response_status" != "200" ]]; then
    echo "Story outcome audio failed with status $response_status" >&2
    exit 1
  fi
  mark_check

  probe_request GET "$base_url/stories/story-1/pages/999/image"
  record_probe "/stories/story-1/pages/999/image" "$response_status" "$response_time_ms"
  if [[ "$response_status" != "400" ]]; then
    echo "Invalid story page should return 400, got $response_status" >&2
    exit 1
  fi
  mark_check

  probe_request GET "$base_url/stories"
  record_probe "/stories[unauthenticated]" "$response_status" "$response_time_ms"
  if [[ "$response_status" != "401" ]]; then
    echo "Protected stories list without token should return 401, got $response_status" >&2
    exit 1
  fi
  mark_check
}

check_scan_and_admin_routes() {
  local token="$1"
  local invalid_file oversized_file

  probe_request POST "$base_url/scan" -F 'file=@/dev/null;type=image/png;filename=empty.png'
  record_probe "/scan[unauthenticated]" "$response_status" "$response_time_ms"
  if [[ "$response_status" != "401" ]]; then
    echo "Unauthorized scan should return 401, got $response_status" >&2
    exit 1
  fi
  mark_check

  invalid_file="$(mktemp)"
  printf 'not-an-image' > "$invalid_file"
  probe_request POST "$base_url/scan" -H "Authorization: Bearer $token" -F "file=@$invalid_file;type=text/plain;filename=sample.txt"
  record_probe "/scan[invalid-type]" "$response_status" "$response_time_ms"
  rm -f "$invalid_file"
  if [[ "$response_status" != "400" ]]; then
    echo "Invalid type scan should return 400, got $response_status" >&2
    exit 1
  fi
  mark_check

  oversized_file="$(mktemp)"
  python3 - <<'PY' "$oversized_file"
import sys
from pathlib import Path
Path(sys.argv[1]).write_bytes(b'0' * (5 * 1024 * 1024 + 1))
PY
  probe_request POST "$base_url/scan" -H "Authorization: Bearer $token" -F "file=@$oversized_file;type=image/jpeg;filename=big.jpg"
  record_probe "/scan[oversized]" "$response_status" "$response_time_ms"
  rm -f "$oversized_file"
  if [[ "$response_status" != "400" ]]; then
    echo "Oversized scan should return 400, got $response_status" >&2
    exit 1
  fi
  mark_check

  request_json GET "$base_url/admin/cleanup-cache"
  record_probe "/admin/cleanup-cache" "$response_status" "$response_time_ms"
  if [[ "$response_status" != "200" ]]; then
    echo "Cleanup cache should return 200, got $response_status" >&2
    echo "$response_body" >&2
    exit 1
  fi
  check_json_body "$response_body"
  mark_check
}

write_metrics() {
  local status_json endpoint_json avg_ms p95_ms status_total success_2xx endpoint_lines status_lines
  endpoint_lines=""
  status_lines=""

  if [[ ${#endpoint_paths[@]} -gt 0 ]]; then
    endpoint_lines="$(printf '%s\n' "${endpoint_paths[@]}")"
    endpoint_json="$(python3 - <<'PY' "$endpoint_lines"
import json
import sys
paths = [line.strip() for line in sys.argv[1].splitlines() if line.strip()]
print(json.dumps(sorted(set(paths))))
PY
)"
  else
    endpoint_json="[]"
  fi

  if [[ ${#status_counts[@]} -gt 0 ]]; then
    status_lines="$(for k in "${!status_counts[@]}"; do echo "$k ${status_counts[$k]}"; done)"
    status_json="$(python3 - <<'PY' "$status_lines"
import json
import sys
items = {}
for line in sys.argv[1].splitlines():
    line = line.strip()
    if not line:
        continue
    code, count = line.split()
    items[code] = int(count)
print(json.dumps(dict(sorted(items.items(), key=lambda x: int(x[0])))))
PY
)"
  else
    status_json="{}"
  fi

  avg_ms="$(python3 - <<'PY' "${latency_ms[*]}"
import sys
values = [int(v) for v in sys.argv[1].split() if v]
print(round(sum(values) / len(values), 2) if values else 0.0)
PY
)"

  p95_ms="$(python3 - <<'PY' "${latency_ms[*]}"
import math
import sys
values = sorted(int(v) for v in sys.argv[1].split() if v)
if not values:
    print(0)
else:
    idx = max(math.ceil(0.95 * len(values)) - 1, 0)
    print(values[idx])
PY
)"

  status_total="$(python3 - <<'PY' "$status_json"
import json
import sys
payload = json.loads(sys.argv[1])
print(sum(payload.values()))
PY
)"

  success_2xx="$(python3 - <<'PY' "$status_json"
import json
import sys
payload = json.loads(sys.argv[1])
print(sum(count for code, count in payload.items() if str(code).startswith('2')))
PY
)"

  python3 - <<'PY' "$metrics_json" "$base_url" "$checks_total" "$checks_passed" "$endpoint_json" "$status_json" "$avg_ms" "$p95_ms" "$status_total" "$success_2xx"
import json
import sys

out_path = sys.argv[1]
base_url = sys.argv[2]
checks_total = int(sys.argv[3])
checks_passed = int(sys.argv[4])
endpoint_coverage = json.loads(sys.argv[5])
status_distribution = json.loads(sys.argv[6])
avg_latency_ms = float(sys.argv[7])
p95_latency_ms = int(sys.argv[8])
status_total = int(sys.argv[9])
success_2xx = int(sys.argv[10])

success_rate = round((success_2xx / status_total) * 100, 2) if status_total else 0.0
pass_rate = round((checks_passed / checks_total) * 100, 2) if checks_total else 0.0

metrics = {
    "base_url": base_url,
    "endpoint_coverage": endpoint_coverage,
    "status_distribution": status_distribution,
    "status_success_2xx_rate_percent": success_rate,
    "avg_latency_ms": avg_latency_ms,
    "p95_latency_ms": p95_latency_ms,
    "checks_total": checks_total,
    "checks_passed": checks_passed,
    "pass_rate_percent": pass_rate,
    "data_integrity": "root, health, auth, stories, scan validation, and admin cleanup verified",
    "resilience": "Authenticated and negative-path routes verified with no OpenAI calls",
    "auth_checks_skipped": False,
}

with open(out_path, "w", encoding="utf-8") as f:
    json.dump(metrics, f, ensure_ascii=True, indent=2)
PY
}

check_root_and_health
check_token_endpoints
token="$token"
check_protected_story_routes "$token"
check_scan_and_admin_routes "$token"
write_metrics

echo "API regression tests passed for $base_url"
