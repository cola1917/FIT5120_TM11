# Data Dictionary

## Document Overview
This data dictionary provides a comprehensive description of the Nutri-Health system's database structure, including the CN2026 food catalog database (PostgreSQL) and local application data (IndexedDB).

**Last Updated**: April 2, 2026  
**Database Version**: PostgreSQL 15+  
**Framework**: SQLAlchemy 2.x ORM

---

## Table of Contents
1. [CN2026 Food Catalog Tables](#cn2026-food-catalog-tables)
   - [cn_fdes Food Description Table](#1-cn_fdes-food-description-table)
   - [cn_nutdes Nutrient Description Table](#2-cn_nutdes-nutrient-description-table)
   - [cn_nutval Nutrient Values Table](#3-cn_nutval-nutrient-values-table)
   - [cn_wght Weight/Serving Size Table](#4-cn_wght-weightserving-size-table)
   - [cn_ctgnme Food Category Table](#5-cn_ctgnme-food-category-table)
   - [cn_gpcnme GPC Standard Code Table](#6-cn_gpcnme-gpc-standard-code-table)
   - [cn_food_tags Food Tags Table](#7-cn_food_tags-food-tags-table)
   - [remote_alternative Alternative Options Table](#8-remote_alternative-alternative-options-table)
2. [Application Initialization Tables](#application-initialization-tables)
   - [app_init_state Initialization State Table](#app_init_state-initialization-state-table)

---

## CN2026 Food Catalog Tables

### 1. cn_fdes Food Description Table

**Table Name**: `cn_fdes`  
**Purpose**: Stores all basic food information from the CN2026 food catalog, including nutritional grades and compliance flags  
**Record Count**: ~9,202 records

| Field | Data Type | Constraints | Nullable | Description |
|-------|-----------|-------------|----------|-------------|
| `cn_code` | INTEGER | PK | ✗ | CN2026 Unique Code, primary key |
| `gtin` | VARCHAR(32) | UK | ✓ | Barcode (International Article Number), key field for scan matching |
| `food_category_code` | INTEGER | FK→cn_ctgnme | ✓ | Food category code, references cn_ctgnme table |
| `gpc_product_code` | VARCHAR(32) | FK→cn_gpcnme | ✓ | GPC standard product code, references cn_gpcnme table |
| `descriptor` | TEXT | - | ✗ | Complete food description, e.g., "Butter, salted" |
| `brand_name` | VARCHAR(255) | - | ✓ | Brand name |
| `brand_owner_name` | VARCHAR(255) | - | ✓ | Brand owner/manufacturer name |
| `form_of_food` | VARCHAR(64) | - | ✓ | Food form, e.g., READY_TO_EAT or UNPREPARED |
| `health_grade` | VARCHAR(1) | - | ✓ | **Computed Field**: Nutritional grade A-E (Nutri-Score), auto-generated based on nutrient composition |
| `hcl_compliant` | BOOLEAN | - | ✓ | **Computed Field**: Whether compliant with Malaysia HCL (Health Claims Law) standards |
| `is_halal_auto` | BOOLEAN | - | ✓ | **Computed Field**: Halal indicator auto-parsed from food description |
| `discontinued_date` | DATE | - | ✓ | Product discontinuation date; NULL indicates active product |

**Indexes**: 
- PK: `cn_code`
- UK: `gtin` (unique constraint)

**Key Design Rationale**:
- `health_grade` is computed using Nutri-Score algorithm, used for food recommendation ranking in the app
- `hcl_compliant` filters for Malaysia local market compliance
- `is_halal_auto` uses heuristic detection from descriptor and other fields (manual verification recommended)
- `discontinued_date` allows keeping historical data while filtering discontinued products

---

### 2. cn_nutdes Nutrient Description Table

**Table Name**: `cn_nutdes`  
**Purpose**: Defines all nutrient codes and their measurement units  
**Record Count**: ~40 records (standard nutrient list)

| Field | Data Type | Constraints | Nullable | Description |
|-------|-----------|-------------|----------|-------------|
| `nutrient_code` | INTEGER | PK | ✗ | Nutrient code, international standard encoding |
| `nutrient_description` | VARCHAR(255) | - | ✗ | Nutrient name, e.g., "Sodium", "Fat" |
| `nutrient_unit` | VARCHAR(32) | - | ✓ | Measurement unit, e.g., "mg", "g", "kcal" |

**Indexes**: 
- PK: `nutrient_code`

**Common Nutrient Examples**:
- 1008: Energy - kcal
- 1009: Protein - g
- 1050: Sodium - mg
- 1100: Fat - g

---

### 3. cn_nutval Nutrient Values Table

**Table Name**: `cn_nutval`  
**Purpose**: Stores nutrient composition data for each food; one food can have multiple nutrient records  
**Record Count**: ~174,838 records

| Field | Data Type | Constraints | Nullable | Description |
|-------|-----------|-------------|----------|-------------|
| `id` | INTEGER | PK | ✗ | Auto-increment primary key, for internal database use |
| `cn_code` | INTEGER | FK→cn_fdes | ✗ | Food code, references cn_fdes table |
| `nutrient_code` | INTEGER | FK→cn_nutdes | ✗ | Nutrient code, references cn_nutdes table |
| `nutrient_value` | FLOAT | - | ✓ | Nutrient amount (per 100g basis) |
| `source_code` | INTEGER | - | ✓ | Data source code: 1 = analyzed, 3 = calculated |
| `value_type_code` | INTEGER | - | ✓ | Value type code (range indicator: exact, min, max, etc.) |
| `per_unit` | VARCHAR(32) | - | ✓ | Per-unit specification |

**Indexes**: 
- PK: `id`
- FK: `cn_code`, `nutrient_code`
- UK: `(cn_code, nutrient_code, source_code, value_type_code, per_unit)` - unique constraint prevents duplicates

**Usage Notes**:
- Each food may have multiple `source_code` entries (analyzed vs. calculated); app should select the more reliable source
- `nutrient_value` = NULL indicates no data for that nutrient in this food
- Nutri-Score calculation depends on specific nutrient fields (sodium, sugar, fat, etc.)

**Example**:
```
cn_code=1001, nutrient_code=1008 (Energy), nutrient_value=100.5, source_code=1
cn_code=1001, nutrient_code=1050 (Sodium), nutrient_value=250, source_code=3
```

---

### 4. cn_wght Weight/Serving Size Table

**Table Name**: `cn_wght`  
**Purpose**: Defines various serving sizes and their corresponding weights in grams, e.g., "1 cup", "1 serving"  
**Record Count**: ~15,271 records

| Field | Data Type | Constraints | Nullable | Description |
|-------|-----------|-------------|----------|-------------|
| `id` | INTEGER | PK | ✗ | Auto-increment primary key, for internal database use |
| `cn_code` | INTEGER | FK→cn_fdes | ✗ | Food code, references cn_fdes table |
| `sequence_num` | INTEGER | - | ✗ | Sequence number; different serving sizes of the same food are ordered by this |
| `measure_description` | VARCHAR(255) | - | ✓ | Serving size description, e.g., "1 cup", "1 slice", "100g" |
| `amount` | FLOAT | - | ✓ | Serving quantity |
| `unit_amount` | FLOAT | - | ✓ | Corresponding weight in grams, used for nutrient calculation |
| `type_of_unit` | VARCHAR(16) | - | ✓ | Unit type code |
| `source_code` | INTEGER | - | ✓ | Data source code |

**Indexes**: 
- PK: `id`
- FK: `cn_code`
- UK: `(cn_code, sequence_num, measure_description)` - serving descriptions for the same food don't repeat

**Usage Notes**:
- `sequence_num` ensures consistent ordering; UI displays multiple serving options in this order
- `unit_amount` is the bridge for nutrient calculation: nutrient_value × (user_amount / unit_amount)
- Common serving sizes (per cup, per slice) help users quickly input consumption amounts

**Example**:
```
cn_code=1001, sequence_num=1, measure_description="1 cup", unit_amount=240
cn_code=1001, sequence_num=2, measure_description="1 tablespoon", unit_amount=15
```

---

### 5. cn_ctgnme Food Category Table

**Table Name**: `cn_ctgnme`  
**Purpose**: Defines primary categories for all foods, e.g., "Dairy Products", "Meat"  
**Record Count**: ~93 records

| Field | Data Type | Constraints | Nullable | Description |
|-------|-----------|-------------|----------|-------------|
| `food_category_code` | INTEGER | PK | ✗ | Food category code |
| `category_description` | VARCHAR(255) | - | ✗ | Category name, e.g., "Dairy Products", "Cereal Products" |

**Indexes**: 
- PK: `food_category_code`

**Common Category Examples**:
- 1: Animal Products
- 2: Vegetables
- 3: Fruits
- 4: Cereals and Cereal Products
- 5: Meat

---

### 6. cn_gpcnme GPC Standard Code Table

**Table Name**: `cn_gpcnme`  
**Purpose**: GPC (Global Product Classification) standard mapping table for international product classification  
**Record Count**: ~200 records

| Field | Data Type | Constraints | Nullable | Description |
|-------|-----------|-------------|----------|-------------|
| `gpc_code` | VARCHAR(32) | PK | ✗ | GPC code (string format) |
| `gpc_description` | VARCHAR(255) | - | ✗ | GPC classification name |

**Indexes**: 
- PK: `gpc_code`

**Notes**:
- GPC is an internationally recognized product classification standard
- `gpc_code` is typically a 6-8 digit string
- More granular and standardized compared to cn_ctgnme

---

### 7. cn_food_tags Food Tags Table

**Table Name**: `cn_food_tags`  
**Purpose**: Labels food attributes, including allergen information and nutritional characteristics  
**Record Count**: ~15,258 records

| Field | Data Type | Constraints | Nullable | Description |
|-------|-----------|-------------|----------|-------------|
| `tag_id` | INTEGER | PK | ✗ | Tag ID, auto-increment primary key |
| `cn_code` | INTEGER | FK→cn_fdes | ✗ | Food code, references cn_fdes table |
| `tag_type` | VARCHAR(32) | - | ✗ | Tag type, e.g., "Allergen", "Feature" |
| `tag_value` | VARCHAR(128) | - | ✗ | Tag value, e.g., "Peanut", "Low-Sodium" |

**Indexes**: 
- PK: `tag_id`
- FK: `cn_code`

**tag_type Classification**:
- `Allergen`: Allergens (peanut, milk, shellfish, nuts, etc.) - used for filtering user allergies
- `Feature`: Nutritional characteristics (low-sodium, low-sugar, high-protein) - used for personalized recommendations

**Usage Notes**:
- Each food can have multiple tags, supporting multi-label requirements
- After users set allergen preferences, the system automatically filters foods containing those allergens
- Feature tags enable recommendation engine to match user goals (e.g., "Build muscle" recommends high-protein foods)

**Example**:
```
cn_code=1001, tag_type="Allergen", tag_value="Milk"
cn_code=1001, tag_type="Feature", tag_value="High-Protein"
```

---

### 8. remote_alternative Alternative Options Table

**Table Name**: `remote_alternative`  
**Purpose**: Provides health alternative recommendations for scanned foods, supporting personalized nutrition advice  
**Record Count**: ~13,017 records

| Field | Data Type | Constraints | Nullable | Description |
|-------|-----------|-------------|----------|-------------|
| `alt_id` | INTEGER | PK | ✗ | Alternative option ID, auto-increment primary key |
| `original_cn_code` | INTEGER | FK→cn_fdes | ✗ | Original food code (user-scanned food) |
| `suggested_cn_code` | INTEGER | FK→cn_fdes | ✗ | Suggested food code (healthier alternative) |
| `swap_reason_en` | TEXT | - | ✗ | Recommendation reason (English), e.g., "Lower sodium, similar taste" |
| `swap_score` | INTEGER | - | ✗ | Priority score (1-10); higher scores display first |

**Indexes**: 
- PK: `alt_id`
- FK: `original_cn_code`, `suggested_cn_code` (both reference cn_fdes)

**Usage Notes**:
- Recommendations are based on nutrient comparison (e.g., sodium content, glycemic index)
- `swap_score` ranks alternatives in the recommendation list; higher-scoring alternatives are more likely to be accepted by users
- One food can have multiple alternative options
- The app displays healthy alternatives on the "Scan Results" page

**Recommendation Standards**:
- From "high-sodium crackers" → recommend "low-sodium whole-wheat crackers"
- From "sugary soda" → recommend "zero-sugar soda/juice"
- From "high-fat fast food" → recommend "lower-calorie fast food"

**Example**:
```
alt_id=1, original_cn_code=1001 (salty crackers), suggested_cn_code=2001 (whole-wheat crackers), 
swap_reason_en="Lower sodium, higher fiber", swap_score=9
```

---

## Application Initialization Tables

### app_init_state Initialization State Table

**Table Name**: `app_init_state`  
**Purpose**: Tracks whether seed data import has been executed during app startup to prevent duplicate imports  
**Record Count**: 1 record

| Field | Data Type | Constraints | Nullable | Description |
|-------|-----------|-------------|----------|-------------|
| `seed_key` | VARCHAR(64) | PK | ✗ | Unique identifier key for seed import, specified by SEED_KEY environment variable |
| `initialized_at` | TIMESTAMP | - | ✗ | Initialization timestamp |

**Indexes**: 
- PK: `seed_key`

**Usage Notes**:
- On app startup, first check if this table contains a record with the corresponding `seed_key`
- If exists, skip seed data import (even if `SEED_ON_STARTUP=true`)
- Prevents accidental re-import of data on multiple restarts
- Supports multiple independent seed import scenarios (distinguished by different `SEED_KEY` values)

**Workflow**:
```
Start Application
  ↓
Create/Validate Table Structure (SQLAlchemy create_all)
  ↓
Check app_init_state Table
  ├─ Record Exists → Skip Seed Import → Startup Complete
  └─ Record Not Exists + SEED_ON_STARTUP=true
      ↓
      Execute Seed Import (load_seed_data)
      ↓
      Write app_init_state Record
      ↓
      Startup Complete
```

---

## Data Relationship Summary

### Core Relationship Diagram
```
cn_ctgnme (1) ──→ (N) cn_fdes
cn_gpcnme (1) ──→ (N) cn_fdes

cn_fdes (1) ──→ (N) cn_nutval
cn_nutdes (1) ──→ (N) cn_nutval

cn_fdes (1) ──→ (N) cn_wght
cn_fdes (1) ──→ (N) cn_food_tags

cn_fdes (1) ──→ (N) remote_alternative (as original food)
cn_fdes (1) ──→ (N) remote_alternative (as suggested food)
```

### Data Flow
```
Raw CN2026 Data
  ↓
ETL Transformation (build_seed_payload.py)
  ├─ Calculate health_grade (Nutri-Score A-E)
  ├─ Check hcl_compliant (Malaysia HCL)
  ├─ Parse is_halal_auto (Halal indicators)
  ├─ Generate food_tags (Allergens, characteristics)
  └─ Build remote_alternative (Health swaps)
  ↓
Seed JSON Files (data/seed/*.json)
  ↓
Database Load (seed_db.py)
  ↓
PostgreSQL 8 Tables
  ↓
Application API Queries
  ↓
Scanner App Frontend (Expo App)
```

---

## Data Statistics

| Table Name | Record Count | Import Time | Notes |
|------------|----------------|------------|-------|
| cn_ctgnme | 93 | ~100ms | Food categories |
| cn_gpcnme | 200 | ~50ms | GPC standard codes |
| cn_nutdes | 40 | ~50ms | Nutrient definitions |
| cn_fdes | 9,202 | ~5s | Food master table |
| cn_nutval | 174,838 | ~30s | Nutrient values (primary) |
| cn_wght | 15,271 | ~3s | Serving size definitions |
| cn_food_tags | 15,258 | ~3s | Tags |
| remote_alternative | 13,017 | ~2s | Alternative options |
| **Total** | **238,019** | **~45s** | **Complete Import** |

---

## Performance Optimization Recommendations

### 1. Query Optimization
- Create index on `gtin` (barcode scan queries)
- Create composite index on `cn_food_tags (cn_code, tag_value)` (allergen filtering)
- Create index on `remote_alternative (original_cn_code)` (alternative queries)

### 2. Caching Strategy
- Cache entire `cn_ctgnme` and `cn_gpcnme` tables (small data, rarely changes)
- Implement LRU cache for frequently queried food info (cn_fdes + basic nutrient values)

### 3. Bulk Operations
- Use batch insertion with chunked INSERTs to avoid oversized transactions
- Disable foreign key constraints before import, re-enable after completion

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SEED_ON_STARTUP` | `false` | Whether to execute seed import on startup |
| `SEED_TRUNCATE_BEFORE_LOAD` | `false` | Whether to clear existing data before import |
| `SEED_KEY` | `cn-2026-v1` | Unique identifier for seed import, used for re-entry prevention |
| `SEED_FORCE_RELOAD` | `false` | Force reload (ignore app_init_state check) |

**Note**: By default, the app only initializes table structure without importing data. Production environments require manual setup or initialization script execution for seed import.

---

## Related Documentation

- [README.md](nutri-health-api/README.md) - Project overview
- [data/README-seed-workflow.md](nutri-health-api/data/README-seed-workflow.md) - Seed import workflow
- [GUIDANCE.md](GUIDANCE.md) - Team onboarding guide
- [app/models/cn_food.py](nutri-health-api/app/models/cn_food.py) - SQLAlchemy model definitions
- [app/services/seed.py](nutri-health-api/app/services/seed.py) - Seed loading service
- [app/etl/build_seed_payload.py](nutri-health-api/app/etl/build_seed_payload.py) - ETL transformation logic
