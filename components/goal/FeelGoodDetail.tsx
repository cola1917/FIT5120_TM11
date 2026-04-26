import React from 'react';
import {
  StyleSheet,
  View,
  Text,
  Image,
  ScrollView,
  Dimensions,
  TouchableOpacity,
  ActivityIndicator,
} from 'react-native';
import { ArrowRight, ArrowLeft } from 'lucide-react-native';
import type { Goal } from './types';
import type { RecommendationResponse } from '../../services/recommendations';

const { width } = Dimensions.get('window');

interface Props {
  goal: Goal;
  onBack?: () => void;
  recommendations?: RecommendationResponse | null;
  recLoading?: boolean;
}

export default function FeelGoodDetail({ goal, onBack, recommendations, recLoading }: Props) {
  const displaySuperFoods = recommendations?.super_power_foods?.map(f => ({
    name: f.name,
    description: `Grade ${f.grade}`,
    image: f.image_url,
  })) ?? goal.superFoods;

  const tinyHeroFoods = recommendations?.tiny_hero_foods ?? [];
  const tryLessFoods = recommendations?.try_less_foods ?? [];
  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>
      {/* Custom Back Button */}
      <TouchableOpacity style={styles.backButton} onPress={onBack}>
        <ArrowLeft color="#FBC02D" size={28} />
        <Text style={styles.backButtonText}>Back to Goals</Text>
      </TouchableOpacity>

      {/* Hero Section */}
      <View style={styles.heroSection}>
        <View style={styles.heroCard}>
          <Text style={styles.heroTitle}>Foods for 😊 {goal.title}</Text>
          <Text style={styles.heroSubtitle}>{goal.description}</Text>
        </View>
      </View>

      {/* Super Power Foods */}
      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <View style={styles.sectionIndicator} />
          <Text style={styles.sectionTitle}>Super Power Foods</Text>
        </View>

        {recLoading ? (
          <ActivityIndicator color="#FBC02D" size="large" style={{ marginVertical: 24 }} />
        ) : (
          <View style={styles.grid}>
            {displaySuperFoods.map((food) => (
              <View key={food.name} style={styles.foodCard}>
                <View style={styles.imageContainer}>
                  <Image source={{ uri: food.image }} style={styles.foodImage} resizeMode="contain" />
                </View>
                <View style={styles.foodInfo}>
                  <Text style={styles.foodName}>{food.name}</Text>
                  <View style={styles.badge}>
                    <Text style={styles.badgeText}>GOOD CHOICE</Text>
                  </View>
                </View>
              </View>
            ))}
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
                <View key={food.cn_code} style={[styles.foodCard, { borderLeftWidth: 4, borderLeftColor: '#9C27B0' }]}>
                  <View style={styles.imageContainer}>
                    <Image source={{ uri: food.image_url }} style={styles.foodImage} resizeMode="contain" />
                  </View>
                  <View style={styles.foodInfo}>
                    <Text style={styles.foodName}>{food.name}</Text>
                    <View style={[styles.badge, { backgroundColor: '#F3E5F5' }]}>
                      <Text style={[styles.badgeText, { color: '#7B1FA2' }]}>HERO CHALLENGE</Text>
                    </View>
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
          <View style={[styles.sectionIndicator, { backgroundColor: '#FFD54F' }]} />
          <Text style={styles.sectionTitle}>Try Less</Text>
        </View>

        {recLoading ? (
          <ActivityIndicator color="#FFD54F" size="large" style={{ marginVertical: 24 }} />
        ) : tryLessFoods.length > 0 ? (
          <View style={styles.grid}>
            {tryLessFoods.map((food) => (
              <View key={food.cn_code} style={[styles.foodCard, { backgroundColor: '#FFF3E0' }]}>
                <View style={styles.imageContainer}>
                  <Image source={{ uri: food.image_url }} style={[styles.foodImage, { opacity: 0.7 }]} resizeMode="contain" />
                </View>
                <View style={styles.foodInfo}>
                  <Text style={styles.foodName}>{food.name}</Text>
                  <View style={[styles.badge, { backgroundColor: '#FFCCBC' }]}>
                    <Text style={[styles.badgeText, { color: '#BF360C' }]}>EAT LESS</Text>
                  </View>
                </View>
              </View>
            ))}
          </View>
        ) : (
          <View style={styles.tryLessCard}>
            <View style={styles.tryLessContent}>
              <View style={styles.badImageContainer}>
                <Image source={{ uri: goal.tryLess.image }} style={styles.badImage} resizeMode="contain" />
              </View>
              <View style={styles.tryLessInfo}>
                <Text style={styles.badName}>{goal.tryLess.name}</Text>
                <Text style={styles.alternativeTip}>{goal.tryLess.alternative.tip}</Text>
                <View style={styles.tryThisRow}>
                  <ArrowRight color="#FBC02D" size={16} />
                  <Text style={styles.tryThisText}>Try a {goal.tryLess.alternative.name} instead!</Text>
                </View>
              </View>
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
    backgroundColor: '#FFFDE7',
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#FBC02D',
  },
  backButtonText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#FBC02D',
  },
  heroSection: {
    marginBottom: 32,
    alignItems: 'center',
  },
  heroCard: {
    backgroundColor: '#fff',
    padding: 24,
    borderRadius: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 10,
    elevation: 4,
    borderBottomWidth: 4,
    borderBottomColor: '#FBC02D',
    width: '100%',
  },
  heroTitle: {
    fontSize: 24,
    fontWeight: '900',
    color: '#FBC02D',
    textAlign: 'center',
    marginBottom: 8,
  },
  heroSubtitle: {
    fontSize: 16,
    color: '#64748b',
    fontWeight: '600',
    textAlign: 'center',
  },
  tipSection: {
    backgroundColor: 'rgba(251, 192, 45, 0.1)',
    padding: 20,
    borderRadius: 20,
    marginBottom: 40,
    borderWidth: 1,
    borderColor: 'rgba(251, 192, 45, 0.2)',
    transform: [{ rotate: '-1deg' }],
  },
  tipText: {
    fontSize: 18,
    fontWeight: '700',
    color: '#FBC02D',
    textAlign: 'center',
    fontStyle: 'italic',
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
    backgroundColor: '#FBC02D',
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
  foodCard: {
    backgroundColor: '#f1f5f9',
    padding: 20,
    borderRadius: 20,
    flexDirection: 'row',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 5,
    elevation: 2,
  },
  imageContainer: {
    width: 80,
    height: 80,
    backgroundColor: '#fff',
    borderRadius: 40,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 10,
    marginRight: 20,
  },
  foodImage: {
    width: '100%',
    height: '100%',
  },
  foodInfo: {
    flex: 1,
  },
  foodName: {
    fontSize: 20,
    fontWeight: '900',
    color: '#36392c',
    marginBottom: 4,
  },
  badge: {
    backgroundColor: '#FFFDE7',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 20,
    alignSelf: 'flex-start',
  },
  badgeText: {
    color: '#FBC02D',
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 1,
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
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.05)',
  },
  tryLessContent: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 20,
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
    opacity: 0.6,
  },
  tryLessInfo: {
    flex: 1,
  },
  badName: {
    fontSize: 20,
    fontWeight: '900',
    color: '#36392c',
    marginBottom: 4,
  },
  alternativeTip: {
    fontSize: 14,
    fontWeight: '600',
    color: '#64748b',
    fontStyle: 'italic',
    lineHeight: 20,
    marginBottom: 8,
  },
  tryThisRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  tryThisText: {
    fontSize: 14,
    fontWeight: '900',
    color: '#FBC02D',
  },
});
