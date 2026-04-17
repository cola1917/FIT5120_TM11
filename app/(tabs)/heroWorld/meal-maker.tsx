/**
 * Meal Maker — Game Screen
 *
 * Performance: Callbacks passed to child components are stabilized with
 * useCallback so that React.memo on children (FallingIngredient, ScoreDisplay,
 * Plate) can skip re-renders effectively.
 */

import React, { useRef, useState, useCallback, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
} from 'react-native';
import { useRouter, useFocusEffect, useNavigation } from 'expo-router';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { Audio } from 'expo-av';

import { useGameEngine } from '@/hooks/games/useGameEngine';
import ScoreDisplay from '@/components/games/meal-maker/ScoreDisplay';
import FallingIngredient from '@/components/games/meal-maker/FallingIngredient';
import Plate from '@/components/games/meal-maker/Plate';
import MealScorePopup from '@/components/games/meal-maker/MealScorePopup';
import GameOverOverlay from '@/components/games/meal-maker/GameOverOverlay';

import { Colors } from '@/constants/colors';
import { Typography } from '@/constants/fonts';
import { Spacing } from '@/constants/spacing';
import { Radius } from '@/constants/radius';

interface PlateZone {
  x: number;
  y: number;
  width: number;
  height: number;
}

export default function MealMakerScreen() {
  const router = useRouter();
  const navigation = useNavigation();

  const {
    gamePhase,
    timeRemaining,
    totalScore,
    activeIngredients,
    plateIngredients,
    lastMealScore,
    showMealScore,
    highScore,
    isNewHighScore,
    startGame,
    resetGame,
    catchIngredient,
    despawnIngredient,
  } = useGameEngine();

  const [plateZone, setPlateZone] = useState<PlateZone | null>(null);
  const plateWrapperRef = useRef<View>(null);

  // ─── AUDIO ────────────────────────────────────────────────

  const menuSoundRef = useRef<Audio.Sound | null>(null);
  const isMenuPlayingRef = useRef(false);

  const roundSoundRef = useRef<Audio.Sound | null>(null);
  const isRoundPlayingRef = useRef(false);

  const playMenuMusic = useCallback(async () => {
    // Prevent duplicate playback
    if (menuSoundRef.current) return;

    try {
      const { sound } = await Audio.Sound.createAsync(
        require('../../../assets/audio/menu-audio.mp3'),
        {
          isLooping: true,
          shouldPlay: true,
          volume: 0.7,
        }
      );

      menuSoundRef.current = sound;
      isMenuPlayingRef.current = true;
    } catch (_) {}
  }, []);

  const stopMenuMusic = useCallback(async () => {
    const sound = menuSoundRef.current;
    // Immediately clear ref (prevents overlap)
    menuSoundRef.current = null;
    isMenuPlayingRef.current = false;

    if (!sound) return;

    try {
      await sound.stopAsync();
    } catch (_) {}

    try {
      await sound.unloadAsync();
    } catch (_) {}

    menuSoundRef.current = null;
    isMenuPlayingRef.current = false;
  }, []);

  const playRoundMusic = useCallback(async () => {
    // Prevent duplicates
    if (isRoundPlayingRef.current) return;

    try {
      // Stop menu music first
      await stopMenuMusic();

      // Clean up existing round sound
      if (roundSoundRef.current) {
        await roundSoundRef.current.unloadAsync().catch(() => {});
        roundSoundRef.current = null;
      }

      const { sound } = await Audio.Sound.createAsync(
        require('../../../assets/audio/round-audio.mp3'),
        {
          isLooping: false,
          shouldPlay: true,
          volume: 0.5
        }
      );

      roundSoundRef.current = sound;
      isRoundPlayingRef.current = true;

      // When round music finishes naturally, reset state
      sound.setOnPlaybackStatusUpdate((status) => {
        if (!status.isLoaded) return;
        if (status.didJustFinish) {
          isRoundPlayingRef.current = false;
          roundSoundRef.current = null;
        }
      });
    } catch (_) {}
  }, [stopMenuMusic]);

  const stopRoundMusic = useCallback(async () => {
    const sound = roundSoundRef.current;
    if (!sound) return;

    try {
      await sound.stopAsync();
    } catch (_) {}

    try {
      await sound.unloadAsync();
    } catch (_) {}

    roundSoundRef.current = null;
    isRoundPlayingRef.current = false;
  }, []);

  // Handle screen focus / blur correctly
  useFocusEffect(
    useCallback(() => {
      playMenuMusic();

      return () => {
        stopMenuMusic();
        stopRoundMusic();
        resetGame();
      };
    }, [playMenuMusic, stopMenuMusic, stopRoundMusic, resetGame])
  );

  useEffect(() => {
    if (gamePhase === 'playing') {
      playRoundMusic();
    } else if (gamePhase === 'idle' || gamePhase === 'game_over') {
      // Stop round → resume menu
      // stopRoundMusic();
    }
  }, [gamePhase, playRoundMusic, stopRoundMusic, playMenuMusic]);

  // ─── Plate Layout ────────────────────────────────────────────────────────────

  const handlePlateLayout = useCallback((_zone: { x: number; y: number; width: number; height: number }) => {
    if (plateWrapperRef.current) {
      plateWrapperRef.current.measureInWindow((x, y, width, height) => {
        setPlateZone({ x, y, width, height });
      });
    }
  }, []);

  // ─── Navigation ──────────────────────────────────────────────────────────────

  const handlePlayAgain = useCallback(() => {
    resetGame();
    setTimeout(() => startGame(), 100);
  }, [resetGame, startGame]);

  const handleBack = useCallback(() => {
    resetGame();
    router.back();
  }, [resetGame, router]);

  const handleStartGame = useCallback(() => {
    startGame();
  }, [startGame]);

  return (
    <GestureHandlerRootView style={styles.root}>
      <View style={styles.container}>
        {gamePhase === 'playing' && (
          <ScoreDisplay score={totalScore} timeRemaining={timeRemaining} onBack={handleBack} />
        )}

        <View style={styles.gameField}>
          {gamePhase === 'playing' &&
            activeIngredients.map((item) => (
              <FallingIngredient
                key={item.id}
                id={item.id}
                ingredient={item.ingredient}
                laneIndex={item.laneIndex}
                fallDuration={item.fallDuration}
                plateZone={plateZone}
                onCatch={catchIngredient}
                onDespawn={despawnIngredient}
              />
            ))}

          {gamePhase === 'idle' && (
            <View style={styles.idleContainer}>
              <Text style={styles.idleEmoji}>🍽️</Text>
              <Text style={styles.idleTitle}>Meal Maker</Text>
              <Text style={styles.idleSubtitle}>
                Drag falling ingredients onto your plate to build healthy meals!
              </Text>
              {highScore > 0 && (
                <Text style={styles.idleHighScore}>⭐ Best: {highScore}</Text>
              )}
              <TouchableOpacity style={styles.startButton} onPress={handleStartGame} activeOpacity={0.85}>
                <Text style={styles.startButtonText}>Start Game</Text>
              </TouchableOpacity>
            </View>
          )}
        </View>

        {(gamePhase === 'playing' || gamePhase === 'idle') && (
          <View style={styles.plateArea} ref={plateWrapperRef}>
            <Plate
              plateIngredients={plateIngredients}
              onPlateLayout={handlePlateLayout}
            />
          </View>
        )}

        {/* Meal Score Popup — centered at top of game field, above everything */}
        {gamePhase === 'playing' && (
          <View style={styles.scorePopupContainer} pointerEvents="none">
            <MealScorePopup
              score={lastMealScore ?? 0}
              visible={showMealScore}
            />
          </View>
        )}

        {gamePhase === 'game_over' && (
          <GameOverOverlay
            score={totalScore}
            highScore={highScore}
            isNewHighScore={isNewHighScore}
            onPlayAgain={handlePlayAgain}
            onBack={handleBack}
          />
        )}
      </View>
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  container: {
    flex: 1,
    backgroundColor: Colors.surface,
  },
  gameField: {
    flex: 1,
    position: 'relative',
    zIndex: 1,
  },
  plateArea: {
    alignItems: 'center',
    paddingBottom: Spacing['2xl'],
    paddingTop: Spacing.sm,
    backgroundColor: Colors.surface_container_low,
    borderTopLeftRadius: Radius.lg,
    borderTopRightRadius: Radius.lg,
    zIndex: 0,
  },
  idleContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: Spacing.xl,
    gap: Spacing.md,
  },
  idleEmoji: { fontSize: 80 },
  idleTitle: {
    ...Typography.displaySmall,
    color: Colors.on_surface,
    textAlign: 'center',
  },
  idleSubtitle: {
    ...Typography.bodyLarge,
    color: Colors.on_surface_variant,
    textAlign: 'center',
    maxWidth: 280,
  },
  idleHighScore: {
    ...Typography.titleMedium,
    color: Colors.primary,
  },
  scorePopupContainer: {
    position: 'absolute',
    top: 80, // below the HUD
    left: 0,
    right: 0,
    alignItems: 'center',
    zIndex: 20,
  },
  startButton: {
    backgroundColor: Colors.primary,
    borderRadius: Radius.full,
    paddingVertical: Spacing.md,
    paddingHorizontal: Spacing['2xl'],
    marginTop: Spacing.md,
  },
  startButtonText: {
    ...Typography.labelLarge,
    color: Colors.on_primary,
    fontSize: 20,
  },
});
