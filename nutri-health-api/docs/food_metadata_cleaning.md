# Food Metadata Cleaning Pipeline

This document describes the cleaning pipeline that transforms raw Canadian Nutrient File
(CN) food descriptors into structured metadata suitable for the NutriHealth recommendation API.

---

## Overview

The pipeline reads a raw food database, filters out unsafe or unsuitable foods for
children aged 7-12, normalizes names, and enriches each record with:

- A clean category (aligned with backend recommendation logic)
- Goal tags (exactly the 6 backend-supported `goal_id` values)
- Taste profile (for alternative food matching)
- Health level (for UI presentation)
- Replacement group (for same-taste healthier alternative generation)

---

## File Paths

| Role | Path |
|------|------|
| Input (raw) | `data/seed/cn_fdes.json` |
| Output (clean JSON) | `data/processed/clean_food_metadata.json` |
| Output (clean CSV) | `data/processed/clean_food_metadata.csv` |
| Removed records | `data/processed/removed_food_records.json` |
| Cleaning summary | `data/processed/cleaning_summary.json` |
| Cleaning script | `scripts/clean_food_metadata.py` |
| Validation script | `scripts/validate_clean_food_metadata.py` |

---

## Input File Structure

`cn_fdes.json` is a flat JSON array of 9,202 records.

Each record has these fields:

| Field | Type | Notes |
|-------|------|-------|
| `cn_code` | int | Unique numeric identifier — used as `food_id` and `source_id` |
| `descriptor` | string | USDA-style long food name (the primary name field) |
| `food_category_code` | int or null | Numeric category code (1–35, or null for USDA school recipes) |
| `health_grade` | string | A / B / C / D / E |
| `hcl_compliant` | bool | Healthy Choice Label compliance flag |
| `is_halal_auto` | bool | Auto-detected halal flag (not relied upon for filtering — keyword-based filtering is used instead) |
| `discontinued_date` | string or null | Non-null for 15 discontinued records |
| `gtin`, `brand_name`, etc. | various | Preserved in processing but not used for inference |

Fields **not present** in this file: `image_url`, `nutrients`, `energy`, `protein`,
`fat`, `carbohydrate`, `sugar`, `sodium`. These are sourced from other CN files
(`CN.2026.03_NUTVAL.json`, etc.) in a separate ETL step.

---

## Supported Backend Goal IDs

The recommendation API validates exactly these 6 values.
**No other goal_id is ever written to the output.**

| goal_id | Label | Meaning |
|---------|-------|---------|
| `grow` | Grow Up | Support height growth, strong bones, healthy development |
| `see` | See Clear | Support eyesight |
| `think` | Think Fast | Support brain and cognitive function |
| `fight` | Fight Germs | Support immunity |
| `feel` | Feel Good | Support mood and energy |
| `strong` | Be Strong | Support muscle and body strength |

---

## Goal-to-Category Mapping

A food can receive multiple goal tags.

| Goal | Primary categories | Extended categories |
|------|--------------------|---------------------|
| `grow` | dairy, meat, vegetables | eggs, beans |
| `see` | vegetables, fruits, fish | (name-based: carrot, sweet potato, spinach, kale, mango, salmon, tuna, broccoli, egg) |
| `think` | fish, dairy, fruits | eggs, beans, grains (oats, whole wheat) |
| `fight` | fruits, vegetables | (name-based: orange, kiwi, berry, broccoli, tomato, bell pepper) |
| `feel` | fruits, vegetables, rice, noodles | grains (oats, cereal, bread) |
| `strong` | meat, fish, dairy | eggs, beans |

---

## Allowed Clean Categories

```
dairy  meat  fish  vegetables  fruits  rice  noodles
grains  beans  eggs  snacks  drinks  mixed_dishes  sauces  other
```

The `food_category_code` numeric codes are mapped to these categories,
and name-based keyword inference overrides the code when a better match is found.

### food_category_code Reference

| Code | Description | clean_category |
|------|-------------|----------------|
| 1 | Dairy (butter, cheese, cream, milk) | dairy |
| 2 | Spices / condiments | sauces |
| 3 | Babyfood | **filtered** |
| 4 | Fats / salad dressings | sauces |
| 5 | Poultry (chicken, turkey) | meat |
| 6 | Soups | mixed_dishes |
| 7 | Sausages / cold cuts | meat (pork items filtered) |
| 8 | Ready-to-eat cereals | grains |
| 9 | Fruits | fruits |
| 10 | Pork | **filtered** (FILTER_NON_HALAL) |
| 11 | Vegetables | vegetables |
| 12 | Seeds / nuts | other |
| 13 | Beef | meat |
| 14 | Beverages | drinks |
| 15 | Fish / seafood | fish |
| 16 | Beans / legumes | beans |
| 17 | Veal / lamb | meat |
| 18 | Breads / bagels / pasta | grains or noodles |
| 19 | Snacks | snacks |
| 20 | Whole grains | grains |
| 21 | Frozen pizza / prepared meals | mixed_dishes |
| 22 | Multi-ingredient dishes | mixed_dishes |
| 25 | Snack bars / jerky | snacks |
| 35 | Alaska Native traditional foods | **filtered** (niche_regional) |
| None | USDA school recipes | mixed_dishes |

---

## Filtering Rules

### Why each filter exists

#### Alcohol (`FILTER_ALCOHOL = True`)
Alcoholic beverages, beer-battered foods, and wine-based sauces are entirely
inappropriate for children aged 7-12. Removing them prevents them from ever
appearing as food options or alternatives.

#### Pork / Non-Halal (`FILTER_NON_HALAL = True`)
The application targets a diverse user base that may include Muslim families.
Pork-derived ingredients (bacon, ham, lard, salami, etc.) are filtered by keyword
across all categories. The entire `food_category_code=10` (pork) is also removed.
Note: `is_halal_auto` from the raw data is not relied upon — it incorrectly marks
some pork records as halal. Keyword-based filtering is the authoritative check.

#### Caffeine / Stimulants (`FILTER_CAFFEINE = True`)
Energy drinks and coffee drinks are stimulants that are not recommended for
children. Coffee-flavoured dairy items (e.g. "coffee cream") are preserved since
the keyword check applies only to clear coffee drinks.

#### Baby Food / Supplements (`FILTER_SUPPLEMENTS = True`)
Records labelled "babyfood", "infant formula", "toddler", "supplement", or
"protein powder" are designed for different demographics or medical contexts.
They are not appropriate for a general child-eating recommendation engine.
`food_category_code=3` (Babyfood) is also entirely filtered.

#### Organ Meats (`FILTER_ORGANS = True`)
Brain, liver, kidney, tripe, gizzard, and similar organ meats are removed
in this initial version. They are unusual choices for children and would generate
poor recommendation UX. They may be re-enabled later for a more complete dataset.

#### Industrial / Noisy Products
Records with packaging codes (e.g. `6/5#`, `30#`) or case-pack formats are
warehouse ingredient entries, not consumer foods. Keeping them would degrade
the quality of name normalization and recommendation text.

#### Discontinued Records
15 records have a non-null `discontinued_date`. These are removed as they
refer to products no longer available.

#### Alaska Native Traditional Foods (category 35)
These are highly niche regional items (whale meat, seal oil, etc.) that are
culturally specific and not suitable for a general children's food app.

#### Unknown Category (`KEEP_UNKNOWN_CATEGORY = False`)
When a record cannot be mapped to any of the 14 supported categories, it falls
into "other". With `KEEP_UNKNOWN_CATEGORY = False`, these records are removed
rather than cluttering the dataset with uncategorised entries. Set to `True`
if you need to inspect or later classify these records.

---

## Name Normalization

The `normalize_food_name()` function converts USDA-style long descriptors
into short, child-friendly names.

### Algorithm

1. Remove parenthetical USDA program notes and packaging codes.
2. Split on comma — the first segment is the base food name.
3. Singularize common plural base words (e.g. "apples" → "apple").
4. Extract useful qualifiers from remaining segments (e.g. "breast", "kidney",
   "brown", "low-fat", "greek", "whole wheat").
5. Reassemble as `base + qualifier` (or qualifier alone if it subsumes the base).
6. Strip ~50 noise words (raw, cooked, canned, frozen, enriched, grade markers,
   cut descriptions, etc.).
7. Apply a small corrections dict (e.g. "lowfat milk" → "low-fat milk").

### Examples

| Raw descriptor | Normalized |
|----------------|------------|
| `Apples, raw, with skin` | `apple` |
| `Egg, whole, raw, fresh` | `egg` |
| `Chicken, broilers or fryers, breast, skinless, boneless, meat only, raw` | `chicken breast` |
| `Rice, brown, long-grain, cooked` | `brown rice` |
| `Beans, kidney, red, mature seeds, canned, solids and liquids` | `kidney beans` |
| `Milk, lowfat, fluid, 1% milkfat` | `low-fat milk` |
| `Carrots, raw` | `carrot` |
| `Broccoli, raw` | `broccoli` |
| `Oats, regular and quick, unenriched, cooked with water` | `oatmeal` |

---

## Output JSON Schema

```json
{
  "food_id": "1012",
  "source_id": "1012",
  "raw_name": "Cheese, cottage, creamed, large or small curd",
  "clean_name": "cottage cheese",
  "display_name": "Cottage Cheese",
  "clean_category": "dairy",
  "original_category": "1",
  "grade": "B",
  "health_level": "healthy",
  "goal_tags": ["grow", "strong", "think"],
  "taste_profile": ["creamy", "mild", "savory"],
  "replacement_group": "dairy_food",
  "child_friendly": true,
  "hcl_compliant": true,
  "image_url": null,
  "removed": false,
  "remove_reason": null
}
```

**Notes:**
- `image_url` is always `null` in this version (not present in source file).
- `goal_tags` is an array in JSON and a comma-separated string in CSV.
- `taste_profile` is an array in JSON and a comma-separated string in CSV.
- Removed records have `removed: true` and are written to `removed_food_records.json`.

---

## Deduplication

Records are deduplicated by `(clean_name, clean_category)`.

When duplicates exist, the preferred record is selected by:

1. `hcl_compliant == true` first
2. Better grade (A > B > C > D > E)
3. Shorter `raw_name` (simpler descriptions tend to be cleaner)
4. Has `image_url` (future-proofing)

---

## How to Run

```bash
# From project root
python scripts/clean_food_metadata.py
python scripts/validate_clean_food_metadata.py
```

Both scripts use only the Python standard library plus `pandas` (CSV writing
uses the stdlib `csv` module — no pandas dependency required).

---

## Using the Cleaned Metadata

### 1. Recommendation filtering
Query `clean_food_metadata.json` by `goal_tags` to find foods that match
a child's selected goal:
```python
# Example: foods for the 'grow' goal
foods = [f for f in records if 'grow' in f['goal_tags']]
```

### 2. Alternative generation
Use `replacement_group` and `taste_profile` to find healthier swaps:
```python
# Find alternatives to chips (crunchy_snack, salty)
alternatives = [
    f for f in records
    if f['replacement_group'] == 'crunchy_snack'
    and f['health_level'] != 'try_less'
    and 'crunchy' in f['taste_profile']
]
```

### 3. Fine-tuning dataset generation (future step)
Each cleaned record can be converted to a JSONL instruction example:

```jsonl
{"messages": [
  {"role": "user", "content": "What is a healthier alternative to chips for a child who wants to be strong?"},
  {"role": "assistant", "content": "Try roasted chickpeas! They are crunchy and satisfying, and packed with protein to help you build strong muscles."}
]}
```

The fields `goal_tags`, `replacement_group`, `taste_profile`, `health_level`,
and `display_name` provide all the structured data needed to auto-generate
these instruction pairs without calling an external API.

### 4. RAG / vector search
Embed `clean_name` + `display_name` using `get_embeddings()` from
`app/services/embedding_provider.py` and store in the FAISS index at
`data/food_vector_db/` for semantic food lookup.

---

## Config Flags

Edit the top of `scripts/clean_food_metadata.py` to adjust behaviour:

```python
FILTER_ALCOHOL = True        # Remove alcohol-related foods
FILTER_NON_HALAL = True      # Remove pork and non-halal keywords
FILTER_CAFFEINE = True       # Remove coffee drinks and energy drinks
FILTER_SUPPLEMENTS = True    # Remove babyfood, formula, supplements
FILTER_ORGANS = True         # Remove organ meats (liver, kidney, etc.)
KEEP_UNKNOWN_CATEGORY = False  # Drop records that cannot be categorized
```
