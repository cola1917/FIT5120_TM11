"""
Recommendation endpoint smoke test.
Uses only the 8 real frontend like/dislike categories:
  fruits, vegetables, rice, bread, noodles, meat, fish, dairy

Verifies for every goal:
1. All three sections return exactly 3 items
2. No food name appears more than once across all three sections
3. tiny_hero items do NOT come from liked categories
4. try_less items come from liked-category pools (not random junk)
5. Blacklist terms are absent from all results

Run:
    .venv/bin/python3 scripts/test_recommendation.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.load_env import ensure_dotenv_loaded
ensure_dotenv_loaded()

from app.services.recommendation import (
    call_model, parse_model_output,
    topup_sections, rewrite_try_less_by_likes,
    _TRY_LESS_BY_CATEGORY,
)
from app.services.filter import filter_output, filter_tiny_hero_by_likes
from app.services.enrichment import infer_category

# Valid frontend categories only
VALID_CATEGORIES = {"fruits", "vegetables", "rice", "bread", "noodles", "meat", "fish", "dairy"}

SEP = "=" * 65
TARGET = 3
failures = []


def run_recommendation(goal, likes=None, dislikes=None, blacklist=None, allergies=None):
    likes     = likes     or []
    dislikes  = dislikes  or []
    blacklist = blacklist or []
    allergies = allergies or []

    raw    = call_model(goal, likes, dislikes, blacklist, allergies)
    parsed = parse_model_output(raw)
    if parsed is None:
        return None

    filtered = filter_output(parsed, blacklist, allergies)
    filtered = filter_tiny_hero_by_likes(filtered, likes)
    filtered = rewrite_try_less_by_likes(filtered, likes)
    filtered = topup_sections(filtered, goal=goal, blacklist=blacklist, allergies=allergies, likes=likes)
    return filtered


def check(label, goal, likes=None, dislikes=None, blacklist=None,
          try_less_must_include_cats=None):
    print(SEP)
    print(f"Case: {label}")
    print(f"  goal={goal}  likes={likes or []}  dislikes={dislikes or []}  blacklist={blacklist or []}")

    result = run_recommendation(goal, likes, dislikes, blacklist)
    if result is None:
        print("  [FAIL] model returned unparseable output")
        failures.append(f"{label}: unparseable model output")
        return

    sections = {
        "super_power_foods": result.get("super_power_foods", []),
        "tiny_hero_foods":   result.get("tiny_hero_foods",   []),
        "try_less_foods":    result.get("try_less_foods",    []),
    }

    all_names: list[str] = []
    ok = True

    for section, items in sections.items():
        short = section.replace("_foods", "")
        print(f"\n  [{short}] ({len(items)} items)")
        for item in items:
            name = item.get("food", item.get("name", "?"))
            cat  = infer_category(name)
            print(f"    • [{cat}] {name}")
            print(f"      {item.get('reason', item.get('grade', ''))}")
        all_names.extend(item.get("food", item.get("name", "")).lower().strip() for item in items)

        # 1. Each section must have exactly TARGET items
        if len(items) != TARGET:
            print(f"  [FAIL] {section}: expected {TARGET} items, got {len(items)}")
            failures.append(f"{label}: {section} has {len(items)} (expected {TARGET})")
            ok = False

        # 5. Blacklist terms must not appear
        for item in items:
            name = item.get("food", item.get("name", "")).lower()
            for term in (blacklist or []):
                if term.lower() in name:
                    print(f"  [FAIL] blacklisted '{term}' in {section}: {name!r}")
                    failures.append(f"{label}: '{term}' in {section} → {name!r}")
                    ok = False

    # 2. No duplicate food names across all sections
    seen: set[str] = set()
    for name in all_names:
        if name in seen:
            print(f"  [FAIL] duplicate food across sections: {name!r}")
            failures.append(f"{label}: duplicate food {name!r}")
            ok = False
        seen.add(name)

    # 3. tiny_hero must NOT come from liked categories
    liked_set = {c.lower() for c in (likes or [])} & VALID_CATEGORIES
    for item in sections["tiny_hero_foods"]:
        name = item.get("food", item.get("name", ""))
        cat  = infer_category(name)
        if cat in liked_set:
            print(f"  [FAIL] tiny_hero '{name}' is in liked category '{cat}'")
            failures.append(f"{label}: tiny_hero '{name}' in liked '{cat}'")
            ok = False

    # 4. try_less must include at least one item from each required liked-category pool
    if try_less_must_include_cats:
        try_less_names = {
            item.get("food", item.get("name", "")).lower().strip()
            for item in sections["try_less_foods"]
        }
        for req_cat in try_less_must_include_cats:
            pool_names = {e["food"].lower().strip() for e in _TRY_LESS_BY_CATEGORY.get(req_cat, [])}
            if not (try_less_names & pool_names):
                print(f"  [FAIL] try_less has no item from '{req_cat}' pool")
                print(f"         got: {sorted(try_less_names)}")
                failures.append(f"{label}: try_less missing pool item for '{req_cat}'")
                ok = False

    if ok:
        print("\n  [OK]")


# ── 1. Baseline — all 6 goals, no preferences ─────────────────────────────────
print(f"\n{'─'*65}")
print("1. BASELINE — all 6 goals, no preferences")
for goal in ["grow", "see", "think", "fight", "feel", "strong"]:
    check(f"{goal} — baseline", goal)

# ── 2. Likes (8 real frontend categories) ─────────────────────────────────────
print(f"\n{'─'*65}")
print("2. LIKES — tiny_hero not from liked; try_less FROM liked category pool")

check("grow — likes: dairy+meat",
      "grow", likes=["dairy", "meat"],
      try_less_must_include_cats=["dairy", "meat"])

check("see — likes: vegetables+fruits",
      "see",  likes=["vegetables", "fruits"],
      try_less_must_include_cats=["vegetables", "fruits"])

check("think — likes: fish+dairy",
      "think", likes=["fish", "dairy"],
      try_less_must_include_cats=["fish", "dairy"])

check("feel — likes: rice+noodles",
      "feel", likes=["rice", "noodles"],
      try_less_must_include_cats=["rice", "noodles"])

check("fight — likes: fruits+vegetables",
      "fight", likes=["fruits", "vegetables"],
      try_less_must_include_cats=["fruits", "vegetables"])

check("strong — likes: meat+fish",
      "strong", likes=["meat", "fish"],
      try_less_must_include_cats=["meat", "fish"])

# ── 3. Dislikes (8 real frontend categories) ──────────────────────────────────
print(f"\n{'─'*65}")
print("3. DISLIKES — model should avoid disliked categories in super_power")

check("grow — dislikes: dairy",
      "grow", dislikes=["dairy"])

check("see — dislikes: fish",
      "see", dislikes=["fish"])

check("strong — dislikes: meat+fish",
      "strong", dislikes=["meat", "fish"])

# ── 4. Blacklist (7 real frontend blacklist terms) ────────────────────────────
print(f"\n{'─'*65}")
print("4. BLACKLIST — blocked terms absent, still 3 items per section")

check("think — blacklist: egg+milk",
      "think", blacklist=["egg", "milk"])

check("fight — blacklist: nuts",
      "fight", blacklist=["nuts"])

check("strong — blacklist: egg+salmon",
      "strong", blacklist=["egg", "salmon"])

check("grow — blacklist: seafood+pork",
      "grow", blacklist=["seafood", "pork"])

# ── 5. Combined likes + dislikes + blacklist ───────────────────────────────────
print(f"\n{'─'*65}")
print("5. COMBINED — likes + dislikes + blacklist (all frontend categories)")

check("feel — likes: fruits, dislikes: dairy, blacklist: nuts",
      "feel", likes=["fruits"], dislikes=["dairy"], blacklist=["nuts"],
      try_less_must_include_cats=["fruits"])

check("grow — likes: vegetables, dislikes: meat+fish, blacklist: egg",
      "grow", likes=["vegetables"], dislikes=["meat", "fish"], blacklist=["egg"],
      try_less_must_include_cats=["vegetables"])

check("think — likes: bread+dairy, dislikes: fish, blacklist: nuts",
      "think", likes=["bread", "dairy"], dislikes=["fish"], blacklist=["nuts"],
      try_less_must_include_cats=["bread", "dairy"])

# ── Summary ───────────────────────────────────────────────────────────────────
print(SEP)
if failures:
    print(f"RESULT: FAIL — {len(failures)} issue(s):")
    for f in failures:
        print(f"  • {f}")
else:
    print("RESULT: PASS")
print(SEP)
