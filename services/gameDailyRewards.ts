/**
 * Game Daily Rewards Service
 *
 * Tracks how many times a user has completed a game per day and awards
 * points to the user profile accordingly. Points can only be awarded
 * a maximum of MAX_DAILY_PLAYS times per day.
 *
 * Storage keys are date-scoped (YYYY-MM-DD) and old keys are pruned
 * automatically on each call to prevent indefinite accumulation.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import { addTotalPoints, getUserProfile } from './userProfile';

// ─── Constants ───────────────────────────────────────────────────────────────

export const MAX_DAILY_PLAYS = 5;

const KEY_PREFIX = 'game_daily_plays_';

// ─── Helpers ─────────────────────────────────────────────────────────────────

function getTodayString(): string {
  const now = new Date();
  const yyyy = now.getFullYear();
  const mm = String(now.getMonth() + 1).padStart(2, '0');
  const dd = String(now.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

function buildKey(gameId: string, dateStr: string): string {
  return `${KEY_PREFIX}${dateStr}_${gameId}`;
}

/**
 * Remove all daily play keys that are not for today.
 * This prevents indefinite accumulation of stale keys.
 */
async function pruneOldKeys(today: string): Promise<void> {
  try {
    const allKeys = await AsyncStorage.getAllKeys();
    const oldKeys = allKeys.filter(
      (k) => k.startsWith(KEY_PREFIX) && !k.includes(`_${today}_`)
    );
    if (oldKeys.length > 0) {
      await AsyncStorage.multiRemove(oldKeys);
    }
  } catch {
    // Silently fail — pruning is non-critical
  }
}

// ─── Public API ──────────────────────────────────────────────────────────────

export interface DailyRewardResult {
  /** Whether points were awarded this call */
  awarded: boolean;
  /** Total plays completed today (after this call) */
  playsToday: number;
  /** Remaining plays that can still award points today */
  playsRemaining: number;
}

/**
 * Attempt to claim points for completing a game.
 *
 * - Reads today's play count for the given game.
 * - If under the daily limit and a user profile exists, adds `score` to totalPoints.
 * - Increments the daily play count regardless of whether points were awarded.
 * - Prunes stale daily keys automatically.
 *
 * @param gameId - Identifier for the game (e.g. 'meal-maker')
 * @param score  - The score earned this session (added to totalPoints if awarded)
 * @returns DailyRewardResult
 */
export async function claimGamePoints(
  gameId: string,
  score: number
): Promise<DailyRewardResult> {
  const today = getTodayString();
  const key = buildKey(gameId, today);

  // Prune old keys in the background (non-blocking)
  pruneOldKeys(today);

  try {
    const raw = await AsyncStorage.getItem(key);
    const playsBeforeThisGame = raw !== null ? parseInt(raw, 10) : 0;
    const playsAfterThisGame = playsBeforeThisGame + 1;

    // Persist the incremented count
    await AsyncStorage.setItem(key, String(playsAfterThisGame));

    const canAward = playsBeforeThisGame < MAX_DAILY_PLAYS;

    if (canAward) {
      // Only award if a profile exists
      const profile = await getUserProfile();
      if (profile) {
        await addTotalPoints(score);
      }
    }

    const playsToday = Math.min(playsAfterThisGame, MAX_DAILY_PLAYS);
    const playsRemaining = Math.max(0, MAX_DAILY_PLAYS - playsAfterThisGame);

    return {
      awarded: canAward,
      playsToday,
      playsRemaining,
    };
  } catch {
    return {
      awarded: false,
      playsToday: MAX_DAILY_PLAYS,
      playsRemaining: 0,
    };
  }
}
