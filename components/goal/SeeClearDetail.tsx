import React from 'react';
import {
  ActivityIndicator,
  Dimensions,
  Image,
  ScrollView,
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
} from 'react-native';
import { ArrowLeft } from 'lucide-react-native';
import type { Goal } from './types';
import type { RecommendationResponse } from '../../services/recommendations';

const { width } = Dimensions.get('window');

interface Props {
  goal: Goal;
  onBack?: () => void;
  recommendations?: RecommendationResponse | null;
  recLoading?: boolean;
}

export default function SeeClearDetail({ goal, onBack, recommendations, recLoading }: Props) {
  const displaySuperFoods = recommendations?.super_power_foods?.map(f => ({
    name: f.name,
    description: `Grade ${f.grade}`,
    image: f.image_url,
    rating: 2,
  })) ?? goal.superFoods;

  const tinyHeroFoods = recommendations?.tiny_hero_foods ?? [];
  const tryLessFoods = recommendations?.try_less_foods ?? [];
  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>
      {/* Custom Back Button */}
      <TouchableOpacity style={styles.backButton} onPress={onBack}>
        <ArrowLeft color="#2196F3" size={28} />
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
          <Text style={styles.heroTitle}>Foods for 👓 {goal.title}</Text>
          <Text style={styles.heroSubtitle}>{goal.description}</Text>
        </View>
        <View style={styles.tipCard}>
          <Text style={styles.tipText}>{goal.mascotTip}</Text>
          <View style={styles.tipTriangle} />
        </View>
      </View>

      {/* Super Power Foods */}
      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <View style={styles.sectionIndicator} />
          <Text style={styles.sectionTitle}>Super Power Foods</Text>
        </View>

        {recLoading ? (
          <ActivityIndicator color="#2196F3" size="large" style={{ marginVertical: 24 }} />
        ) : (
          <View style={styles.grid}>
            {displaySuperFoods.map((food) => (
              <View key={food.name} style={styles.foodCard}>
                <View style={styles.foodInfo}>
                  <Text style={styles.foodName}>{food.name}</Text>
                  <View style={styles.badge}>
                    <Text style={styles.badgeText}>GOOD CHOICE</Text>
                  </View>
                </View>
                <View style={styles.foodIconContainer}>
                  <Image source={{ uri: food.image }} style={styles.foodImage} resizeMode="contain" />
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
                  <View style={styles.foodInfo}>
                    <Text style={styles.foodName}>{food.name}</Text>
                    <Text style={[styles.goodChoiceText, { color: '#7B1FA2' }]}>Hero Challenge</Text>
                  </View>
                  <View style={styles.foodIconContainer}>
                    <Image source={{ uri: food.image_url }} style={styles.foodImage} resizeMode="contain" />
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
              <View key={food.cn_code} style={[styles.foodCard, { backgroundColor: '#FFF3E0' }]}>
                <View style={styles.foodInfo}>
                  <Text style={styles.foodName}>{food.name}</Text>
                  <Text style={[styles.goodChoiceText, { color: '#BF360C' }]}>Eat Less</Text>
                </View>
                <View style={styles.foodIconContainer}>
                  <Image source={{ uri: food.image_url }} style={[styles.foodImage, { opacity: 0.7 }]} resizeMode="contain" />
                </View>
              </View>
            ))}
          </View>
        ) : (
          <View style={styles.tryLessCard}>
            <View style={styles.tryLessContent}>
              <View style={styles.badChoiceColumn}>
                <Image source={{ uri: goal.tryLess.image }} style={styles.badImage} resizeMode="contain" />
                <Text style={styles.badName}>{goal.tryLess.name}</Text>
              </View>
              <View style={styles.tryLessInfo}>
                <Text style={styles.alternativeTip}>{goal.tryLess.alternative.tip}</Text>
                <View style={styles.tryThisRow}>
                  <View style={styles.divider} />
                  <Text style={styles.tryThisText}>Try this instead!</Text>
                  <View style={styles.divider} />
                </View>
                <View style={styles.goodChoiceRow}>
                  <Image source={{ uri: goal.tryLess.alternative.image }} style={styles.goodImage} resizeMode="contain" />
                  <View style={styles.goodChoiceInfo}>
                    <Text style={styles.goodName}>{goal.tryLess.alternative.name}</Text>
                    <Text style={styles.goodTip}>{goal.tryLess.alternative.tip}</Text>
                  </View>
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
    backgroundColor: '#E3F2FD',
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#2196F3',
  },
  backButtonText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#2196F3',
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
    color: '#2196F3',
    fontWeight: '700',
    marginTop: 8,
    textAlign: 'center',
  },
  tipCard: {
    backgroundColor: '#fff',
    padding: 24,
    borderRadius: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 10,
    elevation: 4,
    borderWidth: 2,
    borderColor: 'rgba(0,0,0,0.05)',
    maxWidth: 320,
  },
  tipText: {
    fontSize: 18,
    fontWeight: '700',
    color: '#36392c',
    textAlign: 'center',
    lineHeight: 24,
  },
  tipTriangle: {
    position: 'absolute',
    top: -12,
    left: '50%',
    marginLeft: -12,
    width: 24,
    height: 24,
    backgroundColor: '#fff',
    transform: [{ rotate: '45deg' }],
    borderLeftWidth: 2,
    borderTopWidth: 2,
    borderColor: 'rgba(0,0,0,0.05)',
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
    backgroundColor: '#2196F3',
    marginRight: 12,
  },
  sectionTitle: {
    fontSize: 24,
    fontWeight: '900',
    color: '#2196F3',
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
    justifyContent: 'space-between',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 5,
    elevation: 2,
  },
  foodIconContainer: {
    width: 100,
    height: 100,
    backgroundColor: '#fff',
    borderRadius: 50,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 5,
    elevation: 3,
  },
  foodImage: {
    width: '100%',
    height: '100%',
  },
  foodInfo: {
    flex: 1,
  },
  badge: {
    backgroundColor: '#E3F2FD',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 20,
    alignSelf: 'flex-start',
    marginTop: 4,
  },
  badgeText: {
    color: '#2196F3',
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 1,
  },
  foodName: {
    fontSize: 24,
    fontWeight: '900',
    color: '#36392c',
    marginBottom: 2,
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
    flexDirection: 'column',
    alignItems: 'center',
    gap: 20,
  },
  badChoiceColumn: {
    alignItems: 'center',
  },
  badImage: {
    width: 80,
    height: 80,
    opacity: 0.7,
    marginBottom: 8,
  },
  badName: {
    fontSize: 18,
    fontWeight: '800',
    color: '#64748b',
  },
  tryLessInfo: {
    width: '100%',
    alignItems: 'center',
  },
  alternativeTip: {
    fontSize: 14,
    fontWeight: '600',
    color: '#64748b',
    fontStyle: 'italic',
    textAlign: 'center',
    lineHeight: 20,
    marginBottom: 16,
  },
  tryThisRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    width: '100%',
    marginBottom: 16,
  },
  divider: {
    flex: 1,
    height: 1,
    backgroundColor: 'rgba(0,0,0,0.1)',
  },
  tryThisText: {
    fontSize: 12,
    fontWeight: '900',
    color: '#E91E63',
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginHorizontal: 16,
  },
  goodChoiceRow: {
    backgroundColor: '#f8fafc',
    padding: 16,
    borderRadius: 16,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
    width: '100%',
    borderWidth: 1,
    borderColor: '#FCE4EC',
  },
  goodImage: {
    width: 48,
    height: 48,
  },
  goodChoiceInfo: {
    flex: 1,
  },
  goodName: {
    fontSize: 18,
    fontWeight: '900',
    color: '#36392c',
    marginBottom: 2,
  },
  goodTip: {
    fontSize: 12,
    fontWeight: '600',
    color: '#E91E63',
  },
});
