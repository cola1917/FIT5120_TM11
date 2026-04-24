/**
 * Meal Maker - Game Screen
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
  Image,
  Animated,
} from 'react-native';
import { useRouter, useFocusEffect } from 'expo-router';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { Audio } from 'expo-av';
import { BookOpen, Play, Star } from 'lucide-react-native';

import { useGameEngine } from '@/hooks/games/useGameEngine';
import AboutModal from '@/components/games/meal-maker/AboutModal';
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
  const [showAbout, setShowAbout] = useState(false);
  const plateWrapperRef = useRef<View>(null);

  // Audio

  const menuSoundRef = useRef<Audio.Sound | null>(null);
  const isMenuPlayingRef = useRef(false);

  const roundSoundRef = useRef<Audio.Sound | null>(null);
  const isRoundPlayingRef = useRef(false);

  const playMenuMusic = useCallback(async () => {
    if (menuSoundRef.current) return;
    try {
      const { sound } = await Audio.Sound.createAsync(
        require('../../../assets/audio/menu-audio.mp3'),
        { isLooping: true, shouldPlay: true, volume: 0.7 }
      );
      menuSoundRef.current = sound;
      isMenuPlayingRef.current = true;
    } catch (_) {}
  }, []);

  const stopMenuMusic = useCallback(async () => {
    const sound = menuSoundRef.current;
    menuSoundRef.current = null;
    isMenuPlayingRef.current = false;
    if (!sound) return;
    try { await sound.stopAsync(); } catch (_) {}
    try { await sound.unloadAsync(); } catch (_) {}
  }, []);

  const playRoundMusic = useCallback(async () => {
    if (isRoundPlayingRef.current) return;
    try {
      await stopMenuMusic();
      if (roundSoundRef.current) {
        await roundSoundRef.current.unloadAsync().catch(() => {});
        roundSoundRef.current = null;
      }
      const { sound } = await Audio.Sound.createAsync(
        require('../../../assets/audio/round-audio.mp3'),
        { isLooping: false, shouldPlay: true, volume: 0.5 }
      );
      roundSoundRef.current = sound;
      isRoundPlayingRef.current = true;
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
    try { await sound.stopAsync(); } catch (_) {}
    try { await sound.unloadAsync(); } catch (_) {}
    roundSoundRef.current = null;
    isRoundPlayingRef.current = false;
  }, []);

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
    }
  }, [gamePhase, playRoundMusic]);

  // Plate layout

  const handlePlateLayout = useCallback((_zone: { x: number; y: number; width: number; height: number }) => {
    if (plateWrapperRef.current) {
      plateWrapperRef.current.measureInWindow((x, y, width, height) => {
        setPlateZone({ x, y, width, height });
      });
    }
  }, []);

  // Navigation

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

  // Render

  const scale = useRef(new Animated.Value(1)).current;
  useEffect(() => {
    // Defines a loop: Scale to 1.1, then back to 1
    Animated.loop(
      Animated.sequence([
        Animated.timing(scale, { toValue: 1.05, duration: 400, useNativeDriver: true }),
        Animated.timing(scale, { toValue: 1, duration: 400, useNativeDriver: true })
      ])
    ).start();
  }, []);

  return (
    <GestureHandlerRootView style={styles.root}>
      <View style={styles.container}>

        {/* HUD */}
        {gamePhase === 'playing' && (
          <ScoreDisplay score={totalScore} timeRemaining={timeRemaining} onBack={handleBack} />
        )}

        {/* Game field */}
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

          {/* Idle / start screen */}
          {gamePhase === 'idle' && (
            <View style={styles.idleContainer}>
              <Image
                source={require('../../../assets/images/nutriheroes_logo.png')}
                style={styles.heroImage}
                resizeMode="contain"
              />

              <Text style={styles.idleTitle}>Meal Maker</Text>
              <Text style={styles.idleSubtitle}>Drag foods to build{'\n'}healthy meals!</Text>

              {highScore > 0 && (
                <View style={styles.scoreCard}>
                  <View style={styles.scoreItem}>
                    <Star size={46} color="#F5A623" fill="#FFD15C" />
                    <View>
                      <Text style={styles.scoreLabel}>BEST SCORE</Text>
                      <Text style={styles.scoreValue}>{highScore}</Text>
                    </View>
                  </View>
                </View>
              )}

              <Animated.View style={{...styles.startButtonContainer, transform: [{scale}], alignItems: 'center'}}>
                <TouchableOpacity style={styles.startButton} onPress={handleStartGame} activeOpacity={0.85}>
                  <View style={styles.playIconCircle}>
                    <Play size={28} color={Colors.secondary_dim} fill={Colors.secondary_dim} />
                  </View>
                  <Text style={styles.startButtonText}>START GAME</Text>
                </TouchableOpacity>
              </Animated.View>

              {/* How to Play button */}
              <TouchableOpacity
                style={styles.aboutButton}
                onPress={() => setShowAbout(true)}
                activeOpacity={0.8}
              >
                <BookOpen size={20} color="#4F4A43" />
                <Text style={styles.aboutButtonText}>How to Play</Text>
              </TouchableOpacity>
            </View>
          )}
        </View>

        {/* About modal */}
        <AboutModal visible={showAbout} onClose={() => setShowAbout(false)} />

        {/* Plate area */}
        {gamePhase === 'playing' && (
          <View style={styles.plateArea} ref={plateWrapperRef}>
            <Plate
              plateIngredients={plateIngredients}
              onPlateLayout={handlePlateLayout}
            />
          </View>
        )}

        {/* Meal score popup */}
        {gamePhase === 'playing' && (
          <View style={styles.scorePopupContainer} pointerEvents="none">
            <MealScorePopup
              score={lastMealScore ?? 0}
              visible={showMealScore}
            />
          </View>
        )}

        {/* Game over overlay */}
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

  // Idle screen
  idleContainer: {
    flex: 1,
    alignItems: 'center',
    paddingHorizontal: Spacing.xl,
    paddingTop: Spacing['2xl'],
    gap: Spacing.lg,
    backgroundColor: '#FFFDF4',
  },
  heroImage: {
    height: 160,
    marginTop: Spacing.md,
  },
  idleTitle: {
    ...Typography.displaySmall,
    color: Colors.on_surface,
    textAlign: 'center',
    fontSize: 42,
    fontWeight: '900',
  },
  idleSubtitle: {
    ...Typography.bodyLarge,
    color: Colors.on_surface_variant,
    textAlign: 'center',
    fontSize: 22,
    lineHeight: 30,
  },
  scoreCard: {
    width: '100%',
    maxWidth: 390,
    minHeight: 96,
    borderRadius: 24,
    backgroundColor: '#F7F1E6',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-around',
    paddingHorizontal: Spacing.lg,
    marginTop: Spacing.sm,
  },
  scoreItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.lg,
  },
  scoreLabel: {
    fontSize: 16,
    fontWeight: '900',
    color: '#3F3D38',
  },
  scoreValue: {
    fontSize: 30,
    fontWeight: '900',
    color: '#B5471F',
    textAlign: 'center',
  },
  startButtonContainer: {
    alignItems: 'center',
  },
  startButton: {
    width: '92%',
    maxWidth: 360,
    padding: Spacing.lg,
    borderRadius: 32,
    backgroundColor: Colors.secondary_dim,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.lg,
    marginVertical: Spacing.md,
    shadowColor: '#7A2204',
    shadowOffset: { width: 0, height: 5 },
    shadowOpacity: 0.25,
    shadowRadius: 0,
    elevation: 4,
  },
  playIconCircle: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: '#FFFFFF',
    alignItems: 'center',
    justifyContent: 'center',
  },
  startButtonText: {
    color: Colors.on_primary,
    fontSize: 26,
    fontWeight: '900',
  },
  aboutButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
    paddingVertical: Spacing.md,
    paddingHorizontal: Spacing.xl,
    borderRadius: Radius.full,
    backgroundColor: '#F0EBE0',
  },
  aboutButtonText: {
    fontSize: 17,
    fontWeight: '700',
    color: '#4F4A43',
    fontFamily: 'BeVietnamPro-Medium',
  },

  // Playing overlays
  scorePopupContainer: {
    position: 'absolute',
    top: 80,
    left: 0,
    right: 0,
    alignItems: 'center',
    zIndex: 20,
  },
});
