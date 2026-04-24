/**
 * NutriHealth User Profile Service
 *
 * Stores and retrieves user profile data locally using AsyncStorage.
 * No backend required — all data is stored on-device.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

// ─── Types ───────────────────────────────────────────────────────────────────

export type AvatarId = 'hero' | 'princess';

export type FoodPreferenceItem =
  | 'fruits'
  | 'vegetables'
  | 'rice'
  | 'bread'
  | 'noodles'
  | 'chicken'
  | 'beef'
  | 'pork'
  | 'fish'
  | 'dairy';

export type BlacklistItem =
  | 'egg'
  | 'bread'
  | 'milk'
  | 'peanut'
  | 'seafood'
  | 'nuts';

export interface FoodPreferences {
  likes: FoodPreferenceItem[];
  dislikes: FoodPreferenceItem[];
  blacklist: BlacklistItem[];
}

export interface UserProfile {
  username: string;
  avatarId: AvatarId;
  age: number;
  highScores: Record<string, number>;
  totalPoints: number;
  foodPreferences?: FoodPreferences;
}

// ─── Storage Keys ────────────────────────────────────────────────────────────

const PROFILE_KEY = 'user_profile';

// ─── Profile CRUD ────────────────────────────────────────────────────────────

/**
 * Load the user profile from local storage.
 * Returns null if no profile has been created yet.
 */
export async function getUserProfile(): Promise<UserProfile | null> {
  try {
    const raw = await AsyncStorage.getItem(PROFILE_KEY);
    if (raw === null) return null;
    return JSON.parse(raw) as UserProfile;
  } catch {
    return null;
  }
}

/**
 * Save a user profile to local storage.
 */
export async function saveUserProfile(profile: UserProfile): Promise<void> {
  try {
    await AsyncStorage.setItem(PROFILE_KEY, JSON.stringify(profile));
  } catch {
    // Silently fail — profile storage is non-critical
  }
}

/**
 * Create a new user profile with default generated data.
 */
export async function createUserProfile(
  username: string,
  avatarId: AvatarId,
  age: number,
  foodPreferences?: FoodPreferences
): Promise<UserProfile> {
  const profile: UserProfile = {
    username,
    avatarId,
    age,
    highScores: {},
    totalPoints: 0,
    foodPreferences,
  };
  await saveUserProfile(profile);
  return profile;
}

/**
 * Delete the user profile from local storage.
 */
export async function deleteUserProfile(): Promise<void> {
  try {
    await AsyncStorage.removeItem(PROFILE_KEY);
  } catch {
    // Silently fail
  }
}

/**
 * Check whether a user profile exists.
 */
export async function hasUserProfile(): Promise<boolean> {
  const profile = await getUserProfile();
  return profile !== null;
}

// ─── High Score Integration ───────────────────────────────────────────────────

/**
 * Get the high score for a specific game from the user profile.
 * Returns 0 if no profile or no score for that game.
 */
export async function getProfileHighScore(gameId: string): Promise<number> {
  const profile = await getUserProfile();
  if (!profile) return 0;
  return profile.highScores[gameId] ?? 0;
}

/**
 * Save a new high score for a game into the user profile.
 * Only updates if the new score is higher than the existing one.
 * Returns true if it is a new high score.
 */
export async function saveProfileHighScore(
  gameId: string,
  score: number
): Promise<boolean> {
  const profile = await getUserProfile();
  if (!profile) return false;

  const current = profile.highScores[gameId] ?? 0;
  if (score > current) {
    profile.highScores[gameId] = score;
    await saveUserProfile(profile);
    return true;
  }
  return false;
}

/**
 * Add points to the user's total points counter.
 */
export async function addTotalPoints(points: number): Promise<void> {
  const profile = await getUserProfile();
  if (!profile) return;
  profile.totalPoints = Math.max(0, profile.totalPoints + points);
  await saveUserProfile(profile);
}
