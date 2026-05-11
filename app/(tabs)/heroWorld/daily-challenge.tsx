import AppHeader from "@/components/app_header";
import { Colors } from "@/constants/colors";
import { Typography } from "@/constants/fonts";
import { Radius } from "@/constants/radius";
import { Spacing } from "@/constants/spacing";
import { completeDailyChallenge, getNextDailyChallenge, isDailyChallengeCompletedToday, markDailyChallengeCompletedToday, type DailyChallengeTask } from "@/services/dailyChallenge";
import { addTotalPoints, hasUserProfile } from "@/services/userProfile";
import { useRouter } from "expo-router";
import { Check, CheckCircle, ChevronRight, X } from "lucide-react-native";
import React, { useEffect, useRef, useState } from "react";
import {
  Alert,
  Animated,
  Image,
  Modal,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

// Map task names to images
const TASK_IMAGES: Record<string, any> = {
  "Strong Bone Milk": require("../../../assets/images/strong_Bone_Milk.png"),
  "Power Up Water": require("../../../assets/images/power_Up_Water.png"),
  "Immune Shield Fruit": require("../../../assets/images/immune_shield_fruit.png"),
  "Happy Tummy Veggies": require("../../../assets/images/happy_tummy_veggies.png"),
  "Sparkling White Teeth": require("../../../assets/images/sparkling_white_teeth.png"),
  "Brain Battery Breakfast": require("../../../assets/images/brain_battery_breakfast.png"),
  "Light Body, No Junk": require("../../../assets/images/light_body,_no_junk.png"),
  "Eat Meat and Eggs": require("../../../assets/images/eat_meat_and_eggs.png"),
  "Long-Lasting Grains": require("../../../assets/images/long-lasting_grains.png"),
  "Eat Fish for Brain": require("../../../assets/images/eat_fish_for_brain.png"),
  "Slow Chew, Happy Tummy": require("../../../assets/images/slow_chew,_happy_tummy.png"),
  "Rainbow Plate Hero": require("../../../assets/images/rainbow_plate_hero.png"),
  "Strong Heart, No Fry": require("../../../assets/images/strong_heart,_no_fry.png"),
  "Super Strength Greens": require("../../../assets/images/super_strength_greens.png"),
  "Smart Brain Nuts": require("../../../assets/images/smart_brain_nuts.png"),
  "Early Rest, Sweet Dreams": require("../../../assets/images/early_rest,_sweet_dreams.png"),
};

const DEFAULT_IMAGE = require("../../../assets/images/nutriheroes_icon.png");
const DAILY_CHALLENGE_EXP = 50;

export default function DailyChallengeScreen() {
  const router = useRouter();
  const [challenge, setChallenge] = useState<DailyChallengeTask | null>(null);
  const [loading, setLoading] = useState(true);
  const [showFeedbackModal, setShowFeedbackModal] = useState(false);
  const [feedbackMessage, setFeedbackMessage] = useState("");
  const [completedTaskName, setCompletedTaskName] = useState("");
  const [alreadyCompletedToday, setAlreadyCompletedToday] = useState(false);
  const [profileExists, setProfileExists] = useState(false);
  const [pointsAwarded, setPointsAwarded] = useState(false);

  // Animation refs — matching story-outcome.tsx style
  const floatAnim = useRef(new Animated.Value(0)).current;
  const floatOpacity = useRef(new Animated.Value(0)).current;
  const badgeScale = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    loadChallenge();
  }, []);

  // Trigger the points animation when the modal opens and points were awarded
  useEffect(() => {
    if (!showFeedbackModal || !pointsAwarded) return;

    floatAnim.setValue(0);
    floatOpacity.setValue(1);
    badgeScale.setValue(1);

    Animated.parallel([
      // Float "+50 ⭐" upward and fade out
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
      // Pulse the awarded badge
      Animated.sequence([
        Animated.spring(badgeScale, {
          toValue: 1.12,
          useNativeDriver: true,
          speed: 30,
          bounciness: 10,
        }),
        Animated.spring(badgeScale, {
          toValue: 1,
          useNativeDriver: true,
          speed: 20,
          bounciness: 6,
        }),
      ]),
    ]).start();
  }, [showFeedbackModal, pointsAwarded, floatAnim, floatOpacity, badgeScale]);

  const loadChallenge = async () => {
    try {
      setLoading(true);
      // Check if already completed today and whether a profile exists
      const [completedToday, profileFound] = await Promise.all([
        isDailyChallengeCompletedToday(),
        hasUserProfile(),
      ]);
      setAlreadyCompletedToday(completedToday);
      setProfileExists(profileFound);

      if (!completedToday) {
        const data = await getNextDailyChallenge();
        setChallenge(data);
      }
    } catch (error: any) {
      console.error("Failed to load daily challenge:", error);
      Alert.alert("Error", "Failed to load daily challenge. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleComplete = async () => {
    if (!challenge) return;

    try {
      const response = await completeDailyChallenge(challenge.id);
      setFeedbackMessage(response.feedback);
      setCompletedTaskName(response.task_name);

      // Award EXP to the user profile if one exists
      let awarded = false;
      if (profileExists) {
        await addTotalPoints(DAILY_CHALLENGE_EXP);
        awarded = true;
      }
      setPointsAwarded(awarded);

      // Mark the challenge as completed for today
      await markDailyChallengeCompletedToday();

      setShowFeedbackModal(true);
    } catch (error: any) {
      console.error("Failed to complete challenge:", error);
      Alert.alert("Error", "Failed to complete challenge. Please try again.");
    }
  };

  const handleSkip = () => {
    // Load a new challenge excluding the current one
    if (challenge) {
      loadChallengeWithExclude(challenge.id);
    }
  };

  const loadChallengeWithExclude = async (excludeId: number) => {
    try {
      setLoading(true);
      const data = await getNextDailyChallenge(excludeId);
      setChallenge(data);
    } catch (error: any) {
      console.error("Failed to load next challenge:", error);
      Alert.alert("Error", "Failed to load next challenge. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleCloseFeedback = () => {
    setShowFeedbackModal(false);
    router.push('/(tabs)/heroWorld' as any);
  };

  const getImageForTask = (taskName: string) => {
    return TASK_IMAGES[taskName] || DEFAULT_IMAGE;
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.safeArea}>
        <ScrollView contentContainerStyle={styles.container}>
          <AppHeader />
          <View style={styles.loadingContainer}>
            <Text style={styles.loadingText}>Loading your daily challenge...</Text>
          </View>
        </ScrollView>
      </SafeAreaView>
    );
  }

  // Show completed today screen if already completed
  if (alreadyCompletedToday) {
    return (
      <SafeAreaView style={styles.safeArea}>
        <ScrollView contentContainerStyle={styles.container}>
          <AppHeader />
          <View style={styles.completedContainer}>
            <View style={styles.completedCard}>
              <Text style={styles.completedEmoji}>🌟</Text>
              <Text style={styles.completedTitle}>{"Wow, you're amazing!"}</Text>
              <Text style={styles.completedMessage}>
                {"You've finished today's challenge!"}
              </Text>
              <Text style={styles.completedSubMessage}>
                🎉 Come back tomorrow for a brand new adventure!
              </Text>
              <TouchableOpacity 
                style={styles.backButton} 
                onPress={() => router.push('/(tabs)/heroWorld' as any)}
              >
                <Text style={styles.backButtonText}>Back to Hero World</Text>
              </TouchableOpacity>
            </View>
          </View>
        </ScrollView>
      </SafeAreaView>
    );
  }

  if (!challenge) {
    return (
      <SafeAreaView style={styles.safeArea}>
        <ScrollView contentContainerStyle={styles.container}>
          <AppHeader />
          <View style={styles.loadingContainer}>
            <Text style={styles.loadingText}>No challenges available</Text>
            <TouchableOpacity style={styles.retryButton} onPress={loadChallenge}>
              <Text style={styles.retryButtonText}>Try Again</Text>
            </TouchableOpacity>
          </View>
        </ScrollView>
      </SafeAreaView>
    );
  }

  const taskImage = getImageForTask(challenge.task_name);

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.container}>
        <AppHeader />

        <View style={styles.headerContainer}>
          <Text style={styles.headerEmoji}>🥦</Text>
          <Text style={styles.headerTitle}>DAILY CHALLENGE</Text>
        </View>

        <View style={styles.challengeCard}>
          <View style={styles.imageContainer}>
            <Image source={taskImage} style={styles.challengeImage} resizeMode="cover" />
          </View>

          <View style={styles.contentContainer}>
            <Text style={styles.taskName}>{challenge.task_name}</Text>
            <View style={styles.tipsContainer}>
              <Text style={styles.tipsLabel}>💡 YOUR MISSION:</Text>
              <Text style={styles.tipsText}>{challenge.tips}</Text>
            </View>
          </View>

          <View style={styles.buttonRow}>
            <TouchableOpacity style={[styles.actionButton, styles.skipButton]} onPress={handleSkip}>
              <X color={Colors.on_surface} size={24} />
              <Text style={[styles.actionButtonText, styles.skipButtonText]}>Try Another</Text>
            </TouchableOpacity>

            <TouchableOpacity style={[styles.actionButton, styles.completeButton]} onPress={handleComplete}>
              <Check color={Colors.on_primary} size={24} />
              <Text style={[styles.actionButtonText, styles.completeButtonText]}>Complete!</Text>
            </TouchableOpacity>
          </View>
        </View>

        <View style={styles.infoCard}>
          <Text style={styles.infoTitle}>🌟 Why This Matters</Text>
          <Text style={styles.infoText}>
            Small healthy habits every day add up to big results! Keep completing daily challenges
            to become a true NutriHero!
          </Text>
        </View>
      </ScrollView>

      {/* Feedback Modal */}
      <Modal
        visible={showFeedbackModal}
        transparent={true}
        animationType="fade"
        onRequestClose={handleCloseFeedback}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalEmoji}>🎉</Text>
              <Text style={styles.modalTitle}>CHALLENGE COMPLETE!</Text>
            </View>

            <View style={styles.modalBody}>
              <Text style={styles.modalTaskName}>{completedTaskName}</Text>
              <View style={styles.feedbackBubble}>
                <Text style={styles.feedbackText}>{feedbackMessage}</Text>
              </View>

              {/* EXP award section — only shown when a profile exists */}
              {profileExists && (
                <View style={styles.expContainer}>
                  {pointsAwarded ? (
                    <View style={styles.expWrapper}>
                      {/* Floating "+50 ⭐" animation label */}
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
                        <Text style={styles.floatingPointsText}>+{DAILY_CHALLENGE_EXP} ⭐</Text>
                      </Animated.View>

                      {/* Awarded badge with spring pulse */}
                      <Animated.View style={{ transform: [{ scale: badgeScale }], alignSelf: 'stretch' }}>
                        <View style={styles.awardedBadge}>
                          <CheckCircle size={18} color="#2F9E44" />
                          <Text style={styles.awardedText}>+{DAILY_CHALLENGE_EXP} EXP added!</Text>
                        </View>
                      </Animated.View>
                    </View>
                  ) : null}
                </View>
              )}
            </View>

            <TouchableOpacity style={styles.modalButton} onPress={handleCloseFeedback}>
              <Text style={styles.modalButtonText}>AWESOME!</Text>
              <ChevronRight color={Colors.on_primary} size={24} />
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
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
    paddingTop: Spacing.sm,
    flexGrow: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingTop: 100,
  },
  loadingText: {
    ...Typography.bodyLarge,
    color: Colors.on_surface_variant,
  },
  retryButton: {
    marginTop: Spacing.md,
    backgroundColor: Colors.primary,
    paddingHorizontal: Spacing.xl,
    paddingVertical: Spacing.sm,
    borderRadius: Radius.full,
  },
  retryButtonText: {
    ...Typography.labelLarge,
    color: Colors.on_primary,
    fontWeight: "bold",
  },
  headerContainer: {
    alignItems: "center",
    marginVertical: Spacing.md,
  },
  headerEmoji: {
    fontSize: 48,
    marginBottom: Spacing.xs,
  },
  headerTitle: {
    ...Typography.headlineMedium,
    color: Colors.primary,
    fontWeight: "900",
  },
  challengeCard: {
    backgroundColor: Colors.on_primary,
    borderRadius: Radius.card,
    overflow: "hidden",
    shadowColor: Colors.shadow,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 12,
    elevation: 4,
    marginBottom: Spacing.lg,
  },
  imageContainer: {
    width: "100%",
    height: 200,
    backgroundColor: Colors.surface_container_low,
  },
  challengeImage: {
    width: "100%",
    height: "100%",
  },
  contentContainer: {
    padding: Spacing.lg,
  },
  taskName: {
    ...Typography.headlineSmall,
    color: Colors.on_surface,
    fontWeight: "900",
    marginBottom: Spacing.md,
    textAlign: "center",
  },
  tipsContainer: {
    backgroundColor: Colors.primary_container,
    borderRadius: Radius.md,
    padding: Spacing.md,
    alignItems: "center",
  },
  tipsLabel: {
    ...Typography.labelLarge,
    color: Colors.primary_dim,
    fontWeight: "900",
    marginBottom: Spacing.xs,
  },
  tipsText: {
    ...Typography.bodyLarge,
    color: Colors.on_surface,
    textAlign: "center",
  },
  buttonRow: {
    flexDirection: "row",
    padding: Spacing.lg,
    paddingTop: 0,
    gap: Spacing.md,
  },
  actionButton: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: Spacing.md,
    borderRadius: Radius.full,
    gap: Spacing.sm,
  },
  skipButton: {
    backgroundColor: Colors.surface_container_high,
  },
  skipButtonText: {
    color: Colors.on_surface,
  },
  completeButton: {
    backgroundColor: Colors.primary,
  },
  completeButtonText: {
    color: Colors.on_primary,
  },
  actionButtonText: {
    ...Typography.labelLarge,
    fontWeight: "900",
  },
  infoCard: {
    backgroundColor: Colors.secondary_container,
    borderRadius: Radius.card,
    padding: Spacing.lg,
    marginBottom: Spacing.xl,
  },
  infoTitle: {
    ...Typography.titleMedium,
    color: Colors.on_secondary_container,
    fontWeight: "900",
    marginBottom: Spacing.sm,
  },
  infoText: {
    ...Typography.bodyMedium,
    color: Colors.on_secondary_container,
    lineHeight: 24,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0, 0, 0, 0.6)",
    justifyContent: "center",
    alignItems: "center",
    padding: Spacing.xl,
  },
  modalContent: {
    backgroundColor: Colors.on_primary,
    borderRadius: Radius.card,
    padding: Spacing.xl,
    width: "100%",
    maxWidth: 360,
    alignItems: "center",
  },
  modalHeader: {
    alignItems: "center",
    marginBottom: Spacing.lg,
  },
  modalEmoji: {
    fontSize: 64,
    marginBottom: Spacing.sm,
  },
  modalTitle: {
    ...Typography.headlineMedium,
    color: Colors.primary,
    fontWeight: "900",
    textAlign: "center",
  },
  modalBody: {
    alignItems: "center",
    marginBottom: Spacing.xl,
    width: "100%",
    gap: Spacing.md,
  },
  modalTaskName: {
    ...Typography.titleLarge,
    color: Colors.on_surface,
    fontWeight: "900",
    textAlign: "center",
  },
  feedbackBubble: {
    backgroundColor: Colors.primary_container,
    borderRadius: Radius.md,
    padding: Spacing.md,
    width: "100%",
  },
  feedbackText: {
    ...Typography.bodyLarge,
    color: Colors.on_surface,
    textAlign: "center",
    fontWeight: "600",
  },

  // ─── EXP award animation (matching story-outcome.tsx) ────────────────────────
  expContainer: {
    alignSelf: 'stretch',
  },
  expWrapper: {
    alignItems: 'center',
    position: 'relative',
    gap: Spacing.xs,
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
  awardedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: '#EBFBEE',
    borderRadius: Radius.full,
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderWidth: 2,
    borderColor: '#B2F2BB',
    alignSelf: 'stretch',
  },
  awardedText: {
    color: '#2F9E44',
    fontSize: 16,
    fontWeight: '900',
  },

  // ─── Modal button ─────────────────────────────────────────────────────────────
  modalButton: {
    backgroundColor: Colors.primary,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: Spacing.md,
    paddingHorizontal: Spacing.xl,
    borderRadius: Radius.full,
    gap: Spacing.sm,
    minWidth: 200,
  },
  modalButtonText: {
    ...Typography.labelLarge,
    color: Colors.on_primary,
    fontWeight: "900",
  },

  // ─── Already completed screen ─────────────────────────────────────────────────
  completedContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingTop: 50,
  },
  completedCard: {
    backgroundColor: Colors.on_primary,
    borderRadius: Radius.card,
    padding: Spacing.xl,
    alignItems: "center",
    shadowColor: Colors.shadow,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 12,
    elevation: 4,
    maxWidth: 360,
  },
  completedEmoji: {
    fontSize: 72,
    marginBottom: Spacing.md,
  },
  completedTitle: {
    ...Typography.headlineMedium,
    color: Colors.primary,
    fontWeight: "900",
    textAlign: "center",
    marginBottom: Spacing.sm,
  },
  completedMessage: {
    ...Typography.titleLarge,
    color: Colors.on_surface,
    textAlign: "center",
    marginBottom: Spacing.md,
  },
  completedSubMessage: {
    ...Typography.bodyLarge,
    color: Colors.on_surface_variant,
    textAlign: "center",
    marginBottom: Spacing.xl,
  },
  backButton: {
    backgroundColor: Colors.primary,
    paddingVertical: Spacing.md,
    paddingHorizontal: Spacing.xl,
    borderRadius: Radius.full,
  },
  backButtonText: {
    ...Typography.labelLarge,
    color: Colors.on_primary,
    fontWeight: "900",
  },
});
