"""
Preference filter smoke test for get_scan_alternatives().

覆盖本次修改的所有关键行为:
1. Baseline — 无偏好时正常返回
2. Dislikes 硬过滤 — 被讨厌的类别永远不出现在结果里
3. Likes 排序提示 — 喜欢的类别优先排在前面
4. 全部 dislike 时走 fallback map 的多样化备选（不软放宽）
5. Blacklist + Dislikes + Likes 组合过滤
6. Blacklist 单词边界匹配 — "egg" 不会误杀 "veggie"
7. score=3 永远返回 []

Run:
    .venv/bin/python3 scripts/test_preference_filter.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.load_env import ensure_dotenv_loaded
ensure_dotenv_loaded()

from app.services.scan_alternative_service import (
    get_scan_alternatives,
    infer_alternative_category,
)

SEP = "=" * 60

failures = []


def check(label, food, score, blacklist=None, likes=None, dislikes=None,
          must_not_categories=None, must_not_terms=None,
          expect_empty=False, expect_category=None):
    print(SEP)
    print(f"Case: {label}")
    print(f"  blacklist={blacklist or []}  likes={likes or []}  dislikes={dislikes or []}")

    result = get_scan_alternatives(
        food, score,
        blacklist=blacklist or [],
        likes=likes or [],
        dislikes=dislikes or [],
    )

    if expect_empty:
        if result:
            print(f"  [FAIL] expected [] but got: {[a['name'] for a in result]}")
            failures.append(f"{label}: should be empty")
        else:
            print("  [OK] []")
        return

    if not result:
        print("  [FAIL] got empty result — no alternatives returned")
        failures.append(f"{label}: empty result")
        return

    ok = True
    for alt in result:
        name = alt.get("name", "")
        desc = alt.get("description", "")
        cat  = infer_alternative_category(name) or "unknown"
        print(f"  → [{cat}] {name}")
        print(f"     {desc}")

        # description must not be empty
        if not desc:
            print(f"  [FAIL] description is empty for {name!r}")
            failures.append(f"{label}: empty description for {name!r}")
            ok = False

        # category must not appear
        for bad_cat in (must_not_categories or []):
            if cat == bad_cat:
                print(f"  [FAIL] disliked/banned category '{bad_cat}' in result: {name!r}")
                failures.append(f"{label}: category '{bad_cat}' in {name!r}")
                ok = False

        # term must not appear in name (word-boundary, same as _is_blacklisted)
        for bad_term in (must_not_terms or []):
            if re.search(r"\b" + re.escape(bad_term.lower()), name.lower()):
                print(f"  [FAIL] blacklisted term '{bad_term}' in name: {name!r}")
                failures.append(f"{label}: '{bad_term}' in {name!r}")
                ok = False

    # check that the first result is in expected category (likes ordering)
    if expect_category and result:
        first_cat = infer_alternative_category(result[0]["name"]) or "unknown"
        if first_cat != expect_category:
            print(f"  [WARN] expected first result in category '{expect_category}', got '{first_cat}'")
            # warning only, not a hard failure

    if ok:
        print("  [OK]")


# ── 1. Baseline ───────────────────────────────────────────────────────────────
print(f"\n{'─'*60}")
print("1. BASELINE (no preferences)")
check("chips — no prefs",  "chips",  1)
check("burger — no prefs", "burger", 2)
check("cola — no prefs",   "cola",   1)

# ── 2. Dislikes 硬过滤 ─────────────────────────────────────────────────────────
print(f"\n{'─'*60}")
print("2. DISLIKES HARD FILTER — disliked categories must NEVER appear")
check(
    "burger — dislikes: meat",
    "burger", 2,
    dislikes=["meat"],
    must_not_categories=["meat"],
)
check(
    "cola — dislikes: dairy",
    "cola", 1,
    dislikes=["dairy"],
    must_not_categories=["dairy"],
)
check(
    "chips — dislikes: vegetables",
    "chips", 1,
    dislikes=["vegetables"],
    must_not_categories=["vegetables"],
)
check(
    "fried chicken — dislikes: meat (all model alts removed → veg fallback used)",
    "fried chicken", 1,
    dislikes=["meat"],
    must_not_categories=["meat"],
)

# ── 3. Likes 排序提示 ──────────────────────────────────────────────────────────
print(f"\n{'─'*60}")
print("3. LIKES HINT — liked category should appear first when available")
check(
    "cake — likes: fruits",
    "cake", 1,
    likes=["fruits"],
    expect_category="fruits",   # first result should be fruits
)
check(
    "fried chicken — likes: vegetables",
    "fried chicken", 1,
    likes=["vegetables"],
    expect_category="vegetables",
)

# ── 4. 全部 dislike → fallback map 多样化备选 ──────────────────────────────────
print(f"\n{'─'*60}")
print("4. ALL-DISLIKED → diverse fallback (no soft relax, uses new fallback entries)")
check(
    "burger — dislikes: meat+fish+bread → vegetable fallback",
    "burger", 2,
    dislikes=["meat", "fish", "bread"],
    must_not_categories=["meat", "fish", "bread"],
)
check(
    "fried chicken — dislikes: meat+fish → vegetable fallback",
    "fried chicken", 1,
    dislikes=["meat", "fish"],
    must_not_categories=["meat", "fish"],
)

# ── 5. Blacklist + Dislikes + Likes 组合 ──────────────────────────────────────
print(f"\n{'─'*60}")
print("5. COMBINED blacklist + dislikes + likes")
check(
    "fried chicken — blacklist: egg, dislikes: meat, likes: vegetables",
    "fried chicken", 1,
    blacklist=["egg"],
    dislikes=["meat"],
    likes=["vegetables"],
    must_not_terms=["egg"],
    must_not_categories=["meat"],
)
check(
    "instant noodles — blacklist: egg, dislikes: fish",
    "instant noodles", 2,
    blacklist=["egg"],
    dislikes=["fish"],
    must_not_terms=["egg"],
    must_not_categories=["fish"],
)
check(
    "burger — blacklist: chicken, dislikes: fish, likes: vegetables",
    "burger", 2,
    blacklist=["chicken"],
    dislikes=["fish"],
    likes=["vegetables"],
    must_not_terms=["chicken"],
    must_not_categories=["fish"],
)

# ── 6. Blacklist 单词边界 — "egg" 不误杀 "veggie" ─────────────────────────────
print(f"\n{'─'*60}")
print('6. BLACKLIST WORD BOUNDARY — "egg" must NOT block foods containing "veggie"')
check(
    'chips — blacklist: egg (should NOT remove veggie-named alternatives)',
    "chips", 1,
    blacklist=["egg"],
    # carrot sticks or nori should still appear; result must be non-empty
)
check(
    'fried chicken — blacklist: egg, likes: vegetables (veggie alternatives must survive)',
    "fried chicken", 1,
    blacklist=["egg"],
    likes=["vegetables"],
    # must_not_terms checks word boundary: "egg" should not block "tofu stir-fry with vegetables"
    must_not_terms=["egg"],
)

# ── 7. score=3 永远返回 [] ─────────────────────────────────────────────────────
print(f"\n{'─'*60}")
print("7. SCORE=3 → always empty regardless of preferences")
check(
    "apple — score=3",
    "apple", 3,
    likes=["fruits"], dislikes=["dairy"], blacklist=["nuts"],
    expect_empty=True,
)
check(
    "banana — score=3",
    "banana", 3,
    expect_empty=True,
)

# ── Summary ───────────────────────────────────────────────────────────────────
print(SEP)
if failures:
    print(f"RESULT: FAIL — {len(failures)} issue(s):")
    for f in failures:
        print(f"  • {f}")
else:
    print("RESULT: PASS")
print(SEP)
