import { router, useLocalSearchParams } from 'expo-router';
import * as Speech from 'expo-speech';
import { ArrowLeft, Pause, Play } from 'lucide-react-native';
import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { getStoryText } from '@/services/stories';

export default function StoryOutcomeScreen() {
  const { storyId } = useLocalSearchParams<{ storyId?: string }>();

  const [outcome, setOutcome] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);

  useEffect(() => {
    const loadOutcome = async () => {
      if (!storyId) {
        setLoadFailed(true);
        setLoading(false);
        return;
      }

      setLoading(true);
      setLoadFailed(false);

      try {
        const storyTextData = await getStoryText(storyId);
        setOutcome(storyTextData.outcome);
      } catch (error) {
        console.error('Failed to load story outcome:', error);
        setLoadFailed(true);
      } finally {
        setLoading(false);
      }
    };

    loadOutcome();

    return () => {
      Speech.stop();
    };
  }, [storyId]);

  const handleToggleReadOutcome = () => {
    if (!outcome) {
      Alert.alert('Audio unavailable', 'Audio is unavailable at the moment.');
      return;
    }

    if (isSpeaking) {
      Speech.stop();
      setIsSpeaking(false);
      return;
    }

    if (!outcome.trim()) {
      Alert.alert('Audio unavailable', 'Audio is unavailable at the moment.');
      return;
    }

    try {
      Speech.speak(outcome, {
        language: 'en-US',
        rate: 0.9,
        pitch: 1.0,
        onStart: () => setIsSpeaking(true),
        onDone: () => setIsSpeaking(false),
        onStopped: () => setIsSpeaking(false),
        onError: () => {
          setIsSpeaking(false);
          Alert.alert('Audio unavailable', 'Audio is unavailable at the moment.');
        },
      });
    } catch {
      setIsSpeaking(false);
      Alert.alert('Audio unavailable', 'Audio is unavailable at the moment.');
    }
  };

  const handleGoHome = () => {
    Speech.stop();
    setIsSpeaking(false);
    router.replace('/stories');
  };

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#E77A1F" />
        <Text style={styles.feedbackTitle}>Loading outcome...</Text>
        <Text style={styles.feedbackText}>
          Please wait while we prepare the story outcome.
        </Text>
      </View>
    );
  }

  if (loadFailed || !outcome) {
    return (
      <View style={styles.centered}>
        <Text style={styles.feedbackTitle}>Oops! Let&apos;s try again!</Text>
        <Text style={styles.feedbackText}>
          We could not show the story outcome right now.
        </Text>

        <TouchableOpacity style={styles.primaryAction} onPress={() => router.replace('/stories')}>
          <Text style={styles.primaryActionText}>Go Home</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.screen}>
      <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
        <ArrowLeft size={20} color="#B45309" />
      </TouchableOpacity>

      <View style={styles.card}>
        <View style={styles.content}>
          <View style={styles.titleBubble}>
            <Text style={styles.titleText}>Story Outcome</Text>
          </View>

          <Text style={styles.outcomeText}>{outcome}</Text>

          <TouchableOpacity
            style={[styles.primaryButton, { backgroundColor: '#E77A1F' }]}
            onPress={handleToggleReadOutcome}
          >
            {isSpeaking ? (
              <View style={styles.buttonContent}>
                <Pause size={18} color="#FFFFFF" />
                <Text style={styles.primaryButtonText}>Pause Reading</Text>
              </View>
            ) : (
              <View style={styles.buttonContent}>
                <Play size={18} color="#FFFFFF" />
                <Text style={styles.primaryButtonText}>Read This To Me</Text>
              </View>
            )}
          </TouchableOpacity>

          <TouchableOpacity style={styles.secondaryButton} onPress={handleGoHome}>
            <Text style={styles.secondaryButtonText}>Go Home</Text>
          </TouchableOpacity>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: '#F8F5E9',
    justifyContent: 'center',
    paddingHorizontal: 18,
  },
  backButton: {
    position: 'absolute',
    top: 58,
    left: 18,
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: '#FFFFFF',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 2,
    shadowColor: '#000',
    shadowOpacity: 0.08,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 3 },
    elevation: 4,
  },
  card: {
    backgroundColor: '#FFF8E8',
    borderRadius: 32,
    padding: 16,
    shadowColor: '#000',
    shadowOpacity: 0.08,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
    elevation: 5,
  },
  content: {
    alignItems: 'center',
  },
  titleBubble: {
    backgroundColor: '#FFFFFF',
    borderRadius: 22,
    paddingHorizontal: 18,
    paddingVertical: 14,
    marginBottom: 14,
    borderWidth: 2,
    borderColor: '#F1E3C8',
    alignSelf: 'stretch',
  },
  titleText: {
    fontSize: 24,
    fontWeight: '900',
    color: '#2D241F',
    textAlign: 'center',
    lineHeight: 30,
  },
  outcomeText: {
    fontSize: 17,
    lineHeight: 26,
    color: '#5F5148',
    textAlign: 'center',
    marginBottom: 20,
    paddingHorizontal: 6,
    fontWeight: '600',
  },
  primaryButton: {
    alignSelf: 'stretch',
    borderRadius: 999,
    paddingVertical: 16,
    alignItems: 'center',
    marginBottom: 10,
  },
  buttonContent: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  primaryButtonText: {
    color: '#FFFFFF',
    fontSize: 17,
    fontWeight: '900',
  },
  secondaryButton: {
    alignSelf: 'stretch',
    borderRadius: 999,
    paddingVertical: 14,
    alignItems: 'center',
    backgroundColor: '#FFF3E3',
    borderWidth: 2,
    borderColor: '#F1E3C8',
  },
  secondaryButtonText: {
    color: '#B45309',
    fontSize: 16,
    fontWeight: '900',
  },
  centered: {
    flex: 1,
    backgroundColor: '#F8F5E9',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  feedbackTitle: {
    fontSize: 24,
    fontWeight: '900',
    color: '#2D241F',
    marginTop: 14,
    marginBottom: 8,
    textAlign: 'center',
  },
  feedbackText: {
    fontSize: 16,
    color: '#6C5B4F',
    textAlign: 'center',
    lineHeight: 24,
    marginBottom: 20,
  },
  primaryAction: {
    backgroundColor: '#E77A1F',
    borderRadius: 999,
    paddingHorizontal: 24,
    paddingVertical: 14,
  },
  primaryActionText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '900',
  },
});
