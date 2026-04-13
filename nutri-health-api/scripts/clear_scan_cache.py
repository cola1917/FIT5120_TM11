#!/usr/bin/env python3
"""
清理 scan 结果缓存。

1) 默认：GET /admin/cleanup-cache（只删已过期条目）
2) --all：通过 docker compose 在 Postgres 里 DELETE FROM scan_cache（删全部，含未过期）

依赖：仅标准库 + 本机已装 docker（仅 --all 需要）。

用法:
  python3 scripts/clear_scan_cache.py
  python3 scripts/clear_scan_cache.py --all

环境变量:
  BASE_URL  默认 http://127.0.0.1:8000
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request


def cleanup_expired_via_api(base_url: str) -> int:
    url = f"{base_url.rstrip('/')}/admin/cleanup-cache"
    print(f">>> GET {url} （仅删除过期条目）")
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.loads(resp.read().decode())
    print(json.dumps(body, indent=2, ensure_ascii=False))
    return 0


def clear_all_via_docker() -> int:
    print(
        ">>> docker compose exec db … DELETE FROM scan_cache; "
        "（需在 nutri-health-api 目录执行，且 compose 已启动）"
    )
    cmd = [
        "docker",
        "compose",
        "exec",
        "-T",
        "db",
        "psql",
        "-U",
        "nutrihealth",
        "-d",
        "nutrihealth",
        "-c",
        "DELETE FROM scan_cache;",
    ]
    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError:
        print("未找到 docker 命令", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as e:
        return e.returncode or 1
    print(">>> 完成。")
    return 0


def main() -> int:
    base_url = os.environ.get("BASE_URL", "http://127.0.0.1:8000")
    if "--all" in sys.argv:
        return clear_all_via_docker()
    return cleanup_expired_via_api(base_url)


if __name__ == "__main__":
    raise SystemExit(main())
