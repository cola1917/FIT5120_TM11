/**
 * FoodPreferencesSelector
 *
 * A two-section UI component for selecting food preferences and blacklist items.
 * - Likes/Dislikes section: tiles cycle through 'like' → 'dislike' → 'no preference'
 * - Blacklist section: tiles toggle between selected and not selected
 *
 * Includes animated indicators that demonstrate how each section's selection UI works.
 */

import React, { useEffect, useRef } from 'react';
import {
  Animated,
  Easing,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { Colors } from '@/constants/colors';
import { Typography } from '@/constants/fonts';
import { Spacing } from '@/constants/spacing';
import { Radius } from '@/constants/radius';
import { FoodPreferenceItem, BlacklistItem } from '@/services/userProfile';

// Types

export type LikeDislikeState = 'like' | 'dislike' | 'none';

export type LikeDislikeMap = Record<FoodPreferenceItem, LikeDislikeState>;
export type BlacklistMap = Record<BlacklistItem, boolean>;

// Constants

export const FOOD_PREFERENCE_ITEMS: { id: FoodPreferenceItem; emoji: string; label: string }[] = [
  { id: 'fruits', emoji: '🍓', label: 'Fruits' },
  { id: 'vegetables', emoji: '🥦', label: 'Vegetables' },
  { id: 'rice', emoji: '🍚', label: 'Rice' },
  { id: 'bread', emoji: '🍞', label: 'Bread' },
  { id: 'noodles', emoji: '🍜', label: 'Noodles' },
  { id: 'meat', emoji: '🥩', label: 'Meat' },
  { id: 'fish', emoji: '🐟', label: 'Fish' },
  { id: 'dairy', emoji: '🧀', label: 'Dairy' },
];

export const BLACKLIST_ITEMS: { id: BlacklistItem; emoji: string; label: string }[] = [
  { id: 'egg', emoji: '🥚', label: 'Egg' },
  { id: 'bread', emoji: '🍞', label: 'Bread' },
  { id: 'milk', emoji: '🥛', label: 'Milk' },
  { id: 'pork', emoji: '🥓', label: 'Pork' },
  { id: 'seafood', emoji: '🦐', label: 'Seafood' },
  { id: 'nuts', emoji: '🌰', label: 'Nuts' },
];

// Default State Factories

export function createDefaultLikeDislikeMap(): LikeDislikeMap {
  const map = {} as LikeDislikeMap;
  for (const item of FOOD_PREFERENCE_ITEMS) {
    map[item.id] = 'none';
  }
  return map;
}

export function createDefaultBlacklistMap(): BlacklistMap {
  const map = {} as BlacklistMap;
  for (const item of BLACKLIST_ITEMS) {
    map[item.id] = false;
  }
  return map;
}

// ─── Shared Tile Styles ───────────────────────────────────────────────────────
//
// Both the real interactive tiles and the animated demo tiles share these
// style definitions so they look identical.

const tileStyles = StyleSheet.create({
  // Base tile — used by real tiles (width: '30%') and demo tiles (fixed 80×80)
  tile: {
    width: '30%',
    aspectRatio: 1,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: Radius.card,
    backgroundColor: Colors.surface_container_lowest,
    borderWidth: 2,
    borderColor: Colors.outline_variant,
    paddingVertical: Spacing.sm,
    paddingHorizontal: Spacing.xs,
    position: 'relative',
  },
  // Demo tile overrides only the size; all other properties come from `tile`
  tileDemo: {
    width: 80,
    height: 80,
    aspectRatio: undefined,
  },
  // State variants
  tileLike: {
    borderColor: Colors.primary,
    backgroundColor: Colors.primary_container,
  },
  tileDislike: {
    borderColor: Colors.secondary,
    backgroundColor: Colors.secondary_container,
  },
  tileBlacklisted: {
    borderColor: Colors.error,
    backgroundColor: Colors.error_container,
  },
  // Emoji
  emoji: {
    fontSize: 32,
    marginBottom: Spacing.xs,
  },
  emojiDemo: {
    fontSize: 28,
    marginBottom: 2,
  },
  // Label
  label: {
    ...Typography.labelSmall,
    color: Colors.on_surface_variant,
    textAlign: 'center',
  },
  labelDemo: {
    fontSize: 10,
  },
  labelLike: {
    color: Colors.on_primary_container,
    fontWeight: '700',
  },
  labelDislike: {
    color: Colors.on_secondary_container,
    fontWeight: '700',
  },
  labelBlacklisted: {
    color: Colors.on_error_container,
    fontWeight: '700',
  },
  // Badge (top-right corner indicator)
  indicatorBadge: {
    position: 'absolute',
    top: 4,
    right: 4,
    backgroundColor: Colors.primary,
    borderRadius: Radius.full,
    width: 20,
    height: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  indicatorBadgeDislike: {
    backgroundColor: Colors.secondary,
  },
  indicatorBadgeBlacklist: {
    backgroundColor: Colors.error,
  },
  indicatorText: {
    fontSize: 10,
  },
});

// ─── Animated Like/Dislike Indicator ─────────────────────────────────────────

/**
 * Animated indicator that cycles through the three like/dislike states
 * (none → like → dislike → none) to show users how the tile interaction works.
 */
function LikeDislikeIndicator() {
  const stepRef = useRef(0);
  const stepAnim = useRef(new Animated.Value(0)).current;
  const arrowBounce = useRef(new Animated.Value(0)).current;

  // Derived animated values for each state's opacity
  const noneOpacity = stepAnim.interpolate({
    inputRange: [0, 0.4, 1, 1.4, 2, 2.4, 3],
    outputRange: [1, 0, 0, 0, 0, 0, 1],
    extrapolate: 'clamp',
  });
  const likeOpacity = stepAnim.interpolate({
    inputRange: [0, 0.4, 1, 1.4, 2],
    outputRange: [0, 0, 1, 0, 0],
    extrapolate: 'clamp',
  });
  const dislikeOpacity = stepAnim.interpolate({
    inputRange: [1, 1.4, 2, 2.4, 3],
    outputRange: [0, 0, 1, 0, 0],
    extrapolate: 'clamp',
  });

  // Animated background / border colours for the demo tile
  const bgColor = stepAnim.interpolate({
    inputRange: [0, 0.4, 1, 1.4, 2, 2.4, 3],
    outputRange: [
      Colors.surface_container_lowest,
      Colors.surface_container_lowest,
      Colors.primary_container,
      Colors.primary_container,
      Colors.secondary_container,
      Colors.secondary_container,
      Colors.surface_container_lowest,
    ],
    extrapolate: 'clamp',
  });

  const borderColor = stepAnim.interpolate({
    inputRange: [0, 0.4, 1, 1.4, 2, 2.4, 3],
    outputRange: [
      Colors.outline_variant,
      Colors.outline_variant,
      Colors.primary,
      Colors.primary,
      Colors.secondary,
      Colors.secondary,
      Colors.outline_variant,
    ],
    extrapolate: 'clamp',
  });

  // Badge pop-in scale
  const badgeScale = stepAnim.interpolate({
    inputRange: [0, 0.4, 1, 1.4, 2, 2.4, 3],
    outputRange: [0, 0, 1, 0, 1, 0, 0],
    extrapolate: 'clamp',
  });

  useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(arrowBounce, {
          toValue: 4,
          duration: 400,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
        Animated.timing(arrowBounce, {
          toValue: 0,
          duration: 400,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
      ])
    ).start();

    const runCycle = () => {
      stepRef.current = 0;
      stepAnim.setValue(0);
      Animated.sequence([
        Animated.delay(800),
        Animated.timing(stepAnim, {
          toValue: 1,
          duration: 350,
          easing: Easing.out(Easing.back(1.5)),
          useNativeDriver: false,
        }),
        Animated.delay(1200),
        Animated.timing(stepAnim, {
          toValue: 2,
          duration: 350,
          easing: Easing.out(Easing.back(1.5)),
          useNativeDriver: false,
        }),
        Animated.delay(1200),
        Animated.timing(stepAnim, {
          toValue: 3,
          duration: 350,
          easing: Easing.out(Easing.ease),
          useNativeDriver: false,
        }),
        Animated.delay(600),
      ]).start(({ finished }) => {
        if (finished) runCycle();
      });
    };

    runCycle();
  }, []);

  return (
    <View style={indicatorStyles.container}>
      {/* Demo tile — shares tileStyles.tile + tileStyles.tileDemo */}
      <View style={indicatorStyles.demoWrapper}>
        <Animated.View
          style={[
            tileStyles.tile,
            tileStyles.tileDemo,
            { backgroundColor: bgColor, borderColor: borderColor },
          ]}
        >
          <Text style={[tileStyles.emoji, tileStyles.emojiDemo]}>🍎</Text>
          <Text style={[tileStyles.label, tileStyles.labelDemo]}>Example</Text>

          {/* Like badge */}
          <Animated.View
            style={[
              tileStyles.indicatorBadge,
              { opacity: likeOpacity, transform: [{ scale: badgeScale }] },
            ]}
          >
            <Text style={tileStyles.indicatorText}>👍</Text>
          </Animated.View>

          {/* Dislike badge */}
          <Animated.View
            style={[
              tileStyles.indicatorBadge,
              tileStyles.indicatorBadgeDislike,
              { opacity: dislikeOpacity, transform: [{ scale: badgeScale }] },
            ]}
          >
            <Text style={tileStyles.indicatorText}>👎</Text>
          </Animated.View>
        </Animated.View>
      </View>

      {/* Cycle legend */}
      <View style={indicatorStyles.legend}>
        <Animated.View style={[indicatorStyles.legendStep, { opacity: noneOpacity }]}>
          <View style={[indicatorStyles.legendDot, indicatorStyles.legendDotNone]} />
          <Text style={indicatorStyles.legendText}>No preference</Text>
        </Animated.View>

        <Animated.View style={[indicatorStyles.legendArrow, { transform: [{ translateX: arrowBounce }] }]}>
          <Text style={indicatorStyles.legendArrowText}>→</Text>
        </Animated.View>

        <Animated.View style={[indicatorStyles.legendStep, { opacity: likeOpacity }]}>
          <View style={[indicatorStyles.legendDot, indicatorStyles.legendDotLike]} />
          <Text style={indicatorStyles.legendText}>Like 👍</Text>
        </Animated.View>

        <Animated.View style={[indicatorStyles.legendArrow, { transform: [{ translateX: arrowBounce }] }]}>
          <Text style={indicatorStyles.legendArrowText}>→</Text>
        </Animated.View>

        <Animated.View style={[indicatorStyles.legendStep, { opacity: dislikeOpacity }]}>
          <View style={[indicatorStyles.legendDot, indicatorStyles.legendDotDislike]} />
          <Text style={indicatorStyles.legendText}>Dislike 👎</Text>
        </Animated.View>
      </View>

      <Text style={indicatorStyles.tapHint}>Tap a tile to cycle through states</Text>
    </View>
  );
}

// ─── Animated Blacklist Indicator ─────────────────────────────────────────────

/**
 * Animated indicator that toggles between unselected and blacklisted states
 * to show users how the blacklist tile interaction works.
 */
function BlacklistIndicator() {
  const toggleAnim = useRef(new Animated.Value(0)).current;
  const arrowBounce = useRef(new Animated.Value(0)).current;

  const bgColor = toggleAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [Colors.surface_container_lowest, Colors.error_container],
  });

  const borderColor = toggleAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [Colors.outline_variant, Colors.error],
  });

  const badgeOpacity = toggleAnim.interpolate({
    inputRange: [0, 0.5, 1],
    outputRange: [0, 0, 1],
  });

  const badgeScale = toggleAnim.interpolate({
    inputRange: [0, 0.5, 1],
    outputRange: [0, 0, 1],
  });

  const offOpacity = toggleAnim.interpolate({
    inputRange: [0, 0.4, 1],
    outputRange: [1, 0, 0],
  });

  const onOpacity = toggleAnim.interpolate({
    inputRange: [0, 0.6, 1],
    outputRange: [0, 0, 1],
  });

  useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(arrowBounce, {
          toValue: 4,
          duration: 400,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
        Animated.timing(arrowBounce, {
          toValue: 0,
          duration: 400,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
      ])
    ).start();

    const runCycle = () => {
      toggleAnim.setValue(0);
      Animated.sequence([
        Animated.delay(800),
        Animated.timing(toggleAnim, {
          toValue: 1,
          duration: 400,
          easing: Easing.out(Easing.back(1.5)),
          useNativeDriver: false,
        }),
        Animated.delay(1400),
        Animated.timing(toggleAnim, {
          toValue: 0,
          duration: 350,
          easing: Easing.out(Easing.ease),
          useNativeDriver: false,
        }),
        Animated.delay(600),
      ]).start(({ finished }) => {
        if (finished) runCycle();
      });
    };

    runCycle();
  }, []);

  return (
    <View style={indicatorStyles.container}>
      {/* Demo tile — shares tileStyles.tile + tileStyles.tileDemo */}
      <View style={indicatorStyles.demoWrapper}>
        <Animated.View
          style={[
            tileStyles.tile,
            tileStyles.tileDemo,
            { backgroundColor: bgColor, borderColor: borderColor },
          ]}
        >
          <Text style={[tileStyles.emoji, tileStyles.emojiDemo]}>🥜</Text>
          <Text style={[tileStyles.label, tileStyles.labelDemo]}>Example</Text>

          {/* Blacklist badge */}
          <Animated.View
            style={[
              tileStyles.indicatorBadge,
              tileStyles.indicatorBadgeBlacklist,
              { opacity: badgeOpacity, transform: [{ scale: badgeScale }] },
            ]}
          >
            <Text style={tileStyles.indicatorText}>🚫</Text>
          </Animated.View>
        </Animated.View>
      </View>

      {/* Toggle legend */}
      <View style={indicatorStyles.legend}>
        <Animated.View style={[indicatorStyles.legendStep, { opacity: offOpacity }]}>
          <View style={[indicatorStyles.legendDot, indicatorStyles.legendDotNone]} />
          <Text style={indicatorStyles.legendText}>Can eat</Text>
        </Animated.View>

        <Animated.View style={[indicatorStyles.legendArrow, { transform: [{ translateX: arrowBounce }] }]}>
          <Text style={indicatorStyles.legendArrowText}>→</Text>
        </Animated.View>

        <Animated.View style={[indicatorStyles.legendStep, { opacity: onOpacity }]}>
          <View style={[indicatorStyles.legendDot, indicatorStyles.legendDotBlacklist]} />
          <Text style={indicatorStyles.legendText}>Cannot eat 🚫</Text>
        </Animated.View>
      </View>

      <Text style={indicatorStyles.tapHint}>Tap a tile to mark foods you cannot eat</Text>
    </View>
  );
}

// ─── Indicator-only styles (layout/legend elements not shared with tiles) ─────

const indicatorStyles = StyleSheet.create({
  container: {
    backgroundColor: Colors.surface_container,
    borderRadius: Radius.card,
    padding: Spacing.md,
    alignItems: 'center',
    gap: Spacing.sm,
    borderWidth: 1.5,
    borderColor: Colors.outline_variant,
    borderStyle: 'dashed',
  },
  demoWrapper: {
    alignItems: 'center',
  },
  legend: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.xs,
    flexWrap: 'wrap',
    justifyContent: 'center',
  },
  legendStep: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  legendDot: {
    width: 10,
    height: 10,
    borderRadius: Radius.full,
    borderWidth: 1.5,
    borderColor: Colors.outline_variant,
  },
  legendDotNone: {
    backgroundColor: Colors.surface_container_lowest,
    borderColor: Colors.outline_variant,
  },
  legendDotLike: {
    backgroundColor: Colors.primary_container,
    borderColor: Colors.primary,
  },
  legendDotDislike: {
    backgroundColor: Colors.secondary_container,
    borderColor: Colors.secondary,
  },
  legendDotBlacklist: {
    backgroundColor: Colors.error_container,
    borderColor: Colors.error,
  },
  legendText: {
    ...Typography.labelSmall,
    color: Colors.on_surface_variant,
    fontSize: 11,
  },
  legendArrow: {
    paddingHorizontal: 2,
  },
  legendArrowText: {
    ...Typography.labelSmall,
    color: Colors.on_surface_variant,
    fontSize: 12,
  },
  tapHint: {
    ...Typography.labelSmall,
    color: Colors.on_surface_variant,
    fontSize: 11,
    fontStyle: 'italic',
    textAlign: 'center',
  },
});

// ─── Like/Dislike Tile ────────────────────────────────────────────────────────

interface LikeDislikeTileProps {
  emoji: string;
  label: string;
  state: LikeDislikeState;
  onPress: () => void;
}

function LikeDislikeTile({ emoji, label, state, onPress }: LikeDislikeTileProps) {
  const isLike = state === 'like';
  const isDislike = state === 'dislike';

  const indicator = isLike ? '👍' : isDislike ? '👎' : null;

  return (
    <TouchableOpacity
      style={[
        tileStyles.tile,
        isLike && tileStyles.tileLike,
        isDislike && tileStyles.tileDislike,
      ]}
      onPress={onPress}
      activeOpacity={0.75}
    >
      <Text style={tileStyles.emoji}>{emoji}</Text>
      <Text
        style={[
          tileStyles.label,
          isLike && tileStyles.labelLike,
          isDislike && tileStyles.labelDislike,
        ]}
      >
        {label}
      </Text>
      {indicator && (
        <View
          style={[
            tileStyles.indicatorBadge,
            isDislike && tileStyles.indicatorBadgeDislike,
          ]}
        >
          <Text style={tileStyles.indicatorText}>{indicator}</Text>
        </View>
      )}
    </TouchableOpacity>
  );
}

// ─── Blacklist Tile ───────────────────────────────────────────────────────────

interface BlacklistTileProps {
  emoji: string;
  label: string;
  selected: boolean;
  onPress: () => void;
}

function BlacklistTile({ emoji, label, selected, onPress }: BlacklistTileProps) {
  return (
    <TouchableOpacity
      style={[tileStyles.tile, selected && tileStyles.tileBlacklisted]}
      onPress={onPress}
      activeOpacity={0.75}
    >
      <Text style={tileStyles.emoji}>{emoji}</Text>
      <Text style={[tileStyles.label, selected && tileStyles.labelBlacklisted]}>{label}</Text>
      {selected && (
        <View style={[tileStyles.indicatorBadge, tileStyles.indicatorBadgeBlacklist]}>
          <Text style={tileStyles.indicatorText}>🚫</Text>
        </View>
      )}
    </TouchableOpacity>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

interface FoodPreferencesSelectorProps {
  likeDislikeMap: LikeDislikeMap;
  blacklistMap: BlacklistMap;
  onLikeDislikeChange: (item: FoodPreferenceItem, state: LikeDislikeState) => void;
  onBlacklistChange: (item: BlacklistItem, selected: boolean) => void;
}

export function FoodPreferencesSelector({
  likeDislikeMap,
  blacklistMap,
  onLikeDislikeChange,
  onBlacklistChange,
}: FoodPreferencesSelectorProps) {
  const cycleLikeDislike = (item: FoodPreferenceItem) => {
    const current = likeDislikeMap[item];
    const next: LikeDislikeState =
      current === 'none' ? 'like' : current === 'like' ? 'dislike' : 'none';
    onLikeDislikeChange(item, next);
  };

  const toggleBlacklist = (item: BlacklistItem) => {
    onBlacklistChange(item, !blacklistMap[item]);
  };

  return (
    <View style={styles.container}>
      {/* Likes / Dislikes Section */}
      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>❤️ Likes & Dislikes</Text>
          <Text style={styles.sectionHint}>Tap to cycle: like → dislike → none</Text>
        </View>
        <LikeDislikeIndicator />
        <View style={styles.grid}>
          {FOOD_PREFERENCE_ITEMS.map((item) => (
            <LikeDislikeTile
              key={item.id}
              emoji={item.emoji}
              label={item.label}
              state={likeDislikeMap[item.id]}
              onPress={() => cycleLikeDislike(item.id)}
            />
          ))}
        </View>
      </View>

      {/* Blacklist Section */}
      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>🚫 Food Blacklist</Text>
          <Text style={styles.sectionHint}>Tap to mark foods you cannot eat</Text>
        </View>
        <BlacklistIndicator />
        <View style={styles.grid}>
          {BLACKLIST_ITEMS.map((item) => (
            <BlacklistTile
              key={item.id}
              emoji={item.emoji}
              label={item.label}
              selected={blacklistMap[item.id]}
              onPress={() => toggleBlacklist(item.id)}
            />
          ))}
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: Spacing['2xl'],
  },
  section: {
    gap: Spacing.md,
  },
  sectionHeader: {
    gap: Spacing.xs,
  },
  sectionTitle: {
    ...Typography.titleMedium,
    color: Colors.on_surface,
  },
  sectionHint: {
    ...Typography.labelSmall,
    color: Colors.on_surface_variant,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.sm,
  },
});
