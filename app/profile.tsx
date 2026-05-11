/**
 * Profile Page Screen
 *
 * Shows the user's profile information. Allows deleting the profile.
 * If no profile exists, shows a button to create one.
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
  UserProfile,
  getUserProfile,
  deleteUserProfile,
} from '@/services/userProfile';
import { FOOD_PREFERENCE_ITEMS, BLACKLIST_ITEMS } from '@/components/profile/FoodPreferencesSelector';
import { Image } from 'expo-image';

const LEVEL_THRESHOLDS = [
  { level: 1, exp: 0 },
  { level: 2, exp: 100 },
  { level: 3, exp: 450 },
  { level: 4, exp: 1000 },
] as const;

const EARN_EXP_ITEMS = [
  {
    id: 'read-story',
    image: require('../assets/images/Read_Story_EXP.png'),
    title: 'Read Story',
    exp: 20,
    href: '/stories',
  },
  {
    id: 'meal-maker',
    image: require('../assets/images/Meal_Maker_EXP.png'),
    title: 'Meal Maker',
    exp: 10,
    href: '/heroWorld/meal-maker',
  },
  {
    id: 'daily-challenge',
    image: require('../assets/images/Daily_Challenge_EXP.png'),
    title: 'Daily Challenge',
    exp: 50,
    href: '/heroWorld/daily-challenge',
  },
] as const;

function getHeroProgress(totalPoints: number) {
  const safePoints = Math.max(0, totalPoints);
  const currentLevelIndex = LEVEL_THRESHOLDS.reduce((matchedIndex, threshold, index) => {
    return safePoints >= threshold.exp ? index : matchedIndex;
  }, 0);
  const currentLevel = LEVEL_THRESHOLDS[currentLevelIndex];
  const nextLevel = LEVEL_THRESHOLDS[currentLevelIndex + 1];
  const targetExp = nextLevel?.exp ?? currentLevel.exp;
  const progressRatio = targetExp > 0 ? Math.min(safePoints / targetExp, 1) : 1;
  const progressPercent = `${Math.round(progressRatio * 100)}%` as `${number}%`;

  return {
    level: currentLevel.level,
    currentExp: safePoints,
    targetExp,
    expToNextLevel: nextLevel ? nextLevel.exp - safePoints : 0,
    nextLevel: nextLevel?.level,
    progressPercent,
  };
}

// ─── Food Preferences Display ─────────────────────────────────────────────────

interface FoodPreferencesSummaryProps {
  profile: UserProfile;
}

function FoodPreferencesSummary({ profile }: FoodPreferencesSummaryProps) {
  const prefs = profile.foodPreferences;
  const hasAnyPreference =
    prefs && (prefs.likes.length > 0 || prefs.dislikes.length > 0 || prefs.blacklist.length > 0);

  const getEmoji = (id: string, list: typeof FOOD_PREFERENCE_ITEMS | typeof BLACKLIST_ITEMS) => {
    const found = (list as { id: string; emoji: string }[]).find((i) => i.id === id);
    return found ? found.emoji : '🍴';
  };

  return (
    <View style={prefStyles.section}>
      <View style={prefStyles.sectionHeader}>
        <Text style={prefStyles.sectionTitle}>🍽️ Food Preferences</Text>
        <TouchableOpacity
          style={prefStyles.editButton}
          onPress={() => router.push('/preferences-edit' as any)}
          activeOpacity={0.75}
        >
          <Text style={prefStyles.editButtonText}>Edit</Text>
        </TouchableOpacity>
      </View>

      {!hasAnyPreference ? (
        <View style={prefStyles.emptyCard}>
          <Text style={prefStyles.emptyText}>No preferences set yet.</Text>
          <TouchableOpacity
            style={prefStyles.setNowButton}
            onPress={() => router.push('/preferences-edit' as any)}
            activeOpacity={0.8}
          >
            <Text style={prefStyles.setNowButtonText}>Set Preferences</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <View style={prefStyles.card}>
          {/* Likes */}
          {prefs!.likes.length > 0 && (
            <View style={prefStyles.group}>
              <Text style={prefStyles.groupLabel}>👍 Likes</Text>
              <View style={prefStyles.chipRow}>
                {prefs!.likes.map((item) => (
                  <View key={item} style={[prefStyles.chip, prefStyles.chipLike]}>
                    <Text style={prefStyles.chipEmoji}>{getEmoji(item, FOOD_PREFERENCE_ITEMS)}</Text>
                    <Text style={[prefStyles.chipText, prefStyles.chipTextLike]}>
                      {item.charAt(0).toUpperCase() + item.slice(1)}
                    </Text>
                  </View>
                ))}
              </View>
            </View>
          )}

          {/* Dislikes */}
          {prefs!.dislikes.length > 0 && (
            <View style={prefStyles.group}>
              <Text style={prefStyles.groupLabel}>👎 Dislikes</Text>
              <View style={prefStyles.chipRow}>
                {prefs!.dislikes.map((item) => (
                  <View key={item} style={[prefStyles.chip, prefStyles.chipDislike]}>
                    <Text style={prefStyles.chipEmoji}>{getEmoji(item, FOOD_PREFERENCE_ITEMS)}</Text>
                    <Text style={[prefStyles.chipText, prefStyles.chipTextDislike]}>
                      {item.charAt(0).toUpperCase() + item.slice(1)}
                    </Text>
                  </View>
                ))}
              </View>
            </View>
          )}

          {/* Blacklist */}
          {prefs!.blacklist.length > 0 && (
            <View style={prefStyles.group}>
              <Text style={prefStyles.groupLabel}>🚫 Cannot Eat</Text>
              <View style={prefStyles.chipRow}>
                {prefs!.blacklist.map((item) => (
                  <View key={item} style={[prefStyles.chip, prefStyles.chipBlacklist]}>
                    <Text style={prefStyles.chipEmoji}>{getEmoji(item, BLACKLIST_ITEMS)}</Text>
                    <Text style={[prefStyles.chipText, prefStyles.chipTextBlacklist]}>
                      {item.charAt(0).toUpperCase() + item.slice(1)}
                    </Text>
                  </View>
                ))}
              </View>
            </View>
          )}
        </View>
      )}
    </View>
  );
}

const prefStyles = StyleSheet.create({
  section: {
    gap: Spacing.md,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  sectionTitle: {
    ...Typography.titleLarge,
    color: Colors.on_surface,
  },
  editButton: {
    backgroundColor: Colors.primary_container,
    borderRadius: Radius.badge,
    paddingVertical: Spacing.xs,
    paddingHorizontal: Spacing.md,
  },
  editButtonText: {
    ...Typography.labelMedium,
    color: Colors.on_primary_container,
    fontWeight: '700',
  },
  emptyCard: {
    backgroundColor: Colors.surface_container_lowest,
    borderRadius: Radius.card,
    padding: Spacing.base,
    alignItems: 'center',
    gap: Spacing.md,
    shadowColor: Colors.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 8,
    elevation: 2,
  },
  emptyText: {
    ...Typography.bodyMedium,
    color: Colors.on_surface_variant,
  },
  setNowButton: {
    backgroundColor: Colors.primary,
    borderRadius: Radius.button_secondary,
    paddingVertical: Spacing.sm,
    paddingHorizontal: Spacing.lg,
  },
  setNowButtonText: {
    ...Typography.labelMedium,
    color: Colors.on_primary,
    fontWeight: '700',
  },
  card: {
    backgroundColor: Colors.surface_container_lowest,
    borderRadius: Radius.card,
    padding: Spacing.base,
    gap: Spacing.base,
    shadowColor: Colors.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 8,
    elevation: 2,
  },
  group: {
    gap: Spacing.sm,
  },
  groupLabel: {
    ...Typography.labelMedium,
    color: Colors.on_surface_variant,
  },
  chipRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.sm,
  },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.xs,
    borderRadius: Radius.badge,
    paddingVertical: Spacing.xs,
    paddingHorizontal: Spacing.sm,
  },
  chipLike: {
    backgroundColor: Colors.primary_container,
  },
  chipDislike: {
    backgroundColor: Colors.secondary_container,
  },
  chipBlacklist: {
    backgroundColor: Colors.error_container,
  },
  chipEmoji: {
    fontSize: 14,
  },
  chipText: {
    ...Typography.labelSmall,
  },
  chipTextLike: {
    color: Colors.on_primary_container,
  },
  chipTextDislike: {
    color: Colors.on_secondary_container,
  },
  chipTextBlacklist: {
    color: Colors.on_error_container,
  },
});

// ─── Main Screen ──────────────────────────────────────────────────────────────

export default function ProfileScreen() {
  const insets = useSafeAreaInsets();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  const loadProfile = useCallback(async () => {
    setLoading(true);
    try {
      const p = await getUserProfile();
      setProfile(p);
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      loadProfile();
    }, [loadProfile])
  );

  const handleDeleteProfile = () => {
    Alert.alert(
      'Delete Profile',
      'Are you sure you want to delete your profile? This cannot be undone.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            await deleteUserProfile();
            setProfile(null);
            router.replace('/profile-create' as any);
          },
        },
      ]
    );
  };

  const handleCreateProfile = () => {
    router.push('/profile-create');
  };

  const handleBack = () => {
    router.back();
  };

  const getAvatarImage = () => {
    switch (profile?.avatarId) {
      case 'hero':
        if (profile.totalPoints > LEVEL_THRESHOLDS[3].exp) return (<Image source={require('../assets/images/avatar/hero-4.png')} style={styles.avatarImage}/>);
        if (profile.totalPoints > LEVEL_THRESHOLDS[2].exp) return (<Image source={require('../assets/images/avatar/hero-3.png')} style={styles.avatarImage}/>);
        if (profile.totalPoints > LEVEL_THRESHOLDS[1].exp) return (<Image source={require('../assets/images/avatar/hero-2.png')} style={styles.avatarImage}/>);
        return (<Image source={require('../assets/images/avatar/hero-1.png')} style={styles.avatarImage}/>);
      case 'princess':
        if (profile.totalPoints > LEVEL_THRESHOLDS[3].exp) return (<Image source={require('../assets/images/avatar/princess-4.png')} style={styles.avatarImage}/>);
        if (profile.totalPoints > LEVEL_THRESHOLDS[2].exp) return (<Image source={require('../assets/images/avatar/princess-3.png')} style={styles.avatarImage}/>);
        if (profile.totalPoints > LEVEL_THRESHOLDS[1].exp) return (<Image source={require('../assets/images/avatar/princess-2.png')} style={styles.avatarImage}/>);
        return (<Image source={require('../assets/images/avatar/princess-1.png')} style={styles.avatarImage}/>);
      default:
        break;
    }
  }

  if (loading) {
    return (
      <View style={[styles.container_outer, { paddingTop: insets.top, paddingBottom: insets.bottom }]}>
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={Colors.primary} />
        </View>
      </View>
    );
  }

  if (!profile) {
    return (
      <View style={[styles.container_outer, { paddingTop: insets.top, paddingBottom: insets.bottom }]}>
        <View style={styles.container}>
          {/* Back button */}
          <TouchableOpacity style={styles.backButton} onPress={handleBack}>
            <Text style={styles.backButtonText}>← Back</Text>
          </TouchableOpacity>

          <View style={styles.emptyState}>
            <Text style={styles.emptyEmoji}>👤</Text>
            <Text style={styles.emptyTitle}>No Profile Yet</Text>
            <Text style={styles.emptySubtitle}>
              Create a profile to track your progress and earn rewards!
            </Text>
            <TouchableOpacity style={styles.createButton} onPress={handleCreateProfile} activeOpacity={0.85}>
              <Text style={styles.createButtonText}>✨ Create Profile</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    );
  }

  const mealMakerHighScore = profile.highScores['meal-maker'] ?? 0;
  const heroProgress = getHeroProgress(profile.totalPoints);

  return (
    <View style={[styles.container_outer, { paddingTop: insets.top, paddingBottom: insets.bottom }]}>
      <ScrollView contentContainerStyle={styles.container}>
        {/* Back button */}
        <TouchableOpacity style={styles.backButton} onPress={handleBack}>
          <Text style={styles.backButtonText}>← Back</Text>
        </TouchableOpacity>

        {/* Avatar & Name */}
        <View style={styles.heroSection}>
          <View style={styles.avatarContainer}>
            {getAvatarImage()}
          </View>
          <Text style={styles.username}>{profile.username}</Text>
          <View style={styles.levelPill}>
            <Text style={styles.levelPillText}>Level {heroProgress.level}</Text>
          </View>
        </View>

        {/* Hero Growth */}
        <View style={styles.growthSection}>
          <Text style={styles.sectionTitle}>🌱 Hero Growth</Text>
          <View style={styles.growthCard}>
            <View style={styles.expLine}>
              <Text style={styles.currentExp}>{heroProgress.currentExp}</Text>
              <Text style={styles.expTotal}> / {heroProgress.targetExp} EXP</Text>
            </View>
            <View style={styles.progressTrack}>
              <View style={[styles.progressFill, { width: heroProgress.progressPercent }]} />
            </View>
            <Text style={styles.expHint}>
              {heroProgress.nextLevel
                ? `${heroProgress.expToNextLevel} EXP to Level ${heroProgress.nextLevel}`
                : 'Max level reached'}
            </Text>
          </View>
        </View>

        {/* Earn EXP */}
        <View style={styles.earnSection}>
          <Text style={styles.sectionTitle}>⚡ Earn EXP</Text>
          <View style={styles.earnGrid}>
            {EARN_EXP_ITEMS.map((item) => (
              <TouchableOpacity
                key={item.id}
                style={styles.earnCard}
                onPress={() => router.push(item.href as any)}
                activeOpacity={0.82}
              >
                <Image source={item.image} style={styles.earnImage} contentFit="contain" />
                <Text style={styles.earnTitle}>{item.title}</Text>
                <Text style={styles.earnExp}>+{item.exp} EXP</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* Stats */}
        <View style={styles.statsSection}>
          <Text style={styles.statsSectionTitle}>🏆 Stats</Text>

          <View style={styles.statsGrid}>
            <View style={styles.statCard}>
              <Text style={styles.statEmoji}>⭐</Text>
              <Text style={styles.statValue}>{profile.totalPoints}</Text>
              <Text style={styles.statLabel}>Total Points</Text>
            </View>

            <View style={styles.statCard}>
              <Text style={styles.statEmoji}>🍽️</Text>
              <Text style={styles.statValue}>{mealMakerHighScore}</Text>
              <Text style={styles.statLabel}>Meal Maker Best</Text>
            </View>
          </View>
        </View>

        {/* Profile Info */}
        <View style={styles.infoSection}>
          <View style={styles.infoSectionHeader}>
            <Text style={styles.infoSectionTitle}>👤 Profile Info</Text>
            <TouchableOpacity
              style={styles.editInfoButton}
              onPress={() => router.push('/profile-edit' as any)}
              activeOpacity={0.75}
            >
              <Text style={styles.editInfoButtonText}>Edit</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.infoCard}>
            <View style={styles.infoRow}>
              <Text style={styles.infoKey}>Username</Text>
              <Text style={styles.infoValue}>{profile.username}</Text>
            </View>
            <View style={styles.infoDivider} />
            <View style={styles.infoRow}>
              <Text style={styles.infoKey}>Age</Text>
              <Text style={styles.infoValue}>{profile.age}</Text>
            </View>
          </View>
        </View>

        {/* Food Preferences */}
        <FoodPreferencesSummary profile={profile} />

        {/* Delete Profile */}
        <TouchableOpacity
          style={styles.deleteButton}
          onPress={handleDeleteProfile}
          activeOpacity={0.85}
        >
          <Text style={styles.deleteButtonText}>🗑️ Delete Profile</Text>
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
  heroSection: {
    alignItems: 'center',
    gap: Spacing.sm,
  },
  avatarContainer: {
    width: 250,
    height: 250,
    borderRadius: Radius.md,
    backgroundColor: Colors.on_primary,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 3,
    borderColor: Colors.primary,
    padding: Spacing.sm,
  },
  avatarImage: {
    width: '100%',
    height: '100%',
    // borderRadius: Radius.full
  },
  username: {
    ...Typography.headlineLarge,
    color: Colors.on_surface,
    fontWeight: '900',
  },
  levelPill: {
    backgroundColor: Colors.primary,
    borderRadius: Radius.badge,
    paddingVertical: Spacing.xs,
    paddingHorizontal: Spacing.lg,
  },
  levelPillText: {
    ...Typography.labelLarge,
    color: Colors.on_primary,
    fontWeight: '900',
  },
  ageLabel: {
    ...Typography.bodyLarge,
    color: Colors.on_surface_variant,
  },
  sectionTitle: {
    ...Typography.titleLarge,
    color: Colors.on_surface,
    fontWeight: '900',
  },
  growthSection: {
    gap: Spacing.md,
  },
  growthCard: {
    backgroundColor: Colors.surface_container_lowest,
    borderRadius: Radius.card,
    padding: Spacing.lg,
    gap: Spacing.md,
    shadowColor: Colors.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 8,
    elevation: 2,
  },
  expLine: {
    flexDirection: 'row',
    alignItems: 'flex-end',
  },
  currentExp: {
    ...Typography.headlineMedium,
    color: Colors.primary,
    fontWeight: '900',
  },
  expTotal: {
    ...Typography.titleSmall,
    color: Colors.on_surface,
    fontWeight: '800',
    paddingBottom: 3,
  },
  progressTrack: {
    height: 12,
    borderRadius: Radius.badge,
    backgroundColor: Colors.primary_container,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    borderRadius: Radius.badge,
    backgroundColor: Colors.primary,
  },
  expHint: {
    ...Typography.bodyMedium,
    color: Colors.on_surface_variant,
    fontWeight: '600',
  },
  earnSection: {
    gap: Spacing.md,
  },
  earnGrid: {
    flexDirection: 'row',
    gap: Spacing.md,
  },
  earnCard: {
    flex: 1,
    minHeight: 132,
    backgroundColor: Colors.surface_container_lowest,
    borderRadius: Radius.card,
    paddingVertical: Spacing.base,
    paddingHorizontal: Spacing.sm,
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.xs,
    shadowColor: Colors.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 8,
    elevation: 2,
  },
  earnImage: {
    width: 72,
    height: 58,
  },
  earnTitle: {
    ...Typography.labelMedium,
    color: Colors.on_surface,
    fontWeight: '800',
    textAlign: 'center',
  },
  earnExp: {
    ...Typography.titleMedium,
    color: Colors.primary,
    fontWeight: '900',
    textAlign: 'center',
  },
  statsSection: {
    gap: Spacing.md,
  },
  statsSectionTitle: {
    ...Typography.titleLarge,
    color: Colors.on_surface,
  },
  statsGrid: {
    flexDirection: 'row',
    gap: Spacing.md,
  },
  statCard: {
    flex: 1,
    backgroundColor: Colors.surface_container_lowest,
    borderRadius: Radius.card,
    padding: Spacing.base,
    alignItems: 'center',
    gap: Spacing.xs,
    shadowColor: Colors.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 8,
    elevation: 2,
  },
  statEmoji: {
    fontSize: 32,
  },
  statValue: {
    ...Typography.headlineMedium,
    color: Colors.primary,
    fontWeight: '900',
  },
  statLabel: {
    ...Typography.labelSmall,
    color: Colors.on_surface_variant,
    textAlign: 'center',
  },
  infoSection: {
    gap: Spacing.md,
  },
  infoSectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  infoSectionTitle: {
    ...Typography.titleLarge,
    color: Colors.on_surface,
  },
  editInfoButton: {
    backgroundColor: Colors.primary_container,
    borderRadius: Radius.badge,
    paddingVertical: Spacing.xs,
    paddingHorizontal: Spacing.md,
  },
  editInfoButtonText: {
    ...Typography.labelMedium,
    color: Colors.on_primary_container,
    fontWeight: '700',
  },
  infoCard: {
    backgroundColor: Colors.surface_container_lowest,
    borderRadius: Radius.card,
    overflow: 'hidden',
    shadowColor: Colors.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 8,
    elevation: 2,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: Spacing.base,
    paddingVertical: Spacing.md,
  },
  infoDivider: {
    height: 1,
    backgroundColor: Colors.outline_variant,
    marginHorizontal: Spacing.base,
  },
  infoKey: {
    ...Typography.bodyMedium,
    color: Colors.on_surface_variant,
  },
  infoValue: {
    ...Typography.bodyMedium,
    color: Colors.on_surface,
    fontWeight: '700',
  },
  deleteButton: {
    backgroundColor: Colors.error_container,
    borderRadius: Radius.button_primary,
    paddingVertical: Spacing.base,
    alignItems: 'center',
    marginTop: Spacing.md,
  },
  deleteButtonText: {
    ...Typography.labelLarge,
    color: Colors.on_error_container,
    fontSize: 16,
  },
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.md,
    paddingTop: Spacing['4xl'],
  },
  emptyEmoji: {
    fontSize: 80,
  },
  emptyTitle: {
    ...Typography.headlineMedium,
    color: Colors.on_surface,
    textAlign: 'center',
  },
  emptySubtitle: {
    ...Typography.bodyMedium,
    color: Colors.on_surface_variant,
    textAlign: 'center',
    maxWidth: 280,
  },
  createButton: {
    backgroundColor: Colors.primary,
    borderRadius: Radius.button_primary,
    paddingVertical: Spacing.base,
    paddingHorizontal: Spacing['2xl'],
    alignItems: 'center',
    marginTop: Spacing.md,
  },
  createButtonText: {
    ...Typography.labelLarge,
    color: Colors.on_primary,
    fontSize: 18,
  },
});
