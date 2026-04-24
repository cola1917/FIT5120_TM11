/**
 * FoodPreferencesSelector
 *
 * A two-section UI component for selecting food preferences and blacklist items.
 * - Likes/Dislikes section: tiles cycle through 'like' → 'dislike' → 'no preference'
 * - Blacklist section: tiles toggle between selected and not selected
 */

import React from 'react';
import {
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
  { id: 'chicken', emoji: '🍗', label: 'Chicken' },
  { id: 'beef', emoji: '🥩', label: 'Beef' },
  { id: 'pork', emoji: '🥓', label: 'Pork' },
  { id: 'fish', emoji: '🐟', label: 'Fish' },
  { id: 'dairy', emoji: '🧀', label: 'Dairy' },
];

export const BLACKLIST_ITEMS: { id: BlacklistItem; emoji: string; label: string }[] = [
  { id: 'egg', emoji: '🥚', label: 'Egg' },
  { id: 'bread', emoji: '🍞', label: 'Bread' },
  { id: 'milk', emoji: '🥛', label: 'Milk' },
  { id: 'peanut', emoji: '🥜', label: 'Peanut' },
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

// Like/Dislike Tile

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
        <View style={tileStyles.indicatorBadge}>
          <Text style={tileStyles.indicatorText}>{indicator}</Text>
        </View>
      )}
    </TouchableOpacity>
  );
}

// Blacklist Tile

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

const tileStyles = StyleSheet.create({
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
  emoji: {
    fontSize: 32,
    marginBottom: Spacing.xs,
  },
  label: {
    ...Typography.labelSmall,
    color: Colors.on_surface_variant,
    textAlign: 'center',
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
  indicatorBadgeBlacklist: {
    backgroundColor: Colors.error,
  },
  indicatorText: {
    fontSize: 10,
  },
});

// Main Component

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
