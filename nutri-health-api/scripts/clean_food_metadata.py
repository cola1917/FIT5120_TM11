"""
Food Metadata Cleaning Pipeline
================================
Reads:  data/seed/cn_fdes.json
Writes: data/processed/clean_food_metadata.json
        data/processed/clean_food_metadata.csv
        data/processed/removed_food_records.json
        data/processed/cleaning_summary.json

Run from project root:
    python scripts/clean_food_metadata.py

Inspection notes (cn_fdes.json):
- 9,202 records, flat JSON array
- Fields present: cn_code, gtin, food_category_code, gpc_product_code,
  descriptor, brand_name, brand_owner_name, form_of_food,
  health_grade, hcl_compliant, is_halal_auto, discontinued_date
- Food name lives in 'descriptor' (USDA-style long names)
- No image_url, nutrient values, or food_id in this file
- food_category_code is a numeric code (1–35 + None)
- health_grade is A / B / C / D / E
- 15 records have discontinued_date set
- 2,375 records have food_category_code = None (USDA school recipes)
- is_halal_auto is unreliable for pork records — keyword filtering is used
"""

from __future__ import annotations

import csv
import json
import re
import uuid
from collections import Counter, defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Config flags – set to False to disable a filter
# ---------------------------------------------------------------------------
FILTER_ALCOHOL = True
FILTER_NON_HALAL = True      # removes pork / non-halal keywords
FILTER_CAFFEINE = True
FILTER_SUPPLEMENTS = True    # removes baby food / infant formula / supplements
FILTER_ORGANS = True         # removes obscure organ meats
KEEP_UNKNOWN_CATEGORY = False  # if True, keep records that map to 'other'

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = ROOT / "data" / "seed" / "cn_fdes.json"
OUTPUT_DIR = ROOT / "data" / "processed"

# ---------------------------------------------------------------------------
# Supported goal_ids (must match backend exactly)
# ---------------------------------------------------------------------------
SUPPORTED_GOALS = {"grow", "see", "think", "fight", "feel", "strong"}

# ---------------------------------------------------------------------------
# Allowed output enumerations
# ---------------------------------------------------------------------------
ALLOWED_CATEGORIES = {
    "dairy", "meat", "fish", "vegetables", "fruits",
    "rice", "noodles", "grains", "beans", "eggs",
    "snacks", "drinks", "mixed_dishes", "sauces", "other",
}

ALLOWED_SUB_CATEGORIES = {
    # dairy sub-types
    "plain_milk", "flavored_milk", "yogurt", "cheese", "cheese_spread",
    "butter_fat", "cream", "egg_drink",
    # other categories
    "lean_meat", "processed_meat", "fish", "fruit", "vegetable",
    "rice", "noodles", "grains", "beans",
    "snack_sweet", "sugary_drink", "sauce", "mixed_dish", "other",
}

ALLOWED_HEALTH_LEVELS = {"healthy", "sometimes", "try_less"}

ALLOWED_TASTE_PROFILES = {
    "sweet", "salty", "savory", "creamy", "crunchy",
    "soft", "chewy", "sour", "mild", "rich", "fresh", "cold", "warm",
}

ALLOWED_REPLACEMENT_GROUPS = {
    "sweet_snack", "creamy_snack", "crunchy_snack", "salty_snack",
    "sugary_drink", "dairy_food", "lean_protein", "fish_protein",
    "plant_protein", "rice_meal", "noodle_meal", "vegetable_side",
    "fruit_snack", "breakfast_food", "main_meal", "sauce_condiment",
    "general_food",
}

ALLOWED_RECOMMENDATION_ROLES = {
    "super_power_candidate",   # healthy + goals → positive story role models
    "tiny_hero_candidate",     # nutritious but kids may resist (fish, veg, beans)
    "alternative_candidate",   # healthy swap options for common foods
    "try_less_candidate",      # foods to eat less of (for try_less content)
    "avoid_training_only",     # in dataset but should not appear in recommendations
}

# ---------------------------------------------------------------------------
# food_category_code → initial clean_category hint
# ---------------------------------------------------------------------------
CATEGORY_CODE_MAP: dict[int | None, str | None] = {
    1:    "dairy",
    2:    "sauces",
    3:    None,            # babyfood – filtered by FILTER_SUPPLEMENTS
    4:    "sauces",
    5:    "meat",
    6:    "mixed_dishes",
    7:    "meat",          # sausages (pork items filtered by keyword)
    8:    "grains",
    9:    "fruits",
    10:   "meat",          # pork – filtered by FILTER_NON_HALAL
    11:   "vegetables",
    12:   "other",
    13:   "meat",
    14:   "drinks",
    15:   "fish",
    16:   "beans",
    17:   "meat",
    18:   "grains",
    19:   "snacks",
    20:   "grains",
    21:   "mixed_dishes",
    22:   "mixed_dishes",
    25:   "snacks",
    35:   "other",
    None: "mixed_dishes",
}

# ---------------------------------------------------------------------------
# Filter keyword sets
# ---------------------------------------------------------------------------
ALCOHOL_KEYWORDS = {
    "alcohol", "beer", "wine", "vodka", "rum", "whiskey", "liquor",
    "cocktail", "alcoholic", "wine sauce", "beer battered", "malt beverage",
    "hard cider", "sake", "brandy", "gin", "tequila", "distilled",
}

PORK_KEYWORDS = {
    "pork", "bacon", "ham", "pepperoni", "salami", "prosciutto", "lard",
    "pig", "swine", "pancetta", "chorizo", "spareribs", "fatback",
    "pork fat", "pork loin", "pork chop", "pork rib", "pork shoulder",
    "pork belly",
}

CAFFEINE_KEYWORDS = {
    "energy drink", "caffeinated", "espresso", "energy shot", "caffeine",
}

COFFEE_DRINK_PATTERNS = [
    r"\bcoffee\b(?!.*cream)",
    r"\bcoffee,",
    r"^coffee\b",
]

SUPPLEMENT_KEYWORDS = {
    "babyfood", "infant formula", "infant", "formula", "supplement",
    "protein powder", "meal replacement", "medical food",
    "vitamin supplement", "dietary supplement", "sport supplement",
    "toddler", "junior food",
}

ORGAN_KEYWORDS = {
    "brain", "tripe", "gizzard", "liver", "kidney", "heart",
    "tongue", "sweetbread", "offal", "organ",
}

INDUSTRIAL_PATTERNS = [
    r"\d+/\d+#",
    r"\b\d+#",
    r"\bcase\s+pack\b",
    r"\bct\s+case\b",
    r"\blb\s+(tub|case|bag|jug|box|pail)\b",
    r"\bnet\s*wt\b",
    r"\b\d+-\d+pk\b",
    r"\bindustrial\b",
    r"\bbulk\s+pack\b",
]

# ---------------------------------------------------------------------------
# Category keyword inference
# ---------------------------------------------------------------------------
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "dairy": [
        "milk", "yogurt", "yoghurt", "cheese", "cream", "kefir",
        "butter", "ghee", "eggnog", "whey",
    ],
    "meat": [
        "chicken", "beef", "turkey", "lamb", "veal", "duck", "goose",
        "venison", "bison", "rabbit",
    ],
    "fish": [
        "fish", "salmon", "tuna", "sardine", "cod", "trout", "halibut",
        "tilapia", "catfish", "mackerel", "herring", "anchovy", "snapper",
        "bass", "flounder", "pollock", "shrimp", "prawn", "crab", "lobster",
        "clam", "oyster", "mussel", "scallop", "squid", "octopus", "seafood",
    ],
    "vegetables": [
        "carrot", "broccoli", "spinach", "kale", "tomato", "potato",
        "sweet potato", "pea", "corn", "cabbage", "lettuce", "pumpkin",
        "cucumber", "pepper", "zucchini", "squash", "beet", "celery",
        "onion", "garlic", "leek", "asparagus", "artichoke", "cauliflower",
        "eggplant", "okra", "radish", "turnip", "parsnip", "yam",
        "bok choy", "brussels sprout", "collard", "arugula", "fennel",
        "kohlrabi", "jicama", "watercress", "endive", "chicory",
        "alfalfa", "amaranth leaves",
    ],
    "fruits": [
        "apple", "banana", "orange", "mango", "strawberry", "blueberry",
        "berry", "kiwi", "grape", "pear", "peach", "pineapple", "melon",
        "cherry", "plum", "apricot", "fig", "date", "lemon", "lime",
        "grapefruit", "papaya", "guava", "lychee", "passion fruit",
        "pomegranate", "avocado", "acai", "acerola",
        "cranberry", "raspberry", "blackberry", "watermelon", "cantaloupe",
        "honeydew", "nectarine", "tangerine", "mandarin", "clementine",
        "persimmon", "jackfruit", "starfruit",
    ],
    "rice": [
        "brown rice", "white rice", "fried rice", "rice, brown",
        "rice, white", "jasmine rice", "basmati rice",
    ],
    "noodles": [
        "noodle", "pasta", "spaghetti", "macaroni", "ramen", "udon",
        "soba", "fettuccine", "penne", "linguine", "vermicelli",
        "rice noodle", "glass noodle",
    ],
    "grains": [
        "oat", "oatmeal", "bread", "cereal", "wheat", "whole wheat",
        "tortilla", "pancake", "waffle", "muffin", "granola", "bagel",
        "biscuit", "cracker", "pretzel", "barley", "quinoa", "farro",
        "bulgur", "millet", "amaranth grain", "spelt", "rye",
        "corn grits", "polenta",
    ],
    "beans": [
        "bean", "lentil", "chickpea", "tofu", "soy", "tempeh", "edamame",
        "hummus", "legume", "split pea",
    ],
    "eggs": [
        "egg",
    ],
    "snacks": [
        "cookie", "cake", "candy", "chocolate", "ice cream", "donut",
        "doughnut", "chips", "crisps", "dessert", "pastry", "fries",
        "popcorn", "granola bar", "fruit leather", "gummy", "wafer", "brownie",
    ],
    "drinks": [
        "soda", "soft drink", "juice", "smoothie", "milkshake", "beverage",
        "sports drink", "coconut water", "lemonade", "iced tea", "tea",
        "cocoa", "hot chocolate",
    ],
    "mixed_dishes": [
        "pizza", "sandwich", "soup", "taco", "burger", "curry", "stew",
        "bowl", "wrap", "stir-fry", "casserole", "lasagna", "burrito",
        "enchilada", "chili", "paella", "risotto", "frittata",
    ],
    "sauces": [
        "sauce", "dressing", "dip", "gravy", "ketchup", "mayonnaise",
        "mustard", "relish", "salsa", "vinegar", "oil", "butter sauce",
        "spice", "seasoning", "herb", "marinade",
    ],
}

# Priority order: more specific categories checked first
_CATEGORY_PRIORITY = [
    "rice",
    "noodles",
    "eggs",
    "fish",
    "meat",
    "dairy",
    "beans",
    "vegetables",
    "fruits",
    "grains",
    "snacks",
    "drinks",
    "mixed_dishes",
    "sauces",
]

# ---------------------------------------------------------------------------
# Helper: filter keyword check
# ---------------------------------------------------------------------------
def _contains_any(text: str, keywords: set[str]) -> str | None:
    t = text.lower()
    for kw in keywords:
        if kw in t:
            return kw
    return None


def _matches_pattern(text: str, patterns: list[str]) -> str | None:
    t = text.lower()
    for p in patterns:
        if re.search(p, t):
            return p
    return None


# ===========================================================================
# NAME NORMALIZATION
# ===========================================================================

# --- Modifier lookup tables (phrase in raw text → display form) ---

# Check longest phrases first to avoid partial matches
_FAT_PHRASES: list[tuple[str, str]] = [
    # Word-form descriptors take priority over milkfat percentage codes
    ("part skim milk", "part-skim"),
    ("part-skim milk", "part-skim"),
    ("partially skimmed", "part-skim"),
    ("partially skim", "part-skim"),
    ("part skim", "part-skim"),
    ("part-skim", "part-skim"),
    ("fat free", "fat-free"),
    ("fat-free", "fat-free"),
    ("reduced fat", "reduced-fat"),
    ("reduced-fat", "reduced-fat"),
    ("nonfat", "nonfat"),
    ("non-fat", "nonfat"),
    ("non fat", "nonfat"),
    ("lowfat", "low-fat"),
    ("low-fat", "low-fat"),
    ("low fat", "low-fat"),
    ("whole milk", "whole-milk"),   # for cheese context
    ("skim milk", "skim"),
    ("skim", "skim"),
    # Milkfat percentages: only matched when no word-form qualifier found above
    ("2% milkfat", "2%"),
    ("1% milkfat", "1%"),
    ("0% milkfat", "nonfat"),
    ("light", "light"),             # checked last — ambiguous
]

_SUGAR_PHRASES: list[tuple[str, str]] = [
    ("reduced sugar", "reduced-sugar"),
    ("reduced-sugar", "reduced-sugar"),
    ("no sugar added", "no-sugar-added"),
    ("unsweetened", "unsweetened"),
    ("sweetened", "sweetened"),
]

_SALT_PHRASES: list[tuple[str, str]] = [
    ("without salt", "unsalted"),
    ("no salt added", "unsalted"),
    ("low sodium", "low-sodium"),
    ("reduced sodium", "reduced-sodium"),
    ("unsalted", "unsalted"),
    ("with salt", "salted"),
    ("salted", "salted"),
]

_SPECIAL_PHRASES: list[tuple[str, str]] = [
    ("lactose reduced", "lactose-reduced"),
    ("lactose-reduced", "lactose-reduced"),
    ("lactose free", "lactose-free"),
    ("lactose-free", "lactose-free"),
]

_DAIRY_FLAVORS = [
    "chocolate", "vanilla", "strawberry", "lemon", "peach",
    "blueberry", "raspberry", "maple", "caramel", "fruit",
]

# Cheese varieties (check longer/more specific first)
_CHEESE_VARIETIES: list[str] = [
    "cream cheese", "cottage", "mozzarella", "ricotta", "parmesan",
    "cheddar", "provolone", "monterey jack", "colby jack", "gruyere",
    "swiss", "gouda", "brie", "camembert", "feta", "colby", "american",
    "muenster", "edam", "fontina", "limburger", "romano", "roquefort",
    "blue", "brick", "caraway", "cheshire", "gjetost", "tilsit", "neufchatel",
]

# Cream varieties (phrase → display form)
_CREAM_VARIETIES: list[tuple[str, str]] = [
    ("half and half", "half-and-half"),
    ("half-and-half", "half-and-half"),
    ("sour cream", "sour"),
    ("whipping cream", "whipping"),
    ("whipped cream", "whipped"),
    ("heavy cream", "heavy"),
    ("light cream", "light"),
    ("table cream", "table"),
    ("coffee cream", None),      # filtered by caffeine filter; skip
]

# First words of the raw descriptor that signal this is a dairy item
_DAIRY_BASE_FIRST_WORDS = {
    "cheese", "milk", "cream", "butter", "yogurt", "yoghurt",
    "kefir", "eggnog", "ghee", "whey",
}

# Multi-word base phrases (checked before single-word split)
_DAIRY_BASE_PHRASES = {
    "cream substitute", "cream cheese", "cheese spread",
    "butter oil", "sour cream",
}


def _find_modifier(text: str, phrase_table: list[tuple[str, str]]) -> str | None:
    """Return the first match from a (phrase, display) table."""
    t = text.lower()
    for phrase, display in phrase_table:
        if phrase in t:
            return display
    return None


def _find_cheese_variety(text: str) -> str | None:
    t = text.lower()
    for variety in _CHEESE_VARIETIES:
        if variety in t:
            return variety
    return None


def _find_cream_variety(text: str) -> str | None:
    t = text.lower()
    for phrase, display in _CREAM_VARIETIES:
        if display is None:
            continue
        if phrase in t:
            return display
    return None


def _find_flavor(parts: list[str]) -> str | None:
    """Find dairy flavor in comma-split parts (not base)."""
    text = " ".join(parts).lower()
    for fl in _DAIRY_FLAVORS:
        if fl in text:
            return fl
    return None


def _preprocess_name(raw: str) -> str:
    """Strip USDA program notes, pack codes, and excessive whitespace."""
    name = re.sub(r"\(includes foods for usda[^)]*\)", "", raw, flags=re.I)
    name = re.sub(r"\(usda commodity[^)]*\)", "", name, flags=re.I)
    name = re.sub(r"\(includes[^)]*\)", "", name, flags=re.I)
    name = re.sub(r"\([^)]*\)", "", name)
    name = re.sub(r"\d+/\d+#", "", name)
    name = re.sub(r"\b\d+#", "", name)
    return re.sub(r"\s+", " ", name).strip(" ,")


def _normalize_dairy(base_phrase: str, rest_parts: list[str]) -> str:
    """
    Build a clean, meaningful name for dairy items.
    Preserves: fat level, variety (cheese type/cream type), flavor, salt, special attributes.
    Reconstruction order follows natural English:
      [salt] [fat] [special] [flavor/variety] [base]
    """
    all_text = " ".join([base_phrase] + rest_parts)

    fat_mod = _find_modifier(all_text, _FAT_PHRASES)
    sugar_mod = _find_modifier(all_text, _SUGAR_PHRASES)
    salt_mod = _find_modifier(all_text, _SALT_PHRASES)
    special_mod = _find_modifier(all_text, _SPECIAL_PHRASES)
    flavor = _find_flavor(rest_parts)

    # ── Butter ──────────────────────────────────────────────────────────
    if base_phrase in {"butter oil", "butter oil, anhydrous"}:
        return "butter oil"
    if base_phrase == "butter" or base_phrase.startswith("butter"):
        if salt_mod == "unsalted":
            return "unsalted butter"
        if salt_mod and salt_mod != "salted":
            return f"{salt_mod} butter"
        # "salted" is the default — just say "butter"
        if "whipped" in all_text:
            return "whipped butter"
        return "butter"

    # ── Ghee ────────────────────────────────────────────────────────────
    if "ghee" in base_phrase:
        return "ghee"

    # ── Eggnog ──────────────────────────────────────────────────────────
    if "eggnog" in base_phrase:
        return "eggnog"

    # ── Cheese spread ───────────────────────────────────────────────────
    if base_phrase == "cheese spread" or "cheese spread" in all_text:
        parts: list[str] = []
        if fat_mod:
            parts.append(fat_mod)
        return " ".join(parts + ["cheese spread"])

    # ── Cheese ──────────────────────────────────────────────────────────
    if base_phrase == "cheese" or (base_phrase.startswith("cheese") and "spread" not in base_phrase):
        variety = _find_cheese_variety(all_text)
        parts = []
        if fat_mod:
            parts.append(fat_mod)
        if variety and variety != "cream cheese":
            parts.append(variety)
        parts.append("cheese")
        return " ".join(parts)

    # ── Cream cheese (base_phrase = "cream cheese") ──────────────────────
    if base_phrase == "cream cheese":
        parts = []
        if fat_mod:
            parts.append(fat_mod)
        return " ".join(parts + ["cream cheese"])

    # ── Milk ────────────────────────────────────────────────────────────
    if base_phrase == "milk" or base_phrase.startswith("milk"):
        if flavor:
            # Flavored milk: [sugar_mod] [flavor] milk
            parts = []
            if sugar_mod:
                parts.append(sugar_mod)
            parts.append(flavor)
            return " ".join(parts + ["milk"])
        else:
            # Plain milk: [fat_mod] milk
            parts = []
            if fat_mod and fat_mod not in {"light"}:
                parts.append(fat_mod)
            return " ".join(parts + ["milk"]) if parts else "milk"

    # ── Yogurt / Kefir ──────────────────────────────────────────────────
    if any(kw in base_phrase for kw in {"yogurt", "yoghurt", "kefir"}):
        base_clean = "kefir" if "kefir" in base_phrase else "yogurt"
        parts = []
        if fat_mod and fat_mod != "light":
            parts.append(fat_mod)
        # Greek / Icelandic are variety descriptors
        if "greek" in all_text:
            parts.append("greek")
        elif "icelandic" in all_text or "skyr" in all_text:
            parts.append("icelandic")
        if flavor and flavor not in {"fruit"}:
            parts.append(flavor)
        return " ".join(parts + [base_clean]) if parts else base_clean

    # ── Cream / Cream substitute ─────────────────────────────────────────
    if "cream substitute" in base_phrase:
        parts = []
        if fat_mod and fat_mod != "light":
            parts.append(fat_mod)
        elif "light" in all_text:
            parts.append("light")
        return " ".join(parts + ["cream substitute"])

    if "sour cream" in base_phrase or ("sour" in all_text and "cream" in base_phrase):
        parts = []
        if fat_mod:
            parts.append(fat_mod)
        return " ".join(parts + ["sour cream"])

    if base_phrase == "cream" or base_phrase.startswith("cream"):
        variety = _find_cream_variety(all_text)
        parts = []
        if fat_mod:
            parts.append(fat_mod)
        if variety and variety not in {"light"}:
            parts.append(variety)
        return " ".join(parts + ["cream"])

    # ── Whey / other dairy ───────────────────────────────────────────────
    parts = []
    if fat_mod:
        parts.append(fat_mod)
    if flavor:
        parts.append(flavor)
    return " ".join(parts + [base_phrase]) if parts else base_phrase


# Noise tokens stripped from general (non-dairy) food names
_GENERAL_NOISE_WORDS = [
    r"\(includes foods for usda[^)]*\)",
    r"\(usda[^)]*\)",
    r"\(alaska native\)",
    r"\([^)]*\)",
    r"\busda\b",
    r"\braw\b",
    r"\bcooked\b",
    r"\bcanned\b",
    r"\bfrozen\b",
    r"\bdrained\b",
    r"\brinsed\b",
    r"\bsolids and liquids\b",
    r"\bsolids\b",
    r"\bliquids\b",
    r"\bregular\b",
    r"\bunenriched\b",
    r"\benriched\b",
    r"\bfluid\b",
    r"\bready-to-eat\b",
    r"\bready to eat\b",
    r"\bprepared\b",
    r"\bunprepared\b",
    r"\bunspecified\b",
    r"\bwithout salt\b",
    r"\bwith salt\b",
    r"\bboiled\b",
    r"\bsteamed\b",
    r"\bdehydrated\b",
    r"\bdried\b",
    r"\bcommercially prepared\b",
    r"\bfully cooked\b",
    r"\bfarm-raised\b",
    r"\bwild-caught\b",
    r"\bgrass-fed\b",
    r"\borganic\b",
    r"\bfree-range\b",
    r"\buncooked\b",
    r"\bbroilers or fryers\b",
    r"\bbroiler\b",
    r"\bseparable lean (and fat|only)\b",
    r"\bseparable lean\b",
    r"\btrimmed to \d['']\d? fat\b",
    r"\bchoice\b",
    r"\bselect\b",
    r"\bprime\b",
    r"\blong-grain\b",
    r"\bshort-grain\b",
    r"\bmedium-grain\b",
    r"\bcooked with water\b",
    r"\bin water\b",
    r"\bin oil\b",
    r"\bin brine\b",
    r"\blight syrup\b",
    r"\bheavy syrup\b",
    r"\bno salt added\b",
    r"\bmature seeds?\b",
    r"\bwith skin\b",
    r"\bwithout skin\b",
    r"\bskinless\b",
    r"\bboneless\b",
    r"\bbone-in\b",
    r"\bmeat only\b",
    r"\bwith bone\b",
    r"\beuropean\b",
    r"\bmixed species\b",
    r"\batlantic\b",
    r"\bpacific\b",
    r"\bsmall curd\b",
    r"\blarge curd\b",
    r"\blight meat\b",
    r"\bdark meat\b",
    r"\bground\b(?! beef| turkey| chicken| pork)",
]

# Useful qualifiers to check for in non-dairy names
_GENERAL_KEEP_QUALIFIERS: list[str] = [
    # Must be checked longest-first
    "sweet potato", "sweet pepper",
    "brown rice", "white rice", "fried rice",
    "whole wheat", "whole grain",
    "chicken breast", "chicken thigh", "chicken wing", "chicken drumstick",
    "chicken leg",
    "ground beef", "ground turkey", "ground chicken",
    "kidney bean", "black bean", "pinto bean", "navy bean", "chickpea",
    "peanut butter", "almond butter",
    "orange juice", "apple juice", "grape juice",
    "oatmeal", "oat",
    "low-fat", "low fat", "lowfat", "skim", "nonfat",
    "salmon fillet", "tuna steak",
    "almond milk", "soy milk", "oat milk",
    "tofu", "tempeh",
    "shrimp", "prawn",
    "breast", "thigh", "wing", "drumstick",
    "fillet", "steak",
]


def _normalize_general(base_phrase: str, rest_parts: list[str]) -> str:
    """
    Build a clean name for non-dairy foods.
    Preserves useful qualifiers; strips USDA-style noise.
    """
    combined = " ".join([base_phrase] + rest_parts).lower()

    # Singularize common plural base words
    singular_map = {
        "apples": "apple", "oranges": "orange", "bananas": "banana",
        "carrots": "carrot", "potatoes": "potato", "tomatoes": "tomato",
        "eggs": "egg", "beans": "bean", "oats": "oat",
        "grapes": "grape", "peaches": "peach", "berries": "berry",
        "cherries": "cherry", "lemons": "lemon", "limes": "lime",
        "mangoes": "mango", "pears": "pear", "plums": "plum",
        "dates": "date", "figs": "fig",
        "noodles": "noodle", "cereals": "cereal",
        "crackers": "cracker", "cookies": "cookie",
        "snacks": "snack", "spices": "spice",
    }
    base_clean = singular_map.get(base_phrase, base_phrase)

    # Check for keep-qualifiers in the full text (longest match first)
    kept_qualifiers: list[str] = []
    for phrase in sorted(_GENERAL_KEEP_QUALIFIERS, key=len, reverse=True):
        if phrase in combined and phrase not in " ".join(kept_qualifiers):
            kept_qualifiers.append(phrase)

    # Build candidate from base + qualifiers
    if kept_qualifiers:
        qualifier_str = " ".join(kept_qualifiers)
        # If the qualifier already subsumes the base, use qualifier alone
        if base_clean in qualifier_str:
            candidate = qualifier_str
        elif qualifier_str in base_clean:
            candidate = base_clean
        else:
            candidate = f"{base_clean} {qualifier_str}"
    else:
        candidate = base_clean

    # Strip remaining noise tokens
    result = candidate
    for pattern in _GENERAL_NOISE_WORDS:
        result = re.sub(pattern, " ", result, flags=re.I)
    result = re.sub(r"\s+", " ", result).strip(" ,-")

    # Final corrections
    corrections = {
        "lowfat milk": "low-fat milk",
        "yoghurt": "yogurt",
    }
    return corrections.get(result, result) or base_phrase


def normalize_food_name(raw_name: str) -> str:
    """
    Convert a USDA-style descriptor to a clean, child-friendly food name.
    Dairy items get structured modifier-aware normalization.
    Non-dairy items get qualifier-preserving noise stripping.

    Examples:
      "Cheese, cottage, lowfat, 1% milkfat, lactose reduced" -> "low-fat cottage cheese"
      "Cheese, mozzarella, part skim milk"                   -> "part-skim mozzarella cheese"
      "Cheese, ricotta, whole milk"                          -> "whole-milk ricotta cheese"
      "Milk, chocolate, lowfat, reduced sugar"               -> "reduced-sugar chocolate milk"
      "Cream, half and half, fat free"                       -> "fat-free half-and-half cream"
      "Butter, without salt"                                 -> "unsalted butter"
      "Butter oil, anhydrous"                                -> "butter oil"
      "Eggnog"                                               -> "eggnog"
      "Cream substitute, liquid, light"                      -> "light cream substitute"
      "Apples, raw, with skin"                               -> "apple"
      "Chicken, broilers or fryers, breast, skinless ..."    -> "chicken breast"
      "Rice, brown, long-grain, cooked"                      -> "brown rice"
    """
    if not raw_name:
        return ""

    # Phase 1: pre-process
    name = _preprocess_name(raw_name)
    if not name:
        return raw_name.strip().lower()

    # Phase 2: split into parts
    parts = [p.strip() for p in name.split(",") if p.strip()]
    if not parts:
        return raw_name.strip().lower()

    base_phrase = parts[0].lower().strip()
    rest_parts = [p.lower().strip() for p in parts[1:]]

    # Phase 3: route to dairy vs general normalizer
    base_first_word = base_phrase.split()[0] if base_phrase else ""

    # Check multi-word dairy base phrases first
    is_dairy_base = (
        base_first_word in _DAIRY_BASE_FIRST_WORDS
        or any(base_phrase.startswith(dp) for dp in _DAIRY_BASE_PHRASES)
    )

    if is_dairy_base:
        result = _normalize_dairy(base_phrase, rest_parts)
    else:
        result = _normalize_general(base_phrase, rest_parts)

    return result.strip() if result.strip() else raw_name.strip().lower()


def make_display_name(clean_name: str) -> str:
    return clean_name.title() if clean_name else ""


# ===========================================================================
# SUB-CATEGORY INFERENCE
# ===========================================================================

def infer_sub_category(raw_name: str, clean_name: str, clean_category: str) -> str:
    """
    Assign a fine-grained sub_category within each clean_category.
    Used to drive dairy-specific goal tag and health level logic.
    """
    all_lower = (raw_name + " " + clean_name).lower()

    if clean_category == "dairy":
        # Priority order: most-specific checks first
        if "butter oil" in all_lower or re.search(r"\banhydrous\b", all_lower):
            return "butter_fat"
        if re.search(r"\bbutter\b", all_lower) or "ghee" in all_lower:
            return "butter_fat"
        if "eggnog" in all_lower:
            return "egg_drink"
        # Cream cheese must be checked before cream
        if "cream cheese" in all_lower:
            return "cheese"
        if "cheese spread" in all_lower:
            return "cheese_spread"
        if re.search(r"\bprocess(ed)?\b.*\bcheese\b", all_lower) or re.search(r"\bcheese\b.*\bspread\b", all_lower):
            return "cheese_spread"
        if re.search(r"\bcheese\b", all_lower):
            return "cheese"
        if re.search(r"\byogurt\b|\byoghurt\b|\bkefir\b", all_lower):
            return "yogurt"
        # Cream substitute and cream variants (after cheese checks)
        if "cream substitute" in all_lower or "coffee whitener" in all_lower:
            return "cream"
        if re.search(r"\bcream\b", all_lower):
            return "cream"
        # Milk (after cream checks)
        if re.search(r"\bmilk\b", all_lower):
            flavored_markers = {
                "chocolate", "vanilla", "strawberry", "flavored", "flavoured",
                "fruit-", "fruity",
            }
            if any(fl in all_lower for fl in flavored_markers):
                return "flavored_milk"
            return "plain_milk"
        return "plain_milk"   # fallback for dairy

    if clean_category == "meat":
        processed_patterns = {
            "sausage", "hot dog", "hotdog", "frankfurter", "bratwurst",
            "bologna", "kielbasa", "loaf", "luncheon", "deli meat",
            "cured", "smoked meat", "jerky", "pepperoni",
        }
        if any(p in all_lower for p in processed_patterns):
            return "processed_meat"
        return "lean_meat"

    if clean_category == "fish":
        return "fish"
    if clean_category == "fruits":
        return "fruit"
    if clean_category == "vegetables":
        return "vegetable"
    if clean_category == "rice":
        return "rice"
    if clean_category == "noodles":
        return "noodles"
    if clean_category == "grains":
        return "grains"
    if clean_category == "beans":
        return "beans"
    if clean_category == "snacks":
        return "snack_sweet"
    if clean_category == "drinks":
        return "sugary_drink"
    if clean_category == "sauces":
        return "sauce"
    if clean_category == "mixed_dishes":
        return "mixed_dish"
    return "other"


# ===========================================================================
# CATEGORY INFERENCE
# ===========================================================================

def infer_category(raw_name: str, category_code: int | None) -> str:
    name_lower = raw_name.lower()
    for cat in _CATEGORY_PRIORITY:
        keywords = CATEGORY_KEYWORDS.get(cat, [])
        for kw in keywords:
            if len(kw) <= 4:
                if re.search(rf"\b{re.escape(kw)}\b", name_lower):
                    return cat
            else:
                if kw in name_lower:
                    return cat
    code_cat = CATEGORY_CODE_MAP.get(category_code, "other")
    return code_cat if code_cat else "other"


# ===========================================================================
# GOAL TAG INFERENCE — dairy-aware, sub_category-driven
# ===========================================================================

def infer_goal_tags(
    clean_name: str,
    clean_category: str,
    sub_category: str,
    health_level: str,
) -> list[str]:
    """
    Map food to supported goal_ids.
    Dairy items use sub_category to avoid blanket grow/strong/think assignments.
    Foods with health_level == 'try_less' receive no goal tags.
    """
    tags: set[str] = set()
    name = clean_name.lower()

    # === DAIRY ===
    if clean_category == "dairy":
        if sub_category in {"butter_fat", "cream"}:
            pass  # pure fats / cream — no nutritional goal benefit for children

        elif sub_category == "egg_drink":   # eggnog
            pass  # high sugar, seasonal treat — no goals

        elif sub_category == "flavored_milk":  # chocolate milk, vanilla milk
            if health_level != "try_less":
                tags.add("grow")  # still provides calcium/protein, conservative

        elif sub_category in {"plain_milk"}:
            tags.add("grow")
            tags.add("strong")
            if health_level != "try_less":
                tags.add("think")   # dairy + brain health (choline, B12)

        elif sub_category == "yogurt":
            tags.add("grow")
            tags.add("strong")
            if health_level != "try_less":
                tags.add("think")

        elif sub_category == "cheese":
            # Only assign goals when health_level is not try_less
            if health_level in {"healthy", "sometimes"}:
                tags.add("grow")
                tags.add("strong")
            # No think for cheese — less relevant than plain dairy

        elif sub_category == "cheese_spread":
            # Only genuinely healthy (grade A/B) cheese spreads
            if health_level == "healthy":
                tags.add("grow")

        # Unknown dairy sub-type fallback
        else:
            if health_level in {"healthy", "sometimes"}:
                tags.add("grow")
                tags.add("strong")

    # === MEAT ===
    elif clean_category == "meat":
        tags.add("grow")
        tags.add("strong")

    # === FISH ===
    elif clean_category == "fish":
        tags.add("see")
        tags.add("strong")
        tags.add("think")   # omega-3 for brain

    # === VEGETABLES ===
    elif clean_category == "vegetables":
        tags.add("grow")
        tags.add("feel")
        tags.add("fight")
        see_veg = {"carrot", "sweet potato", "spinach", "kale", "broccoli", "pumpkin", "squash"}
        if any(v in name for v in see_veg):
            tags.add("see")
        fight_veg = {"broccoli", "tomato", "pepper", "garlic", "spinach", "kale"}
        if any(v in name for v in fight_veg):
            tags.add("fight")

    # === FRUITS ===
    elif clean_category == "fruits":
        tags.add("see")
        tags.add("feel")
        tags.add("fight")
        tags.add("think")
        fight_fruits = {"orange", "kiwi", "berry", "strawberry", "blueberry", "cranberry", "lemon", "lime"}
        if any(f in name for f in fight_fruits):
            tags.add("fight")

    # === RICE ===
    elif clean_category == "rice":
        tags.add("feel")

    # === NOODLES ===
    elif clean_category == "noodles":
        tags.add("feel")

    # === GRAINS ===
    elif clean_category == "grains":
        tags.add("feel")
        think_grains = {"oat", "oatmeal", "whole wheat", "whole grain"}
        if any(g in name for g in think_grains):
            tags.add("think")

    # === BEANS ===
    elif clean_category == "beans":
        tags.add("grow")
        tags.add("strong")
        tags.add("think")    # plant protein + complex carbs

    # === EGGS ===
    elif clean_category == "eggs":
        # Note: sub_category "egg_drink" (eggnog) is handled under dairy
        tags.add("grow")
        tags.add("strong")
        tags.add("see")     # lutein/zeaxanthin for eye health

    # Safety net: try_less foods get no goal recommendations
    if health_level == "try_less":
        tags.clear()

    return sorted(t for t in tags if t in SUPPORTED_GOALS)


# ===========================================================================
# TASTE PROFILE INFERENCE
# ===========================================================================

def infer_taste_profile(clean_name: str, clean_category: str) -> list[str]:
    tags: set[str] = set()
    name = clean_name.lower()

    sweet_triggers = {
        "fruit", "apple", "banana", "orange", "mango", "berry", "grape",
        "pear", "peach", "pineapple", "melon", "cherry", "candy", "cake",
        "cookie", "ice cream", "soda", "juice", "chocolate", "honey",
        "sweet", "dessert", "pastry", "donut", "eggnog",
    }
    salty_crunchy_triggers = {
        "chips", "crisps", "fries", "cracker", "pretzel", "popcorn",
    }
    creamy_triggers = {
        "yogurt", "milk", "cheese", "cream", "ice cream",
        "milkshake", "smoothie", "butter", "eggnog",
    }
    crunchy_triggers = {
        "apple", "carrot", "celery", "chips", "cracker", "cereal",
        "granola", "nut", "almond", "cashew",
    }
    savory_triggers = {
        "chicken", "beef", "fish", "turkey", "lamb", "salmon", "tuna",
        "egg", "bean", "lentil", "tofu", "soup", "stew", "curry",
        "sandwich", "burger", "pizza", "pasta", "noodle",
    }
    fresh_triggers = {
        "salad", "lettuce", "spinach", "cucumber", "tomato",
        "mint", "parsley", "coriander",
    }
    warm_triggers = {
        "soup", "stew", "curry", "noodle", "rice", "oatmeal", "porridge",
        "casserole", "tea",
    }

    if any(kw in name for kw in sweet_triggers) or clean_category == "fruits":
        tags.add("sweet")
    if any(kw in name for kw in salty_crunchy_triggers):
        tags.add("salty")
        tags.add("crunchy")
    if any(kw in name for kw in creamy_triggers) or clean_category == "dairy":
        tags.add("creamy")
    if any(kw in name for kw in crunchy_triggers):
        tags.add("crunchy")
    if any(kw in name for kw in savory_triggers) or clean_category in {"meat", "fish", "eggs", "beans", "mixed_dishes"}:
        tags.add("savory")
    if any(kw in name for kw in fresh_triggers) or clean_category == "vegetables":
        tags.add("fresh")
    if any(kw in name for kw in warm_triggers) or clean_category in {"rice", "noodles"}:
        tags.add("warm")

    if not tags:
        tags.add("mild")

    return sorted(tags & ALLOWED_TASTE_PROFILES)


# ===========================================================================
# HEALTH LEVEL INFERENCE — dairy-aware, sub_category-driven
# ===========================================================================

def infer_health_level(
    clean_name: str,
    clean_category: str,
    sub_category: str,
    grade: str | None,
) -> str:
    """
    Determine health_level: 'healthy' | 'sometimes' | 'try_less'.
    Dairy sub-types get fine-grained rules based on fat content and sweetness.
    Grade D/E → try_less for most non-core categories.
    """
    name = clean_name.lower()
    grade_upper = (grade or "").upper()

    # Universal try_less triggers from name
    try_less_name = {
        "soda", "soft drink", "candy", "cookie", "cake", "ice cream",
        "donut", "doughnut", "chips", "fries", "fried", "dessert",
        "pastry", "syrup", "sweetened beverage", "energy drink",
        "chocolate bar", "toffee", "caramel",
    }
    if any(kw in name for kw in try_less_name):
        return "try_less"

    # ── Dairy-specific rules ───────────────────────────────────────────
    if clean_category == "dairy":
        if sub_category == "butter_fat":
            # Butter and butter oil are high in saturated fat
            return "try_less"

        if sub_category == "egg_drink":  # eggnog
            if grade_upper in {"D", "E"}:
                return "try_less"
            return "sometimes"   # festive, rich, high-calorie

        if sub_category == "cream":
            if grade_upper in {"D", "E"}:
                return "try_less"
            return "sometimes"

        if sub_category == "cheese_spread":
            if grade_upper in {"D", "E"}:
                return "try_less"
            return "sometimes"

        if sub_category == "cheese":
            if grade_upper in {"D", "E"}:
                return "try_less"
            # Low-fat/part-skim cheese with good grade → healthy
            low_fat_markers = {"low-fat", "part-skim", "nonfat", "skim", "fat-free", "reduced-fat"}
            if grade_upper in {"A", "B"} and any(m in name for m in low_fat_markers):
                return "healthy"
            if grade_upper in {"A", "B"}:
                return "sometimes"
            return "sometimes"

        if sub_category == "flavored_milk":
            if grade_upper in {"D", "E"}:
                return "try_less"
            # Reduced-sugar flavored milk is better than regular
            if "reduced-sugar" in name or "no-sugar-added" in name:
                return "sometimes"
            return "sometimes"

        if sub_category in {"plain_milk", "yogurt"}:
            if grade_upper in {"D", "E"}:
                return "sometimes"
            if grade_upper in {"A", "B"}:
                return "healthy"
            if grade_upper == "C":
                return "sometimes"
            return "healthy"

        # Default dairy fallback
        if grade_upper in {"D", "E"}:
            return "try_less"
        if grade_upper in {"A", "B"}:
            return "healthy"
        return "sometimes"

    # ── Non-dairy ──────────────────────────────────────────────────────
    if grade_upper in {"D", "E"}:
        return "try_less"

    core_categories = {
        "meat", "fish", "vegetables", "fruits", "rice", "noodles",
        "grains", "beans", "eggs",
    }
    if grade_upper in {"A", "B"} and clean_category in core_categories:
        return "healthy"
    if grade_upper == "C":
        return "sometimes"
    if grade_upper in {"A", "B"}:
        return "sometimes"

    # Fallback by category
    if clean_category in core_categories:
        return "healthy"
    return "sometimes"


# ===========================================================================
# REPLACEMENT GROUP INFERENCE
# ===========================================================================

def infer_replacement_group(clean_name: str, clean_category: str) -> str:
    name = clean_name.lower()

    sugary_drink_triggers = {"soda", "soft drink", "juice drink", "sweetened", "energy drink", "lemonade"}
    creamy_snack_triggers = {"ice cream", "yogurt", "milkshake", "pudding", "custard", "eggnog"}
    crunchy_snack_triggers = {"chips", "crisps", "fries", "cracker", "popcorn", "pretzel"}
    sweet_snack_triggers = {"candy", "cookie", "cake", "dessert", "pastry", "donut", "brownie", "chocolate bar"}
    breakfast_triggers = {"oat", "oatmeal", "cereal", "granola", "bread", "bagel", "toast", "muffin", "pancake", "waffle"}

    if any(kw in name for kw in sugary_drink_triggers):
        return "sugary_drink"
    if any(kw in name for kw in creamy_snack_triggers):
        return "creamy_snack"
    if any(kw in name for kw in crunchy_snack_triggers):
        return "crunchy_snack"
    if any(kw in name for kw in sweet_snack_triggers):
        return "sweet_snack"

    category_map = {
        "fruits":       "fruit_snack",
        "dairy":        "dairy_food",
        "meat":         "lean_protein",
        "fish":         "fish_protein",
        "beans":        "plant_protein",
        "rice":         "rice_meal",
        "noodles":      "noodle_meal",
        "vegetables":   "vegetable_side",
        "mixed_dishes": "main_meal",
        "sauces":       "sauce_condiment",
        "snacks":       "sweet_snack",
        "drinks":       "sugary_drink",
        "eggs":         "lean_protein",
    }
    if clean_category in category_map:
        return category_map[clean_category]
    if clean_category == "grains":
        if any(kw in name for kw in breakfast_triggers):
            return "breakfast_food"
        return "general_food"
    return "general_food"


# ===========================================================================
# RECOMMENDATION ROLE INFERENCE
# ===========================================================================

def infer_recommendation_role(
    clean_name: str,
    clean_category: str,
    sub_category: str,
    health_level: str,
    goal_tags: list[str],
) -> str:
    """
    Assign a recommendation role used to generate child-friendly story content.

    avoid_training_only : in dataset but never shown as a recommendation
    try_less_candidate  : foods kids should eat less of (soda, candy, chips)
    super_power_candidate : healthy foods with clear goals (carrot, salmon, yogurt)
    tiny_hero_candidate : nutritious but kids may resist (broccoli, sardines, lentils)
    alternative_candidate : healthy swaps for common less-healthy foods
    """
    name = clean_name.lower()

    # avoid_training_only: pure fats / cream / industrial-adjacent items with no goals
    avoid_sub_categories = {"butter_fat", "cream"}
    avoid_name_patterns = {"butter oil", "cream substitute", "lard", "margarine", "ghee"}
    if sub_category in avoid_sub_categories and not goal_tags:
        return "avoid_training_only"
    if any(n in name for n in avoid_name_patterns) and not goal_tags:
        return "avoid_training_only"
    if sub_category == "cheese_spread" and health_level == "try_less":
        return "avoid_training_only"

    # try_less_candidate: unhealthy foods featured in "try less" story segments
    if health_level == "try_less":
        return "try_less_candidate"

    # super_power_candidate: healthy + meaningful goals → story heroes
    if health_level == "healthy" and goal_tags:
        return "super_power_candidate"

    # tiny_hero_candidate: nutritious but children often resist
    tiny_hero_cats = {"vegetables", "beans", "fish"}
    reluctant_names = {
        "broccoli", "spinach", "kale", "brussels", "asparagus",
        "sardine", "anchovy", "mackerel", "herring",
        "lentil", "chickpea", "tofu", "tempeh",
    }
    if clean_category in tiny_hero_cats and health_level in {"healthy", "sometimes"}:
        if any(n in name for n in reluctant_names) or clean_category == "fish":
            return "tiny_hero_candidate"
        if clean_category == "vegetables" and health_level == "healthy":
            return "tiny_hero_candidate"

    # alternative_candidate: healthy substitutions for common less-healthy foods
    alt_subs = {"yogurt", "plain_milk", "fruit", "grains"}
    alt_cats = {"fruits", "grains", "eggs", "beans"}
    if sub_category in alt_subs or clean_category in alt_cats:
        if health_level in {"healthy", "sometimes"}:
            return "alternative_candidate"

    # Default for kept foods with goals
    if goal_tags and health_level in {"healthy", "sometimes"}:
        return "super_power_candidate"
    if health_level in {"healthy", "sometimes"}:
        return "alternative_candidate"

    return "alternative_candidate"


# ===========================================================================
# FILTER LOGIC
# ===========================================================================

def should_remove(
    raw_name: str,
    category_code: int | None,
    discontinued: bool,
) -> tuple[bool, str | None]:
    name_lower = (raw_name or "").lower()

    if discontinued:
        return True, "discontinued"

    if FILTER_SUPPLEMENTS:
        kw = _contains_any(name_lower, SUPPLEMENT_KEYWORDS)
        if kw:
            return True, f"supplement_or_babyfood: '{kw}'"
        if category_code == 3:
            return True, "supplement_or_babyfood: category_code=3 (babyfood)"

    if FILTER_ALCOHOL:
        kw = _contains_any(name_lower, ALCOHOL_KEYWORDS)
        if kw:
            return True, f"alcohol: '{kw}'"

    if FILTER_NON_HALAL:
        kw = _contains_any(name_lower, PORK_KEYWORDS)
        if kw:
            return True, f"non_halal_pork: '{kw}'"
        if category_code == 10:
            return True, "non_halal_pork: category_code=10 (pork)"

    if FILTER_CAFFEINE:
        kw = _contains_any(name_lower, CAFFEINE_KEYWORDS)
        if kw:
            return True, f"caffeine: '{kw}'"
        for p in COFFEE_DRINK_PATTERNS:
            if re.search(p, name_lower):
                return True, "caffeine: coffee drink"

    if FILTER_ORGANS:
        kw = _contains_any(name_lower, ORGAN_KEYWORDS)
        if kw:
            return True, f"organ_meat: '{kw}'"

    p = _matches_pattern(name_lower, INDUSTRIAL_PATTERNS)
    if p:
        return True, f"industrial_noisy: matches '{p}'"

    if category_code == 35:
        return True, "niche_regional: category_code=35 (Alaska Native)"

    if not KEEP_UNKNOWN_CATEGORY:
        inferred = infer_category(raw_name, category_code)
        if inferred == "other":
            return True, "unknown_category: maps to 'other' (KEEP_UNKNOWN_CATEGORY=False)"

    return False, None


# ===========================================================================
# DEDUPLICATION
# ===========================================================================

def _grade_rank(grade: str | None) -> int:
    order = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}
    return order.get((grade or "").upper(), 5)


def deduplicate(records: list[dict]) -> tuple[list[dict], list[dict]]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in records:
        key = (r["clean_name"], r["clean_category"])
        groups[key].append(r)

    kept, duplicates = [], []
    for key, group in groups.items():
        if len(group) == 1:
            kept.append(group[0])
            continue
        group.sort(key=lambda r: (
            not r.get("hcl_compliant", False),
            _grade_rank(r.get("grade")),
            len(r.get("raw_name") or ""),
            0 if r.get("image_url") else 1,
        ))
        kept.append(group[0])
        for dup in group[1:]:
            dup["removed"] = True
            dup["remove_reason"] = f"duplicate of cn_code={group[0]['source_id']}"
            duplicates.append(dup)
    return kept, duplicates


# ===========================================================================
# RECORD PROCESSING
# ===========================================================================

def load_input(path: Path) -> list[dict]:
    print(f"Loading: {path}")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        print(f"  -> Found {len(data)} records (flat array)")
        return data
    if isinstance(data, dict):
        for key in ("foods", "data", "records", "items", "results"):
            if key in data and isinstance(data[key], list):
                print(f"  -> Found {len(data[key])} records under key '{key}'")
                return data[key]
        raise ValueError(
            f"Unexpected JSON object structure. Top-level keys: {list(data.keys())}"
        )
    raise ValueError(f"Unexpected JSON type: {type(data).__name__}.")


def process_record(raw: dict) -> dict:
    cn_code = raw.get("cn_code")
    raw_name = (
        raw.get("descriptor") or raw.get("name") or raw.get("food_name") or ""
    ).strip()

    clean_name = normalize_food_name(raw_name)
    display_name = make_display_name(clean_name)

    category_code = raw.get("food_category_code")
    clean_category = infer_category(raw_name, category_code)
    original_category = str(category_code) if category_code is not None else None

    grade = raw.get("health_grade") or raw.get("grade")
    hcl_compliant = bool(raw.get("hcl_compliant", False))
    image_url = raw.get("image_url") or None

    sub_category = infer_sub_category(raw_name, clean_name, clean_category)
    health_level = infer_health_level(clean_name, clean_category, sub_category, grade)
    goal_tags = infer_goal_tags(clean_name, clean_category, sub_category, health_level)
    taste_profile = infer_taste_profile(clean_name, clean_category)
    replacement_group = infer_replacement_group(clean_name, clean_category)
    recommendation_role = infer_recommendation_role(
        clean_name, clean_category, sub_category, health_level, goal_tags
    )

    return {
        "food_id":            str(cn_code) if cn_code is not None else str(uuid.uuid4()),
        "source_id":          str(cn_code) if cn_code is not None else None,
        "raw_name":           raw_name,
        "clean_name":         clean_name,
        "display_name":       display_name,
        "clean_category":     clean_category,
        "sub_category":       sub_category,
        "original_category":  original_category,
        "grade":              (grade or "").upper() or None,
        "health_level":       health_level,
        "goal_tags":          goal_tags,
        "taste_profile":      taste_profile,
        "replacement_group":  replacement_group,
        "recommendation_role": recommendation_role,
        "child_friendly":     True,
        "hcl_compliant":      hcl_compliant,
        "image_url":          image_url,
        "removed":            False,
        "remove_reason":      None,
    }


# ===========================================================================
# BEFORE / AFTER EXAMPLES
# ===========================================================================

EXAMPLE_RAW_NAMES = [
    "Butter, without salt",
    "Butter oil, anhydrous",
    "Cheese, cottage, lowfat, 1% milkfat, lactose reduced",
    "Cheese, mozzarella, part skim milk",
    "Cheese, ricotta, whole milk",
    "Cheese spread, American or Cheddar cheese base, reduced fat",
    "Cream, half and half, fat free",
    "Eggnog",
    "Milk, chocolate, lowfat, reduced sugar",
    "Cream substitute, liquid, light",
]


def print_before_after_examples(raw_records: list[dict]) -> None:
    """Look up the example records from raw data and print their cleaned output."""
    raw_map = {r.get("descriptor", ""): r for r in raw_records}

    print("\n" + "=" * 70)
    print("BEFORE / AFTER EXAMPLES")
    print("=" * 70)

    for raw_name in EXAMPLE_RAW_NAMES:
        raw = raw_map.get(raw_name)
        if raw is None:
            print(f"\n[NOT FOUND IN DATA] {raw_name}")
            continue

        record = process_record(raw)
        grade = record.get("grade") or "?"
        print(f"\n  RAW          : {raw_name}")
        print(f"  clean_name   : {record['clean_name']}")
        print(f"  sub_category : {record['sub_category']}")
        print(f"  category     : {record['clean_category']}")
        print(f"  grade        : {grade}")
        print(f"  health_level : {record['health_level']}")
        print(f"  goal_tags    : {record['goal_tags']}")
        print(f"  rec_role     : {record['recommendation_role']}")

    print("=" * 70)


# ===========================================================================
# MAIN PIPELINE
# ===========================================================================

def run():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    raw_records = load_input(INPUT_PATH)
    total_input = len(raw_records)
    print(f"Total input records: {total_input}")

    kept_records: list[dict] = []
    removed_records: list[dict] = []
    removal_reason_counts: dict[str, int] = defaultdict(int)

    print("Processing records...")
    for i, raw in enumerate(raw_records, 1):
        if i % 1000 == 0:
            print(f"  {i}/{total_input}...")

        raw_name = (raw.get("descriptor") or raw.get("name") or raw.get("food_name") or "").strip()
        category_code = raw.get("food_category_code")
        discontinued = raw.get("discontinued_date") is not None

        remove, reason = should_remove(raw_name, category_code, discontinued)
        record = process_record(raw)

        if remove:
            reason_key = reason.split(":")[0] if reason else "unknown"
            removal_reason_counts[reason_key] += 1
            record["removed"] = True
            record["remove_reason"] = reason
            record["child_friendly"] = False
            removed_records.append(record)
        else:
            kept_records.append(record)

    print(f"\nBefore deduplication: {len(kept_records)} kept, {len(removed_records)} removed")
    kept_records, dup_removed = deduplicate(kept_records)
    removed_records.extend(dup_removed)
    removal_reason_counts["duplicate"] += len(dup_removed)
    print(f"After deduplication:  {len(kept_records)} kept, {len(removed_records)} removed")

    # --- Write outputs ---

    csv_fields = [
        "food_id", "source_id", "raw_name", "clean_name", "display_name",
        "clean_category", "sub_category", "original_category", "grade",
        "health_level", "goal_tags", "taste_profile", "replacement_group",
        "recommendation_role", "child_friendly", "hcl_compliant", "image_url",
        "removed", "remove_reason",
    ]

    clean_json_path = OUTPUT_DIR / "clean_food_metadata.json"
    with open(clean_json_path, "w", encoding="utf-8") as f:
        json.dump(kept_records, f, indent=2, ensure_ascii=False)
    print(f"\nWrote: {clean_json_path}  ({len(kept_records)} records)")

    clean_csv_path = OUTPUT_DIR / "clean_food_metadata.csv"
    with open(clean_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()
        for rec in kept_records:
            row = dict(rec)
            row["goal_tags"] = ",".join(rec.get("goal_tags") or [])
            row["taste_profile"] = ",".join(rec.get("taste_profile") or [])
            writer.writerow(row)
    print(f"Wrote: {clean_csv_path}")

    removed_json_path = OUTPUT_DIR / "removed_food_records.json"
    removed_output = [
        {
            "food_id":        r.get("food_id"),
            "source_id":      r.get("source_id"),
            "raw_name":       r.get("raw_name"),
            "clean_name":     r.get("clean_name"),
            "clean_category": r.get("clean_category"),
            "sub_category":   r.get("sub_category"),
            "grade":          r.get("grade"),
            "remove_reason":  r.get("remove_reason"),
        }
        for r in removed_records
    ]
    with open(removed_json_path, "w", encoding="utf-8") as f:
        json.dump(removed_output, f, indent=2, ensure_ascii=False)
    print(f"Wrote: {removed_json_path}  ({len(removed_output)} records)")

    category_counts = Counter(r["clean_category"] for r in kept_records)
    sub_cat_counts = Counter(r["sub_category"] for r in kept_records)
    goal_counts: Counter = Counter()
    for r in kept_records:
        for g in r.get("goal_tags") or []:
            goal_counts[g] += 1
    health_level_counts = Counter(r["health_level"] for r in kept_records)
    replacement_group_counts = Counter(r["replacement_group"] for r in kept_records)
    rec_role_counts = Counter(r["recommendation_role"] for r in kept_records)
    grade_counts = Counter(r.get("grade") or "Unknown" for r in kept_records)

    summary = {
        "input_file": str(INPUT_PATH),
        "total_input": total_input,
        "total_kept": len(kept_records),
        "total_removed": len(removed_records),
        "removal_by_reason": dict(removal_reason_counts),
        "category_counts": dict(category_counts.most_common()),
        "sub_category_counts": dict(sub_cat_counts.most_common()),
        "goal_tag_counts": dict(goal_counts.most_common()),
        "health_level_counts": dict(health_level_counts),
        "health_level_pct": {
            k: round(v / len(kept_records) * 100, 1) if kept_records else 0
            for k, v in health_level_counts.items()
        },
        "replacement_group_counts": dict(replacement_group_counts.most_common()),
        "recommendation_role_counts": dict(rec_role_counts.most_common()),
        "grade_counts": dict(grade_counts.most_common()),
        "config": {
            "FILTER_ALCOHOL": FILTER_ALCOHOL,
            "FILTER_NON_HALAL": FILTER_NON_HALAL,
            "FILTER_CAFFEINE": FILTER_CAFFEINE,
            "FILTER_SUPPLEMENTS": FILTER_SUPPLEMENTS,
            "FILTER_ORGANS": FILTER_ORGANS,
            "KEEP_UNKNOWN_CATEGORY": KEEP_UNKNOWN_CATEGORY,
        },
    }

    summary_path = OUTPUT_DIR / "cleaning_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"Wrote: {summary_path}")

    # --- Console summary ---
    print("\n" + "=" * 60)
    print("CLEANING SUMMARY")
    print("=" * 60)
    print(f"  Input records  : {total_input}")
    print(f"  Kept records   : {len(kept_records)}")
    print(f"  Removed records: {len(removed_records)}")
    print(f"\n  Removed by reason:")
    for reason, count in sorted(removal_reason_counts.items(), key=lambda x: -x[1]):
        print(f"    {reason:<35} {count:>5}")
    print(f"\n  Categories (kept):")
    for cat, count in category_counts.most_common():
        print(f"    {cat:<20} {count:>5}")
    print(f"\n  Goal tags (kept):")
    for goal, count in goal_counts.most_common():
        print(f"    {goal:<10} {count:>5}")
    print(f"\n  Health levels (kept):")
    for level in ("healthy", "sometimes", "try_less"):
        count = health_level_counts.get(level, 0)
        pct = count / len(kept_records) * 100 if kept_records else 0
        print(f"    {level:<15} {count:>5}  ({pct:.1f}%)")
    print(f"\n  Recommendation roles (kept):")
    for role, count in rec_role_counts.most_common():
        print(f"    {role:<30} {count:>5}")
    print("=" * 60)

    # --- Before/After examples ---
    print_before_after_examples(raw_records)

    print("\nDone.")


if __name__ == "__main__":
    run()
