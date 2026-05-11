"""
Blacklist filter smoke test for get_scan_alternatives().

Verifies:
1. Without blacklist → baseline alternatives returned
2. With blacklist → blacklisted terms absent from results
3. Alternatives are still returned (not empty) after filtering

Run:
    .venv/bin/python3 scripts/test_blacklist_filter.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.load_env import ensure_dotenv_loaded
ensure_dotenv_loaded()

from app.services.scan_alternative_service import get_scan_alternatives

SEP = "=" * 55

# (food, score, blacklist, terms_that_must_not_appear_in_any_name)
CASES = [
    # Baseline — no blacklist
    ("chips",           1, [],           []),
    ("cola",            1, [],           []),
    ("burger",          2, [],           []),
    # With blacklist — filtered term must not appear, result must still be non-empty
    ("chips",           1, ["nori"],     ["nori"]),
    ("cola",            1, ["milk"],     ["milk"]),
    ("burger",          2, ["chicken"],  ["chicken"]),
    ("instant noodles", 2, ["egg"],      ["egg"]),
    # score=3 always returns []
    ("apple",           3, ["nuts"],     []),
]

failures = []

for food, score, blacklist, must_not in CASES:
    label = f"{food!r}  score={score}  blacklist={blacklist}"
    print(SEP)
    print(f"Food: {label}")

    result = get_scan_alternatives(food, score, blacklist=blacklist)

    # score>=3 must always be empty
    if score >= 3:
        if result:
            print(f"  [FAIL] expected [] for score>=3, got: {result}")
            failures.append(f"{label} → non-empty for score>=3")
        else:
            print("  [OK] []")
        continue

    # With or without blacklist, result should not be empty
    if not result:
        print("  [FAIL] got empty result — no alternatives returned")
        failures.append(f"{label} → empty result")
        continue

    ok = True
    for alt in result:
        name = alt.get("name", "")
        print(f"  → {name}")
        print(f"     {alt.get('description', '')}")
        for term in must_not:
            if term.lower() in name.lower():
                print(f"  [FAIL] blacklisted '{term}' found in: {name!r}")
                failures.append(f"{label} → '{term}' in {name!r}")
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
