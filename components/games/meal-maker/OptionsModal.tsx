/**
 * OptionsModal — Game settings modal for Meal Maker
 *
 * Provides:
 *  - Volume control (step buttons) affecting all in-game sounds
 *  - Difficulty selector (Easy / Medium / Hard)
 */

import React from 'react';
import {
  Modal,
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Platform,
} from 'react-native';
import { Minus, Plus, X } from 'lucide-react-native';
import { Colors } from '@/constants/colors';
import { Spacing } from '@/constants/spacing';
import { Radius } from '@/constants/radius';
import type { GameDifficulty } from '@/services/gameSettings';

interface OptionsModalProps {
  visible: boolean;
  volume: number;
  difficulty: GameDifficulty;
  onVolumeChange: (v: number) => void;
  onDifficultyChange: (d: GameDifficulty) => void;
  onClose: () => void;
}

const DIFFICULTIES: { key: GameDifficulty; label: string; emoji: string; description: string }[] = [
  { key: 'easy',   label: 'Easy',   emoji: '🌱', description: 'Slower items, 0.8× points' },
  { key: 'medium', label: 'Medium', emoji: '⚡', description: 'Normal speed, 1× points' },
  { key: 'hard',   label: 'Hard',   emoji: '🔥', description: 'Faster items, 1.25× points' },
];

const VOLUME_STEP = 0.1;

export default function OptionsModal({
  visible,
  volume,
  difficulty,
  onVolumeChange,
  onDifficultyChange,
  onClose,
}: OptionsModalProps) {
  const handleVolumeDown = () => {
    onVolumeChange(Math.max(0, parseFloat((volume - VOLUME_STEP).toFixed(1))));
  };

  const handleVolumeUp = () => {
    onVolumeChange(Math.min(1, parseFloat((volume + VOLUME_STEP).toFixed(1))));
  };

  // Build a visual bar of 10 segments
  const filledSegments = Math.round(volume * 10);

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onClose}
    >
      <View style={styles.backdrop}>
        <View style={styles.sheet}>
          {/* Header */}
          <View style={styles.header}>
            <Text style={styles.title}>Settings</Text>
            <TouchableOpacity onPress={onClose} style={styles.closeButton} activeOpacity={0.7}>
              <X size={22} color={Colors.on_surface_variant} />
            </TouchableOpacity>
          </View>

          {/* Volume */}
          <View style={styles.section}>
            <Text style={styles.sectionLabel}>🔊 Volume</Text>
            <View style={styles.volumeRow}>
              <TouchableOpacity
                style={styles.volumeStepButton}
                onPress={handleVolumeDown}
                activeOpacity={0.7}
                disabled={volume <= 0}
              >
                <Minus size={18} color={volume <= 0 ? Colors.outline_variant : Colors.on_surface} />
              </TouchableOpacity>

              {/* Segmented bar */}
              <View style={styles.volumeBar}>
                {Array.from({ length: 10 }).map((_, i) => (
                  <View
                    key={i}
                    style={[
                      styles.volumeSegment,
                      i < filledSegments && styles.volumeSegmentFilled,
                    ]}
                  />
                ))}
              </View>

              <TouchableOpacity
                style={styles.volumeStepButton}
                onPress={handleVolumeUp}
                activeOpacity={0.7}
                disabled={volume >= 1}
              >
                <Plus size={18} color={volume >= 1 ? Colors.outline_variant : Colors.on_surface} />
              </TouchableOpacity>
            </View>
            <Text style={styles.volumeValue}>{Math.round(volume * 100)}%</Text>
          </View>

          {/* Difficulty */}
          <View style={styles.section}>
            <Text style={styles.sectionLabel}>🎮 Difficulty</Text>
            <View style={styles.difficultyRow}>
              {DIFFICULTIES.map((d) => {
                const selected = difficulty === d.key;
                return (
                  <TouchableOpacity
                    key={d.key}
                    style={[styles.difficultyButton, selected && styles.difficultyButtonSelected]}
                    onPress={() => onDifficultyChange(d.key)}
                    activeOpacity={0.8}
                  >
                    <Text style={styles.difficultyEmoji}>{d.emoji}</Text>
                    <Text style={[styles.difficultyLabel, selected && styles.difficultyLabelSelected]}>
                      {d.label}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </View>
            {/* Description for selected difficulty */}
            {DIFFICULTIES.filter((d) => d.key === difficulty).map((d) => (
              <Text key={d.key} style={styles.difficultyDescription}>{d.description}</Text>
            ))}
          </View>

          {/* Done button */}
          <TouchableOpacity style={styles.doneButton} onPress={onClose} activeOpacity={0.85}>
            <Text style={styles.doneButtonText}>Done</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.45)',
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: Spacing.xl,
  },
  sheet: {
    width: '100%',
    maxWidth: 400,
    backgroundColor: '#FFFDF4',
    borderRadius: 28,
    padding: Spacing.xl,
    gap: Spacing.lg,
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 8 },
        shadowOpacity: 0.18,
        shadowRadius: 20,
      },
      android: { elevation: 10 },
    }),
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  title: {
    fontSize: 24,
    fontWeight: '900',
    color: '#3E3A35',
  },
  closeButton: {
    padding: Spacing.xs,
  },
  section: {
    gap: Spacing.sm,
  },
  sectionLabel: {
    fontSize: 17,
    fontWeight: '800',
    color: '#3E3A35',
  },
  volumeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
  },
  volumeStepButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    borderWidth: 1.5,
    borderColor: Colors.outline_variant,
    backgroundColor: Colors.surface_container_low,
    alignItems: 'center',
    justifyContent: 'center',
  },
  volumeBar: {
    flex: 1,
    flexDirection: 'row',
    gap: 3,
    alignItems: 'center',
  },
  volumeSegment: {
    flex: 1,
    height: 20,
    borderRadius: 4,
    backgroundColor: Colors.outline_variant,
  },
  volumeSegmentFilled: {
    backgroundColor: Colors.secondary_dim,
  },
  volumeValue: {
    fontSize: 14,
    fontWeight: '700',
    color: Colors.on_surface_variant,
    textAlign: 'center',
  },
  difficultyRow: {
    flexDirection: 'row',
    gap: Spacing.sm,
  },
  difficultyButton: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: Spacing.md,
    borderRadius: Radius.md,
    borderWidth: 2,
    borderColor: Colors.outline_variant,
    backgroundColor: Colors.surface_container_low,
    gap: Spacing.xs,
  },
  difficultyButtonSelected: {
    borderColor: Colors.secondary_dim,
    backgroundColor: '#FFF3E3',
  },
  difficultyEmoji: {
    fontSize: 22,
  },
  difficultyLabel: {
    fontSize: 14,
    fontWeight: '800',
    color: Colors.on_surface_variant,
  },
  difficultyLabelSelected: {
    color: Colors.secondary_dim,
  },
  difficultyDescription: {
    fontSize: 13,
    fontWeight: '600',
    color: Colors.on_surface_variant,
    textAlign: 'center',
  },
  doneButton: {
    backgroundColor: Colors.secondary_dim,
    borderRadius: Radius.full,
    paddingVertical: Spacing.md,
    alignItems: 'center',
    marginTop: Spacing.xs,
  },
  doneButtonText: {
    color: Colors.on_primary,
    fontSize: 17,
    fontWeight: '900',
  },
});
