/**
 * Profile Creation Screen
 *
 * Shown when no user profile exists. Collects username, avatar, age,
 * and food preferences (likes/dislikes + blacklist).
 * All data is stored locally — no backend calls.
 */

import React, { useState } from 'react';
import {
  Alert,
  Image,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Colors } from '@/constants/colors';
import { Typography } from '@/constants/fonts';
import { Spacing } from '@/constants/spacing';
import { Radius } from '@/constants/radius';
import {
  AvatarId,
  BlacklistItem,
  FoodPreferenceItem,
  FoodPreferences,
  createUserProfile,
} from '@/services/userProfile';
import {
  FoodPreferencesSelector,
  LikeDislikeMap,
  LikeDislikeState,
  BlacklistMap,
  createDefaultLikeDislikeMap,
  createDefaultBlacklistMap,
} from '@/components/profile/FoodPreferencesSelector';


// Avatar Carousel

interface AvatarCarouselProps {
  selectedAvatar: AvatarId;
  onAvatarChange: (avatarId: AvatarId) => void;
}

function AvatarCarousel({ selectedAvatar, onAvatarChange }: AvatarCarouselProps) {
  return (
    <View style={avatarStyles.container}>
      <TouchableOpacity
        style={[avatarStyles.avatarItem, selectedAvatar === 'hero' && avatarStyles.avatarItemSelected]}
        onPress={() => onAvatarChange('hero')}
        activeOpacity={0.3}
      >
        <Image
          source={require('../assets/images/avatar/hero-1.png')}
          resizeMode='contain'
          style={styles.avatarImage}
        />
      </TouchableOpacity>
      <TouchableOpacity
        style={[avatarStyles.avatarItem, selectedAvatar === 'princess' && avatarStyles.avatarItemSelected]}
        onPress={() => onAvatarChange('princess')}
        activeOpacity={0.3}
      >
        <Image
          source={require('../assets/images/avatar/princess-1.png')}
          resizeMode='contain'
          style={styles.avatarImage}
        />
      </TouchableOpacity>
    </View>
  );
}

const avatarStyles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: Spacing.md,
  },
  avatarItem: {
    width: '40%',
    alignItems: 'center',
    paddingVertical: Spacing.md, 
    borderRadius: Radius.card,
    borderWidth: 2,
    borderColor: Colors.outline_variant,
    backgroundColor: Colors.surface_container_lowest,
    opacity: 0.5
  },
  avatarItemSelected: {
    borderColor: Colors.primary,
    opacity: 1
  },
  avatarEmoji: {
    fontSize: 52,
    marginBottom: Spacing.xs,
  },
  avatarLabel: {
    ...Typography.labelMedium,
    color: Colors.on_surface_variant,
  },
  avatarLabelSelected: {
    color: Colors.on_primary_container,
    fontWeight: '900',
  },
});

// Main Screen

export default function ProfileCreateScreen() {
  const [username, setUsername] = useState('');
  const [avatarId, setAvatarId] = useState<AvatarId>('hero');
  const [ageString, setAgeString] = useState('10');
  const [usernameError, setUsernameError] = useState('');
  const [ageError, setAgeError] = useState('');
  const [creating, setCreating] = useState(false);

  // Food preferences state
  const [likeDislikeMap, setLikeDislikeMap] = useState<LikeDislikeMap>(createDefaultLikeDislikeMap);
  const [blacklistMap, setBlacklistMap] = useState<BlacklistMap>(createDefaultBlacklistMap);

  const validateUsername = (value: string): string => {
    if (!value.trim()) return 'Username is required.';
    if (value.length > 16) return 'Username must be 16 characters or fewer.';
    if (!/^[a-zA-Z0-9]+$/.test(value)) return 'Username must be alphanumeric only.';
    return '';
  };

  const validateAge = (value: number): string => {
    if (!Number.isInteger(value) || value < 1 || value > 99) {
      return 'Age must be between 1 and 99.';
    }
    return '';
  };

  const handleLikeDislikeChange = (item: FoodPreferenceItem, state: LikeDislikeState) => {
    setLikeDislikeMap((prev) => ({ ...prev, [item]: state }));
  };

  const handleBlacklistChange = (item: BlacklistItem, selected: boolean) => {
    setBlacklistMap((prev) => ({ ...prev, [item]: selected }));
  };

  const buildFoodPreferences = (): FoodPreferences => {
    const likes: FoodPreferenceItem[] = [];
    const dislikes: FoodPreferenceItem[] = [];
    for (const [item, state] of Object.entries(likeDislikeMap) as [FoodPreferenceItem, LikeDislikeState][]) {
      if (state === 'like') likes.push(item);
      else if (state === 'dislike') dislikes.push(item);
    }
    const blacklist: BlacklistItem[] = (Object.entries(blacklistMap) as [BlacklistItem, boolean][])
      .filter(([, selected]) => selected)
      .map(([item]) => item);
    return { likes, dislikes, blacklist };
  };

  const handleCreate = async () => {
    const uErr = validateUsername(username);
    const age = Number.parseInt(ageString);
    const aErr = validateAge(age);
    setUsernameError(uErr);
    setAgeError(aErr);

    if (uErr || aErr) return;

    setCreating(true);
    try {
      const foodPreferences = buildFoodPreferences();
      await createUserProfile(username.trim(), avatarId, age, foodPreferences);
      router.replace('/scan');
    } catch {
      Alert.alert('Error', 'Could not create profile. Please try again.');
    } finally {
      setCreating(false);
    }
  };

  const handleSkip = () => {
    router.replace('/scan');
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.emoji}>🌟</Text>
          <Text style={styles.title}>Create Your Hero!</Text>
          <Text style={styles.subtitle}>
            Set up your profile to track your progress and earn rewards.
          </Text>
        </View>

        {/* Username */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Hero Name</Text>
          <TextInput
            style={[styles.textInput, usernameError ? styles.textInputError : null]}
            placeholder="Enter your name..."
            placeholderTextColor={Colors.on_surface_variant}
            value={username}
            onChangeText={(text) => {
              setUsername(text);
              if (usernameError) setUsernameError(validateUsername(text));
            }}
            maxLength={16}
            autoCapitalize="none"
            autoCorrect={false}
          />
          {!!usernameError && <Text style={styles.errorText}>{usernameError}</Text>}
          <Text style={styles.hintText}>Max 16 characters, letters and numbers only.</Text>
        </View>

        {/* Avatar */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Choose Your Avatar</Text>
          <AvatarCarousel selectedAvatar={avatarId} onAvatarChange={setAvatarId} />
        </View>

        {/* Age */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Your Age</Text>
          <TextInput
            style={[styles.textInput, ageError ? styles.textInputError : null]}
            placeholder="Enter your age..."
            placeholderTextColor={Colors.on_surface_variant}
            value={ageString}
            keyboardType='number-pad'
            onChangeText={(ageString) => {
              setAgeString(ageString);
            }}
            maxLength={2}
            autoCapitalize="none"
            autoCorrect={false}
          />
          {!!ageError && <Text style={styles.errorText}>{ageError}</Text>}
        </View>

        {/* Food Preferences */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Food Preferences</Text>
          <Text style={styles.hintText}>
            Tell us what you like, dislike, and what you cannot eat. You can always skip this.
          </Text>
          <View style={styles.preferencesContainer}>
            <FoodPreferencesSelector
              likeDislikeMap={likeDislikeMap}
              blacklistMap={blacklistMap}
              onLikeDislikeChange={handleLikeDislikeChange}
              onBlacklistChange={handleBlacklistChange}
            />
          </View>
        </View>

        {/* Create Button */}
        <TouchableOpacity
          style={[styles.createButton, creating && styles.createButtonDisabled]}
          onPress={handleCreate}
          activeOpacity={0.85}
          disabled={creating}
        >
          <Text style={styles.createButtonText}>
            {creating ? 'Creating...' : '✨ Create Profile'}
          </Text>
        </TouchableOpacity>

        {/* Skip */}
        <TouchableOpacity style={styles.skipButton} onPress={handleSkip} activeOpacity={0.7}>
          <Text style={styles.skipButtonText}>Skip for now</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: Colors.surface,
  },
  container: {
    paddingHorizontal: Spacing.lg,
    paddingTop: Spacing['2xl'],
    paddingBottom: Spacing['4xl'],
    gap: Spacing['2xl'],
  },
  header: {
    alignItems: 'center',
    gap: Spacing.sm,
  },
  emoji: {
    fontSize: 64,
  },
  title: {
    ...Typography.displaySmall,
    color: Colors.primary,
    textAlign: 'center',
  },
  subtitle: {
    ...Typography.bodyMedium,
    color: Colors.on_surface_variant,
    textAlign: 'center',
    maxWidth: 280,
  },
  section: {
    gap: Spacing.sm,
  },
  sectionLabel: {
    ...Typography.titleMedium,
    color: Colors.on_surface,
  },
  textInput: {
    backgroundColor: Colors.surface_container_lowest,
    borderRadius: Radius.input,
    borderWidth: 1.5,
    borderColor: Colors.outline_variant,
    paddingHorizontal: Spacing.base,
    paddingVertical: Spacing.md,
    ...Typography.bodyLarge,
    color: Colors.on_surface,
  },
  textInputError: {
    borderColor: Colors.error,
  },
  errorText: {
    ...Typography.labelSmall,
    color: Colors.error,
  },
  hintText: {
    ...Typography.labelSmall,
    color: Colors.on_surface_variant,
  },
  avatarImage: {
    width: '100%',
    height: 150
  },
  preferencesContainer: {
    backgroundColor: Colors.surface_container_low,
    borderRadius: Radius.card,
    padding: Spacing.base,
    marginTop: Spacing.xs,
  },
  createButton: {
    backgroundColor: Colors.primary,
    borderRadius: Radius.button_primary,
    paddingVertical: Spacing.base,
    alignItems: 'center',
    marginTop: Spacing.md,
  },
  createButtonDisabled: {
    opacity: 0.6,
  },
  createButtonText: {
    ...Typography.labelLarge,
    color: Colors.on_primary,
    fontSize: 18,
  },
  skipButton: {
    alignItems: 'center',
    paddingVertical: Spacing.sm,
  },
  skipButtonText: {
    ...Typography.bodyMedium,
    color: Colors.on_surface_variant,
    textDecorationLine: 'underline',
  },
});
