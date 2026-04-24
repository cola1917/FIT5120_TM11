/**
 * AboutModal — How to Play & Scoring guide for Meal Maker
 *
 * Designed for children aged 7–12. Uses large text, emoji-heavy layout,
 * and simple language. Presented as a full-screen modal overlay.
 */

import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Modal,
  SafeAreaView,
} from 'react-native';
import { X } from 'lucide-react-native';
import { Colors } from '@/constants/colors';
import { Spacing } from '@/constants/spacing';
import { Radius } from '@/constants/radius';

interface AboutModalProps {
  visible: boolean;
  onClose: () => void;
}

// Scoring data
// Curated subset of combinations, grouped by theme for readability.

const SCORING_GROUPS = [
  {
    title: '🌟 Best Meals',
    color: '#FFF3CD',
    borderColor: '#F5A623',
    rows: [
      { combo: '🥦 + 🍚 + 🍗', label: 'Veggie + Grain + Protein', pts: 10 },
      { combo: '🥦 + 🥦 + 🥦', label: '3 Vegetables', pts: 8 },
      { combo: '🥦 + 🥦 + 🍗', label: '2 Veggies + Protein', pts: 8 },
      { combo: '🥦 + 🥦 + 🍚', label: '2 Veggies + Grain', pts: 8 },
    ],
  },
  {
    title: '👍 Good Meals',
    color: '#E8F5E9',
    borderColor: '#4CAF50',
    rows: [
      { combo: '🍗 + 🍗 + 🍗', label: '3 Proteins', pts: 7 },
      { combo: '🥦 + 🍗 + 🍗', label: 'Veggie + 2 Proteins', pts: 7 },
      { combo: '🍚 + 🍗 + 🍗', label: 'Grain + 2 Proteins', pts: 6 },
      { combo: '🍚 + 🍚 + 🍚', label: '3 Grains', pts: 5 },
    ],
  },
  {
    title: '😐 Okay Meals',
    color: '#FFF8E1',
    borderColor: '#FFC107',
    rows: [
      { combo: '🥦 + 🍔 + 🍗', label: 'Veggie + Junk + Protein', pts: 4 },
      { combo: '🥦 + 🍔 + 🍚', label: 'Veggie + Junk + Grain', pts: 4 },
      { combo: '🍚 + 🍔 + 🍗', label: 'Grain + Junk + Protein', pts: 4 },
    ],
  },
  {
    title: '😬 Not Great',
    color: '#FBE9E7',
    borderColor: '#FF7043',
    rows: [
      { combo: '🍔 + 🍔 + 🍔', label: '3 Junk Foods', pts: -8 },
      { combo: '🍔 + 🍬 + 🍬', label: 'Junk + 2 Candies', pts: -8 },
      { combo: '🍬 + 🍬 + 🍬', label: '3 Candies', pts: -10 },
    ],
  },
];

// Component

export default function AboutModal({ visible, onClose }: AboutModalProps) {
  return (
    <Modal
      visible={visible}
      animationType="slide"
      presentationStyle="pageSheet"
      onRequestClose={onClose}
    >
      <SafeAreaView style={styles.safeArea}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.headerTitle}>How to Play 🍽️</Text>
          <TouchableOpacity
            style={styles.closeButton}
            onPress={onClose}
            activeOpacity={0.7}
            hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
          >
            <X size={26} color={Colors.on_surface} />
          </TouchableOpacity>
        </View>

        <ScrollView
          style={styles.scroll}
          contentContainerStyle={styles.scrollContent}
          showsVerticalScrollIndicator={false}
        >
          {/* How to play */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>🎮 The Game</Text>
            <View style={styles.card}>
              <StepRow emoji="👀" text="Foods fall from the top of the screen." />
              <StepRow emoji="👆" text="Drag 3 foods onto your plate to make a meal." />
              <StepRow emoji="⏱️" text="You have 60 seconds — make as many meals as you can!" />
              <StepRow emoji="⭐" text="Healthy meals earn more points. Junk food loses points!" />
            </View>
          </View>

          {/* Food categories */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>🥗 Food Groups</Text>
            <View style={styles.card}>
              <CategoryRow emoji="🥦🥕🍅" label="Vegetables" color="#4CAF50" />
              <CategoryRow emoji="🍚🍞🍝" label="Grains" color="#D7A86E" />
              <CategoryRow emoji="🍗🥚🐟" label="Proteins" color="#FFCC80" />
              <CategoryRow emoji="🍔🍟🍕" label="Junk Food" color="#FF7043" />
              <CategoryRow emoji="🍬🍭🎂" label="Candy" color="#F48FB1" />
            </View>
          </View>

          {/* Scoring */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>🏆 Scoring</Text>
            <Text style={styles.scoringHint}>
              Mix healthy foods for the best score!
            </Text>

            {SCORING_GROUPS.map((group) => (
              <View
                key={group.title}
                style={[
                  styles.scoringGroup,
                  { backgroundColor: group.color, borderColor: group.borderColor },
                ]}
              >
                <Text style={styles.scoringGroupTitle}>{group.title}</Text>
                {group.rows.map((row) => (
                  <View key={row.combo} style={styles.scoringRow}>
                    <Text style={styles.scoringCombo}>{row.combo}</Text>
                    <Text style={styles.scoringLabel}>{row.label}</Text>
                    <Text
                      style={[
                        styles.scoringPts,
                        { color: row.pts >= 0 ? '#006b1b' : '#b02500' },
                      ]}
                    >
                      {row.pts >= 0 ? `+${row.pts}` : `${row.pts}`}
                    </Text>
                  </View>
                ))}
              </View>
            ))}
          </View>

          {/* Tip */}
          <View style={styles.tipBox}>
            <Text style={styles.tipText}>
              💡 <Text style={styles.tipBold}>Tip:</Text> The best meal is a Vegetable + Grain + Protein — that earns you{' '}
              <Text style={styles.tipBold}>10 points!</Text>
            </Text>
          </View>
        </ScrollView>

        {/* Got it button */}
        <View style={styles.footer}>
          <TouchableOpacity style={styles.gotItButton} onPress={onClose} activeOpacity={0.85}>
            <Text style={styles.gotItText}>Got it! Let{"'"}s play 🎉</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    </Modal>
  );
}

// Sub-components

function StepRow({ emoji, text }: { emoji: string; text: string }) {
  return (
    <View style={styles.stepRow}>
      <Text style={styles.stepEmoji}>{emoji}</Text>
      <Text style={styles.stepText}>{text}</Text>
    </View>
  );
}

function CategoryRow({
  emoji,
  label,
  color,
}: {
  emoji: string;
  label: string;
  color: string;
}) {
  return (
    <View style={styles.categoryRow}>
      <View style={[styles.categoryDot, { backgroundColor: color }]} />
      <Text style={styles.categoryEmoji}>{emoji}</Text>
      <Text style={styles.categoryLabel}>{label}</Text>
    </View>
  );
}

// Styles

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#FFFDF4',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: Spacing.xl,
    paddingVertical: Spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: Colors.surface_container_high,
    backgroundColor: '#FFFDF4',
  },
  headerTitle: {
    fontSize: 26,
    fontWeight: '900',
    color: Colors.on_surface,
    fontFamily: 'PlusJakartaSans-Variable',
  },
  closeButton: {
    width: 40,
    height: 40,
    borderRadius: Radius.full,
    backgroundColor: Colors.surface_container,
    alignItems: 'center',
    justifyContent: 'center',
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: Spacing.xl,
    paddingTop: Spacing.lg,
    paddingBottom: Spacing['2xl'],
    gap: Spacing.lg,
  },

  // Sections
  section: {
    gap: Spacing.sm,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '800',
    color: Colors.on_surface,
    fontFamily: 'PlusJakartaSans-Variable',
  },
  card: {
    backgroundColor: Colors.surface_container_lowest,
    borderRadius: Radius.card,
    padding: Spacing.lg,
    gap: Spacing.md,
    shadowColor: Colors.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },

  // Steps
  stepRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: Spacing.md,
  },
  stepEmoji: {
    fontSize: 22,
    lineHeight: 28,
    width: 30,
    textAlign: 'center',
  },
  stepText: {
    flex: 1,
    fontSize: 17,
    lineHeight: 24,
    color: Colors.on_surface,
    fontFamily: 'BeVietnamPro-Regular',
  },

  // Categories
  categoryRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.md,
    paddingVertical: Spacing.xs,
  },
  categoryDot: {
    width: 12,
    height: 12,
    borderRadius: Radius.full,
  },
  categoryEmoji: {
    fontSize: 20,
    width: 72,
  },
  categoryLabel: {
    fontSize: 17,
    color: Colors.on_surface,
    fontFamily: 'BeVietnamPro-Medium',
    fontWeight: '600',
  },

  // Scoring
  scoringHint: {
    fontSize: 16,
    color: Colors.on_surface_variant,
    fontFamily: 'BeVietnamPro-Regular',
    marginBottom: Spacing.xs,
  },
  scoringGroup: {
    borderRadius: Radius.card,
    borderWidth: 2,
    padding: Spacing.md,
    gap: Spacing.sm,
    marginBottom: Spacing.sm,
  },
  scoringGroupTitle: {
    fontSize: 17,
    fontWeight: '800',
    color: Colors.on_surface,
    fontFamily: 'PlusJakartaSans-Variable',
    marginBottom: Spacing.xs,
  },
  scoringRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
  },
  scoringCombo: {
    fontSize: 18,
    width: 90,
  },
  scoringLabel: {
    flex: 1,
    fontSize: 14,
    color: Colors.on_surface_variant,
    fontFamily: 'BeVietnamPro-Regular',
  },
  scoringPts: {
    fontSize: 18,
    fontWeight: '900',
    fontFamily: 'PlusJakartaSans-Variable',
    minWidth: 36,
    textAlign: 'right',
  },

  // Tip
  tipBox: {
    backgroundColor: Colors.primary_container,
    borderRadius: Radius.card,
    padding: Spacing.lg,
  },
  tipText: {
    fontSize: 16,
    lineHeight: 24,
    color: Colors.on_primary_container,
    fontFamily: 'BeVietnamPro-Regular',
  },
  tipBold: {
    fontFamily: 'BeVietnamPro-Bold',
    fontWeight: '700',
  },

  // Footer
  footer: {
    paddingHorizontal: Spacing.xl,
    paddingVertical: Spacing.lg,
    backgroundColor: '#FFFDF4',
    borderTopWidth: 1,
    borderTopColor: Colors.surface_container_high,
  },
  gotItButton: {
    backgroundColor: Colors.secondary_dim,
    borderRadius: 28,
    paddingVertical: Spacing.lg,
    alignItems: 'center',
    shadowColor: '#7A2204',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 0,
    elevation: 3,
  },
  gotItText: {
    fontSize: 20,
    fontWeight: '900',
    color: '#ffffff',
    fontFamily: 'PlusJakartaSans-Variable',
  },
});
