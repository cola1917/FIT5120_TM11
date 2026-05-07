import { router, useLocalSearchParams } from 'expo-router';
import { ArrowLeft, CheckCircle, Pause, Play, Star } from 'lucide-react-native';
import React, { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Animated,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { getAuthHeaders, getStoryOutcomeAudioUrl, getStoryText } from '@/services/stories';
import { claimStoryPoints, hasClaimedStoryPoints, hasUserProfile } from '@/services/userProfile';
import { Audio } from 'expo-av';

const STORY_POINTS = 10;

export default function StoryOutcomeScreen() {
  const { storyId } = useLocalSearchParams<{ storyId: string }>();

  const [outcome, setOutcome] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);
  const [authHeaders, setAuthHeaders] = useState<{ Authorization: string } | null>(null);
  const [audioState, setAudioState] = useState<'playing'| 'idle' | 'error'>('idle');
  const [profileExists, setProfileExists] = useState(false);
  const [alreadyClaimed, setAlreadyClaimed] = useState(false);
  const [claiming, setClaiming] = useState(false);

  // Animation values for the claim points celebration
  const floatAnim = useRef(new Animated.Value(0)).current;
  const floatOpacity = useRef(new Animated.Value(0)).current;
  const buttonScale = useRef(new Animated.Value(1)).current;

  const soundRef = useRef<Audio.Sound | null>(null);

  const loadAuthHeaders = async () => {
    try {
      const headers = await getAuthHeaders();
      setAuthHeaders(headers);
    } catch (err) {
      console.error(err);
    }
  };
  
  const setupAudio = async () => {
    try {
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: false,
        playsInSilentModeIOS: true,
        staysActiveInBackground: false,
      });
    } catch (err) {
      console.error('Failed to setup audio:', err);
    }
  };

  const cleanupAudio = async () => {
    try {
      if (soundRef.current) {
        await soundRef.current.stopAsync();
        await soundRef.current.unloadAsync();
        soundRef.current = null;
      }
      setAudioState('idle');
    } catch (err) {
      console.error('Failed to cleanup audio:', err);
    }
  };

  const playAudioForPage = async () => {
    try {
      // Stop any currently playing audio
      await cleanupAudio();

      const audioUrl = getStoryOutcomeAudioUrl(storyId);
      
      // Create and load the sound
      const { sound } = await Audio.Sound.createAsync(
        {
          uri: audioUrl,
          headers: authHeaders || undefined,
        },
        { shouldPlay: true }
      );

      soundRef.current = sound;
      setAudioState('playing');

      // Set up callback for when audio finishes
      sound.setOnPlaybackStatusUpdate((status) => {
        if (status.isLoaded && status.didJustFinish) {
          setAudioState('idle');
        }
      });
    } catch (err) {
      console.error('Failed to play audio:', err);
      setAudioState('error');
    }
  }

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
        const [storyTextData, claimed, profileFound] = await Promise.all([
          getStoryText(storyId),
          hasClaimedStoryPoints(storyId),
          hasUserProfile(),
        ]);
        setOutcome(storyTextData.outcome);
        setAlreadyClaimed(claimed);
        setProfileExists(profileFound);
      } catch (error) {
        console.error('Failed to load story outcome:', error);
        setLoadFailed(true);
      } finally {
        setLoading(false);
      }
    };
    loadAuthHeaders();
    loadOutcome();
    setupAudio();

    return () => {
      cleanupAudio();
    };
  }, [storyId]);

  const handleToggleReadOutcome = async () => {
    if (!outcome) {
      Alert.alert('Audio unavailable', 'Audio is unavailable at the moment.');
      return;
    }

    if (audioState === 'idle' || audioState === 'error') {
      await playAudioForPage();
    } else if (audioState === 'playing') {
      await cleanupAudio();
    }

    if (!outcome.trim()) {
      Alert.alert('Audio unavailable', 'Audio is unavailable at the moment.');
      return;
    }
  };

  const runClaimAnimation = () => {
    // Reset animation values
    floatAnim.setValue(0);
    floatOpacity.setValue(1);
    buttonScale.setValue(1);

    Animated.parallel([
      // Float the "+10 ⭐" label upward and fade it out
      Animated.timing(floatAnim, {
        toValue: -80,
        duration: 1000,
        useNativeDriver: true,
      }),
      Animated.sequence([
        Animated.delay(400),
        Animated.timing(floatOpacity, {
          toValue: 0,
          duration: 600,
          useNativeDriver: true,
        }),
      ]),
      // Pulse the button: scale up then back to normal
      Animated.sequence([
        Animated.spring(buttonScale, {
          toValue: 1.12,
          useNativeDriver: true,
          speed: 30,
          bounciness: 10,
        }),
        Animated.spring(buttonScale, {
          toValue: 1,
          useNativeDriver: true,
          speed: 20,
          bounciness: 6,
        }),
      ]),
    ]).start();
  };

  const handleClaimPoints = async () => {
    if (claiming || alreadyClaimed) return;

    setClaiming(true);
    try {
      const awarded = await claimStoryPoints(storyId, STORY_POINTS);
      if (awarded) {
        runClaimAnimation();
        // Delay flipping the UI state so the animation plays first
        setTimeout(() => {
          setAlreadyClaimed(true);
          setClaiming(false);
        }, 900);
      } else {
        // Already claimed (race condition guard)
        setAlreadyClaimed(true);
        setClaiming(false);
      }
    } catch (err) {
      console.error('Failed to claim story points:', err);
      setClaiming(false);
    }
  };

  const handleGoHome = () => {
    cleanupAudio();
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
            {audioState === 'playing' ? (
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

          {/* Claim points section — only shown when a user profile exists */}
          {profileExists && (
            <View style={styles.claimContainer}>
              {alreadyClaimed ? (
                <View style={styles.claimedBadge}>
                  <CheckCircle size={18} color="#2F9E44" />
                  <Text style={styles.claimedText}>Points Already Claimed!</Text>
                </View>
              ) : (
                <View style={styles.claimWrapper}>
                  {/* Floating "+10 ⭐" animation label */}
                  <Animated.View
                    style={[
                      styles.floatingPoints,
                      {
                        transform: [{ translateY: floatAnim }],
                        opacity: floatOpacity,
                      },
                    ]}
                    pointerEvents="none"
                  >
                    <Text style={styles.floatingPointsText}>+{STORY_POINTS} ⭐</Text>
                  </Animated.View>

                  <Animated.View style={{ transform: [{ scale: buttonScale }], alignSelf: 'stretch' }}>
                    <TouchableOpacity
                      style={[styles.claimButton, claiming && styles.claimButtonDisabled]}
                      onPress={handleClaimPoints}
                      disabled={claiming}
                      activeOpacity={0.85}
                    >
                      <View style={styles.buttonContent}>
                        <Star size={18} color="#FFFFFF" fill="#FFFFFF" />
                        <Text style={styles.claimButtonText}>
                          {claiming ? 'Claiming...' : `Claim ${STORY_POINTS} Points`}
                        </Text>
                      </View>
                    </TouchableOpacity>
                  </Animated.View>
                </View>
              )}
            </View>
          )}

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
  // ─── Claim Points ───────────────────────────────────────────────────────────
  claimContainer: {
    alignSelf: 'stretch',
    marginBottom: 10,
  },
  claimWrapper: {
    alignItems: 'center',
    position: 'relative',
  },
  floatingPoints: {
    position: 'absolute',
    top: 0,
    zIndex: 10,
    backgroundColor: '#FFF3CD',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderWidth: 2,
    borderColor: '#F5C842',
    shadowColor: '#000',
    shadowOpacity: 0.12,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
    elevation: 4,
  },
  floatingPointsText: {
    fontSize: 20,
    fontWeight: '900',
    color: '#B45309',
  },
  claimButton: {
    alignSelf: 'stretch',
    backgroundColor: '#2F9E44',
    borderRadius: 999,
    paddingVertical: 16,
    alignItems: 'center',
  },
  claimButtonDisabled: {
    opacity: 0.6,
  },
  claimButtonText: {
    color: '#FFFFFF',
    fontSize: 17,
    fontWeight: '900',
  },
  claimedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: '#EBFBEE',
    borderRadius: 999,
    paddingVertical: 14,
    paddingHorizontal: 20,
    borderWidth: 2,
    borderColor: '#B2F2BB',
  },
  claimedText: {
    color: '#2F9E44',
    fontSize: 16,
    fontWeight: '900',
  },
  // ─── Secondary button ───────────────────────────────────────────────────────
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
  // ─── Feedback states ────────────────────────────────────────────────────────
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
