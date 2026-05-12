import AppHeader from '@/components/app_header';
import { Colors } from '@/constants/colors';
import { Typography } from '@/constants/fonts';
import { Radius } from '@/constants/radius';
import { Spacing } from '@/constants/spacing';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { 
  Search, 
  Map as MapIcon, 
  Coffee, 
  Wine, 
  Store, 
  ArrowRight, 
  Star, 
  Heart, 
} from 'lucide-react-native';
import React from 'react';
import {
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

export default function FoodQuestMapNearbyScreen() {
  const router = useRouter();
  const { foodName } = useLocalSearchParams<{ foodName?: string }>();
  const insets = useSafeAreaInsets();
  
  const displayName = foodName || 'Strawberry Shake';

  const handleBack = () => {
    router.back();
  };

  const handleLocationPress = (location: string) => {
    console.log('Navigating to:', location);
  };

  const handleAskAdult = () => {
    console.log('Asking adult for permission');
  };

  return (
    <View style={[styles.safeArea, { paddingTop: insets.top, paddingBottom: insets.bottom }]}>
      <ScrollView contentContainerStyle={styles.container} showsVerticalScrollIndicator={false}>
        {/* App Header */}
        <AppHeader />

        {/* Header Title Section */}
        <View style={styles.headerSection}>
          <View style={styles.starsContainer}>
            <Star color={Colors.tertiary} size={20} fill={Colors.tertiary} />
            <Star color={Colors.tertiary} size={20} fill={Colors.tertiary} />
            <Star color={Colors.tertiary} size={20} fill={Colors.tertiary} />
          </View>
          <Text style={styles.headerTitle}>Nearby Places for {displayName}</Text>
        </View>

        {/* Recommended Food Card */}
        <View style={styles.recommendedCard}>
          <View style={styles.foodImageWrapper}>
            <View style={styles.foodPlaceholder}>
              <Text style={styles.foodPlaceholderEmoji}>🥤</Text>
            </View>
          </View>
          
          <View style={styles.foodInfo}>
            <View style={styles.foodInfoHeader}>
              <Text style={styles.foodName}>{displayName}</Text>
              <TouchableOpacity>
                <Heart color={Colors.tertiary} size={30} fill={Colors.tertiary} />
              </TouchableOpacity>
            </View>
            <Text style={styles.foodDescription}>
              A super-yummy boost for your hero energy! Packed with real berries and creamy goodness.
            </Text>
          </View>

          {/* Mascot Peeking */}
          <View style={styles.mascotPeeking}>
            <Text style={styles.mascotPeekingEmoji}>🦸</Text>
          </View>
        </View>

        {/* Map Search Section */}
        <View style={styles.mapSearchSection}>
          <View style={styles.sectionTitleRow}>
            <Search color={Colors.primary} size={24} />
            <Text style={styles.sectionTitle}>Map Search Results</Text>
          </View>

          {/* Search Bar */}
          <View style={styles.searchBar}>
            <Search color={Colors.outline} size={24} />
            <Text style={styles.searchText}>Strawberry Shake where to buy near me</Text>
          </View>

          {/* Map Preview */}
          <View style={styles.mapPreview}>
            <View style={styles.mapPlaceholder}>
              <Text style={styles.mapPlaceholderEmoji}>🗺️</Text>
            </View>
          </View>

          {/* Result List */}
          <View style={styles.resultList}>
            {/* Item 1 */}
            <TouchableOpacity 
              style={styles.resultItem}
              onPress={() => handleLocationPress('Berry Smoothie Café')}
              activeOpacity={0.7}
            >
              <View style={styles.resultLeft}>
                <View style={[styles.resultIcon, { backgroundColor: Colors.secondary_container }]}>
                  <Coffee color={Colors.on_secondary_container} size={30} />
                </View>
                <View>
                  <Text style={styles.resultName}>Berry Smoothie Café</Text>
                  <Text style={styles.resultDistance}>0.5 km • Smoothies & Shakes</Text>
                </View>
              </View>
              <View style={[styles.resultButton, { backgroundColor: Colors.secondary }]}>
                <ArrowRight color={Colors.on_secondary} size={24} />
              </View>
            </TouchableOpacity>

            {/* Item 2 */}
            <TouchableOpacity 
              style={styles.resultItem}
              onPress={() => handleLocationPress('Fresh Drink House')}
              activeOpacity={0.7}
            >
              <View style={styles.resultLeft}>
                <View style={[styles.resultIcon, { backgroundColor: Colors.primary_container }]}>
                  <Wine color={Colors.on_primary_container} size={30} />
                </View>
                <View>
                  <Text style={styles.resultName}>Fresh Drink House</Text>
                  <Text style={styles.resultDistance}>1.2 km • Healthy Drinks</Text>
                </View>
              </View>
              <View style={[styles.resultButton, { backgroundColor: Colors.secondary }]}>
                <ArrowRight color={Colors.on_secondary} size={24} />
              </View>
            </TouchableOpacity>

            {/* Item 3 */}
            <TouchableOpacity 
              style={styles.resultItem}
              onPress={() => handleLocationPress('Jaya Grocer')}
              activeOpacity={0.7}
            >
              <View style={styles.resultLeft}>
                <View style={[styles.resultIcon, { backgroundColor: Colors.tertiary_container }]}>
                  <Store color={Colors.on_tertiary_container} size={30} />
                </View>
                <View>
                  <Text style={styles.resultName}>Jaya Grocer</Text>
                  <Text style={styles.resultDistance}>2.0 km • Supermarket</Text>
                </View>
              </View>
              <View style={[styles.resultButton, { backgroundColor: Colors.secondary }]}>
                <ArrowRight color={Colors.on_secondary} size={24} />
              </View>
            </TouchableOpacity>
          </View>
        </View>

        {/* Safety Section */}
        <View style={styles.safetySection}>
          <View style={styles.safetyContent}>
            <Text style={styles.safetyTitle}>Safety First!</Text>
            <Text style={styles.safetyDescription}>
              Always go with a parent or a grown-up hero when you visit new places. Stay safe and have fun on your quest!
            </Text>
            <TouchableOpacity 
              style={styles.askAdultButton}
              onPress={handleAskAdult}
              activeOpacity={0.9}
            >
              <Text style={styles.askAdultButtonText}>Ask Mom or Dad</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Bottom Spacer */}
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
    marginTop: Spacing.lg,
    marginBottom: Spacing.lg,
    gap: Spacing.xs,
    alignItems: 'center',
  },
  starsContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
  },
  headerTitle: {
    ...Typography.headlineLarge,
    color: Colors.on_background,
    fontWeight: '800',
    lineHeight: 36,
    textAlign: 'center',
  },
  recommendedCard: {
    backgroundColor: Colors.surface_container_highest,
    borderRadius: Radius.card,
    padding: Spacing.xl,
    shadowColor: Colors.shadow,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.08,
    shadowRadius: 20,
    elevation: 4,
    marginBottom: Spacing.xxl,
    overflow: 'visible',
    position: 'relative',
  },
  foodImageWrapper: {
    width: 160,
    height: 160,
    backgroundColor: Colors.surface_container_lowest,
    borderRadius: Radius.medium,
    overflow: 'hidden',
    padding: Spacing.md,
    marginBottom: Spacing.lg,
    alignSelf: 'center',
  },
  foodImage: {
    width: '100%',
    height: '100%',
  },
  foodInfo: {
    gap: Spacing.sm,
  },
  foodInfoHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: Spacing.xs,
  },
  foodName: {
    ...Typography.headlineMedium,
    color: Colors.primary,
    fontWeight: '700',
    flex: 1,
  },
  foodDescription: {
    ...Typography.bodyLarge,
    color: Colors.on_surface_variant,
    lineHeight: 26,
  },
  foodPlaceholder: {
    width: '100%',
    height: '100%',
    alignItems: 'center',
    justifyContent: 'center',
  },
  foodPlaceholderEmoji: {
    fontSize: 80,
  },
  mascotPeeking: {
    position: 'absolute',
    top: -40,
    right: -16,
    width: 80,
    height: 80,
    alignItems: 'center',
    justifyContent: 'center',
    transform: [{ rotate: '12deg' }],
  },
  mascotPeekingEmoji: {
    fontSize: 60,
  },
  mapSearchSection: {
    marginBottom: Spacing.xl,
  },
  sectionTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
    marginBottom: Spacing.md,
  },
  sectionTitle: {
    ...Typography.titleMedium,
    color: Colors.on_surface,
    fontWeight: '700',
  },
  searchBar: {
    backgroundColor: Colors.surface_container_high,
    borderRadius: Radius.full,
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
    marginBottom: Spacing.lg,
  },
  searchText: {
    ...Typography.bodyLarge,
    color: Colors.on_surface,
    fontWeight: '600',
    flex: 1,
  },
  mapPreview: {
    borderRadius: Radius.card,
    overflow: 'hidden',
    height: 256,
    marginBottom: Spacing.xl,
    shadowColor: Colors.shadow,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.08,
    shadowRadius: 20,
    elevation: 4,
    backgroundColor: Colors.surface_container_lowest,
    alignItems: 'center',
    justifyContent: 'center',
  },
  mapPlaceholder: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  mapPlaceholderEmoji: {
    fontSize: 120,
  },
  resultList: {
    gap: Spacing.lg,
  },
  resultItem: {
    backgroundColor: Colors.surface_container_low,
    borderRadius: Radius.medium,
    padding: Spacing.lg,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  resultLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.md,
    flex: 1,
  },
  resultIcon: {
    width: 56,
    height: 56,
    borderRadius: Radius.medium,
    alignItems: 'center',
    justifyContent: 'center',
  },
  resultName: {
    ...Typography.titleMedium,
    color: Colors.on_surface,
    fontWeight: '700',
  },
  resultDistance: {
    ...Typography.bodySmall,
    color: Colors.on_surface_variant,
    marginTop: 2,
  },
  resultButton: {
    width: 48,
    height: 48,
    borderRadius: Radius.full,
    alignItems: 'center',
    justifyContent: 'center',
  },
  safetySection: {
    backgroundColor: Colors.surface_container_low,
    borderRadius: Radius.card,
    padding: Spacing.xl,
    borderWidth: 4,
    borderColor: Colors.surface_container_highest,
    borderStyle: 'dashed',
    marginBottom: Spacing.lg,
    overflow: 'hidden',
  },
  safetyContent: {
    gap: Spacing.md,
  },
  safetyTitle: {
    ...Typography.displaySmall,
    color: Colors.primary,
    fontWeight: '900',
  },
  safetyDescription: {
    ...Typography.bodyLarge,
    color: Colors.on_surface,
    lineHeight: 28,
    fontWeight: '600',
  },
  askAdultButton: {
    backgroundColor: Colors.primary,
    paddingVertical: Spacing.lg,
    paddingHorizontal: Spacing.xxl,
    borderRadius: Radius.full,
    alignSelf: 'flex-start',
    shadowColor: Colors.shadow,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.08,
    shadowRadius: 20,
    elevation: 4,
  },
  askAdultButtonText: {
    ...Typography.titleMedium,
    color: Colors.on_primary,
    fontWeight: '700',
    fontSize: 18,
  },
  bottomSpacer: {
  },
});