/**
 * ScoreDisplay — HUD component showing score, timer, and back button.
 * During a round, shows a back arrow instead of the drawer toggle.
 *
 * Performance: Wrapped in React.memo so it only re-renders when
 * score or timeRemaining actually change, not on ingredient list updates.
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Colors } from '@/constants/colors';
import { Typography } from '@/constants/fonts';
import { Spacing } from '@/constants/spacing';
import { Radius } from '@/constants/radius';

interface ScoreDisplayProps {
  score: number;
  timeRemaining: number;
  onBack: () => void;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

function ScoreDisplayInner({ score, timeRemaining, onBack }: ScoreDisplayProps) {
  const insets = useSafeAreaInsets();
  const isUrgent = timeRemaining <= 10;

  return (
    <View style={[styles.container, { paddingTop: insets.top + Spacing.sm }]}>
      <View style={styles.inner}>

        <View style={styles.hudItems}>
          <View style={styles.item}>
            <Text style={styles.label}>⏱</Text>
            <Text style={[styles.value, isUrgent && styles.urgentValue]}>
              {formatTime(timeRemaining)}
            </Text>
          </View>
          <View style={styles.divider} />
          <View style={styles.item}>
            <Text style={styles.label}>⭐</Text>
            <Text style={styles.value}>{score}</Text>
          </View>
        </View>
      </View>
    </View>
  );
}

const ScoreDisplay = React.memo(ScoreDisplayInner);
export default ScoreDisplay;

const styles = StyleSheet.create({
  container: {
    backgroundColor: Colors.surface_container,
    paddingBottom: Spacing.sm,
    paddingHorizontal: Spacing.md,
    borderBottomLeftRadius: Radius.lg,
    borderBottomRightRadius: Radius.lg,
  },
  inner: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  hudItems: {
    flex: 1,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
  },
  item: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.xs,
    paddingHorizontal: Spacing.md,
  },
  label: {
    fontSize: 22,
  },
  value: {
    ...Typography.headlineMedium,
    color: Colors.on_surface,
  },
  urgentValue: {
    color: Colors.tertiary,
  },
  divider: {
    width: 1,
    height: 28,
    backgroundColor: Colors.outline_variant,
    opacity: 0.4,
    marginHorizontal: Spacing.sm,
  },
});
