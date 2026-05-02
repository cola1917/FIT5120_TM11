"""
Metrics collector for API deploy integration tests.

Provides a thread-safe collector that records probe data (path, status code,
latency) from pytest tests and writes a ``api_metrics.json`` artifact in the
same format previously produced by the shell-based smoke / regression scripts.
"""

from __future__ import annotations

import json
import math
import os
import threading
import time
from pathlib import Path
from typing import Dict, List


_ARTIFACTS_DIR = Path(__file__).parent.parent / "reports" / "artifacts"


class MetricsCollector:
    """Accumulate per-request telemetry and persist to JSON when done."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._endpoint_paths: List[str] = []
        self._latency_ms: List[float] = []
        self._status_counts: Dict[str, int] = {}
        self._checks_total: int = 0
        self._checks_passed: int = 0
        self._auth_checks_skipped: bool = True

    # ------------------------------------------------------------------
    # Recording helpers
    # ------------------------------------------------------------------

    def record(self, path: str, status: int, latency_ms: float) -> None:
        """Record a single HTTP probe."""
        with self._lock:
            self._endpoint_paths.append(path)
            self._latency_ms.append(latency_ms)
            key = str(status)
            self._status_counts[key] = self._status_counts.get(key, 0) + 1

    def mark_check(self, passed: bool = True) -> None:
        with self._lock:
            self._checks_total += 1
            if passed:
                self._checks_passed += 1

    def set_auth_checks_skipped(self, skipped: bool) -> None:
        with self._lock:
            self._auth_checks_skipped = skipped

    # ------------------------------------------------------------------
    # Context-manager helper for timing a single request
    # ------------------------------------------------------------------

    class _Timer:
        def __init__(self, collector: "MetricsCollector", path: str) -> None:
            self._collector = collector
            self._path = path
            self._start: float = 0.0
            self.status: int = 0

        def __enter__(self) -> "MetricsCollector._Timer":
            self._start = time.perf_counter()
            return self

        def __exit__(self, *_args: object) -> None:
            elapsed_ms = (time.perf_counter() - self._start) * 1000
            if self.status:
                self._collector.record(self._path, self.status, elapsed_ms)

    def probe(self, path: str) -> "MetricsCollector._Timer":
        return self._Timer(self, path)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self, base_url: str) -> dict:
        latencies = sorted(self._latency_ms)
        avg_ms = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
        if latencies:
            idx = max(math.ceil(0.95 * len(latencies)) - 1, 0)
            p95_ms = round(latencies[idx], 2)
        else:
            p95_ms = 0.0

        status_dist = dict(sorted(self._status_counts.items(), key=lambda kv: int(kv[0])))
        status_total = sum(status_dist.values())
        success_2xx = sum(v for k, v in status_dist.items() if k.startswith("2"))
        success_rate = round(success_2xx / status_total * 100, 2) if status_total else 0.0
        pass_rate = round(self._checks_passed / self._checks_total * 100, 2) if self._checks_total else 0.0

        resilience = (
            "Authenticated and negative-path routes verified with no OpenAI calls"
            if not self._auth_checks_skipped
            else "Authenticated paths skipped (no credentials)"
        )

        return {
            "base_url": base_url,
            "endpoint_coverage": sorted(set(self._endpoint_paths)),
            "status_distribution": status_dist,
            "status_success_2xx_rate_percent": success_rate,
            "avg_latency_ms": avg_ms,
            "p95_latency_ms": p95_ms,
            "checks_total": self._checks_total,
            "checks_passed": self._checks_passed,
            "pass_rate_percent": pass_rate,
            "data_integrity": "health payload, root payload, and public stories assets verified",
            "resilience": resilience,
            "auth_checks_skipped": self._auth_checks_skipped,
        }

    def write_json(self, base_url: str, output_path: Path | None = None) -> Path:
        """Write metrics JSON and return the path."""
        if output_path is None:
            output_path = _ARTIFACTS_DIR / "api_metrics.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        data = self.to_dict(base_url)
        output_path.write_text(json.dumps(data, ensure_ascii=True, indent=2), encoding="utf-8")
        return output_path
