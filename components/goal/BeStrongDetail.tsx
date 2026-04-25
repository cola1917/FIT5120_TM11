import React from 'react';
import {
  ActivityIndicator,
  StyleSheet,
  View,
  Text,
  Image,
  ScrollView,
  Dimensions,
  TouchableOpacity,
} from 'react-native';
import { ArrowRight, Star, ArrowLeft } from 'lucide-react-native';
import type { Goal } from './types';
import type { RecommendationResponse } from '../../services/recommendations';

const { width } = Dimensions.get('window');

interface Props {
  goal: Goal;
  onBack?: () => void;
  recommendations?: RecommendationResponse | null;
  recLoading?: boolean;
}

export default function BeStrongDetail({ goal, onBack, recommendations, recLoading }: Props) {
  const displaySuperFoods = recommendations?.super_power_foods?.map(f => ({
    name: f.name,
    description: `Grade ${f.grade}`,
    image: f.image_url,
  })) ?? goal.superFoods;

  const sf0 = displaySuperFoods[0] ?? goal.superFoods[0];
  const sf1 = displaySuperFoods[1] ?? goal.superFoods[1];
  const sf2 = displaySuperFoods[2] ?? goal.superFoods[2];

  const tinyHeroFoods = recommendations?.tiny_hero_foods ?? [];
  const tryLessFoods = recommendations?.try_less_foods ?? [];
  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>
      {/* Custom Back Button */}
      <TouchableOpacity style={styles.backButton} onPress={onBack}>
        <ArrowLeft color="#3F51B5" size={28} />
        <Text style={styles.backButtonText}>Back to Goals</Text>
      </TouchableOpacity>

      {/* Hero Section */}
      <View style={styles.heroSection}>
        <Text style={styles.heroTitle}>Foods for 💪 {goal.title}</Text>
        <Text style={styles.heroSubtitle}>{goal.description}</Text>
      </View>

      {/* Good Choice Section */}
      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <View style={styles.sectionIndicator} />
          <Text style={styles.sectionTitle}>Good Choice</Text>
        </View>

        {recLoading ? (
          <ActivityIndicator color="#3F51B5" size="large" style={{ marginVertical: 24 }} />
        ) : (
          <View style={styles.grid}>
            {/* Main Card */}
            <View style={styles.mainCard}>
              <View style={styles.cardHeader}>
                <View style={styles.badge}>
                  <Text style={styles.badgeText}>GOOD CHOICE</Text>
                </View>
                <Text style={styles.foodNameLarge}>{sf0.name}</Text>
              </View>
              <View style={styles.mainImageContainer}>
                <Image source={{ uri: sf0.image }} style={styles.mainImage} resizeMode="cover" />
              </View>
              <Text style={styles.descriptionText}>{sf0.description}</Text>
            </View>

            {/* Row of smaller cards */}
            <View style={styles.row}>
              <View style={styles.smallCard}>
                <View style={styles.smallImageContainer}>
                  <Image source={{ uri: sf1.image }} style={styles.smallImage} resizeMode="contain" />
                </View>
                <Text style={styles.foodNameSmall}>{sf1.name}</Text>
              </View>

              <View style={styles.smallCard}>
                <View style={styles.smallImageContainer}>
                  <Image source={{ uri: sf2.image }} style={styles.smallImage} resizeMode="contain" />
                </View>
                <Text style={styles.foodNameSmall}>{sf2.name}</Text>
              </View>
            </View>
          </View>
        )}
      </View>

      {/* Tiny Hero Challenge */}
      {(recLoading || tinyHeroFoods.length > 0) && (
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <View style={[styles.sectionIndicator, { backgroundColor: '#9C27B0' }]} />
            <Text style={[styles.sectionTitle, { color: '#9C27B0' }]}>Tiny Hero Challenge</Text>
          </View>
          <Text style={styles.challengeSubtitle}>Try these healthy foods — your taste buds might surprise you!</Text>
          {recLoading ? (
            <ActivityIndicator color="#9C27B0" size="large" style={{ marginVertical: 24 }} />
          ) : (
            <View style={styles.grid}>
              {tinyHeroFoods.map((food) => (
                <View key={food.cn_code} style={[styles.mainCard, { borderLeftWidth: 4, borderLeftColor: '#9C27B0', padding: 16 }]}>
                  <View style={styles.cardHeader}>
                    <View style={[styles.badge, { backgroundColor: '#9C27B0' }]}>
                      <Text style={styles.badgeText}>HERO CHALLENGE</Text>
                    </View>
                    <Text style={styles.foodNameLarge}>{food.name}</Text>
                  </View>
                  <View style={[styles.mainImageContainer, { height: 100 }]}>
                    <Image source={{ uri: food.image_url }} style={styles.mainImage} resizeMode="cover" />
                  </View>
                </View>
              ))}
            </View>
          )}
        </View>
      )}

      {/* Try Less Section */}
      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <View style={[styles.sectionIndicator, { backgroundColor: '#FF8A65' }]} />
          <Text style={styles.sectionTitle}>Try Less</Text>
        </View>

        {recLoading ? (
          <ActivityIndicator color="#FF8A65" size="large" style={{ marginVertical: 24 }} />
        ) : tryLessFoods.length > 0 ? (
          <View style={styles.grid}>
            {tryLessFoods.map((food) => (
              <View key={food.cn_code} style={[styles.smallCard, { flexDirection: 'row', alignItems: 'center', gap: 12, padding: 16 }]}>
                <View style={[styles.smallImageContainer, { width: 64, height: 64 }]}>
                  <Image source={{ uri: food.image_url }} style={[styles.smallImage, { opacity: 0.7 }]} resizeMode="contain" />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.foodNameSmall}>{food.name}</Text>
                  <View style={[styles.badge, { backgroundColor: '#FFCCBC', marginTop: 4 }]}>
                    <Text style={[styles.badgeText, { color: '#BF360C' }]}>EAT LESS</Text>
                  </View>
                </View>
              </View>
            ))}
          </View>
        ) : (
          <View style={styles.tryLessCard}>
            <View style={styles.tryLessContent}>
              <View style={styles.choiceRow}>
                <View style={styles.badImageContainer}>
                  <Image source={{ uri: goal.tryLess.image }} style={styles.badImage} resizeMode="contain" />
                </View>
                <ArrowRight color="#3b82f6" size={24} />
                <View style={styles.goodImageContainer}>
                  <Image source={{ uri: goal.tryLess.alternative.image }} style={styles.goodImage} resizeMode="contain" />
                </View>
              </View>
              <Text style={styles.tipText}>{goal.tryLess.alternative.tip}</Text>
            </View>
          </View>
        )}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  contentContainer: {
    paddingHorizontal: 24,
    paddingTop: 16,
    paddingBottom: 100,
  },
  backButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 16,
    alignSelf: 'flex-start',
    paddingVertical: 8,
    paddingHorizontal: 12,
    backgroundColor: '#E8EAF6',
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#3F51B5',
  },
  backButtonText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#3F51B5',
  },
  heroSection: {
    marginBottom: 32,
    alignItems: 'center',
  },
  heroTitle: {
    fontSize: 32,
    fontWeight: '900',
    color: '#36392c',
    textAlign: 'center',
    lineHeight: 40,
  },
  heroSubtitle: {
    fontSize: 18,
    color: '#64748b',
    fontWeight: '600',
    marginTop: 8,
    textAlign: 'center',
  },
  section: {
    marginBottom: 40,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 20,
  },
  sectionIndicator: {
    width: 6,
    height: 32,
    borderRadius: 3,
    backgroundColor: '#3F51B5',
    marginRight: 12,
  },
  sectionTitle: {
    fontSize: 24,
    fontWeight: '900',
    color: '#36392c',
  },
  challengeSubtitle: {
    fontSize: 14,
    color: '#7B1FA2',
    fontWeight: '600',
    marginBottom: 16,
    fontStyle: 'italic',
  },
  grid: {
    gap: 16,
  },
  mainCard: {
    backgroundColor: '#f1f5f9',
    borderRadius: 24,
    padding: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 10,
    elevation: 4,
  },
  cardHeader: {
    marginBottom: 16,
  },
  badge: {
    backgroundColor: '#3F51B5',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 20,
    alignSelf: 'flex-start',
    marginBottom: 8,
  },
  badgeText: {
    color: '#fff',
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 1,
  },
  foodNameLarge: {
    fontSize: 28,
    fontWeight: '900',
    color: '#36392c',
  },
  mainImageContainer: {
    height: 160,
    backgroundColor: '#fff',
    borderRadius: 20,
    overflow: 'hidden',
    marginBottom: 16,
    borderWidth: 4,
    borderColor: '#fff',
  },
  mainImage: {
    width: '100%',
    height: '100%',
  },
  descriptionText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#64748b',
    fontStyle: 'italic',
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 16,
  },
  smallCard: {
    flex: 1,
    backgroundColor: '#f1f5f9',
    borderRadius: 20,
    padding: 16,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 5,
    elevation: 2,
  },
  smallImageContainer: {
    width: '100%',
    height: 100,
    backgroundColor: '#fff',
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 8,
    marginBottom: 12,
  },
  smallImage: {
    width: '100%',
    height: '100%',
  },
  foodNameSmall: {
    fontSize: 16,
    fontWeight: '900',
    color: '#36392c',
    textAlign: 'center',
  },
  tryLessCard: {
    backgroundColor: '#fff',
    borderRadius: 24,
    padding: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 10,
    elevation: 4,
    borderWidth: 2,
    borderStyle: 'dashed',
    borderColor: 'rgba(0,0,0,0.1)',
  },
  tryLessContent: {
    alignItems: 'center',
  },
  choiceRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-around',
    width: '100%',
    marginBottom: 20,
  },
  badImageContainer: {
    width: 80,
    height: 80,
    backgroundColor: '#f1f5f9',
    borderRadius: 40,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 12,
  },
  badImage: {
    width: '100%',
    height: '100%',
    opacity: 0.5,
  },
  goodImageContainer: {
    width: 100,
    height: 100,
    backgroundColor: '#E8EAF6',
    borderRadius: 50,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    borderWidth: 4,
    borderColor: '#fff',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 5,
    elevation: 3,
  },
  goodImage: {
    width: '100%',
    height: '100%',
  },
  tipText: {
    fontSize: 16,
    fontWeight: '800',
    color: '#36392c',
    textAlign: 'center',
    fontStyle: 'italic',
    lineHeight: 24,
  },
});
