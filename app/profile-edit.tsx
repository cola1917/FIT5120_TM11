/**
 * Profile Edit Screen
 *
 * Allows the user to edit their username and age.
 * Loads the current profile, pre-populates the fields, and saves on confirm.
 */

import React, { useCallback, useState } from 'react';
import {
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router, useFocusEffect } from 'expo-router';
import { Colors } from '@/constants/colors';
import { Typography } from '@/constants/fonts';
import { Spacing } from '@/constants/spacing';
import { Radius } from '@/constants/radius';
import { getUserProfile, saveUserProfile } from '@/services/userProfile';

export default function ProfileEditScreen() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [username, setUsername] = useState('');
  const [ageString, setAgeString] = useState('');
  const [usernameError, setUsernameError] = useState('');
  const [ageError, setAgeError] = useState('');

  const loadProfile = useCallback(async () => {
    setLoading(true);
    try {
      const profile = await getUserProfile();
      if (profile) {
        setUsername(profile.username);
        setAgeString(String(profile.age));
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      loadProfile();
    }, [loadProfile])
  );

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

  const handleSave = async () => {
    const uErr = validateUsername(username);
    const age = Number.parseInt(ageString);
    const aErr = validateAge(age);
    setUsernameError(uErr);
    setAgeError(aErr);

    if (uErr || aErr) return;

    setSaving(true);
    try {
      const profile = await getUserProfile();
      if (!profile) {
        Alert.alert('Error', 'No profile found. Please create a profile first.');
        return;
      }
      profile.username = username.trim();
      profile.age = age;
      await saveUserProfile(profile);
      router.back();
    } catch {
      Alert.alert('Error', 'Could not save profile. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleBack = () => {
    router.back();
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={Colors.primary} />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        {/* Header row */}
        <TouchableOpacity style={styles.backButton} onPress={handleBack}>
          <Text style={styles.backButtonText}>← Back</Text>
        </TouchableOpacity>

        {/* Title */}
        <View style={styles.titleSection}>
          <Text style={styles.titleEmoji}>✏️</Text>
          <Text style={styles.title}>Edit Profile</Text>
          <Text style={styles.subtitle}>Update your hero name and age.</Text>
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

        {/* Age */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Your Age</Text>
          <TextInput
            style={[styles.textInput, ageError ? styles.textInputError : null]}
            placeholder="Enter your age..."
            placeholderTextColor={Colors.on_surface_variant}
            value={ageString}
            keyboardType="number-pad"
            onChangeText={(text) => {
              setAgeString(text);
              if (ageError) {
                const parsed = Number.parseInt(text);
                setAgeError(validateAge(parsed));
              }
            }}
            maxLength={2}
            autoCapitalize="none"
            autoCorrect={false}
          />
          {!!ageError && <Text style={styles.errorText}>{ageError}</Text>}
          <Text style={styles.hintText}>Must be between 1 and 99.</Text>
        </View>

        {/* Save Button */}
        <TouchableOpacity
          style={[styles.saveButton, saving && styles.saveButtonDisabled]}
          onPress={handleSave}
          activeOpacity={0.85}
          disabled={saving}
        >
          <Text style={styles.saveButtonText}>
            {saving ? 'Saving...' : '💾 Save Changes'}
          </Text>
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
    paddingTop: Spacing.base,
    paddingBottom: Spacing['4xl'],
    gap: Spacing['2xl'],
  },
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  backButton: {
    alignSelf: 'flex-start',
    paddingVertical: Spacing.xs,
    paddingHorizontal: Spacing.sm,
  },
  backButtonText: {
    ...Typography.bodyLarge,
    color: Colors.primary,
    fontWeight: '700',
  },
  titleSection: {
    alignItems: 'center',
    gap: Spacing.sm,
  },
  titleEmoji: {
    fontSize: 56,
  },
  title: {
    ...Typography.headlineMedium,
    color: Colors.on_surface,
    fontWeight: '900',
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
  saveButton: {
    backgroundColor: Colors.primary,
    borderRadius: Radius.button_primary,
    paddingVertical: Spacing.base,
    alignItems: 'center',
    marginTop: Spacing.md,
  },
  saveButtonDisabled: {
    opacity: 0.6,
  },
  saveButtonText: {
    ...Typography.labelLarge,
    color: Colors.on_primary,
    fontSize: 18,
  },
});
