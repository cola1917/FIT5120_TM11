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

export default function GrowUpDetail({ goal, onBack, recommendations, recLoading }: Props) {
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
        <ArrowLeft color="#4CAF50" size={28} />
        <Text style={styles.backButtonText}>Back to Goals</Text>
      </TouchableOpacity>

      {/* Hero Section */}
      <View style={styles.heroSection}>
        <View style={styles.heroImageContainer}>
          <Image 
            source={{ uri: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCrSM32q7XlPujehh6OBCUPQAxm54TnFOlVSbzvWsgAQtxU0KjG2n5wyUpxc_4EiVW9McN_SUvWo7fgk8Awixd4Pa3jdEu0P8Q8p78PeKWQfha8XySUS0wIWtJoY0QmzMHDRWqRoximNSRa8MU1FTDaC5CUdx0jOUJ054Er76eGsdJN0-JWkgHihX8_2EFJJwNygVT_ZyNmxvi_1ntUT5leg-lVCD4Y9xaNHGfXH1Nuzzzz6aqzUwBC9Mm4r_vONOZSeq1fIQL94nuU' }} 
            style={styles.heroImage} 
            resizeMode="contain"
          />
        </View>
        <View style={styles.heroTextContainer}>
          <Text style={styles.heroTitle}>Foods for 🌱 {goal.title}</Text>
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
          <ActivityIndicator color="#4CAF50" size="large" style={{ marginVertical: 24 }} />
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
          <View style={[styles.sectionIndicator, { backgroundColor: '#FF8A65' }]} />
          <Text style={[styles.sectionTitle, { color: '#FF8A65' }]}>Try Less</Text>
        </View>

        {recLoading ? (
          <ActivityIndicator color="#FF8A65" size="large" style={{ marginVertical: 24 }} />
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
              <View style={styles.choiceColumn}>
                <View style={styles.badImageContainer}>
                  <Image source={{ uri: goal.tryLess.image }} style={styles.badImage} resizeMode="contain" />
                </View>
                <Text style={styles.choiceName}>{goal.tryLess.name}</Text>
              </View>
              <View style={styles.transitionColumn}>
                <Text style={[styles.tipText, { color: '#4CAF50' }]}>{goal.tryLess.alternative.tip}</Text>
                <ArrowRight color="#4CAF50" size={32} />
                <Text style={styles.tryThisText}>TRY THIS INSTEAD!</Text>
              </View>
              <View style={styles.choiceColumn}>
                <View style={styles.goodImageContainer}>
                  <Image source={{ uri: goal.tryLess.alternative.image }} style={styles.goodImage} resizeMode="contain" />
                </View>
                <Text style={styles.goodChoiceName}>{goal.tryLess.alternative.name}</Text>
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
    backgroundColor: '#E8F5E9',
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#4CAF50',
  },
  backButtonText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#4CAF50',
  },
  heroSection: {
    marginBottom: 40,
    alignItems: 'center',
  },
  heroImageContainer: {
    width: 192,
    height: 192,
    marginBottom: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  heroImage: {
    width: '100%',
    height: '100%',
  },
  heroTextContainer: {
    alignItems: 'center',
    marginBottom: 24,
  },
  heroTitle: {
    fontSize: 32,
    fontWeight: '900',
    color: '#36392c',
    textAlign: 'center',
  },
  heroSubtitle: {
    fontSize: 20,
    color: '#4CAF50',
    fontWeight: '700',
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
    backgroundColor: '#4CAF50',
    marginRight: 12,
  },
  sectionTitle: {
    fontSize: 24,
    fontWeight: '900',
    color: '#4CAF50',
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
    backgroundColor: '#E8F5E9',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 20,
    alignSelf: 'flex-start',
  },
  badgeText: {
    color: '#2E7D32',
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
    borderColor: 'rgba(76, 175, 80, 0.2)',
  },
  tryLessContent: {
    flexDirection: 'column',
    alignItems: 'center',
    gap: 24,
  },
  choiceColumn: {
    alignItems: 'center',
  },
  badImageContainer: {
    width: 80,
    height: 80,
    backgroundColor: '#f1f5f9',
    borderRadius: 40,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 12,
    marginBottom: 8,
  },
  badImage: {
    width: '100%',
    height: '100%',
    opacity: 0.6,
  },
  choiceName: {
    fontSize: 16,
    fontWeight: '700',
    color: '#64748b',
  },
  transitionColumn: {
    alignItems: 'center',
    paddingHorizontal: 20,
  },
  tipText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#64748b',
    textAlign: 'center',
    fontStyle: 'italic',
    lineHeight: 20,
    marginBottom: 12,
  },
  tryThisText: {
    fontSize: 12,
    fontWeight: '900',
    color: '#4CAF50',
    marginTop: 8,
    letterSpacing: 1,
  },
  goodImageContainer: {
    width: 120,
    height: 120,
    backgroundColor: '#E8F5E9',
    borderRadius: 60,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 20,
    marginBottom: 12,
    borderWidth: 6,
    borderColor: '#fff',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 6,
  },
  goodImage: {
    width: '100%',
    height: '100%',
  },
  goodChoiceName: {
    fontSize: 22,
    fontWeight: '900',
    color: '#36392c',
  },
});
