/**
 * NutriHealth Game Configuration
 * "Meal Maker" - Game 1
 *
 * All game balance parameters are configurable here.
 */

import type { GameDifficulty } from '../services/gameSettings';

// ─── Difficulty Configuration ────────────────────────────────────────────────

export interface DifficultyConfig {
  /** Multiplier applied to spawn interval (>1 = slower spawning = easier) */
  spawnMultiplier: number;
  /** Multiplier applied to fall duration (>1 = slower falling = easier) */
  fallMultiplier: number;
  /** Multiplier applied to points earned per meal */
  pointsMultiplier: number;
}

export const DIFFICULTY_CONFIG: Record<GameDifficulty, DifficultyConfig> = {
  easy:   { spawnMultiplier: 1.4, fallMultiplier: 1.4, pointsMultiplier: 0.8 },
  medium: { spawnMultiplier: 1.0, fallMultiplier: 1.0, pointsMultiplier: 1.0 },
  hard:   { spawnMultiplier: 0.7, fallMultiplier: 0.7, pointsMultiplier: 1.25 },
};

// ─── Timing & Layout ────────────────────────────────────────────────────────

export const ROUND_DURATION_SECONDS = 60;
export const NUM_LANES = 6;
export const MAX_INGREDIENTS_PER_LANE = 5;
export const MAX_ACTIVE_INGREDIENTS = 8;
export const PLATE_CAPACITY = 3;

/**
 * After spawning in a lane, that lane is blocked for this many subsequent spawns.
 * Prevents ingredients from stacking too closely in the same lane.
 */
export const LANE_BLOCK_COUNT = 3;

/** Spawn interval in ms — decreases over time (speeds up spawning) */
export const SPAWN_INTERVAL_INITIAL_MS = 1000;
export const SPAWN_INTERVAL_MIN_MS = 100;
/** Every X seconds, spawn interval decreases by SPAWN_INTERVAL_STEP_MS */
export const SPAWN_DIFFICULTY_STEP_SECONDS = 5;
export const SPAWN_INTERVAL_STEP_MS = 200;

/** Fall duration in ms — decreases over time (ingredients fall faster) */
export const FALL_DURATION_INITIAL_MIN_MS = 4000;
export const FALL_DURATION_INITIAL_MAX_MS = 6000;
export const FALL_DURATION_MIN_MS = 2300;
/** Every X seconds, fall duration decreases by FALL_DURATION_STEP_MS */
export const FALL_DIFFICULTY_STEP_SECONDS = 5;
export const FALL_DURATION_STEP_MS = 300;

// ─── Ingredient Categories ───────────────────────────────────────────────────

export type IngredientCategory = 'vegetable' | 'carbohydrate' | 'protein' | 'junk' | 'candy';

export interface IngredientDefinition {
  id: string;
  name: string;
  category: IngredientCategory;
  emoji: string;
  color: string;
}

export const INGREDIENTS: IngredientDefinition[] = [
  // Vegetables
  { id: 'broccoli',    name: 'Broccoli',   category: 'vegetable',     emoji: '🥦', color: '#4CAF50' },
  { id: 'carrot',      name: 'Carrot',     category: 'vegetable',     emoji: '🥕', color: '#FF9800' },
  { id: 'tomato',      name: 'Tomato',     category: 'vegetable',     emoji: '🍅', color: '#F44336' },
  { id: 'corn',        name: 'Corn',       category: 'vegetable',     emoji: '🌽', color: '#FFEB3B' },
  { id: 'pea',         name: 'Pea',        category: 'vegetable',     emoji: '🫛', color: '#66BB6A' },

  // Carbohydrates
  { id: 'rice',        name: 'Rice',       category: 'carbohydrate',  emoji: '🍚', color: '#FFF9C4' },
  { id: 'bread',       name: 'Bread',      category: 'carbohydrate',  emoji: '🍞', color: '#D7A86E' },
  { id: 'pasta',       name: 'Pasta',      category: 'carbohydrate',  emoji: '🍝', color: '#FFD54F' },
  { id: 'potato',      name: 'Potato',     category: 'carbohydrate',  emoji: '🥔', color: '#C8A96E' },
  { id: 'noodles',     name: 'Noodles',    category: 'carbohydrate',  emoji: '🍜', color: '#FFE082' },

  // Proteins
  { id: 'chicken',     name: 'Chicken',    category: 'protein',       emoji: '🍗', color: '#FFCC80' },
  { id: 'egg',         name: 'Egg',        category: 'protein',       emoji: '🥚', color: '#FFF8E1' },
  { id: 'fish',        name: 'Fish',       category: 'protein',       emoji: '🐟', color: '#80DEEA' },
  { id: 'meat',        name: 'Meat',       category: 'protein',       emoji: '🍖', color: '#F5F5DC' },
  { id: 'beef',        name: 'Beef',       category: 'protein',       emoji: '🥩', color: '#EF9A9A' },

  // Junk Food
  { id: 'burger',      name: 'Burger',     category: 'junk',          emoji: '🍔', color: '#FF7043' },
  { id: 'fries',       name: 'Fries',      category: 'junk',          emoji: '🍟', color: '#FFC107' },
  { id: 'pizza',       name: 'Pizza',      category: 'junk',          emoji: '🍕', color: '#FF8A65' },
  { id: 'hotdog',      name: 'Hotdog',     category: 'junk',          emoji: '🌭', color: '#FF6E40' },
  { id: 'nuggets',     name: 'Nuggets',    category: 'junk',          emoji: '🍿', color: '#FFCA28' },

  // Candy
  { id: 'candy',       name: 'Candy',      category: 'candy',         emoji: '🍬', color: '#F48FB1' },
  { id: 'lollipop',    name: 'Lollipop',   category: 'candy',         emoji: '🍭', color: '#CE93D8' },
  { id: 'cake',        name: 'Cake',       category: 'candy',         emoji: '🎂', color: '#F8BBD0' },
  { id: 'donut',       name: 'Donut',      category: 'candy',         emoji: '🍩', color: '#FFAB91' },
  { id: 'icecream',    name: 'Ice Cream',  category: 'candy',         emoji: '🍦', color: '#B3E5FC' },
];

// ─── Scoring Matrix ──────────────────────────────────────────────────────────
// Categories sorted alphabetically: C=carbohydrate, J=junk, K=candy, P=protein, V=vegetable
// Key format: sorted category initials joined, e.g. "VVV", "CVP" → sorted → "CPV"

const CATEGORY_INITIAL: Record<IngredientCategory, string> = {
  carbohydrate: 'C',
  junk: 'J',
  candy: 'K',
  protein: 'P',
  vegetable: 'V',
};

/**
 * Scoring table for all 35 order-independent 3-ingredient combinations.
 * Key: 3 category initials sorted alphabetically (e.g. "CPV", "VVV")
 */
export const MEAL_SCORE_TABLE: Record<string, number> = {
  // 3 of the same
  VVV: 8,
  CCC: 5,
  PPP: 7,
  JJJ: -8,
  KKK: -10,

  // 2 vegetables
  CVV: 8,
  PVV: 8,
  JVV: 4,
  KVV: 4,

  // 2 carbohydrates
  CCV: 6,
  CCP: 6,
  CCJ: 3,
  CCK: 3,

  // 2 proteins
  PPV: 7,
  CPP: 6,
  JPP: 3,
  KPP: 3,

  // 2 junk
  JJV: 1,
  CJJ: 1,
  JJP: 1,
  JJK: -8,

  // 2 candy
  KKV: 0,
  CKK: 0,
  KKP: 0,
  JKK: -8,

  // 1 of each (mixed triples)
  CPV: 10,  // vegetable + carb + protein (best combo)
  CJV: 4,
  CKV: 3,
  JPV: 4,
  KPV: 3,
  JKV: 0,
  CJP: 4,
  CKP: 3,
  CJK: 0,
  JKP: 0,
};

/**
 * Calculate the score for a completed meal.
 * @param categories - Array of exactly 3 ingredient categories
 * @returns Score for the meal (0 if combination not found)
 */
export function calculateMealScore(categories: IngredientCategory[]): number {
  if (categories.length !== PLATE_CAPACITY) return 0;

  const key = categories
    .map((c) => CATEGORY_INITIAL[c])
    .sort()
    .join('');

  return MEAL_SCORE_TABLE[key] ?? 0;
}

/**
 * Get a random ingredient definition
 */
export function getRandomIngredient(): IngredientDefinition {
  return INGREDIENTS[Math.floor(Math.random() * INGREDIENTS.length)];
}

/**
 * Calculate current fall duration based on elapsed time
 */
export function getCurrentFallDuration(elapsedSeconds: number): { min: number; max: number } {
  const steps = Math.floor(elapsedSeconds / FALL_DIFFICULTY_STEP_SECONDS);
  const reduction = steps * FALL_DURATION_STEP_MS;
  const min = Math.max(FALL_DURATION_MIN_MS, FALL_DURATION_INITIAL_MIN_MS - reduction);
  const max = Math.max(FALL_DURATION_MIN_MS + 500, FALL_DURATION_INITIAL_MAX_MS - reduction);
  return { min, max };
}

/**
 * Calculate current spawn interval based on elapsed time
 */
export function getCurrentSpawnInterval(elapsedSeconds: number): number {
  const steps = Math.floor(elapsedSeconds / SPAWN_DIFFICULTY_STEP_SECONDS);
  const reduction = steps * SPAWN_INTERVAL_STEP_MS;
  return Math.max(SPAWN_INTERVAL_MIN_MS, SPAWN_INTERVAL_INITIAL_MS - reduction);
}
