/**
 * NutriHealth Game Storage Service
 *
 * Persists game scores locally using AsyncStorage.
 * No backend required — all data is stored on-device.
 *
 * High scores are stored in the user profile (services/userProfile.ts).
 * This service delegates high score reads/writes to the profile service.
 */

import { saveProfileHighScore, getProfileHighScore } from './userProfile';

/**
 * Get the all-time high score for a game.
 * Reads from the user profile. Returns 0 if no score has been saved yet.
 */
export async function getHighScore(gameId: string): Promise<number> {
  return getProfileHighScore(gameId);
}

/**
 * Save a new score if it is higher than the existing high score.
 * Writes to the user profile. Returns true if the new score is a new high score.
 */
export async function saveHighScore(gameId: string, score: number): Promise<boolean> {
  return saveProfileHighScore(gameId, score);
}

/**
 * Save a completed game score: updates the high score in the user profile.
 * Returns true if the score is a new high score.
 */
export async function saveGameScore(gameId: string, score: number): Promise<boolean> {
  return saveHighScore(gameId, score);
}
