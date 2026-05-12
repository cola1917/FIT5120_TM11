#!/usr/bin/env python3
"""Generate a small second-round fine-tuning patch dataset focused on tiny_hero behavior.

Writes OpenAI chat-format JSONL files:
- data/finetune_patch/tiny_hero_patch_train.jsonl
- data/finetune_patch/tiny_hero_patch_valid.jsonl
- data/finetune_patch/tiny_hero_patch_summary.json
"""
from __future__ import annotations
import argparse, json, random
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR_DEFAULT = ROOT / "data" / "finetune_patch"

SYSTEM = (
    "You are a child-friendly healthy eating recommendation assistant for children aged 7-12. "
    "Return valid JSON only. Do not mention calories. Do not use medical jargon. "
    "Do not recommend pork, alcohol, caffeine drinks, supplements, baby formula, or medical foods. "
    "Only use supported goal_id values: grow, see, think, fight, feel, strong."
)

GOALS = ["grow", "see", "think", "fight", "feel", "strong"]

PATTERNS = {
    "grow": [
        ("dairy", ["milk", "yogurt", "cottage cheese"], ["chicken", "fish", "sweet potato"], ["ice cream", "cake"]),
        ("meat", ["chicken", "beef", "lamb", "fish"], ["milk", "yogurt", "sweet potato"], ["chips", "fries"]),
    ],
    "see": [
        ("vegetables", ["carrot", "spinach", "kale", "sweet potato"], ["mango", "orange", "salmon"], ["candy", "soda"]),
        ("fish", ["salmon", "tuna"], ["carrot", "mango", "spinach"], ["ice cream", "cookie"]),
    ],
    "think": [
        ("fish", ["salmon", "tuna", "fish"], ["yogurt", "berries", "oats"], ["cake", "soda"]),
        ("dairy", ["yogurt", "milk"], ["salmon", "berries", "oats"], ["ice cream", "muffin"]),
    ],
    "fight": [
        ("vegetables", ["broccoli", "spinach", "kale", "tomato"], ["orange", "berries", "kiwi"], ["soda", "candy"]),
        ("fruits", ["orange", "kiwi", "berries"], ["broccoli", "spinach", "carrot"], ["cake", "cookie"]),
    ],
    "feel": [
        ("fruits", ["mango", "banana", "berries", "orange"], ["rice", "noodles", "oatmeal"], ["candy", "cake", "muffin"]),
        ("vegetables", ["sweet potato", "carrot", "corn"], ["banana", "mango", "rice"], ["ice cream", "chips"]),
    ],
    "strong": [
        ("meat", ["chicken", "beef", "fish", "eggs"], ["milk", "yogurt", "salmon"], ["chips", "fries"]),
        ("fish", ["salmon", "tuna"], ["chicken", "beef", "eggs"], ["candy", "soda"]),
    ],
}

LIKES = {
    "grow": ["sweet snacks", "ice cream", "cookies", "chips", "smooth foods"],
    "see": ["fruits", "sweet foods", "juice", "snacks", "smoothies"],
    "think": ["sweet foods", "snacks", "fruit snacks", "cookies", "soft foods"],
    "fight": ["soda", "candy", "chips", "sweet snacks", "juice"],
    "feel": ["snacks", "candy", "sweet snacks", "soft foods", "chips"],
    "strong": ["chips", "fries", "snacks", "sweet foods", "crispy foods"],
}

SAFETY = [
    ("peanut", ["banana", "mango", "yogurt"], ["carrot"], ["candy"]),
    ("pork", ["orange", "rice", "milk"], ["spinach"], ["chips"]),
    ("eggs", ["mango", "chicken", "yogurt"], ["fish"], ["cake"]),
    ("alcohol", ["berries", "noodles", "milk"], ["broccoli"], ["soda"]),
]

def cap(s: str) -> str:
    return s[:1].upper() + s[1:]

def reason_super(food: str, goal: str) -> str:
    return f"{cap(food)} is a better everyday choice that can support the {goal} goal."

def reason_tiny(food: str, goal: str, disliked: str) -> str:
    return f"{cap(food)} supports the {goal} goal, but it is a small challenge because {disliked} is not usually preferred."

def reason_try(food: str, goal: str) -> str:
    return f"{cap(food)} can be enjoyable, but it should stay in try-less foods and not be treated as a {goal} goal food."

def make_chat(goal: str, likes: str, dislikes: str, blacklist: str, output: dict) -> dict:
    user = (
        f"Task: integrated_recommendation\n"
        f"Goal: {goal}\n"
        f"Likes: {likes}\n"
        f"Dislikes: {dislikes}\n"
        f"Blacklist: {blacklist}\n"
        f"Recommend foods."
    )
    return {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
            {"role": "assistant", "content": json.dumps(output, ensure_ascii=False)},
        ]
    }

def generate(seed: int = 42) -> list[dict]:
    random.seed(seed)
    examples = []

    for goal in GOALS:
        for i in range(60):
            disliked, tiny_targets, super_targets, try_targets = PATTERNS[goal][i % 2]
            tiny_foods = random.sample(tiny_targets, min(2, len(tiny_targets)))
            super_foods = random.sample(super_targets, min(2, len(super_targets)))
            try_foods = random.sample(try_targets, min(2, len(try_targets)))

            output = {
                "goal": goal,
                "super_power_foods": [{"food": f, "reason": reason_super(f, goal)} for f in super_foods],
                "tiny_hero_foods": [{"food": f, "reason": reason_tiny(f, goal, disliked)} for f in tiny_foods],
                "try_less_foods": [{"food": f, "reason": reason_try(f, goal)} for f in try_foods],
            }
            row = make_chat(goal, LIKES[goal][i % len(LIKES[goal])], disliked, "none", output)
            row["_metadata"] = {"type": "tiny_hero", "goal": goal, "dislike": disliked}
            examples.append(row)

    for i in range(60):
        blacklist, super_targets, tiny_targets, try_targets = SAFETY[i % len(SAFETY)]
        goal = GOALS[i % len(GOALS)]
        output = {
            "goal": goal,
            "super_power_foods": [{"food": f, "reason": reason_super(f, goal)} for f in random.sample(super_targets, 2) if blacklist.lower() not in f.lower()],
            "tiny_hero_foods": [{"food": f, "reason": reason_tiny(f, goal, "vegetables")} for f in tiny_targets if blacklist.lower() not in f.lower()],
            "try_less_foods": [{"food": f, "reason": reason_try(f, goal)} for f in try_targets if blacklist.lower() not in f.lower()],
        }
        row = make_chat(goal, "snacks", "vegetables", blacklist, output)
        row["_metadata"] = {"type": "safety", "goal": goal, "blacklist": blacklist}
        examples.append(row)

    random.seed(seed)
    random.shuffle(examples)
    return examples

def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            clean = {"messages": row["messages"]}
            f.write(json.dumps(clean, ensure_ascii=False) + "\n")

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(OUT_DIR_DEFAULT))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--valid-ratio", type=float, default=0.2)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    examples = generate(args.seed)
    split = int(len(examples) * (1 - args.valid_ratio))
    train, valid = examples[:split], examples[split:]

    train_path = out_dir / "tiny_hero_patch_train.jsonl"
    valid_path = out_dir / "tiny_hero_patch_valid.jsonl"
    summary_path = out_dir / "tiny_hero_patch_summary.json"

    write_jsonl(train_path, train)
    write_jsonl(valid_path, valid)

    summary = {
        "total_examples": len(examples),
        "train_examples": len(train),
        "valid_examples": len(valid),
        "tiny_hero_examples": sum(1 for e in examples if e["_metadata"]["type"] == "tiny_hero"),
        "safety_examples": sum(1 for e in examples if e["_metadata"]["type"] == "safety"),
        "seed": args.seed,
        "goal_counts": dict(Counter(e["_metadata"]["goal"] for e in examples)),
        "output_files": {
            "train": str(train_path),
            "valid": str(valid_path),
            "summary": str(summary_path),
        },
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Tiny hero patch dataset generated.")
    print(f"Train examples: {len(train)}")
    print(f"Valid examples: {len(valid)}")
    print(f"Total examples: {len(examples)}")
    print(f"Summary: {summary_path}")

    if args.verbose:
        for sample in examples[:3]:
            preview = json.dumps({"messages": sample["messages"]}, ensure_ascii=False)[:300]
            print("SAMPLE:", preview + "...")

if __name__ == "__main__":
    main()
