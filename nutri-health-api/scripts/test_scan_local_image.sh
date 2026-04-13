#!/usr/bin/env bash
# =============================================================================
# 本地图片扫描测试 — 查看响应里是否包含 alternatives[].image_url
#
# 【行为说明 / 何时会有 alternatives】
# 1. 需要先识别出食物：vision 模型返回的 confidence、food_name 会决定 recognised。
# 2. 仅当 recognised 为 true 且 RAG（FAISS 向量库）加载成功时，才会走 RAG + 改写，并填充 alternatives。
# 3. 每个 alternative 的 image_url 由服务端生成（Pollinations 等 URL），不是「你上传的那张图」的缩略图；
#    用于展示「替代食物」的示意图。
# 4. 若命中 scan 缓存，会直接返回旧 JSON，不会重新算 alternatives；测试前可用 clear_scan_cache.sh 清缓存。
#
# 用法:
#   chmod +x scripts/test_scan_local_image.sh
#   ./scripts/test_scan_local_image.sh
#   ./scripts/test_scan_local_image.sh /path/to/photo.jpg
#
# 环境变量:
#   BASE_URL  默认 http://127.0.0.1:8000
# =============================================================================
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
IMAGE_PATH="${1:-/Users/zbh_1111/Desktop/WechatIMG456.jpg}"

if [[ ! -f "$IMAGE_PATH" ]]; then
  echo "文件不存在: $IMAGE_PATH" >&2
  exit 1
fi

echo ">>> POST $BASE_URL/token (demo / demo123)"
TOKEN_JSON=$(curl -sS -X POST "${BASE_URL}/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=demo&password=demo123")

TOKEN=$(echo "$TOKEN_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo ">>> POST $BASE_URL/scan (multipart: file)"
RESP=$(curl -sS -X POST "${BASE_URL}/scan" \
  -H "Authorization: Bearer ${TOKEN}" \
  -F "file=@${IMAGE_PATH};type=image/jpeg")

echo "$RESP" | python3 -m json.tool

echo
echo ">>> alternatives 摘要（若有）:"
echo "$RESP" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
except Exception as e:
    print('(解析 JSON 失败)', e)
    sys.exit(0)
alts = data.get('alternatives')
if not alts:
    print('  (无 alternatives：可能未识别、RAG 未就绪、或走了缓存旧结果)')
else:
    for i, a in enumerate(alts, 1):
        name = a.get('name', '?')
        url = a.get('image_url', '')
        print(f'  [{i}] {name}')
        print(f'      image_url: {url}')
"
