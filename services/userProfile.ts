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
  | 'meat'
  | 'fish'
  | 'dairy';

export type BlacklistItem =
  | 'egg'
  | 'bread'
  | 'milk'
  | 'pork'
  | 'seafood'
  | 'meat'
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
  completedStories: string[];
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
    completedStories: [],
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

// ─── Story Completion ─────────────────────────────────────────────────────────

/**
 * Check whether the user has already claimed points for a given story.
 * Returns false if no profile exists or the story has not been completed.
 */
export async function hasClaimedStoryPoints(storyId: string): Promise<boolean> {
  const profile = await getUserProfile();
  if (!profile) return false;
  const completed = profile.completedStories ?? [];
  return completed.includes(storyId);
}

/**
 * Claim points for completing a story.
 * Adds the storyId to completedStories and increments totalPoints.
 * Returns true if points were awarded, false if already claimed or no profile.
 */
export async function claimStoryPoints(storyId: string, points: number): Promise<boolean> {
  const profile = await getUserProfile();
  if (!profile) return false;

  const completed = profile.completedStories ?? [];
  if (completed.includes(storyId)) return false;

  profile.completedStories = [...completed, storyId];
  profile.totalPoints = Math.max(0, profile.totalPoints + points);
  await saveUserProfile(profile);
  return true;
}
