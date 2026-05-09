/**
 * Game Settings Service
 *
 * Stores and retrieves game-specific settings locally using AsyncStorage.
 * These settings are independent from the user profile.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

// ─── Types ───────────────────────────────────────────────────────────────────

export type GameDifficulty = 'easy' | 'medium' | 'hard';

export interface GameSettings {
  volume: number;       // 0.0 – 1.0
  difficulty: GameDifficulty;
}

// ─── Defaults ────────────────────────────────────────────────────────────────

export const DEFAULT_GAME_SETTINGS: GameSettings = {
  volume: 0.7,
  difficulty: 'medium',
};

// ─── Storage Key ─────────────────────────────────────────────────────────────

const SETTINGS_KEY = 'game_settings';

// ─── CRUD ────────────────────────────────────────────────────────────────────

/**
 * Load game settings from local storage.
 * Returns defaults if no settings have been saved yet.
 */
export async function getGameSettings(): Promise<GameSettings> {
  try {
    const raw = await AsyncStorage.getItem(SETTINGS_KEY);
    if (raw === null) return { ...DEFAULT_GAME_SETTINGS };
    const parsed = JSON.parse(raw) as Partial<GameSettings>;
    return {
      volume: typeof parsed.volume === 'number' ? parsed.volume : DEFAULT_GAME_SETTINGS.volume,
      difficulty: parsed.difficulty ?? DEFAULT_GAME_SETTINGS.difficulty,
    };
  } catch {
    return { ...DEFAULT_GAME_SETTINGS };
  }
}

/**
 * Save game settings to local storage.
 */
export async function saveGameSettings(settings: GameSettings): Promise<void> {
  try {
    await AsyncStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
  } catch {
    // Silently fail — settings storage is non-critical
  }
}
