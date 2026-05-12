"""
Full pipeline smoke test for scan alternatives.
Tests get_scan_alternatives() including post-processing filters and fallback map.

Run:
    python3 scripts/test_pipeline_smoke.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.load_env import ensure_dotenv_loaded
ensure_dotenv_loaded()

from app.services.scan_alternative_service import get_scan_alternatives

TEST_CASES = [
    ("candy",            1),
    ("cake",             1),
    ("ice cream",        1),
    ("chocolate cookie", 1),
    ("chips",            1),
    ("cola",             1),
    ("donut",            1),
    ("pizza",            1),
    ("hot dog",          1),
    ("bubble tea",       1),
    ("burger",           2),
    ("fried chicken",    1),
    ("instant noodles",  2),
    ("french fries",     2),
    ("apple",            3),
]

JUNK_TERMS = {
    "candy", "cake", "cookie", "cookies", "ice cream", "soda",
    "cola", "chips", "fries", "french fries", "donut", "doughnut",
    "pastry", "chocolate bar", "brownie",
}

SEP = "=" * 55

failures = []

print()
for food, score in TEST_CASES:
    print(SEP)
    print(f"Food: {food!r}  score={score}")

    if score >= 3:
        result = get_scan_alternatives(food, score)
        if result:
            print(f"  [FAIL] score>=3 but got alternatives: {result}")
            failures.append(f"{food}: should be empty for score>=3")
        else:
            print("  [OK] score>=3 → []")
        continue

    result = get_scan_alternatives(food, score)

    if not result:
        print("  [FAIL] got empty alternatives")
        failures.append(f"{food}: empty result")
        continue

    ok = True
    for alt in result:
        name = alt.get("name", "")
        desc = alt.get("description", "")
        print(f"  → {name}")
        print(f"     {desc}")

        name_lower = name.lower().strip()

        # single raw ingredient check
        if " " not in name_lower and len(name_lower) > 0:
            print(f"  [WARN] single-word name: {name!r}")

        # junk food leaked through
        for term in JUNK_TERMS:
            if term in name_lower:
                print(f"  [FAIL] junk term {term!r} in alternative name")
                failures.append(f"{food}: junk term {term!r} in {name!r}")
                ok = False
                break

        if not desc:
            print(f"  [FAIL] empty description")
            failures.append(f"{food}: empty description")
            ok = False

    if ok:
        print("  [OK]")

print(SEP)
if failures:
    print(f"RESULT: FAIL — {len(failures)} issue(s):")
    for f in failures:
        print(f"  • {f}")
else:
    print("RESULT: PASS")
print(SEP)
