/**
 * GameOverOverlay — End-of-round results screen
 *
 * Shows score, high score badge, motivational message, and daily points
 * reward status (matching the animation style from story-outcome.tsx).
 */

import React, { useEffect, useRef } from 'react';
import { Animated, Image, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import Reanimated, {
  Easing,
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withSequence,
  withTiming,
} from 'react-native-reanimated';
import { ArrowLeft, CheckCircle, Heart, RotateCcw } from 'lucide-react-native';
import { Colors } from '@/constants/colors';
import { Typography } from '@/constants/fonts';
import { Spacing } from '@/constants/spacing';
import { Radius } from '@/constants/radius';
import type { DailyRewardResult } from '@/services/gameDailyRewards';
import { MAX_DAILY_PLAYS } from '@/services/gameDailyRewards';

const MEDIUM_SCORE_THRESHOLD = 120;
const HIGH_SCORE_THRESHOLD = 180;

interface GameOverOverlayProps {
  score: number;
  highScore: number;
  isNewHighScore: boolean;
  dailyReward: DailyRewardResult | null;
  onPlayAgain: () => void;
  onBack: () => void;
}

export default function GameOverOverlay({
  score,
  highScore,
  isNewHighScore,
  dailyReward,
  onPlayAgain,
  onBack,
}: GameOverOverlayProps) {
  // ─── Reanimated: high score pulse ────────────────────────────────────────────
  const pulseScale = useSharedValue(1);

  useEffect(() => {
    if (isNewHighScore) {
      pulseScale.value = withRepeat(
        withSequence(
          withTiming(1.08, { duration: 400, easing: Easing.inOut(Easing.ease) }),
          withTiming(1, { duration: 400, easing: Easing.inOut(Easing.ease) })
        ),
        4,
        false
      );
    }
  }, [isNewHighScore, pulseScale]);

  const pulseStyle = useAnimatedStyle(() => ({
    transform: [{ scale: pulseScale.value }],
  }));

  // ─── Animated: daily reward float + badge pulse (mirrors story-outcome.tsx) ──
  const floatAnim = useRef(new Animated.Value(0)).current;
  const floatOpacity = useRef(new Animated.Value(0)).current;
  const badgeScale = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    if (!dailyReward?.awarded) return;

    // Reset
    floatAnim.setValue(0);
    floatOpacity.setValue(1);
    badgeScale.setValue(1);

    Animated.parallel([
      // Float "+score ⭐" upward and fade out
      Animated.timing(floatAnim, {
        toValue: -80,
        duration: 1000,
        useNativeDriver: true,
      }),
      Animated.sequence([
        Animated.delay(400),
        Animated.timing(floatOpacity, {
          toValue: 0,
          duration: 600,
          useNativeDriver: true,
        }),
      ]),
      // Pulse the badge
      Animated.sequence([
        Animated.spring(badgeScale, {
          toValue: 1.12,
          useNativeDriver: true,
          speed: 30,
          bounciness: 10,
        }),
        Animated.spring(badgeScale, {
          toValue: 1,
          useNativeDriver: true,
          speed: 20,
          bounciness: 6,
        }),
      ]),
    ]).start();
  }, [dailyReward, floatAnim, floatOpacity, badgeScale]);

  return (
    <View style={styles.overlay}>
      <View style={styles.content}>
        <Text style={styles.title}>Great Job, Hero!</Text>

        <Image
          source={require('../../../assets/images/Game_results_screen.png')}
          style={styles.heroImage}
          resizeMode="contain"
        />

        <Reanimated.View style={[styles.scoreCard, isNewHighScore && pulseStyle]}>
          <Text style={styles.scoreLabel}>SCORE</Text>
          <Text style={styles.scoreValue}>{score}</Text>
          {isNewHighScore && (
            <View style={styles.newBestBadge}>
              <Text style={styles.newBestText}>NEW BEST!</Text>
            </View>
          )}
          {!!highScore && !isNewHighScore && (
            <Text style={styles.bestText}>Best: {highScore}</Text>
          )}
        </Reanimated.View>

        {score > HIGH_SCORE_THRESHOLD ?
          (
            <View style={styles.messageCard}>
              <Text style={styles.messageText}>You made healthy choices!</Text>
              <Text style={styles.messageText}>Keep being awesome!</Text>
              <Heart size={24} color="#79B95B" fill="#79B95B" />
            </View>
          ) :
          score > MEDIUM_SCORE_THRESHOLD ?
            (<Text style={styles.messageText}>You made healthy choices!</Text>) :
            (undefined)
        }

        {/* Daily reward section */}
        {dailyReward !== null && (
          <View style={styles.rewardContainer}>
            {dailyReward.awarded ? (
              <View style={styles.rewardWrapper}>
                {/* Floating "+score ⭐" label */}
                <Animated.View
                  style={[
                    styles.floatingPoints,
                    {
                      transform: [{ translateY: floatAnim }],
                      opacity: floatOpacity,
                    },
                  ]}
                  pointerEvents="none"
                >
                  <Text style={styles.floatingPointsText}>+{score} ⭐</Text>
                </Animated.View>

                {/* Awarded badge */}
                <Animated.View style={{ transform: [{ scale: badgeScale }], alignSelf: 'stretch' }}>
                  <View style={styles.awardedBadge}>
                    <CheckCircle size={18} color="#2F9E44" />
                    <Text style={styles.awardedText}>+{score} points added!</Text>
                  </View>
                </Animated.View>

                <Text style={styles.playsText}>
                  Daily plays: {dailyReward.playsToday}/{MAX_DAILY_PLAYS}
                </Text>
              </View>
            ) : (
              <View style={styles.limitBadge}>
                <Text style={styles.limitText}>
                  Daily limit reached ({MAX_DAILY_PLAYS}/{MAX_DAILY_PLAYS}) — come back tomorrow!
                </Text>
              </View>
            )}
          </View>
        )}

        <View style={styles.buttons}>
          <TouchableOpacity style={styles.primaryButton} onPress={onPlayAgain} activeOpacity={0.85}>
            <RotateCcw size={24} color="#FFFFFF" strokeWidth={3} />
            <Text style={styles.primaryButtonText}>PLAY AGAIN</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.secondaryButton} onPress={onBack} activeOpacity={0.85}>
            <ArrowLeft size={22} color="#B64220" />
            <Text style={styles.secondaryButtonText}>BACK TO MENU</Text>
          </TouchableOpacity>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: '#FFFDF4',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 100,
  },
  content: {
    width: '100%',
    maxWidth: 420,
    alignItems: 'center',
    paddingHorizontal: Spacing.xl,
    gap: Spacing.md,
  },
  title: {
    ...Typography.displaySmall,
    color: '#A93B1D',
    textAlign: 'center',
    fontSize: 34,
    lineHeight: 42,
    fontWeight: '900',
  },
  heroImage: {
    width: '82%',
    height: 160,
    marginTop: -Spacing.sm,
    marginBottom: -Spacing.md,
  },
  scoreCard: {
    width: '66%',
    minHeight: 128,
    borderRadius: 22,
    borderWidth: 2,
    borderColor: '#F0DDC6',
    backgroundColor: '#FFFDF8',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: Spacing.md,
    shadowColor: Colors.shadow,
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.06,
    shadowRadius: 16,
    elevation: 3,
  },
  scoreLabel: {
    fontSize: 18,
    fontWeight: '900',
    color: '#3E3A35',
    letterSpacing: 0,
  },
  scoreValue: {
    fontSize: 56,
    lineHeight: 64,
    fontWeight: '900',
    color: '#B64220',
  },
  newBestBadge: {
    backgroundColor: '#5FAC45',
    borderRadius: Radius.full,
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.xs,
  },
  newBestText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '900',
  },
  bestText: {
    fontSize: 18,
    fontWeight: '700',
    color: Colors.on_surface_variant,
  },
  messageCard: {
    width: '100%',
    borderRadius: 18,
    borderWidth: 1.5,
    borderColor: '#D8EDC7',
    backgroundColor: '#F4FAEC',
    paddingVertical: Spacing.base,
    paddingHorizontal: Spacing.lg,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: Spacing.sm,
  },
  messageText: {
    flexShrink: 1,
    color: '#2F6B2E',
    fontSize: 18,
    lineHeight: 26,
    fontWeight: '800',
    textAlign: 'center',
  },

  // ─── Daily reward ────────────────────────────────────────────────────────────
  rewardContainer: {
    alignSelf: 'stretch',
  },
  rewardWrapper: {
    alignItems: 'center',
    position: 'relative',
    gap: Spacing.xs,
  },
  floatingPoints: {
    position: 'absolute',
    top: 0,
    zIndex: 10,
    backgroundColor: '#FFF3CD',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderWidth: 2,
    borderColor: '#F5C842',
    shadowColor: '#000',
    shadowOpacity: 0.12,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
    elevation: 4,
  },
  floatingPointsText: {
    fontSize: 20,
    fontWeight: '900',
    color: '#B45309',
  },
  awardedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: '#EBFBEE',
    borderRadius: Radius.full,
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderWidth: 2,
    borderColor: '#B2F2BB',
    alignSelf: 'stretch',
  },
  awardedText: {
    color: '#2F9E44',
    fontSize: 16,
    fontWeight: '900',
  },
  playsText: {
    fontSize: 13,
    fontWeight: '700',
    color: Colors.on_surface_variant,
    textAlign: 'center',
  },
  limitBadge: {
    backgroundColor: '#FFF8E1',
    borderRadius: Radius.full,
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderWidth: 2,
    borderColor: '#FFE082',
    alignItems: 'center',
  },
  limitText: {
    color: '#B45309',
    fontSize: 14,
    fontWeight: '800',
    textAlign: 'center',
  },

  // ─── Buttons ─────────────────────────────────────────────────────────────────
  buttons: {
    width: '100%',
    gap: Spacing.md,
    marginTop: Spacing.md,
  },
  primaryButton: {
    height: 58,
    borderRadius: 22,
    backgroundColor: '#C83A08',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.md,
    shadowColor: '#7A2204',
    shadowOffset: { width: 0, height: 5 },
    shadowOpacity: 0.22,
    shadowRadius: 0,
    elevation: 4,
  },
  primaryButtonText: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: '900',
  },
  secondaryButton: {
    height: 50,
    borderRadius: 18,
    borderWidth: 1.5,
    borderColor: '#F0DDC6',
    backgroundColor: '#FFF9EC',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.sm,
  },
  secondaryButtonText: {
    color: '#B64220',
    fontSize: 16,
    fontWeight: '900',
  },
});
