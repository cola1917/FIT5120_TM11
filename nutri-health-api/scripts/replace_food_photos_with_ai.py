#!/usr/bin/env python3
"""Replace selected food photos with locally cached AI-generated food images."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
DATA_JSON = ROOT / "data" / "processed" / "clean_food_metadata.json"
IDS_TXT = ROOT / "data" / "processed" / "food_photo_ai_replacement_ids.txt"
REPORT_JSON = ROOT / "data" / "processed" / "food_photo_ai_replacement_report.json"
REVIEW_HTML = ROOT / "food_photo_review_ai_replaced.html"
PHOTO_DIR = ROOT / "static" / "food_photos"
BACKUP_DIR = ROOT / "static" / "food_photos_ai_replaced_backup"


def load_records(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array in {path}")
    return data


def save_records(path: Path, records: list[dict[str, Any]]) -> None:
    temp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    temp.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for attempt in range(5):
        try:
            temp.replace(path)
            return
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.5)


def food_name(record: dict[str, Any]) -> str:
    for key in ("display_name", "food_name", "raw_name", "name"):
        value = record.get(key)
        if value:
            return str(value)
    return str(record.get("food_id", "food"))


def read_ids(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def prompt_for(record: dict[str, Any]) -> str:
    name = food_name(record)
    return (
        f"Realistic studio food photography of {name}, showing only the edible food itself, "
        "centered on a plain white background, square composition, clean soft lighting, "
        "single target food subject, appetizing but simple, no text, no labels, no logo, "
        "no packaging, no hands, no people, no utensils unless essential to recognize the food"
    )


def pollinations_url(prompt: str, seed: str, size: int) -> str:
    encoded = urllib.parse.quote(prompt)
    return (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?model=flux&width={size}&height={size}&nologo=true&seed={seed}"
    )


def download_image(url: str, timeout: int) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "nutri-health-photo-replacer/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("Content-Type", "")
        if not content_type.startswith("image/"):
            raise ValueError(f"Unexpected Content-Type {content_type}")
        return response.read()


def write_square_jpg(image_bytes: bytes, output: Path, size: int, quality: int) -> None:
    temp = output.with_suffix(".tmp.jpg")
    with Image.open(io.BytesIO(image_bytes)) as image:
        image = ImageOps.exif_transpose(image).convert("RGB")
        image = ImageOps.fit(image, (size, size), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
        image.save(temp, "JPEG", quality=quality, optimize=True)
    temp.replace(output)


def html_escape(value: Any) -> str:
    return (
        str(value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def write_review(entries: list[dict[str, Any]]) -> None:
    cards = []
    for entry in entries:
        src = str(entry["image_url"]).lstrip("/")
        cards.append(
            f"""
    <article class="card">
      <img src="{html_escape(src)}" alt="{html_escape(entry['name'])}" loading="lazy">
      <div class="meta">
        <strong>{html_escape(entry['name'])}</strong>
        <span>ID: {html_escape(entry['food_id'])}</span>
        <span>Source: ai_generated</span>
        <span>Prompt: {html_escape(entry['prompt'])}</span>
      </div>
    </article>"""
        )

    REVIEW_HTML.write_text(
        f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Food Photo Review - AI Replaced</title>
<style>
  body {{ font-family: Arial, sans-serif; margin: 24px; background: #f6f7f9; color: #17202a; }}
  h1 {{ font-size: 24px; margin: 0 0 8px; }}
  p {{ margin: 0 0 18px; color: #586273; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 16px; }}
  .card {{ background: #fff; border: 1px solid #a7c3e8; border-radius: 8px; overflow: hidden; }}
  img {{ width: 100%; aspect-ratio: 1 / 1; object-fit: cover; display: block; background: #fff; }}
  .meta {{ padding: 10px 12px 12px; display: grid; gap: 4px; font-size: 13px; }}
  .meta strong {{ font-size: 15px; }}
  .meta span {{ color: #586273; overflow-wrap: anywhere; }}
</style>
</head>
<body>
<h1>Food Photo Review - AI Replaced</h1>
<p>Showing {len(entries)} manually selected replacements. All images are local 384x384 JPG files.</p>
<section class="grid">
{''.join(cards)}
</section>
</body>
</html>
""",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids-file", type=Path, default=IDS_TXT)
    parser.add_argument("--size", type=int, default=384)
    parser.add_argument("--quality", type=int, default=85)
    parser.add_argument("--sleep", type=float, default=1.0)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--force", action="store_true", help="Regenerate records already marked as ai_generated")
    args = parser.parse_args()

    records = load_records(DATA_JSON)
    by_id = {str(record.get("food_id")): record for record in records}
    ids = read_ids(args.ids_file)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_run_dir = BACKUP_DIR / timestamp
    entries: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    if args.apply:
        PHOTO_DIR.mkdir(parents=True, exist_ok=True)
        backup_run_dir.mkdir(parents=True, exist_ok=True)

    for food_id in ids:
        record = by_id.get(food_id)
        if not record:
            errors.append({"food_id": food_id, "error": "food_id not found"})
            continue
        if record.get("image_source") == "ai_generated" and not args.force:
            continue

        name = food_name(record)
        prompt = prompt_for(record)
        seed = hashlib.sha256(f"{food_id}:{name}".encode("utf-8")).hexdigest()[:12]
        url = pollinations_url(prompt, seed, args.size)

        try:
            if args.apply:
                output = PHOTO_DIR / f"{food_id}.jpg"
                if output.exists():
                    shutil.copy2(output, backup_run_dir / output.name)

                image_bytes = download_image(url, args.timeout)
                write_square_jpg(image_bytes, output, args.size, args.quality)

                record["image_url"] = f"/static/food_photos/{food_id}.jpg"
                record["image_source"] = "ai_generated"
                record["image_license"] = "ai_generated"
                record["image_photographer"] = "AI generated"
                record["image_photographer_url"] = ""
                record["image_original_url"] = url
                record["image_source_id"] = seed
                record["image_query"] = name
                record["image_alt"] = f"AI-generated food photo of {name}"
                record["image_match_confidence"] = "manual_ai"
                record["image_status"] = "ready"
                save_records(DATA_JSON, records)

            entries.append(
                {
                    "food_id": food_id,
                    "name": name,
                    "prompt": prompt,
                    "image_url": f"/static/food_photos/{food_id}.jpg",
                    "seed": seed,
                }
            )
            time.sleep(args.sleep)
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            errors.append({"food_id": food_id, "name": name, "error": str(exc)})

    report = {
        "apply": args.apply,
        "requested": len(ids),
        "updated": len(entries) if args.apply else 0,
        "previewed": len(entries),
        "errors": errors,
        "backup_dir": str(backup_run_dir) if args.apply else None,
        "review_html": str(REVIEW_HTML) if args.apply else None,
        "entries": entries,
    }

    if args.apply:
        save_records(DATA_JSON, records)
        REPORT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        write_review(entries)

    print(json.dumps({k: v for k, v in report.items() if k != "entries"}, indent=2, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
