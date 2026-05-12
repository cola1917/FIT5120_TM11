/**
 * useGameEngine — Custom hook for "Meal Maker" game state & logic
 *
 * Manages: game phase, timer, ingredient spawning, plate state,
 * meal completion, scoring, and difficulty progression.
 *
 * Performance: State is split into separate pieces so that timer ticks
 * don't cause ingredient list re-renders, and ingredient list changes
 * don't cause HUD re-renders. Callbacks use refs for stable identity.
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import { Audio } from 'expo-av';
import * as Haptics from 'expo-haptics';
import {
  ROUND_DURATION_SECONDS,
  NUM_LANES,
  MAX_INGREDIENTS_PER_LANE,
  MAX_ACTIVE_INGREDIENTS,
  PLATE_CAPACITY,
  LANE_BLOCK_COUNT,
  DIFFICULTY_CONFIG,
  IngredientDefinition,
  getRandomIngredient,
  calculateMealScore,
  getCurrentFallDuration,
  getCurrentSpawnInterval,
} from '../../constants/GameConfig';
import { saveGameScore, getHighScore } from '../../services/gameStorage';
import { claimGamePoints, DailyRewardResult } from '../../services/gameDailyRewards';
import type { GameDifficulty } from '../../services/gameSettings';

export const GAME_ID = 'meal-maker';

export type GamePhase = 'idle' | 'playing' | 'game_over';

export interface ActiveIngredient {
  id: string;
  ingredient: IngredientDefinition;
  laneIndex: number;
  fallDuration: number;
}

export interface GameActions {
  startGame: () => void;
  resetGame: () => void;
  catchIngredient: (id: string) => void;
  despawnIngredient: (id: string) => void;
}

export interface GameEngineOptions {
  volume: number;
  difficulty: GameDifficulty;
}

export function useGameEngine({ volume, difficulty }: GameEngineOptions) {
  // ─── Split state for performance ─────────────────────────────────────────────
  // Timer state is separate so ticking doesn't re-render ingredient list
  const [gamePhase, setGamePhase] = useState<GamePhase>('idle');
  const [timeRemaining, setTimeRemaining] = useState(ROUND_DURATION_SECONDS);
  const [totalScore, setTotalScore] = useState(0);
  const [activeIngredients, setActiveIngredients] = useState<ActiveIngredient[]>([]);
  const [plateIngredients, setPlateIngredients] = useState<IngredientDefinition[]>([]);
  const [lastMealScore, setLastMealScore] = useState<number | null>(null);
  const [showMealScore, setShowMealScore] = useState(false);
  const [highScore, setHighScore] = useState(0);
  const [isNewHighScore, setIsNewHighScore] = useState(false);

  // Daily reward state
  const [dailyReward, setDailyReward] = useState<DailyRewardResult | null>(null);

  // Refs for intervals (avoid stale closures)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const spawnerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const elapsedSecondsRef = useRef(0);
  const totalScoreRef = useRef(0);
  const activeIngredientsRef = useRef<ActiveIngredient[]>([]);
  const plateIngredientsRef = useRef<IngredientDefinition[]>([]);
  const isMealCompletingRef = useRef(false);
  const gamePhaseRef = useRef<GamePhase>('idle');

  // Keep volume and difficulty accessible in callbacks without stale closures
  const volumeRef = useRef(volume);
  volumeRef.current = volume;
  const difficultyRef = useRef(difficulty);
  difficultyRef.current = difficulty;

  // Lane occupancy: laneIndex → count of ingredients currently in that lane
  const laneCountsRef = useRef<number[]>(new Array(NUM_LANES).fill(0));

  // Lane blocking: laneIndex → number of remaining spawns this lane is blocked for
  const laneBlockCountdownRef = useRef<number[]>(new Array(NUM_LANES).fill(0));

  // ─── Cleanup ────────────────────────────────────────────────────────────────

  const clearAllIntervals = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (spawnerRef.current) {
      clearTimeout(spawnerRef.current);
      spawnerRef.current = null;
    }
  }, []);

  useEffect(() => {
    // Load high score on mount
    getHighScore(GAME_ID).then((hs) => {
      setHighScore(hs);
    });
    return clearAllIntervals;
  }, [clearAllIntervals]);

  // ─── End Game ───────────────────────────────────────────────────────────────

  const endGame = useCallback(async () => {
    clearAllIntervals();
    gamePhaseRef.current = 'game_over';
    const finalScore = totalScoreRef.current;
    const [isNew, hs, reward] = await Promise.all([
      saveGameScore(GAME_ID, finalScore),
      getHighScore(GAME_ID),
      claimGamePoints(GAME_ID, finalScore),
    ]);

    activeIngredientsRef.current = [];
    plateIngredientsRef.current = [];
    laneCountsRef.current = new Array(NUM_LANES).fill(0);
    laneBlockCountdownRef.current = new Array(NUM_LANES).fill(0);
    isMealCompletingRef.current = false;

    setGamePhase('game_over');
    setTimeRemaining(0);
    setActiveIngredients([]);
    setPlateIngredients([]);
    setShowMealScore(false);
    setHighScore(hs);
    setIsNewHighScore(isNew);
    setDailyReward(reward);
  }, [clearAllIntervals]);

  // Keep endGame ref current for timer closure
  const endGameRef = useRef(endGame);
  endGameRef.current = endGame;

  // ─── Spawner ─────────────────────────────────────────────────────────────────

  const scheduleNextSpawn = useCallback(() => {
    const elapsed = elapsedSecondsRef.current;
    const diffConfig = DIFFICULTY_CONFIG[difficultyRef.current];
    const baseInterval = getCurrentSpawnInterval(elapsed);
    const interval = Math.round(baseInterval * diffConfig.spawnMultiplier);

    spawnerRef.current = setTimeout(() => {
      // Bail if game is no longer playing
      if (gamePhaseRef.current !== 'playing') return;

      // Check if we can spawn
      const active = activeIngredientsRef.current;
      if (active.length >= MAX_ACTIVE_INGREDIENTS) {
        scheduleNextSpawn();
        return;
      }

      // Decrement all lane block countdowns
      const blockCountdowns = laneBlockCountdownRef.current;
      const newBlockCountdowns = blockCountdowns.map((c) => Math.max(0, c - 1));
      laneBlockCountdownRef.current = newBlockCountdowns;

      // Find available lanes:
      // - not blocked (countdown === 0)
      // - not at max occupancy
      const laneCounts = laneCountsRef.current;
      const availableLanes = laneCounts
        .map((count, idx) => ({ count, idx, blocked: newBlockCountdowns[idx] > 0 }))
        .filter(({ count, blocked }) => count < MAX_INGREDIENTS_PER_LANE && !blocked)
        .map(({ idx }) => idx);

      if (availableLanes.length === 0) {
        scheduleNextSpawn();
        return;
      }

      // Pick a random available lane
      const laneIndex = availableLanes[Math.floor(Math.random() * availableLanes.length)];

      // Block this lane for the next LANE_BLOCK_COUNT spawns
      laneBlockCountdownRef.current[laneIndex] = LANE_BLOCK_COUNT;

      // Pick a random ingredient
      const ingredient = getRandomIngredient();

      // Calculate fall duration based on elapsed time and difficulty
      const { min, max } = getCurrentFallDuration(elapsed);
      const baseFall = min + Math.random() * (max - min);
      const fallDuration = Math.round(baseFall * diffConfig.fallMultiplier);

      const newIngredient: ActiveIngredient = {
        id: `${ingredient.id}_${Date.now()}_${Math.random().toString(36).slice(2)}`,
        ingredient,
        laneIndex,
        fallDuration,
      };

      laneCountsRef.current[laneIndex] += 1;
      activeIngredientsRef.current = [...active, newIngredient];

      setActiveIngredients(activeIngredientsRef.current);

      scheduleNextSpawn();
    }, interval);
  }, []);

  // ─── Start Game ──────────────────────────────────────────────────────────────

  const startGame = useCallback(() => {
    clearAllIntervals();

    elapsedSecondsRef.current = 0;
    totalScoreRef.current = 0;
    activeIngredientsRef.current = [];
    plateIngredientsRef.current = [];
    laneCountsRef.current = new Array(NUM_LANES).fill(0);
    laneBlockCountdownRef.current = new Array(NUM_LANES).fill(0);
    isMealCompletingRef.current = false;
    gamePhaseRef.current = 'playing';

    setGamePhase('playing');
    setTimeRemaining(ROUND_DURATION_SECONDS);
    setTotalScore(0);
    setActiveIngredients([]);
    setPlateIngredients([]);
    setLastMealScore(null);
    setShowMealScore(false);
    setIsNewHighScore(false);
    setDailyReward(null);

    // Start countdown timer — only updates timeRemaining, not ingredients
    timerRef.current = setInterval(() => {
      elapsedSecondsRef.current += 1;
      setTimeRemaining((prev) => {
        const newTime = prev - 1;
        if (newTime <= 0) {
          endGameRef.current();
          return prev;
        }
        return newTime;
      });
    }, 1000);

    // Start spawner
    scheduleNextSpawn();
  }, [clearAllIntervals, scheduleNextSpawn]);

  // ─── Reset Game ──────────────────────────────────────────────────────────────

  const resetGame = useCallback(() => {
    clearAllIntervals();
    elapsedSecondsRef.current = 0;
    totalScoreRef.current = 0;
    activeIngredientsRef.current = [];
    plateIngredientsRef.current = [];
    laneCountsRef.current = new Array(NUM_LANES).fill(0);
    laneBlockCountdownRef.current = new Array(NUM_LANES).fill(0);
    isMealCompletingRef.current = false;
    gamePhaseRef.current = 'idle';

    getHighScore(GAME_ID).then((hs) => {
      setGamePhase('idle');
      setTimeRemaining(ROUND_DURATION_SECONDS);
      setTotalScore(0);
      setActiveIngredients([]);
      setPlateIngredients([]);
      setLastMealScore(null);
      setShowMealScore(false);
      setHighScore(hs);
      setIsNewHighScore(false);
      setDailyReward(null);
    });
  }, [clearAllIntervals]);

  // ─── Catch Ingredient ────────────────────────────────────────────────────────

  const playCatchIngredientSound = useCallback(async () => {
    try {
      const { sound } = await Audio.Sound.createAsync(
        require('../../assets/audio/pop.mp3'), { shouldPlay: true, volume: volumeRef.current }
      );
  
      sound.setOnPlaybackStatusUpdate((status) => {
        if (!status.isLoaded) return;
        if (status.didJustFinish) {
          sound.unloadAsync();
        }
      });
    } catch (_) {}
  }, []);

  const completeMealRef = useRef<(plate: IngredientDefinition[]) => void>(() => {});

  const catchIngredient = useCallback((id: string) => {
    const active = activeIngredientsRef.current;
    const target = active.find((i) => i.id === id);
    if (!target) return;

    // Don't catch if plate is already full or meal is completing
    if (plateIngredientsRef.current.length >= PLATE_CAPACITY || isMealCompletingRef.current) return;

    // Remove from active, free lane
    activeIngredientsRef.current = active.filter((i) => i.id !== id);
    laneCountsRef.current[target.laneIndex] = Math.max(0, laneCountsRef.current[target.laneIndex] - 1);

    // Add to plate
    playCatchIngredientSound();
    const newPlate = [...plateIngredientsRef.current, target.ingredient];
    plateIngredientsRef.current = newPlate;

    // Check for meal completion — clear plate immediately, show score popup briefly
    if (newPlate.length === PLATE_CAPACITY) {
      completeMealRef.current(newPlate);
    } else {
      setActiveIngredients(activeIngredientsRef.current);
      setPlateIngredients(newPlate);
    }
  }, [playCatchIngredientSound]);

  // ─── Complete Meal ───────────────────────────────────────────────────────────

  const playMealCompleteSound = useCallback(async () => {
    try {
      const { sound } = await Audio.Sound.createAsync(
        require('../../assets/audio/meal-complete.mp3'), { shouldPlay: true, volume: volumeRef.current }
      );

      sound.setOnPlaybackStatusUpdate((status) => {
        if (!status.isLoaded) return;
        if (status.didJustFinish) {
          sound.unloadAsync();
        }
      });
    } catch (_) {}
  }, []);

  const completeMeal = useCallback((plate: IngredientDefinition[]) => {
    playMealCompleteSound();
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    const categories = plate.map((i) => i.category);
    const baseMealScore = calculateMealScore(categories);
    const diffConfig = DIFFICULTY_CONFIG[difficultyRef.current];
    const mealScore = Math.round(baseMealScore * diffConfig.pointsMultiplier);

    totalScoreRef.current += mealScore;
    if (totalScoreRef.current < 0) totalScoreRef.current = 0;

    // Clear plate immediately — plate is ready for new ingredients right away
    plateIngredientsRef.current = [];
    isMealCompletingRef.current = false;

    setActiveIngredients(activeIngredientsRef.current);
    setTotalScore(totalScoreRef.current);
    setPlateIngredients([]);
    setLastMealScore(mealScore);
    setShowMealScore(true);

    // Hide score popup after 1s (plate is already accepting ingredients)
    setTimeout(() => {
      setShowMealScore(false);
      setLastMealScore(null);
    }, 1000);
  }, [playMealCompleteSound]);

  // Keep completeMealRef current
  completeMealRef.current = completeMeal;

  // ─── Despawn Ingredient ──────────────────────────────────────────────────────

  const despawnIngredient = useCallback((id: string) => {
    const active = activeIngredientsRef.current;
    const target = active.find((i) => i.id === id);
    if (!target) return;

    activeIngredientsRef.current = active.filter((i) => i.id !== id);
    laneCountsRef.current[target.laneIndex] = Math.max(0, laneCountsRef.current[target.laneIndex] - 1);

    setActiveIngredients(activeIngredientsRef.current);
  }, []);

  return {
    gamePhase,
    timeRemaining,
    totalScore,
    activeIngredients,
    plateIngredients,
    lastMealScore,
    showMealScore,
    highScore,
    isNewHighScore,
    dailyReward,
    startGame,
    resetGame,
    catchIngredient,
    despawnIngredient,
  };
}
