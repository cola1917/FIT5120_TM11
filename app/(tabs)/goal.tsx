/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import AppHeader from '@/components/app_header';
import {
  Baby,
  Dumbbell,
  Glasses,
  Lightbulb,
  ShieldPlus,
  Smile
} from 'lucide-react-native';
import React, { useEffect, useState } from 'react';
import {
  Dimensions,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import BeStrongDetail from '../../components/goal/BeStrongDetail';
import FeelGoodDetail from '../../components/goal/FeelGoodDetail';
import FightGermsDetail from '../../components/goal/FightGermsDetail';
import GrowUpDetail from '../../components/goal/GrowUpDetail';
import SeeClearDetail from '../../components/goal/SeeClearDetail';
import ThinkFastDetail from '../../components/goal/ThinkFastDetail';
import type { Goal } from '../../components/goal/types';
import { getUserProfile } from '../../services/userProfile';
import { getRecommendations, type RecommendationResponse } from '../../services/recommendations';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

// Goal metadata - only navigation info, no hardcoded food data
interface GoalMeta {
  id: string;
  title: string;
  subtitle: string;
  icon: React.ComponentType<{ size?: number; color?: string; strokeWidth?: number }>;
  gradient: string[];
  emoji: string;
}

const GOAL_METAS: GoalMeta[] = [
  {
    id: 'grow',
    title: 'POWER STRONGER',
    subtitle: 'Grow Like a Hero!',
    icon: Baby,
    gradient: ['#6366f1', '#8b5cf6'],
    emoji: '🌱',
  },
  {
    id: 'see',
    title: 'SUPER VISION',
    subtitle: 'Eagle Eyes!',
    icon: Glasses,
    gradient: ['#a855f7', '#f97316'],
    emoji: '👓',
  },
  {
    id: 'think',
    title: 'SMART BOOST',
    subtitle: 'Genius Mode!',
    icon: Lightbulb,
    gradient: ['#401500', '#dc2626'],
    emoji: '🧠',
  },
  {
    id: 'fight',
    title: 'GERM BUSTER',
    subtitle: 'Shield Power!',
    icon: ShieldPlus,
    gradient: ['#f97316', '#dc2626'],
    emoji: '🛡️',
  },
  {
    id: 'feel',
    title: 'HAPPY HERO',
    subtitle: 'Smile Shine!',
    icon: Smile,
    gradient: ['#facc15', '#f97316'],
    emoji: '😊',
  },
  {
    id: 'strong',
    title: 'MUSCLE MAGIC',
    subtitle: 'Hero Strength!',
    icon: Dumbbell,
    gradient: ['#2563eb', '#312e81'],
    emoji: '💪',
  },
];

export default function GoalScreen() {
  const [selectedGoalId, setSelectedGoalId] = useState<string | null>(null);
  const [recommendations, setRecommendations] = useState<RecommendationResponse | null>(null);
  const [recLoading, setRecLoading] = useState(false);

  const selectedGoalMeta = GOAL_METAS.find(g => g.id === selectedGoalId);

  useEffect(() => {
    if (!selectedGoalId) {
      setRecommendations(null);
      return;
    }

    let cancelled = false;

    const fetchRecs = async () => {
      setRecLoading(true);
      setRecommendations(null);
      try {
        const profile = await getUserProfile();
        const prefs = profile?.foodPreferences;

        const data = await getRecommendations(
          selectedGoalId,
          prefs?.likes ?? [],
          prefs?.dislikes ?? [],
          prefs?.blacklist ?? []
        );

        if (!cancelled) setRecommendations(data);
      } catch {
        // API failed: keep recommendations null so components fall back to static GOALS data
        if (!cancelled) setRecommendations(null);
      } finally {
        if (!cancelled) setRecLoading(false);
      }
    };

    fetchRecs();
    return () => { cancelled = true; };
  }, [selectedGoalId]);

  const renderGoalList = () => (
    <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
      {/* Hero Section */}
      <View style={styles.heroSection}>
        <Text style={styles.heroTitle}>Goals</Text>
        <Text style={styles.heroSubtitle}>
          Pick a path and complete daily quests to earn hero badges.
        </Text>
      </View>

      {/* Goals Grid */}
      <View style={styles.grid}>
        {GOAL_METAS.map((goalMeta, index) => (
          <TouchableOpacity
            key={goalMeta.id}
            style={[
              styles.goalCard,
              {
                transform: [{ rotate: `${index % 2 === 0 ? -2 : 2}deg` }],
              },
            ]}
            activeOpacity={0.9}
            onPress={() => setSelectedGoalId(goalMeta.id)}
          >
            <View
              style={[
                styles.goalCardContent,
                {
                  backgroundColor: goalMeta.gradient[0],
                },
              ]}
            >
              {/* Background Icon */}
              <View style={styles.bgIconContainer}>
                <goalMeta.icon size={120} color="#ffffff" strokeWidth={1} />
              </View>

              {/* Content */}
              <View style={styles.cardContent}>
                <View style={[styles.iconCircle, { backgroundColor: 'rgba(255,255,255,0.2)' }]}>
                  <goalMeta.icon size={40} color="#ffffff" />
                </View>
                <Text style={styles.cardTitle}>{goalMeta.title}</Text>
                <Text style={styles.cardSubtitle}>{goalMeta.subtitle}</Text>
              </View>
            </View>
          </TouchableOpacity>
        ))}
      </View>
    </ScrollView>
  );

  const renderGoalDetail = () => {
    if (!selectedGoalMeta) return null;

    const detailProps = {
      onBack: () => setSelectedGoalId(null),
      recommendations,
      recLoading,
    };

    switch (selectedGoalMeta.id) {
      case 'grow':
        return <GrowUpDetail {...detailProps} />;
      case 'see':
        return <SeeClearDetail {...detailProps} />;
      case 'think':
        return <ThinkFastDetail {...detailProps} />;
      case 'fight':
        return <FightGermsDetail {...detailProps} />;
      case 'feel':
        return <FeelGoodDetail {...detailProps} />;
      case 'strong':
        return <BeStrongDetail {...detailProps} />;
      default:
        return null;
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.container}>
        {/* Shared app header with menu button */}
        <AppHeader title={selectedGoalId ? selectedGoalMeta?.title : 'NutriHeroes'} />

        {/* Content */}
        {selectedGoalId ? renderGoalDetail() : renderGoalList()}

      </ScrollView>
      
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#F6F8EC',
  },
  container: {
    flex: 1,
    paddingHorizontal: 20,
    paddingTop: 8,
    backgroundColor: '#F8F5E9',
  },
  scrollView: {
    flex: 1,
  },
  heroSection: {
    alignItems: 'center',
    paddingVertical: 24,
    paddingHorizontal: 24,
  },
  heroTitle: {
    fontSize: 36,
    fontWeight: '900',
    color: '#B45309',
    marginBottom: 8,
  },
  heroSubtitle: {
    fontSize: 15,
    lineHeight: 22,
    color: '#666',
    textAlign: 'center',
    maxWidth: 280,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 24,
    paddingHorizontal: 24,
    paddingBottom: 32,
  },
  goalCard: {
    width: CARD_WIDTH,
    height: 220,
  },
  goalCardContent: {
    flex: 1,
    borderRadius: 16,
    overflow: 'hidden',
    position: 'relative',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  bgIconContainer: {
    position: 'absolute',
    top: -16,
    right: -16,
    opacity: 0.1,
    transform: [{ rotate: '12deg' }],
  },
  cardContent: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 20,
  },
  iconCircle: {
    width: 80,
    height: 80,
    borderRadius: 40,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '900',
    color: '#ffffff',
    textTransform: 'uppercase',
    letterSpacing: 1,
    textAlign: 'center',
  },
  cardSubtitle: {
    fontSize: 10,
    fontWeight: '700',
    color: 'rgba(255,255,255,0.9)',
    textTransform: 'uppercase',
    letterSpacing: 2,
    marginTop: 4,
    textAlign: 'center',
  },
  detailFallback: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  detailTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 16,
    color: '#333',
  },
  detailDescription: {
    fontSize: 16,
    color: '#666',
    textAlign: 'center',
    lineHeight: 24,
  },
  backButton: {
    marginTop: 32,
    backgroundColor: '#1E90FF',
    paddingHorizontal: 32,
    paddingVertical: 12,
    borderRadius: 24,
  },
  backButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: 'bold',
  },
});
