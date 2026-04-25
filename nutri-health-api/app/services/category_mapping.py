"""
Category mapping tables for the recommendation service.

All set operations (union, intersection, difference) are done on preference ID
strings. Only convert to cn_ctg_no integers when building SQL WHERE clauses.
"""

# ── Preference ID → CN category codes ────────────────────────────────────────
# Keys are the API-level preference IDs sent by the frontend.
# Values are lists of food_category_code integers from cn_ctgnme.

PREFERENCE_TO_CATEGORY: dict[str, list[int]] = {
    "fruits":     [9],
    "vegetables": [11],
    "rice":       [20],   # shared with noodles; disambiguated by food name
    "noodles":    [20],   # shared with rice; disambiguated by food name
    "bread":      [18],
    "meat":       [5, 13, 10],   # poultry (5) + beef (13) + pork (10)
    "fish":       [15],
    "dairy":      [1],
}

# Reverse mapping: category code → preference ID (used for labelling FoodItem)
# When multiple prefs share a code (rice/noodles → 20), last write wins;
# 'noodles' will be the label for cat 20 which is acceptable for display.
CAT_CODE_TO_PREF: dict[int, str] = {}
for _pref, _codes in PREFERENCE_TO_CATEGORY.items():
    for _code in _codes:
        CAT_CODE_TO_PREF[_code] = _pref

# ── Food name keywords for cat-20 disambiguation ─────────────────────────────

RICE_KEYWORDS: list[str] = ["%rice%", "%congee%", "%porridge%"]
NOODLE_KEYWORDS: list[str] = ["%noodle%", "%pasta%", "%spaghetti%", "%vermicelli%", "%macaroni%"]

# ── Blacklist item → allergen tag values (cn_food_tags.tag_value) ─────────────
# 'pork' is NOT in this dict; it is excluded via food_category_code = 10.

BLACKLIST_TO_ALLERGEN: dict[str, list[str]] = {
    "egg":     ["Egg"],
    "bread":   ["Gluten"],
    "milk":    ["Milk"],
    "seafood": ["Shellfish"],
    "nuts":    ["TreeNut", "Peanut"],
}

# ── Goal ID → relevant preference IDs ────────────────────────────────────────
# Used to define "goal relevance" for all three recommendation sections.
# Kept as preference ID strings, never as category code integers.

GOAL_RELEVANT_PREFS: dict[str, list[str]] = {
    "grow":   ["dairy", "meat", "vegetables"],
    "see":    ["vegetables", "fruits", "fish"],
    "think":  ["fish", "dairy", "fruits"],
    "fight":  ["fruits", "vegetables"],
    "feel":   ["fruits", "vegetables", "rice", "noodles"],
    "strong": ["meat", "fish", "dairy"],
}

# ── Common / Rare food keywords (used for scoring only, never for filtering) ──
# COMMON: everyday foods children typically know and eat (+2 per match in pool sort)
# RARE:   unusual or unfamiliar foods that should be deprioritized (-4 per match)
# Matching is substring on the lowercase descriptor.

COMMON_FOOD_KEYWORDS: list[str] = [
    # Fruits
    "apple", "banana", "orange", "grape", "mango", "watermelon", "strawberry",
    "pear", "peach", "melon", "pineapple", "papaya", "lychee",
    # Vegetables
    "carrot", "broccoli", "spinach", "tomato", "potato", "corn", "pea",
    "cabbage", "cauliflower", "cucumber", "onion", "lettuce", "celery",
    # Proteins
    "chicken", "beef", "pork", "fish", "egg", "prawn", "shrimp", "tofu",
    # Grains
    "rice", "bread", "noodle", "pasta", "oat",
    # Dairy
    "milk", "cheese", "yogurt",
    # Legumes
    "bean", "lentil",
]

RARE_FOOD_KEYWORDS: list[str] = [
    # Organ meats
    "liver", "kidney", "heart", "tripe", "intestine", "tongue", "brain",
    "offal", "blood", "marrow", "thymus", "sweetbread", "spleen",
    # Unusual seafood
    "sea cucumber", "abalone", "jellyfish", "urchin", "barnacle",
    "geoduck", "conch", "whelk",
    # Other uncommon
    "frog", "snail", "escargot", "venison", "shark", "eel",
    "emu", "turtle",
]

# ── Junk / dessert food keywords (filtered from healthy sections only) ────────
# Foods matching these keywords are excluded from super_power and tiny_hero
# but are allowed in try_less (where recommending "eat less" is appropriate).

JUNK_FOOD_KEYWORDS: list[str] = [
    # Frozen desserts
    "ice cream", "popsicle", "sherbet", "sorbet", "gelato",
    # Confectionery
    "candy", "chocolate bar", "lollipop", "jelly bean", "gummy",
    "caramel", "toffee", "nougat", "fudge",
    # Baked desserts
    "cake", "cookie", "brownie", "doughnut", "donut", "muffin",
    "pastry", "pie filling", "frosting", "icing",
    # Snack foods
    "chips", "crisps", "popcorn",
    # Sweet sauces / toppings
    "syrup", "whipped cream", "chocolate sauce",
    # Sugary drinks
    "soda", "soft drink", "energy drink",
]
