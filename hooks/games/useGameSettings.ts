/**
 * useGameSettings — Custom hook for reactive game settings.
 *
 * Loads settings from AsyncStorage on mount and provides
 * setters that persist changes immediately.
 */

import { useCallback, useEffect, useState } from 'react';
import {
  GameDifficulty,
  GameSettings,
  DEFAULT_GAME_SETTINGS,
  getGameSettings,
  saveGameSettings,
} from '@/services/gameSettings';

export interface UseGameSettingsResult {
  settings: GameSettings;
  loading: boolean;
  setVolume: (volume: number) => void;
  setDifficulty: (difficulty: GameDifficulty) => void;
}

export function useGameSettings(): UseGameSettingsResult {
  const [settings, setSettings] = useState<GameSettings>({ ...DEFAULT_GAME_SETTINGS });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getGameSettings().then((s) => {
      setSettings(s);
      setLoading(false);
    });
  }, []);

  const setVolume = useCallback((volume: number) => {
    setSettings((prev) => {
      const next = { ...prev, volume };
      saveGameSettings(next);
      return next;
    });
  }, []);

  const setDifficulty = useCallback((difficulty: GameDifficulty) => {
    setSettings((prev) => {
      const next = { ...prev, difficulty };
      saveGameSettings(next);
      return next;
    });
  }, []);

  return { settings, loading, setVolume, setDifficulty };
}
