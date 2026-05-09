#!/usr/bin/env python3
"""Validate tiny hero patch JSONL files."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIR_DEFAULT = ROOT / "data" / "finetune_patch"

SUPPORTED_GOALS = {"grow", "see", "think", "fight", "feel", "strong"}
JUNK = ["candy", "cake", "cookie", "muffin", "soda", "ice cream", "chips", "fries"]
SAUCE_TERMS = ["sauce", "sauces", "dressing", "dip", "gravy", "ketchup", "mayonnaise", "mayo", "syrup", "spread", "cream sauce", "cheese sauce", "sour dressing"]
CALORIE_TERMS = ["calorie", "calories", "kcal"]
BLACKLIST_TERMS = ["peanut", "pork", "alcohol"]

def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as e:
                    raise ValueError(f"{path}:{i} invalid JSONL: {e}") from e
    return rows

def flatten(obj) -> str:
    return json.dumps(obj, ensure_ascii=False).lower()

def section_text(parsed: dict, section: str) -> str:
    return flatten(parsed.get(section, []))

def validate_file(path: Path) -> dict:
    rows = load_jsonl(path)
    errors = []
    for idx, row in enumerate(rows, 1):
        msgs = row.get("messages")
        if not isinstance(msgs, list) or len(msgs) != 3:
            errors.append(f"{path.name}:{idx} invalid messages")
            continue
        assistant = msgs[2].get("content", "")
        try:
            parsed = json.loads(assistant)
        except json.JSONDecodeError:
            errors.append(f"{path.name}:{idx} assistant content is not JSON")
            continue

        goal = parsed.get("goal")
        if goal not in SUPPORTED_GOALS:
            errors.append(f"{path.name}:{idx} unsupported goal: {goal}")

        txt = flatten(parsed)
        if any(term in txt for term in CALORIE_TERMS):
            errors.append(f"{path.name}:{idx} calorie mention")
        if any(term in txt for term in SAUCE_TERMS):
            errors.append(f"{path.name}:{idx} sauce/condiment term found")
        if any(term in txt for term in BLACKLIST_TERMS):
            # Blacklisted safety terms should not appear in assistant outputs.
            errors.append(f"{path.name}:{idx} blacklisted term found")

        tiny = parsed.get("tiny_hero_foods")
        if not isinstance(tiny, list) or not tiny:
            errors.append(f"{path.name}:{idx} tiny_hero_foods missing/empty")

        super_txt = section_text(parsed, "super_power_foods")
        if any(term in super_txt for term in JUNK):
            errors.append(f"{path.name}:{idx} junk food in super_power_foods")

        tiny_txt = section_text(parsed, "tiny_hero_foods")
        if any(term in tiny_txt for term in JUNK):
            errors.append(f"{path.name}:{idx} try_less/junk food in tiny_hero_foods")

        user = msgs[1].get("content", "").lower()
        if "goal: grow" in user and "dislikes: meat" in user and "bean" in tiny_txt:
            errors.append(f"{path.name}:{idx} beans used for grow + dislikes meat")
        if "goal: strong" in user and "dislikes: meat" in user and "bean" in tiny_txt:
            errors.append(f"{path.name}:{idx} beans used for strong + dislikes meat")

    return {"path": str(path), "rows": len(rows), "errors": errors}

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default=str(DIR_DEFAULT))
    args = parser.parse_args()

    d = Path(args.dir)
    train = d / "tiny_hero_patch_train.jsonl"
    valid = d / "tiny_hero_patch_valid.jsonl"
    results = [validate_file(train), validate_file(valid)]

    total_rows = sum(r["rows"] for r in results)
    all_errors = [e for r in results for e in r["errors"]]
    print("Tiny hero patch validation")
    print(f"Rows: {total_rows}")
    print(f"Errors: {len(all_errors)}")
    if all_errors:
        for e in all_errors[:50]:
            print("ERROR:", e)
        raise SystemExit(1)
    print("All checks passed.")

if __name__ == "__main__":
    main()
