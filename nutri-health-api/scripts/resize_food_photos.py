"""
Resize downloaded food photos to a consistent UI-friendly square size.

By default this creates one backup copy per original image in:
    static/food_photos_original/

Run from the nutri-health-api directory:
    python scripts/resize_food_photos.py --apply
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parent.parent
PHOTO_DIR = ROOT / "static" / "food_photos"
BACKUP_DIR = ROOT / "static" / "food_photos_original"


def resize_photo(path: Path, size: int, quality: int, backup: bool) -> tuple[tuple[int, int], int, int]:
    old_bytes = path.stat().st_size
    with Image.open(path) as image:
        original_size = (image.width, image.height)
        image = ImageOps.exif_transpose(image)
        image = ImageOps.fit(image.convert("RGB"), (size, size), method=Image.Resampling.LANCZOS)

        if backup:
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            backup_path = BACKUP_DIR / path.name
            if not backup_path.exists():
                shutil.copy2(path, backup_path)

        image.save(path, format="JPEG", quality=quality, optimize=True, progressive=True)

    return original_size, old_bytes, path.stat().st_size


def main() -> int:
    parser = argparse.ArgumentParser(description="Resize food photos to square JPEGs.")
    parser.add_argument("--apply", action="store_true", help="Write resized files")
    parser.add_argument("--size", type=int, default=384, help="Output width/height in pixels")
    parser.add_argument("--quality", type=int, default=85, help="JPEG quality")
    parser.add_argument("--no-backup", action="store_true", help="Do not create original-image backups")
    args = parser.parse_args()

    if args.size <= 0:
        raise ValueError("--size must be positive")
    if not 1 <= args.quality <= 95:
        raise ValueError("--quality must be between 1 and 95")

    paths = sorted(PHOTO_DIR.glob("*.jpg"))
    total_before = sum(path.stat().st_size for path in paths)
    changed = 0
    preview = []

    for path in paths:
        with Image.open(path) as image:
            needs_resize = image.width != args.size or image.height != args.size
            original_size = (image.width, image.height)

        if not needs_resize:
            continue

        if args.apply:
            original_size, old_bytes, new_bytes = resize_photo(
                path,
                size=args.size,
                quality=args.quality,
                backup=not args.no_backup,
            )
        else:
            old_bytes = path.stat().st_size
            new_bytes = old_bytes

        changed += 1
        if len(preview) < 10:
            preview.append(
                {
                    "file": path.name,
                    "from": f"{original_size[0]}x{original_size[1]}",
                    "to": f"{args.size}x{args.size}",
                    "old_kb": round(old_bytes / 1024, 1),
                    "new_kb": round(new_bytes / 1024, 1),
                }
            )

    total_after = sum(path.stat().st_size for path in paths)
    print(f"Photos scanned: {len(paths)}")
    print(f"Photos needing resize: {changed}")
    print(f"Total before: {total_before / 1024 / 1024:.2f} MB")
    print(f"Total after: {total_after / 1024 / 1024:.2f} MB")
    print(f"Target: {args.size}x{args.size}, JPEG quality {args.quality}")
    print("Preview:")
    for item in preview:
        print(f"  {item['file']}: {item['from']} -> {item['to']} ({item['old_kb']} KB -> {item['new_kb']} KB)")

    if not args.apply:
        print("Dry run only. Re-run with --apply to write changes.")
    elif not args.no_backup:
        print(f"Original backups kept in: {BACKUP_DIR}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
