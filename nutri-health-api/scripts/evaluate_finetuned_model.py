#!/usr/bin/env python3
"""
Evaluate a fine-tuned food recommendation model against manual edge cases.

Usage:
    python scripts/evaluate_finetuned_model.py
    python scripts/evaluate_finetuned_model.py --model ft:gpt-4o-mini-... --limit 5
    python scripts/evaluate_finetuned_model.py --output-json results.json --output-csv results.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from pathlib import Path

# Load .env before importing OpenAI so the key is available immediately.
# Falls back to a manual parser when python-dotenv is not installed (e.g. system Python).
def _load_env_file(env_path: Path) -> None:
    """Parse a .env file and set variables into os.environ (no overwrite)."""
    try:
        with open(env_path, encoding="utf-8") as _f:
            for _line in _f:
                _line = _line.strip()
                if not _line or _line.startswith("#") or "=" not in _line:
                    continue
                _key, _, _val = _line.partition("=")
                _key = _key.strip()
                _val = _val.strip().strip('"').strip("'")
                if _key and _key not in os.environ:
                    os.environ[_key] = _val
    except OSError:
        pass

_env_path = Path(__file__).resolve().parent.parent / ".env"
try:
    from dotenv import load_dotenv
    load_dotenv(_env_path if _env_path.exists() else None)
except ImportError:
    if _env_path.exists():
        _load_env_file(_env_path)

try:
    from openai import OpenAI
except ImportError:
    print("Error: openai package not installed.  Run: pip install openai>=1.40.0")
    sys.exit(1)


# ─── Defaults ────────────────────────────────────────────────────────────────

DEFAULT_MODEL       = "ft:gpt-4o-mini-2024-07-18:personal::Dcz8w84o"
DEFAULT_TEMPERATURE = 0.25
DEFAULT_TOP_P       = 0.85
DEFAULT_CASES       = "scripts/manual_edge_cases.json"
DEFAULT_OUTPUT_JSON = "data/evaluation/manual_evaluation_results.json"
DEFAULT_OUTPUT_CSV  = "data/evaluation/manual_evaluation_results.csv"

SUPPORTED_GOALS = {"grow", "see", "think", "fight", "feel", "strong"}

SYSTEM_PROMPT = (
    "You are a child-friendly healthy eating recommendation assistant for children aged 7-12.\n"
    "Return valid JSON only.\n"
    "Do not mention calories.\n"
    "Do not use medical jargon.\n"
    "Do not recommend pork, alcohol, caffeine drinks, supplements, baby formula, or medical foods.\n"
    "Only use supported goal_id values: grow, see, think, fight, feel, strong."
)


# ─── Prompt builders ─────────────────────────────────────────────────────────

_IMPORTANT_RULES = """\
Important:
- User preferences are broad food categories, not exact foods.
- Choose specific child-friendly foods based on the goal and category preferences.
- super_power_foods should match the goal and align with liked categories when possible.
- tiny_hero_foods should match the goal but come from disliked or not-preferred categories.
- try_less_foods should be less healthy foods related to liked categories when appropriate.
- Do not simply avoid disliked categories. If a disliked category is important for the goal, choose a small challenge food from that category as tiny_hero_foods.
- Do not put unhealthy snacks, candy, cake, cookies, soda, syrup, chips, fries, or ice cream in super_power_foods.
- Sweet fruits can support feel, but sweet snacks should not be treated as feel goal foods.
- Do not recommend sauces or condiments in any section.
- Respect blacklist and allergies strictly.
- Return valid JSON only."""

_GOAL_CATEGORY_LOGIC = """\
Goal-specific category logic:
grow:
- related categories: dairy, meat, vegetables
- if dairy is disliked, a dairy food can still be tiny_hero
- if meat is disliked, a meat/fish food can still be tiny_hero

see:
- related categories: vegetables, fruits, fish
- if vegetables are disliked, a vegetable can still be tiny_hero
- if fish is disliked, a fish can still be tiny_hero

think:
- related categories: fish, dairy, fruits
- if fish or dairy is disliked, it can still appear as tiny_hero

fight:
- Fight means supporting everyday wellness and resistance.
- Primary related categories: fruits and vegetables.
- If fruits or vegetables are disliked, they can still appear as tiny_hero.
- Secondary supporting categories can include dairy, fish, eggs, beans, and simple grains when they are child-friendly and not try_less.
- Good examples include orange, berries, kiwi, broccoli, spinach, tomato, yogurt, egg, fish, beans, and oats.
- Do not use candy, soda, chips, cake, cookies, ice cream, sauces, or sweetened drinks as fight super_power foods.

feel:
- related categories: fruits, vegetables, rice, noodles
- sweet fruits are good feel candidates
- candy, cake, cookies, soda, and ice cream are not feel super_power foods

strong:
- related categories: meat, fish, dairy
- if meat, fish, or dairy is disliked, it can still appear as tiny_hero"""

_OUTPUT_SCHEMA = """\
Output schema:
{
  "goal": "...",
  "super_power_foods": [
    {"food": "...", "reason": "..."}
  ],
  "tiny_hero_foods": [
    {"food": "...", "reason": "..."}
  ],
  "try_less_foods": [
    {"food": "...", "reason": "..."}
  ]
}"""


def build_user_prompt(case_input: dict) -> str:
    goal      = case_input.get("goal", "")
    likes     = case_input.get("likes", [])
    dislikes  = case_input.get("dislikes", [])
    blacklist = case_input.get("blacklist", [])
    allergies = case_input.get("allergies", [])
    blacklist_str = ", ".join(blacklist) if blacklist else "none"
    allergies_str = ", ".join(allergies) if allergies else "none"
    header = (
        "Task: integrated_recommendation\n"
        f"Goal: {goal}\n"
        f"Liked preference categories: {', '.join(likes) if likes else 'none'}\n"
        f"Disliked preference categories: {', '.join(dislikes) if dislikes else 'none'}\n"
        f"Blacklist: {blacklist_str}\n"
        f"Allergies: {allergies_str}\n"
        "\n"
    )
    return header + _IMPORTANT_RULES + "\n\n" + _GOAL_CATEGORY_LOGIC + "\n\n" + _OUTPUT_SCHEMA


# ─── Text extraction helpers ─────────────────────────────────────────────────

def _section_to_text(items: list) -> str:
    """
    Flatten a section list into a single lowercase string.
    Each item may be a plain string or a dict (with name/reason/etc. fields).
    Both the food name and any reason/description text are included so that
    matching covers the full context the model produced.
    """
    if not isinstance(items, list):
        return ""
    parts: list[str] = []
    for item in items:
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, dict):
            parts.extend(str(v) for v in item.values())
    return " ".join(parts).lower()


def _all_parsed_text(parsed: dict) -> str:
    """Return all text in a parsed response as a single lowercase string."""
    parts: list[str] = []
    for v in parsed.values():
        if isinstance(v, (str, int, float)):
            parts.append(str(v))
        elif isinstance(v, list):
            parts.append(_section_to_text(v))
        elif isinstance(v, dict):
            parts.append(_all_parsed_text(v))
    return " ".join(parts).lower()


def _hit(term: str, text: str) -> bool:
    """
    Case-insensitive match with a leading word boundary.
    - 'cake'   does NOT match 'pancake'  (no boundary before 'cake' inside a word)
    - 'cookie' DOES    match 'cookies'   (leading boundary only; trailing 's' is fine)
    - 'muffin' DOES    match 'muffins', 'muffin top'
    Multi-word terms (e.g. 'ice cream') use plain substring match.
    """
    t = term.lower()
    if " " in t:
        return t in text
    return bool(re.search(r"\b" + re.escape(t), text))


# ─── JSON parsing ────────────────────────────────────────────────────────────

def parse_model_output(raw: str) -> dict | None:
    """
    Parse model output as JSON.
    Strips markdown code fences (```json … ```) if present before parsing.
    """
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        result = json.loads(text)
        return result if isinstance(result, dict) else None
    except (json.JSONDecodeError, ValueError):
        return None


# ─── Post-generation filter ──────────────────────────────────────────────────

# Terms that must never appear in any output item regardless of input.
GLOBAL_BANNED_TERMS: list[str] = [
    # pork family
    "pork", "bacon", "ham", "pepperoni", "salami", "prosciutto", "lard",
    # alcohol
    "alcohol", "wine", "beer", "vodka", "rum", "whiskey", "liquor",
    # caffeine / stimulants
    "coffee", "caffeine", "energy drink",
    # medical / special foods
    "supplement", "baby formula", "medical food",
    # condiments / sauces
    "sauce", "dressing", "dip", "gravy", "ketchup", "mayonnaise", "mayo",
    "syrup", "spread",
]

_SECTION_ORDER = ["super_power_foods", "tiny_hero_foods", "try_less_foods"]


def filter_output(parsed: dict | None, blacklist: list[str]) -> dict | None:
    """
    Remove banned items from model output and deduplicate across sections.

    Steps:
    1. Drop any food item whose name contains a dynamic blacklist term or global banned term.
    2. Deduplicate across sections (super_power > tiny_hero > try_less priority).
    Does NOT invent replacement items.
    Returns None if parsed is None.
    """
    if parsed is None:
        return None

    all_banned = list(blacklist) + GLOBAL_BANNED_TERMS

    def item_is_banned(item) -> bool:
        if isinstance(item, dict):
            food_name = str(item.get("food", item.get("name", ""))).lower()
        else:
            food_name = str(item).lower()
        return any(_hit(term, food_name) for term in all_banned)

    def food_key(item) -> str:
        if isinstance(item, dict):
            return str(item.get("food", item.get("name", str(item)))).lower().strip()
        return str(item).lower().strip()

    seen: set[str] = set()
    result: dict = {k: v for k, v in parsed.items() if k not in _SECTION_ORDER}

    for section in _SECTION_ORDER:
        items = parsed.get(section, [])
        if not isinstance(items, list):
            result[section] = []
            continue
        kept = []
        for item in items:
            if item_is_banned(item):
                continue
            key = food_key(item)
            if key in seen:
                continue
            seen.add(key)
            kept.append(item)
        result[section] = kept

    return result


# ─── Per-case evaluation ─────────────────────────────────────────────────────

def evaluate_case(
    case: dict,
    parsed: dict | None,
    raw_output: str,
) -> tuple[dict[str, bool], list[str]]:
    """
    Run all checks for one case.
    Returns (checks_dict, failed_checks_list).
    A check value of True means the check passed.
    """
    checks: dict[str, bool] = {}
    failed: list[str] = []
    expected: dict = case.get("expected_checks", {})

    # ── 1. JSON parse success ─────────────────────────────────────────────────
    checks["json_parse"] = parsed is not None
    if not checks["json_parse"]:
        failed.append("json_parse_failed")
        return checks, failed          # structural checks are meaningless

    # ── 2. Required sections present ─────────────────────────────────────────
    required = ["super_power_foods", "tiny_hero_foods", "try_less_foods"]
    missing  = [s for s in required if s not in parsed]
    checks["required_sections"] = len(missing) == 0
    if missing:
        failed.append("missing_sections:" + ",".join(missing))

    # ── 3. Goal value is supported ────────────────────────────────────────────
    goal_out = str(parsed.get("goal", "")).strip().lower()
    checks["goal_supported"] = goal_out in SUPPORTED_GOALS or goal_out == ""
    if not checks["goal_supported"]:
        failed.append(f"unsupported_goal:{goal_out}")

    # Build section texts for targeted checks
    sp_text = _section_to_text(parsed.get("super_power_foods", []))
    th_text = _section_to_text(parsed.get("tiny_hero_foods",   []))
    tl_text = _section_to_text(parsed.get("try_less_foods",    []))

    # For "anywhere" checks include raw output to catch text outside the schema
    everywhere = _all_parsed_text(parsed) + " " + raw_output.lower()

    # ── 4. must_not_include_anywhere ─────────────────────────────────────────
    blist_terms = expected.get("must_not_include_anywhere", [])
    blist_hits  = [t for t in blist_terms if _hit(t, everywhere)]
    checks["must_not_include_anywhere"] = len(blist_hits) == 0
    if blist_hits:
        failed.append("blacklist_violation:" + ",".join(blist_hits))

    # ── 5. must_not_include_in_super_power ───────────────────────────────────
    sp_ban  = expected.get("must_not_include_in_super_power", [])
    sp_hits = [t for t in sp_ban if _hit(t, sp_text)]
    checks["must_not_include_in_super_power"] = len(sp_hits) == 0
    if sp_hits:
        failed.append("super_power_violation:" + ",".join(sp_hits))

    # ── 6. should_include_any_in_super_power ─────────────────────────────────
    sp_want = expected.get("should_include_any_in_super_power", [])
    if sp_want:
        checks["should_include_any_in_super_power"] = any(_hit(t, sp_text) for t in sp_want)
        if not checks["should_include_any_in_super_power"]:
            failed.append("super_power_missing_expected_foods")
    else:
        checks["should_include_any_in_super_power"] = True

    # ── 7. tiny_hero_should_include_any ──────────────────────────────────────
    th_want = expected.get("tiny_hero_should_include_any", [])
    if th_want:
        checks["tiny_hero_should_include_any"] = any(_hit(t, th_text) for t in th_want)
        if not checks["tiny_hero_should_include_any"]:
            failed.append("tiny_hero_missing_expected_foods")
    else:
        checks["tiny_hero_should_include_any"] = True

    # ── 8. try_less_should_include_any ───────────────────────────────────────
    tl_want = expected.get("try_less_should_include_any", [])
    if tl_want:
        checks["try_less_should_include_any"] = any(_hit(t, tl_text) for t in tl_want)
        if not checks["try_less_should_include_any"]:
            failed.append("try_less_missing_expected_foods")
    else:
        checks["try_less_should_include_any"] = True

    # ── 9. try_less items must not carry goal_tags ────────────────────────────
    tl_items  = parsed.get("try_less_foods", [])
    tl_tagged = [
        str(item.get("name", item))
        for item in tl_items
        if isinstance(item, dict) and "goal_tags" in item
    ]
    checks["try_less_no_goal_tags"] = len(tl_tagged) == 0
    if tl_tagged:
        failed.append("try_less_has_goal_tags:" + ",".join(tl_tagged))

    # ── 10. No calorie mentions ───────────────────────────────────────────────
    calorie_terms = ["calorie", "calories", "kcal"]
    calorie_hits  = [t for t in calorie_terms if _hit(t, everywhere)]
    checks["no_calorie_mentions"] = len(calorie_hits) == 0
    if calorie_hits:
        failed.append("calorie_mentioned:" + ",".join(calorie_hits))

    return checks, failed


# ─── API call ────────────────────────────────────────────────────────────────

def call_model(
    client: OpenAI,
    model: str,
    temperature: float,
    top_p: float,
    case: dict,
) -> str:
    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        top_p=top_p,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": build_user_prompt(case["input"])},
        ],
    )
    return response.choices[0].message.content or ""


# ─── Output writers ──────────────────────────────────────────────────────────

CSV_FIELDS = [
    "case_id", "goal",
    "raw_passed", "raw_failed_checks_count", "raw_failed_checks",
    "filtered_passed", "filtered_failed_checks_count", "filtered_failed_checks",
    "json_parse", "required_sections", "goal_supported",
    "raw_blacklist_ok", "filtered_blacklist_ok",
    "raw_super_power_ok", "filtered_super_power_ok",
    "should_include_any_in_super_power",
    "tiny_hero_should_include_any",
    "raw_try_less_ok", "filtered_try_less_ok",
    "try_less_no_goal_tags", "no_calorie_mentions", "error",
]


def write_json(path: Path, model: str, temperature: float, top_p: float, results: list[dict], summary: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "model":       model,
                "temperature": temperature,
                "top_p":       top_p,
                "summary":     summary,
                "results":     results,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )


def write_csv(path: Path, results: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for r in results:
            rc = r["raw_checks"]
            fc = r["filtered_checks"]
            writer.writerow({
                "case_id":                       r["case_id"],
                "goal":                          r["goal"],
                "raw_passed":                    r["raw_passed"],
                "raw_failed_checks_count":       len(r["raw_failed"]),
                "raw_failed_checks":             "; ".join(r["raw_failed"]),
                "filtered_passed":               r["filtered_passed"],
                "filtered_failed_checks_count":  len(r["filtered_failed"]),
                "filtered_failed_checks":        "; ".join(r["filtered_failed"]),
                "json_parse":                    rc.get("json_parse", ""),
                "required_sections":             rc.get("required_sections", ""),
                "goal_supported":                rc.get("goal_supported", ""),
                "raw_blacklist_ok":              rc.get("must_not_include_anywhere", ""),
                "filtered_blacklist_ok":         fc.get("must_not_include_anywhere", ""),
                "raw_super_power_ok":            rc.get("must_not_include_in_super_power", ""),
                "filtered_super_power_ok":       fc.get("must_not_include_in_super_power", ""),
                "should_include_any_in_super_power": rc.get("should_include_any_in_super_power", ""),
                "tiny_hero_should_include_any":  rc.get("tiny_hero_should_include_any", ""),
                "raw_try_less_ok":               rc.get("try_less_should_include_any", ""),
                "filtered_try_less_ok":          fc.get("try_less_should_include_any", ""),
                "try_less_no_goal_tags":         rc.get("try_less_no_goal_tags", ""),
                "no_calorie_mentions":           rc.get("no_calorie_mentions", ""),
                "error":                         r.get("error") or "",
            })


# ─── Entry point ─────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate a fine-tuned food recommendation model against manual edge cases.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--model",       default=DEFAULT_MODEL,            help="OpenAI model ID (base or fine-tuned)")
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE, help="Sampling temperature")
    parser.add_argument("--top-p",       type=float, default=DEFAULT_TOP_P,       help="Top-p nucleus sampling")
    parser.add_argument("--limit",       type=int,   default=None,                help="Evaluate only the first N cases")
    parser.add_argument("--cases",       default=DEFAULT_CASES,            help="Path to edge-cases JSON file")
    parser.add_argument("--output-json", default=DEFAULT_OUTPUT_JSON,      help="Path for JSON results output")
    parser.add_argument("--output-csv",  default=DEFAULT_OUTPUT_CSV,       help="Path for CSV results output")
    args = parser.parse_args()

    # ── Validate API key (never print it) ────────────────────────────────────
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY is not set in environment or .env file.")
        sys.exit(1)
    client = OpenAI(api_key=api_key)

    # ── Load cases ───────────────────────────────────────────────────────────
    cases_path = Path(args.cases)
    if not cases_path.exists():
        print(f"Error: cases file not found: {cases_path}")
        sys.exit(1)
    with open(cases_path, encoding="utf-8") as f:
        cases: list[dict] = json.load(f)

    if args.limit:
        cases = cases[: args.limit]

    total = len(cases)
    print(f"Model        : {args.model}")
    print(f"Temperature  : {args.temperature}  |  top_p: {args.top_p}")
    print(f"Cases file   : {args.cases}")
    print(f"Cases to run : {total}")
    print(f"Output JSON  : {args.output_json}")
    print(f"Output CSV   : {args.output_csv}")
    print("-" * 64)

    results: list[dict] = []

    for i, case in enumerate(cases, 1):
        case_id    = case.get("case_id", f"case_{i}")
        goal       = case.get("input", {}).get("goal", "?")
        blacklist  = case.get("input", {}).get("blacklist", [])
        raw_output = ""
        raw_parsed = None
        error_msg  = None

        print(f"[{i:>3}/{total}] {case_id:<30} goal={goal:<8} ... ", end="", flush=True)

        try:
            raw_output = call_model(client, args.model, args.temperature, args.top_p, case)
            raw_parsed = parse_model_output(raw_output)
        except Exception as exc:
            error_msg = str(exc)
            print(f"API ERROR: {error_msg}")

        filtered_parsed = filter_output(raw_parsed, blacklist)

        raw_checks, raw_failed           = evaluate_case(case, raw_parsed,      raw_output)
        # For the filtered evaluation pass "" as raw_output so the "anywhere" check
        # only inspects the filtered structured output, not the pre-filter LLM text.
        filtered_checks, filtered_failed = evaluate_case(case, filtered_parsed, "")

        raw_passed      = len(raw_failed) == 0
        filtered_passed = len(filtered_failed) == 0

        if filtered_passed:
            print("PASS")
        else:
            print(f"FAIL  ({len(filtered_failed)} check{'s' if len(filtered_failed) != 1 else ''} failed, filtered)")
            for fc in filtered_failed:
                print(f"           ! {fc}")

        results.append({
            "case_id":         case_id,
            "goal":            goal,
            "raw_passed":      raw_passed,
            "raw_failed":      raw_failed,
            "raw_checks":      raw_checks,
            "filtered_passed": filtered_passed,
            "filtered_failed": filtered_failed,
            "filtered_checks": filtered_checks,
            "error":           error_msg,
            "raw_output":      raw_output,
            "raw_parsed":      raw_parsed,
            "filtered_parsed": filtered_parsed,
        })

        # Brief pause between calls to stay within rate limits
        if i < total:
            time.sleep(0.4)

    # ── Build summary ────────────────────────────────────────────────────────
    parse_ok = sum(1 for r in results if r["raw_checks"].get("json_parse", False))

    raw_passed_count      = sum(1 for r in results if r["raw_passed"])
    filtered_passed_count = sum(1 for r in results if r["filtered_passed"])

    raw_sp_violations      = sum(1 for r in results if not r["raw_checks"].get("must_not_include_in_super_power", True))
    filtered_sp_violations = sum(1 for r in results if not r["filtered_checks"].get("must_not_include_in_super_power", True))

    raw_blist_violations      = sum(1 for r in results if not r["raw_checks"].get("must_not_include_anywhere", True))
    filtered_blist_violations = sum(1 for r in results if not r["filtered_checks"].get("must_not_include_anywhere", True))

    raw_tiny_miss      = sum(1 for r in results if not r["raw_checks"].get("tiny_hero_should_include_any", True))
    filtered_tiny_miss = sum(1 for r in results if not r["filtered_checks"].get("tiny_hero_should_include_any", True))

    raw_try_miss      = sum(1 for r in results if not r["raw_checks"].get("try_less_should_include_any", True))
    filtered_try_miss = sum(1 for r in results if not r["filtered_checks"].get("try_less_should_include_any", True))

    summary = {
        "total":                          total,
        "json_parse_rate":                f"{parse_ok / total * 100:.1f}%",
        "raw_passed":                     raw_passed_count,
        "raw_pass_rate":                  f"{raw_passed_count / total * 100:.1f}%",
        "filtered_passed":                filtered_passed_count,
        "filtered_pass_rate":             f"{filtered_passed_count / total * 100:.1f}%",
        "raw_super_power_violations":     raw_sp_violations,
        "filtered_super_power_violations": filtered_sp_violations,
        "raw_blacklist_violations":       raw_blist_violations,
        "filtered_blacklist_violations":  filtered_blist_violations,
        "raw_tiny_hero_misses":           raw_tiny_miss,
        "filtered_tiny_hero_misses":      filtered_tiny_miss,
        "raw_try_less_misses":            raw_try_miss,
        "filtered_try_less_misses":       filtered_try_miss,
    }

    print()
    print("=" * 64)
    print("EVALUATION SUMMARY")
    print("=" * 64)
    print(f"  Total cases                    : {total}")
    print(f"  JSON parse success rate        : {parse_ok}/{total}  ({parse_ok / total * 100:.1f}%)")
    print()
    print(f"  {'Metric':<35} {'Raw':>6}  {'Filtered':>8}")
    print(f"  {'-'*35} {'-'*6}  {'-'*8}")
    print(f"  {'Pass rate':<35} {raw_passed_count / total * 100:>5.1f}%  {filtered_passed_count / total * 100:>7.1f}%")
    print(f"  {'Super_power violations':<35} {raw_sp_violations:>6}  {filtered_sp_violations:>8}")
    print(f"  {'Blacklist violations':<35} {raw_blist_violations:>6}  {filtered_blist_violations:>8}")
    print(f"  {'Tiny_hero misses':<35} {raw_tiny_miss:>6}  {filtered_tiny_miss:>8}")
    print(f"  {'Try_less misses':<35} {raw_try_miss:>6}  {filtered_try_miss:>8}")
    print("=" * 64)

    # ── Write outputs ────────────────────────────────────────────────────────
    write_json(Path(args.output_json), args.model, args.temperature, args.top_p, results, summary)
    write_csv(Path(args.output_csv), results)

    print(f"\nJSON results : {args.output_json}")
    print(f"CSV results  : {args.output_csv}")


if __name__ == "__main__":
    main()
