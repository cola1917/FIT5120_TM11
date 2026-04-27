/**
 * Preferences Edit Screen
 *
 * Allows the user to view and update their food preferences (likes/dislikes + blacklist).
 * Loads the current profile, pre-populates the selector, and saves on confirm.
 */

import React, { useCallback, useState } from 'react';
import {
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
  ActivityIndicator,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { router, useFocusEffect } from 'expo-router';
import { Colors } from '@/constants/colors';
import { Typography } from '@/constants/fonts';
import { Spacing } from '@/constants/spacing';
import { Radius } from '@/constants/radius';
import {
  BlacklistItem,
  FoodPreferenceItem,
  FoodPreferences,
  getUserProfile,
  saveUserProfile,
} from '@/services/userProfile';
import {
  FoodPreferencesSelector,
  LikeDislikeMap,
  LikeDislikeState,
  BlacklistMap,
  createDefaultLikeDislikeMap,
  createDefaultBlacklistMap,
  FOOD_PREFERENCE_ITEMS,
  BLACKLIST_ITEMS,
} from '@/components/profile/FoodPreferencesSelector';

// ─── Helpers ──────────────────────────────────────────────────────────────────

function buildMapsFromPreferences(prefs?: FoodPreferences): {
  likeDislikeMap: LikeDislikeMap;
  blacklistMap: BlacklistMap;
} {
  const likeDislikeMap = createDefaultLikeDislikeMap();
  const blacklistMap = createDefaultBlacklistMap();

  if (!prefs) return { likeDislikeMap, blacklistMap };

  for (const item of prefs.likes) {
    likeDislikeMap[item] = 'like';
  }
  for (const item of prefs.dislikes) {
    likeDislikeMap[item] = 'dislike';
  }
  for (const item of prefs.blacklist) {
    blacklistMap[item] = true;
  }

  return { likeDislikeMap, blacklistMap };
}

function buildPreferencesFromMaps(
  likeDislikeMap: LikeDislikeMap,
  blacklistMap: BlacklistMap
): FoodPreferences {
  const likes: FoodPreferenceItem[] = [];
  const dislikes: FoodPreferenceItem[] = [];

  for (const item of FOOD_PREFERENCE_ITEMS) {
    const state = likeDislikeMap[item.id];
    if (state === 'like') likes.push(item.id);
    else if (state === 'dislike') dislikes.push(item.id);
  }

  const blacklist: BlacklistItem[] = BLACKLIST_ITEMS.filter(
    (item) => blacklistMap[item.id]
  ).map((item) => item.id);

  return { likes, dislikes, blacklist };
}

// ─── Screen ───────────────────────────────────────────────────────────────────

export default function PreferencesEditScreen() {
  const insets = useSafeAreaInsets();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [likeDislikeMap, setLikeDislikeMap] = useState<LikeDislikeMap>(createDefaultLikeDislikeMap);
  const [blacklistMap, setBlacklistMap] = useState<BlacklistMap>(createDefaultBlacklistMap);

  const loadPreferences = useCallback(async () => {
    setLoading(true);
    try {
      const profile = await getUserProfile();
      if (profile) {
        const { likeDislikeMap: ldMap, blacklistMap: blMap } = buildMapsFromPreferences(
          profile.foodPreferences
        );
        setLikeDislikeMap(ldMap);
        setBlacklistMap(blMap);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      loadPreferences();
    }, [loadPreferences])
  );

  const handleLikeDislikeChange = (item: FoodPreferenceItem, state: LikeDislikeState) => {
    setLikeDislikeMap((prev) => ({ ...prev, [item]: state }));
  };

  const handleBlacklistChange = (item: BlacklistItem, selected: boolean) => {
    setBlacklistMap((prev) => ({ ...prev, [item]: selected }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const profile = await getUserProfile();
      if (!profile) {
        Alert.alert('Error', 'No profile found. Please create a profile first.');
        return;
      }
      profile.foodPreferences = buildPreferencesFromMaps(likeDislikeMap, blacklistMap);
      await saveUserProfile(profile);
      router.back();
    } catch {
      Alert.alert('Error', 'Could not save preferences. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleBack = () => {
    router.back();
  };

  if (loading) {
    return (
      <View style={[styles.container_outer, { paddingTop: insets.top, paddingBottom: insets.bottom }]}>
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={Colors.primary} />
        </View>
      </View>
    );
  }

  return (
    <View style={[styles.container_outer, { paddingTop: insets.top, paddingBottom: insets.bottom }]}>
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        {/* Header row */}
        <View style={styles.headerRow}>
          <TouchableOpacity style={styles.backButton} onPress={handleBack}>
            <Text style={styles.backButtonText}>← Back</Text>
          </TouchableOpacity>
        </View>

        {/* Title */}
        <View style={styles.titleSection}>
          <Text style={styles.titleEmoji}>🍽️</Text>
          <Text style={styles.title}>Food Preferences</Text>
          <Text style={styles.subtitle}>
            Update what you like, dislike, and foods you cannot eat.
          </Text>
        </View>

        {/* Selector */}
        <View style={styles.preferencesContainer}>
          <FoodPreferencesSelector
            likeDislikeMap={likeDislikeMap}
            blacklistMap={blacklistMap}
            onLikeDislikeChange={handleLikeDislikeChange}
            onBlacklistChange={handleBlacklistChange}
          />
        </View>

        {/* Save Button */}
        <TouchableOpacity
          style={[styles.saveButton, saving && styles.saveButtonDisabled]}
          onPress={handleSave}
          activeOpacity={0.85}
          disabled={saving}
        >
          <Text style={styles.saveButtonText}>
            {saving ? 'Saving...' : '💾 Save Preferences'}
          </Text>
        </TouchableOpacity>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container_outer: {
    flex: 1,
    backgroundColor: Colors.surface,
  },
  container: {
    paddingHorizontal: Spacing.lg,
    paddingTop: Spacing.base,
    paddingBottom: Spacing['4xl'],
    gap: Spacing['2xl'],
  },
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  backButton: {
    alignSelf: 'flex-start',
    paddingVertical: Spacing.xs,
    paddingHorizontal: Spacing.sm,
  },
  backButtonText: {
    ...Typography.bodyLarge,
    color: Colors.primary,
    fontWeight: '700',
  },
  titleSection: {
    alignItems: 'center',
    gap: Spacing.sm,
  },
  titleEmoji: {
    fontSize: 56,
  },
  title: {
    ...Typography.headlineMedium,
    color: Colors.on_surface,
    fontWeight: '900',
    textAlign: 'center',
  },
  subtitle: {
    ...Typography.bodyMedium,
    color: Colors.on_surface_variant,
    textAlign: 'center',
    maxWidth: 280,
  },
  preferencesContainer: {
    backgroundColor: Colors.surface_container_low,
    borderRadius: Radius.card,
    padding: Spacing.base,
  },
  saveButton: {
    backgroundColor: Colors.primary,
    borderRadius: Radius.button_primary,
    paddingVertical: Spacing.base,
    alignItems: 'center',
  },
  saveButtonDisabled: {
    opacity: 0.6,
  },
  saveButtonText: {
    ...Typography.labelLarge,
    color: Colors.on_primary,
    fontSize: 18,
  },
});
