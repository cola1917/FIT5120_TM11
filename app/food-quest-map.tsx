import AppHeader from '@/components/app_header';
import { Colors } from '@/constants/colors';
import { Typography } from '@/constants/fonts';
import { Radius } from '@/constants/radius';
import { Spacing } from '@/constants/spacing';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { ArrowLeft, Sparkles, Heart, MapPin, Compass } from 'lucide-react-native';
import React from 'react';
import {
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

export default function FoodQuestMapScreen() {
  const router = useRouter();
  const { foodName } = useLocalSearchParams<{ foodName?: string }>();
  const insets = useSafeAreaInsets();
  
  const displayName = foodName || 'This Food';

  const handleFindFood = () => {
    // Navigate to nearby places screen with the food name
    if (foodName) {
      router.push(`/food-quest-map-nearby?foodName=${encodeURIComponent(foodName)}` as any);
    } else {
      router.push('/food-quest-map-nearby' as any);
    }
  };

  const handleBack = () => {
    router.back();
  };

  return (
    <View style={[styles.safeArea, { paddingTop: insets.top, paddingBottom: insets.bottom }]}>
      <ScrollView contentContainerStyle={styles.container} showsVerticalScrollIndicator={false}>
        {/* App Header */}
        <AppHeader />

        {/* Header Section */}
        <View style={styles.headerSection}>
          <Sparkles color={Colors.primary_fixed} size={32} />
          <Text style={styles.headerTitle}>Where can I find {displayName}?</Text>
          <Sparkles color={Colors.primary_fixed} size={32} />
        </View>
        <Text style={styles.headerSubtitle}>Let's search nearby places with an adult.</Text>

        {/* Recommended Food Card */}
        <View style={styles.recommendedCard}>
          <View style={styles.recommendedBadge}>
            <Text style={styles.recommendedBadgeText}>RECOMMENDED FOOD</Text>
          </View>
          
          <View style={styles.foodImageContainer}>
            <View style={styles.foodPlaceholder}>
              <Text style={styles.foodPlaceholderEmoji}>🍽️</Text>
            </View>
            <TouchableOpacity style={styles.heartButton}>
              <Heart color={Colors.tertiary} size={24} fill={Colors.tertiary} />
            </TouchableOpacity>
          </View>

          <View style={styles.foodInfo}>
            <Text style={styles.foodName}>{displayName}</Text>
            <Text style={styles.foodDescription}>
              A yummy and healthy choice that gives you energy!
            </Text>
          </View>
        </View>

        {/* Find This Food Section */}
        <View style={styles.findFoodCard}>
          <View style={styles.mapIconContainer}>
            <Compass color={Colors.on_primary} size={36} strokeWidth={2.5} />
          </View>
          <Text style={styles.findFoodTitle}>Find This Food</Text>
          <Text style={styles.findFoodDescription}>
            Search nearby places that may offer this food or similar choices.
          </Text>
        </View>

        {/* Main Action Button */}
        <TouchableOpacity 
          style={styles.findFoodButton}
          onPress={handleFindFood}
          activeOpacity={0.9}
        >
          <MapPin color={Colors.on_primary} size={30} />
          <Text style={styles.findFoodButtonText}>FIND THIS FOOD</Text>
        </TouchableOpacity>

        {/* Safety Tip */}
        <View style={styles.safetyCard}>
          <View style={styles.safetyMascotContainer}>
            <Text style={styles.safetyMascotEmoji}>🦸</Text>
          </View>
          <View style={styles.safetyTextContainer}>
            <Text style={styles.safetyTitle}>Safety First!</Text>
            <Text style={styles.safetyDescription}>Ask an adult before visiting any place.</Text>
          </View>
        </View>

        {/* Back Button */}
        <TouchableOpacity 
          style={styles.backButton}
          onPress={handleBack}
          activeOpacity={0.7}
        >
          <ArrowLeft color={Colors.on_surface_variant} size={24} />
          <Text style={styles.backButtonText}>Back to Goal Foods</Text>
        </TouchableOpacity>

        {/* Bottom Spacer for Tab Bar */}
        <View style={[styles.bottomSpacer, { height: insets.bottom + Spacing.xxl }]} />
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: Colors.surface,
  },
  container: {
    paddingHorizontal: Spacing.lg,
    paddingTop: Spacing.md,
    paddingBottom: Spacing.xl,
    flexGrow: 1,
  },
  headerSection: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.sm,
    marginTop: Spacing.lg,
    marginBottom: Spacing.xs,
  },
  headerTitle: {
    ...Typography.headlineLarge,
    color: Colors.on_surface,
    fontWeight: '800',
    textAlign: 'center',
    flex: 1,
  },
  headerSubtitle: {
    ...Typography.bodyLarge,
    color: Colors.on_surface_variant,
    textAlign: 'center',
    fontWeight: '600',
    marginBottom: Spacing.lg,
  },
  recommendedCard: {
    backgroundColor: Colors.surface_container_lowest,
    borderRadius: Radius.card,
    padding: Spacing.xl,
    shadowColor: Colors.shadow,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 12,
    elevation: 4,
    marginBottom: Spacing.lg,
    overflow: 'hidden',
  },
  recommendedBadge: {
    backgroundColor: Colors.tertiary_container,
    alignSelf: 'flex-start',
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs,
    borderRadius: Radius.full,
    marginBottom: Spacing.lg,
  },
  recommendedBadgeText: {
    ...Typography.labelSmall,
    color: Colors.on_tertiary_container,
    fontWeight: '700',
    letterSpacing: 1,
  },
  foodImageContainer: {
    width: '100%',
    aspectRatio: 1,
    backgroundColor: Colors.surface_container,
    borderRadius: Radius.medium,
    overflow: 'hidden',
    alignItems: 'center',
    justifyContent: 'center',
    transform: [{ rotate: '2deg' }],
    marginBottom: Spacing.lg,
  },
  foodImage: {
    width: '100%',
    height: '100%',
    padding: Spacing.md,
  },
  heartButton: {
    position: 'absolute',
    top: Spacing.md,
    right: Spacing.md,
    backgroundColor: Colors.surface_container_lowest,
    padding: Spacing.sm,
    borderRadius: Radius.full,
    shadowColor: Colors.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 3,
  },
  foodInfo: {
    alignItems: 'center',
    gap: Spacing.xs,
  },
  foodName: {
    ...Typography.headlineLarge,
    color: Colors.primary,
    fontWeight: '900',
    textAlign: 'center',
  },
  foodDescription: {
    ...Typography.bodyLarge,
    color: Colors.on_surface,
    textAlign: 'center',
    lineHeight: 26,
    paddingHorizontal: Spacing.md,
  },
  findFoodCard: {
    backgroundColor: Colors.surface_container_high,
    borderRadius: Radius.card,
    padding: Spacing.xl,
    alignItems: 'center',
    marginBottom: Spacing.lg,
  },
  mapIconContainer: {
    width: 80,
    height: 80,
    backgroundColor: Colors.primary_container,
    borderRadius: Radius.full,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: Spacing.md,
    shadowColor: Colors.primary_container,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  findFoodTitle: {
    ...Typography.titleLarge,
    color: Colors.on_surface,
    fontWeight: '700',
    marginBottom: Spacing.xs,
  },
  findFoodDescription: {
    ...Typography.bodyLarge,
    color: Colors.on_surface_variant,
    textAlign: 'center',
    lineHeight: 24,
    fontWeight: '600',
  },
  findFoodButton: {
    backgroundColor: Colors.primary,
    height: 80,
    borderRadius: Radius.medium,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.md,
    shadowColor: Colors.primary,
    shadowOffset: { width: 0, height: 12 },
    shadowOpacity: 0.3,
    shadowRadius: 24,
    elevation: 8,
    marginBottom: Spacing.lg,
  },
  findFoodButtonText: {
    ...Typography.titleLarge,
    color: Colors.on_primary,
    fontWeight: '900',
    fontSize: 20,
  },
  safetyCard: {
    backgroundColor: `${Colors.secondary_container}40`,
    borderRadius: Radius.card,
    padding: Spacing.lg,
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.lg,
    marginBottom: Spacing.lg,
    overflow: 'hidden',
  },
  safetyMascotContainer: {
    flexShrink: 0,
    width: 96,
    height: 96,
    borderRadius: Radius.full,
    backgroundColor: 'rgba(255, 255, 255, 0.6)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  safetyMascot: {
    width: 64,
    height: 64,
  },
  safetyTextContainer: {
    flex: 1,
    gap: Spacing.xs,
  },
  safetyTitle: {
    ...Typography.titleMedium,
    color: Colors.secondary,
    fontWeight: '700',
  },
  safetyDescription: {
    ...Typography.bodyMedium,
    color: Colors.on_secondary_container,
    fontWeight: '600',
  },
  backButton: {
    borderWidth: 2,
    borderColor: Colors.outline_variant,
    borderRadius: Radius.medium,
    paddingVertical: Spacing.lg,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.sm,
    marginBottom: Spacing.lg,
  },
  backButtonText: {
    ...Typography.labelLarge,
    color: Colors.on_surface_variant,
    fontWeight: '700',
    fontSize: 16,
  },
  bottomSpacer: {
  },
});