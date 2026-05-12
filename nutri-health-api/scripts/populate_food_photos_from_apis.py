"""
Populate food photos from Pexels first, then Unsplash as fallback.

Reads:
    data/processed/clean_food_metadata.json

Writes, when --apply is passed:
    data/processed/clean_food_metadata.json
    data/processed/food_photo_lookup_report.json
    static/food_photos/{food_id}.jpg              (only with --download)

Required environment variables:
    PEXELS_API_KEY
    UNSPLASH_ACCESS_KEY                           (optional fallback)

Examples:
    python scripts/populate_food_photos_from_apis.py --limit 20
    python scripts/populate_food_photos_from_apis.py --limit 20 --apply
    python scripts/populate_food_photos_from_apis.py --download --apply

By default the script only fills missing/non-real image_url values. It treats
old AI-generated Pollinations URLs as replaceable.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parent.parent
CLEAN_JSON = ROOT / "data" / "processed" / "clean_food_metadata.json"
REPORT_JSON = ROOT / "data" / "processed" / "food_photo_lookup_report.json"
PHOTO_DIR = ROOT / "static" / "food_photos"
PHOTO_SIZE = 384
JPEG_QUALITY = 85

PEXELS_SEARCH_URL = "https://api.pexels.com/v1/search"
UNSPLASH_SEARCH_URL = "https://api.unsplash.com/search/photos"

AI_GENERATED_MARKERS = (
    "image.pollinations.ai",
    "pollinations.ai",
)


class ApiError(RuntimeError):
    pass


def load_dotenv(path: Path = ROOT / ".env") -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def load_json_array(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    if not isinstance(payload, list):
        raise ValueError(f"{path} must contain a JSON array")
    return payload


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def request_json(url: str, headers: dict[str, str], timeout: int = 20) -> dict[str, Any]:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ApiError(f"HTTP {exc.code} for {url}: {body[:300]}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ApiError(f"Request failed for {url}: {exc}") from exc


def download_file(url: str, dest: Path, headers: dict[str, str] | None = None, timeout: int = 30) -> None:
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "NutriHealthBot/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        content_type = resp.headers.get("Content-Type", "")
        if "image" not in content_type:
            raise ApiError(f"Unexpected Content-Type while downloading {url}: {content_type}")
        image_bytes = resp.read()
    if len(image_bytes) < 1024:
        raise ApiError(f"Downloaded image is too small for {url}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(image_bytes)
    resize_photo(dest)


def resize_photo(path: Path, size: int = PHOTO_SIZE, quality: int = JPEG_QUALITY) -> None:
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image)
        image = ImageOps.fit(image.convert("RGB"), (size, size), method=Image.Resampling.LANCZOS)
        image.save(path, format="JPEG", quality=quality, optimize=True, progressive=True)


def clean_query_text(value: str) -> str:
    text = value.lower()
    text = re.sub(
        r"\b(recipe for schools|cn|case|count|ct|oz|onz|lb|lbs|"
        r"fully cooked|certified|gluten free|all natural ingredients)\b",
        " ",
        text,
    )
    text = re.sub(r"[^a-z0-9\s-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def food_name(record: dict[str, Any]) -> str:
    for key in ("display_name", "clean_name", "raw_name"):
        value = str(record.get(key) or "").strip()
        if value:
            return value
    return str(record.get("food_id") or "food").strip() or "food"


def build_queries(record: dict[str, Any], subject_only: bool = False) -> list[str]:
    raw_name = clean_query_text(str(record.get("raw_name") or ""))
    name = clean_query_text(food_name(record))
    clean_name = clean_query_text(str(record.get("clean_name") or ""))
    category = clean_query_text(str(record.get("clean_category") or "food"))
    sub_category = clean_query_text(str(record.get("sub_category") or ""))

    if subject_only:
        candidates = [
            f"{name} isolated",
            f"{name} on white background",
            f"{name} food close up",
            f"single {name} food item",
            name,
            f"{clean_name} isolated" if clean_name and clean_name != name else "",
            f"{clean_name} on white background" if clean_name and clean_name != name else "",
            f"{raw_name} isolated" if raw_name and raw_name != name else "",
            f"{raw_name} on white background" if raw_name and raw_name != name else "",
            f"{sub_category.replace('_', ' ')} isolated" if sub_category else "",
            f"{category} food isolated",
        ]
    else:
        candidates = [
            name,
            f"{name} food white background",
            f"{name} food isolated",
            f"{name} food",
            clean_name if clean_name and clean_name != name else "",
            f"{clean_name} food white background" if clean_name and clean_name != name else "",
            f"{clean_name} food isolated" if clean_name and clean_name != name else "",
            f"{raw_name} food white background" if raw_name and raw_name != name else "",
            f"{raw_name} food isolated" if raw_name and raw_name != name else "",
            f"{raw_name} food" if raw_name and raw_name != name else "",
            f"{sub_category.replace('_', ' ')} food white background" if sub_category else "",
            f"{sub_category.replace('_', ' ')} food" if sub_category else "",
            f"{category} food white background",
            f"{category} food",
        ]

    seen: set[str] = set()
    queries: list[str] = []
    for candidate in candidates:
        candidate = re.sub(r"\s+", " ", candidate).strip()
        if candidate and candidate not in seen:
            queries.append(candidate)
            seen.add(candidate)
    return queries


def is_replaceable_image_url(value: Any) -> bool:
    if not value:
        return True
    text = str(value)
    return any(marker in text for marker in AI_GENERATED_MARKERS)


def score_match(query: str, name: str, alt: str | None) -> str:
    haystack = f"{name} {alt or ''}".lower()
    tokens = [token for token in clean_query_text(query).split() if token != "food"]
    matched = sum(1 for token in tokens if token in haystack)
    if tokens and matched >= max(1, len(tokens) - 1):
        return "high"
    if matched:
        return "medium"
    return "low"


def pexels_search(query: str, api_key: str) -> dict[str, Any] | None:
    params_dict = {
        "query": query,
        "size": "medium",
        "locale": "en-US",
        "per_page": 15,
        "page": 1,
    }
    if "white background" in query or "on white background" in query or "isolated" in query:
        params_dict["color"] = "white"

    params = urllib.parse.urlencode(params_dict)
    payload = request_json(
        f"{PEXELS_SEARCH_URL}?{params}",
        headers={"Authorization": api_key, "User-Agent": "NutriHealthBot/1.0"},
    )
    photos = payload.get("photos") or []
    if not photos:
        return None

    photo = photos[0]
    src = photo.get("src") or {}
    return {
        "image_url": src.get("large") or src.get("medium") or src.get("original"),
        "download_url": src.get("large2x") or src.get("original") or src.get("large"),
        "image_source": "pexels",
        "image_license": "Pexels License",
        "image_photographer": photo.get("photographer"),
        "image_photographer_url": photo.get("photographer_url"),
        "image_original_url": photo.get("url"),
        "image_source_id": str(photo.get("id") or ""),
        "image_query": query,
        "image_alt": photo.get("alt"),
        "image_match_confidence": score_match(query, food_name({"display_name": photo.get("alt") or ""}), photo.get("alt")),
    }


def unsplash_track_download(download_location: str, access_key: str) -> None:
    separator = "&" if "?" in download_location else "?"
    url = f"{download_location}{separator}client_id={urllib.parse.quote(access_key)}"
    request_json(url, headers={"Accept-Version": "v1", "User-Agent": "NutriHealthBot/1.0"})


def unsplash_search(query: str, access_key: str) -> dict[str, Any] | None:
    params = urllib.parse.urlencode(
        {
            "query": query,
            "orientation": "squarish",
            "content_filter": "high",
            "per_page": 5,
            "page": 1,
        }
    )
    payload = request_json(
        f"{UNSPLASH_SEARCH_URL}?{params}",
        headers={
            "Authorization": f"Client-ID {access_key}",
            "Accept-Version": "v1",
            "User-Agent": "NutriHealthBot/1.0",
        },
    )
    results = payload.get("results") or []
    if not results:
        return None

    photo = results[0]
    urls = photo.get("urls") or {}
    links = photo.get("links") or {}
    user = photo.get("user") or {}
    return {
        "image_url": urls.get("regular") or urls.get("small") or urls.get("raw"),
        "download_url": urls.get("regular") or urls.get("full") or urls.get("raw"),
        "unsplash_download_location": links.get("download_location"),
        "image_source": "unsplash",
        "image_license": "Unsplash License",
        "image_photographer": user.get("name"),
        "image_photographer_url": user.get("links", {}).get("html"),
        "image_original_url": links.get("html"),
        "image_source_id": str(photo.get("id") or ""),
        "image_query": query,
        "image_alt": photo.get("alt_description") or photo.get("description"),
        "image_match_confidence": score_match(query, food_name({"display_name": photo.get("alt_description") or ""}), photo.get("description")),
    }


def find_photo(
    record: dict[str, Any],
    pexels_key: str | None,
    unsplash_key: str | None,
    sleep_seconds: float,
    subject_only: bool,
) -> dict[str, Any] | None:
    for query in build_queries(record, subject_only=subject_only):
        if pexels_key:
            photo = pexels_search(query, pexels_key)
            time.sleep(sleep_seconds)
            if photo and photo.get("image_url"):
                return photo

        if unsplash_key:
            photo = unsplash_search(query, unsplash_key)
            time.sleep(sleep_seconds)
            if photo and photo.get("image_url"):
                return photo

    return None


def apply_photo(record: dict[str, Any], photo: dict[str, Any], download: bool, unsplash_key: str | None) -> None:
    image_url = photo["image_url"]
    if download:
        food_id = str(record.get("food_id") or "").strip() or clean_query_text(food_name(record)).replace(" ", "_")
        dest = PHOTO_DIR / f"{food_id}.jpg"

        if photo.get("image_source") == "unsplash" and photo.get("unsplash_download_location") and unsplash_key:
            unsplash_track_download(photo["unsplash_download_location"], unsplash_key)

        download_file(photo["download_url"] or image_url, dest)
        image_url = f"/static/food_photos/{dest.name}"

    record["image_url"] = image_url
    for key in (
        "image_source",
        "image_license",
        "image_photographer",
        "image_photographer_url",
        "image_original_url",
        "image_source_id",
        "image_query",
        "image_alt",
        "image_match_confidence",
    ):
        record[key] = photo.get(key)


def main() -> int:
    parser = argparse.ArgumentParser(description="Populate food photos from Pexels and Unsplash.")
    parser.add_argument("--input", type=Path, default=CLEAN_JSON)
    parser.add_argument("--apply", action="store_true", help="Write changes to disk")
    parser.add_argument("--overwrite", action="store_true", help="Replace all existing image_url values")
    parser.add_argument("--download", action="store_true", help="Download images into static/food_photos and store local /static URLs")
    parser.add_argument("--subject-only", action="store_true", help="Prefer isolated/close-up single-food images over lifestyle photos")
    parser.add_argument("--limit", type=int, default=None, help="Process only the first N eligible records")
    parser.add_argument("--sleep", type=float, default=0.25, help="Delay between API calls to reduce rate-limit risk")
    args = parser.parse_args()

    load_dotenv()
    pexels_key = os.getenv("PEXELS_API_KEY")
    unsplash_key = os.getenv("UNSPLASH_ACCESS_KEY")
    if not pexels_key and not unsplash_key:
        raise EnvironmentError("Set PEXELS_API_KEY and/or UNSPLASH_ACCESS_KEY before running this script.")

    records = load_json_array(args.input)
    report: dict[str, Any] = {
        "input": str(args.input),
        "apply": args.apply,
        "download": args.download,
        "processed": 0,
        "updated": 0,
        "skipped_existing": 0,
        "not_found": 0,
        "rate_limited": False,
        "stopped_reason": None,
        "errors": [],
        "low_confidence": [],
        "preview": [],
    }

    for record in records:
        if args.limit is not None and report["processed"] >= args.limit:
            break

        if not args.overwrite and not is_replaceable_image_url(record.get("image_url")):
            report["skipped_existing"] += 1
            continue

        report["processed"] += 1
        try:
            photo = find_photo(record, pexels_key, unsplash_key, args.sleep, args.subject_only)
            if not photo:
                record["image_status"] = "not_found"
                report["not_found"] += 1
                continue

            apply_photo(record, photo, args.download, unsplash_key)
            record["image_status"] = "ready"
            report["updated"] += 1

            entry = {
                "food_id": record.get("food_id"),
                "name": food_name(record),
                "source": photo.get("image_source"),
                "confidence": photo.get("image_match_confidence"),
                "image_url": record.get("image_url"),
            }
            if len(report["preview"]) < 10:
                report["preview"].append(entry)
            if photo.get("image_match_confidence") == "low":
                report["low_confidence"].append(entry)

        except ApiError as exc:
            error_message = str(exc)
            if "HTTP 429" in error_message:
                report["rate_limited"] = True
                report["stopped_reason"] = error_message
                break

            record["image_status"] = "error"
            report["errors"].append(
                {
                    "food_id": record.get("food_id"),
                    "name": food_name(record),
                    "error": error_message,
                }
            )
        except Exception as exc:
            record["image_status"] = "error"
            report["errors"].append(
                {
                    "food_id": record.get("food_id"),
                    "name": food_name(record),
                    "error": str(exc),
                }
            )

    print(json.dumps(report, indent=2, ensure_ascii=False))

    if args.apply:
        save_json(args.input, records)
        save_json(REPORT_JSON, report)
        print(f"Changes written to {args.input}")
        print(f"Report written to {REPORT_JSON}")
    else:
        print("Dry run only. Re-run with --apply to write changes.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
