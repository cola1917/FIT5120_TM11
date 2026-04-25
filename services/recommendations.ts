/**
 * Recommendations Service
 *
 * Fetches personalised food recommendations from the backend based on the
 * user's goal and food preferences (read from local UserProfile).
 *
 * chicken / beef / pork are consolidated into "meat" before the API call
 * because the backend category mapping uses "meat" as the unified key.
 */

import { getToken } from './auth';
import type { BlacklistItem, FoodPreferenceItem } from './userProfile';

const BACKEND_URL = 'https://fit5120-tm11.onrender.com';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface FoodItem {
  cn_code: number;
  name: string;
  category: string;
  grade: string;
  image_url: string;
}

export interface RecommendationResponse {
  super_power_foods: FoodItem[];
  tiny_hero_foods: FoodItem[];
  try_less_foods: FoodItem[];
}

// ─── Preference normalisation ─────────────────────────────────────────────────

const MEAT_PREFS = new Set<FoodPreferenceItem>(['chicken', 'beef', 'pork']);

/**
 * Merge chicken / beef / pork into a single "meat" API preference ID.
 * All other preference values pass through unchanged.
 */
function normalizePrefs(items: FoodPreferenceItem[]): string[] {
  const hasMeat = items.some((i) => MEAT_PREFS.has(i));
  const others = items.filter((i) => !MEAT_PREFS.has(i));
  return hasMeat ? [...others, 'meat'] : others;
}

// ─── API call ─────────────────────────────────────────────────────────────────

/**
 * Fetch personalised food recommendations for the given goal.
 *
 * Always calls the backend even when preferences are empty — the backend
 * handles empty arrays gracefully with goal-aware fallbacks.
 *
 * @param goalId   - One of: grow | see | think | fight | feel | strong
 * @param likes    - User's liked food preference items (from UserProfile)
 * @param dislikes - User's disliked food preference items (from UserProfile)
 * @param blacklist - User's allergen / excluded items (from UserProfile)
 */
export async function getRecommendations(
  goalId: string,
  likes: FoodPreferenceItem[],
  dislikes: FoodPreferenceItem[],
  blacklist: BlacklistItem[]
): Promise<RecommendationResponse> {
  const token = await getToken();

  const body = {
    goal_id: goalId,
    likes: normalizePrefs(likes),
    dislikes: normalizePrefs(dislikes),
    blacklist: blacklist as string[],
  };

  const response = await fetch(`${BACKEND_URL}/recommendations`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Recommendations request failed: ${response.status}`);
  }

  return response.json() as Promise<RecommendationResponse>;
}
