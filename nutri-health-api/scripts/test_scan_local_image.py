#!/usr/bin/env python3
"""
上传本地图片调用 POST /scan，查看是否返回 alternatives[].image_url。

依赖：仅标准库（urllib / json / os）。

用法:
  python3 scripts/test_scan_local_image.py
  python3 scripts/test_scan_local_image.py /path/to/photo.jpg

环境变量:
  BASE_URL  默认 http://127.0.0.1:8000
"""
from __future__ import annotations

import json
import mimetypes
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid


def _post_form_token(base_url: str) -> str:
    data = urllib.parse.urlencode(
        {"username": "demo", "password": "demo123"}
    ).encode()
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/token",
        data=data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read().decode())
    return body["access_token"]


def _post_multipart_scan(base_url: str, token: str, image_path: str) -> dict:
    boundary = f"----NutriBoundary{uuid.uuid4().hex}"
    filename = os.path.basename(image_path)
    ctype = mimetypes.guess_type(image_path)[0] or "application/octet-stream"
    with open(image_path, "rb") as f:
        file_bytes = f.read()

    part_header = (
        f'--{boundary}\r\n'
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {ctype}\r\n\r\n"
    ).encode("utf-8")
    part_footer = f"\r\n--{boundary}--\r\n".encode("utf-8")
    body = part_header + file_bytes + part_footer

    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/scan",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    base_url = os.environ.get("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    default_img = "/Users/zbh_1111/Desktop/WechatIMG456.jpg"
    image_path = sys.argv[1] if len(sys.argv) > 1 else default_img

    if not os.path.isfile(image_path):
        print(f"文件不存在: {image_path}", file=sys.stderr)
        return 1

    try:
        print(f">>> POST {base_url}/token (demo / demo123)")
        token = _post_form_token(base_url)
        print(f">>> POST {base_url}/scan")
        data = _post_multipart_scan(base_url, token, image_path)
    except urllib.error.HTTPError as e:
        err = e.read().decode(errors="replace")
        print(f"HTTP {e.code}: {err}", file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"请求失败: {e.reason}", file=sys.stderr)
        return 1

    print(json.dumps(data, indent=2, ensure_ascii=False))

    print()
    print(">>> alternatives 摘要（若有）:")
    alts = data.get("alternatives")
    if not alts:
        print("  (无 alternatives：可能未识别、RAG 未就绪、或走了缓存旧结果)")
    else:
        for i, a in enumerate(alts, 1):
            name = a.get("name", "?")
            url = a.get("image_url", "")
            print(f"  [{i}] {name}")
            print(f"      image_url: {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
