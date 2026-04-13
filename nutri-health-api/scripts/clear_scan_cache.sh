#!/usr/bin/env bash
# =============================================================================
# 清理 scan 结果缓存
#
# 【两种模式】
# 1) 默认：调用 GET /admin/cleanup-cache — 仅删除「已过期」的缓存条目。
# 2) --all：直接清空数据库表 scan_cache（含未过期），便于重复测同一张图。
#    需要本机已用 docker compose 启动，且在 nutri-health-api 目录下执行，
#    且容器名为 nutrihealth-db（见 docker-compose.yml）。
#
# 用法:
#   chmod +x scripts/clear_scan_cache.sh
#   ./scripts/clear_scan_cache.sh              # 只清过期
#   ./scripts/clear_scan_cache.sh --all        # 清空全部 scan 缓存
#
# 环境变量:
#   BASE_URL  默认 http://127.0.0.1:8000
# =============================================================================
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

if [[ "${1:-}" == "--all" ]]; then
  echo ">>> 清空表 scan_cache（需 docker compose 已启动，且在项目根目录执行）"
  if ! command -v docker &>/dev/null; then
    echo "未找到 docker 命令" >&2
    exit 1
  fi
  docker compose exec -T db psql -U nutrihealth -d nutrihealth -c "DELETE FROM scan_cache;"
  echo ">>> 完成。"
  exit 0
fi

echo ">>> GET $BASE_URL/admin/cleanup-cache （仅删除过期条目）"
curl -sS "${BASE_URL}/admin/cleanup-cache" | python3 -m json.tool
