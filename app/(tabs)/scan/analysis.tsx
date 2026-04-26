import { router, useLocalSearchParams } from 'expo-router';
import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Dimensions,
  FlatList,
  Image,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { scanFood, ApiError } from '../../../services/api';
import { AutoSizeText, ResizeTextMode } from 'react-native-auto-size-text';

interface RecommendedFood {
  id: string;
  name: string;
  description: string;
  image: string;
}

interface AnalysisResult {
  rating: 'HEALTHY' | 'MODERATE' | 'UNHEALTHY';
  label: string;
  mascotMessage: string;
  recommendedFoods: RecommendedFood[];
}

/*
  DEBUG FLAGS FOR TESTING

  Set these to true temporarily when you want to test failure states:
  - DEBUG_FORCE_LOADING_DELAY: makes loading message visible longer
  - DEBUG_FORCE_UNABLE_TO_RECOGNISE: tests "Unable to recognise this food"
  - DEBUG_FORCE_NO_RESULT: tests "Unable to retrieve result at the moment"
  - DEBUG_FORCE_NO_ALTERNATIVES_AVAILABLE: tests "No alternative available at the moment"
  - DEBUG_FORCE_NO_ALTERNATIVES_RESULT: tests "Unable to retrieve result at the moment" in alternatives area
*/
const DEBUG_FORCE_LOADING_DELAY = false;
const DEBUG_FORCE_UNABLE_TO_RECOGNISE = false;
const DEBUG_FORCE_NO_RESULT = false;
const DEBUG_FORCE_NO_ALTERNATIVES_AVAILABLE = false;
const DEBUG_FORCE_NO_ALTERNATIVES_RESULT = false;

// Mock data is no longer needed as we fetch from the backend
// Kept for reference during development if needed

const { width } = Dimensions.get('window');
const ALTERNATIVE_CARD_WIDTH = width - 80;

export default function AnalysisScreen() {
  const { photoUri } = useLocalSearchParams<{ photoUri?: string }>();

  const [loading, setLoading] = useState(true);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [noResult, setNoResult] = useState(false);
  const [cannotRecognise, setCannotRecognise] = useState(false);
  const [alternativesUnavailable, setAlternativesUnavailable] = useState(false);
  const [alternativesResultFailed, setAlternativesResultFailed] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  const loadAnalysis = async () => {
    setLoading(true);
    setAnalysisResult(null);
    setNoResult(false);
    setCannotRecognise(false);
    setAlternativesUnavailable(false);
    setAlternativesResultFailed(false);
    setApiError(null);

    const delay = DEBUG_FORCE_LOADING_DELAY ? 2200 : 700;

    // If no photo URI, show error immediately
    if (!photoUri) {
      setNoResult(true);
      setLoading(false);
      return;
    }

    // Handle debug flags first
    if (DEBUG_FORCE_UNABLE_TO_RECOGNISE) {
      setCannotRecognise(true);
      setLoading(false);
      return;
    }

    if (DEBUG_FORCE_NO_RESULT) {
      setNoResult(true);
      setLoading(false);
      return;
    }

    try {
      // Call backend API to scan the food image
      console.log('Scanning food image:', photoUri);
      const scanResponse = await scanFood(photoUri);
      
      console.log('Scan response received:', scanResponse);
      
      // Check if food was not recognized (confidence = 0 or food_name = "Food Item")
      if (scanResponse.confidence === 0 || scanResponse.food_name.toLowerCase() === 'food item') {
        setCannotRecognise(true);
        setLoading(false);
        return;
      }
      
      // Map backend response to frontend format
      // Backend uses: 1 = unhealthy, 2 = moderate, 3 = healthy
      const rating: 'HEALTHY' | 'MODERATE' | 'UNHEALTHY' = 
        scanResponse.assessment_score === 3 ? 'HEALTHY' :
        scanResponse.assessment_score === 2 ? 'MODERATE' : 'UNHEALTHY';
      
      const labelMap: Record<string, string> = {
        'HEALTHY': 'Great Choice!',
        'MODERATE': 'Could Be Better',
        'UNHEALTHY': 'Needs an Upgrade'
      };
      
      const mascotMessages: Record<string, string> = {
        'HEALTHY': 'Awesome! This food is super healthy for you!',
        'MODERATE': 'This is okay, but maybe we can find something even better!',
        'UNHEALTHY': 'This snack is tasty, but we can make it more hero-worthy!'
      };

      // Map alternatives from backend
      const recommendedFoods: RecommendedFood[] = scanResponse.alternatives && scanResponse.alternatives.length > 0
        ? scanResponse.alternatives.map((alt, index) => {
            if (!alt.image && !alt.imageUrl && !alt.image_url) {
              throw new Error(`Missing image for alternative food: ${alt.name}`);
            }
            return {
              id: `alt-${index}`,
              name: alt.name,
              description: alt.description || 'A healthier option for you!',
              image: alt.image || alt.imageUrl || alt.image_url!
            };
          })
        : [];

      // For HEALTHY or MODERATE foods, show encouraging messages instead of alternatives
      const encouragingMessages: Record<string, RecommendedFood[]> = {
        'HEALTHY': [
          {
            id: 'encourage-healthy-1',
            name: '🌟 Super Star!',
            description: 'You made an amazing healthy choice! Keep up the great work, little hero!',
            image: 'https://image.pollinations.ai/prompt/healthy%20kid%20superhero%20celebrating%20food%20photography%20white%20background?model=flux&width=512&height=512'
          }
        ]
      };

      // Use encouraging messages when no alternatives are available for HEALTHY/MODERATE foods
      let displayRecommendedFoods: RecommendedFood[] = recommendedFoods;
      if (recommendedFoods.length === 0 && (rating === 'HEALTHY' || rating === 'MODERATE')) {
        displayRecommendedFoods = encouragingMessages[rating];
      }

      const result: AnalysisResult = {
        rating,
        label: labelMap[rating],
        mascotMessage: mascotMessages[rating],
        recommendedFoods: displayRecommendedFoods
      };

      // Handle empty alternatives - only show unavailable message for UNHEALTHY foods
      // For HEALTHY/MODERATE, we already show encouraging messages
      if (displayRecommendedFoods.length === 0 && rating === 'UNHEALTHY') {
        if (DEBUG_FORCE_NO_ALTERNATIVES_AVAILABLE) {
          setAlternativesUnavailable(true);
        } else if (DEBUG_FORCE_NO_ALTERNATIVES_RESULT) {
          setAlternativesResultFailed(true);
        }
      }

      setAnalysisResult(result);
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : String(error || '');
      const isNoFoodDetected = errorMessage.toLowerCase().includes('no food detected');

      if (isNoFoodDetected) {
        setCannotRecognise(true);
      } else if (error instanceof ApiError) {
        const isNoFoodDetected =
          error.statusCode === 400 &&
          error.message.toLowerCase().includes('no food detected');

        if (isNoFoodDetected) {
          setCannotRecognise(true);
        } else if (error.statusCode === 408) {
          setApiError('Request timed out. Please try again!');
        } else if (error.statusCode === 0) {
          setApiError('Network error. Please check your connection!');
        } else if (error.statusCode === 401) {
          setApiError('Authentication failed. Please log in again!');
        } else {
          setApiError(error.message || 'Failed to analyze image. Please try again.');
        }
      } else {
        console.log('Unexpected scan error:', error);
        setApiError('An unexpected error occurred. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAnalysis();
  }, [photoUri]);

  const handleSwap = (food: RecommendedFood) => {
    // For now, this is a placeholder action.
    // Later, this can open a detail page or save the healthier option.
    console.log('Swap selected:', food.name);
  };

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#E8814A" />
        <Text style={styles.feedbackTitle}>Analyzing your food...</Text>
        <Text style={styles.feedbackText}>
          Please wait while we check your scan.
        </Text>
      </View>
    );
  }

  if (cannotRecognise) {
    return (
      <View style={styles.centered}>
        <Text style={styles.feedbackTitle}>Oops! I can’t see your food clearly</Text>
        <Text style={styles.feedbackText}>
          Can you try again?
        </Text>

        <TouchableOpacity
          style={styles.primaryAction}
          onPress={() => router.replace('/scan/camera')}
        >
          <Text style={styles.primaryActionText}>Retry Scan</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.secondaryAction}
          onPress={() => router.replace('/scan')}
        >
          <Text style={styles.secondaryActionText}>Go Home</Text>
        </TouchableOpacity>
      </View>
    );
  }

  // Show API error if present
  if (apiError) {
    return (
      <View style={styles.centered}>
        <Text style={styles.feedbackTitle}>Error</Text>
        <Text style={styles.feedbackText}>{apiError}</Text>

        <TouchableOpacity style={styles.primaryAction} onPress={loadAnalysis}>
          <Text style={styles.primaryActionText}>Retry</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.secondaryAction}
          onPress={() => router.replace('/scan')}
        >
          <Text style={styles.secondaryActionText}>Go Home</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (noResult || !analysisResult) {
    return (
      <View style={styles.centered}>
        <Text style={styles.feedbackTitle}>Unable to retrieve result at the moment</Text>
        <Text style={styles.feedbackText}>
          Please try again. We do not want to show incomplete or confusing information.
        </Text>

        <TouchableOpacity style={styles.primaryAction} onPress={loadAnalysis}>
          <Text style={styles.primaryActionText}>Retry</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.secondaryAction}
          onPress={() => router.replace('/scan')}
        >
          <Text style={styles.secondaryActionText}>Go Home</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const isUnhealthy = analysisResult.rating === 'UNHEALTHY';
  const ratingColor = isUnhealthy ? '#E8814A' : '#4CAF50';

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.contentContainer}
      showsVerticalScrollIndicator={false}
    >
      {/* Section 1: Evaluation area */}
      <View style={styles.evaluationCard}>
        <View style={styles.badge}>
          <Text style={styles.badgeText}>
            {isUnhealthy ? 'NOT SO SUPER' : 'SUPER!'}
          </Text>
        </View>

        <View style={styles.foodImageContainer}>
          {photoUri ? (
            <Image
              source={{ uri: photoUri }}
              style={styles.foodImage}
              resizeMode="contain"
            />
          ) : (
            <Text style={styles.fallbackText}>No captured photo</Text>
          )}
        </View>

        <View style={styles.mascotRow}>
          <Image
            source={require('../../../assets/images/nutriheroes_icon.png')}
            style={styles.mascotImage}
            resizeMode="contain"
          />
          <View style={styles.speechBubble}>
            <Text style={styles.speechText}>
              {analysisResult.mascotMessage}
            </Text>
          </View>
        </View>

        <Text style={[styles.ratingText, { color: ratingColor }]}>
          {analysisResult.rating}
        </Text>

        <View
          style={[styles.labelBadge, { backgroundColor: `${ratingColor}30` }]}
        >
          <AutoSizeText 
            style={[styles.labelText, { color: ratingColor }]}
            mode={ResizeTextMode.max_lines}
            numberOfLines={1}
            fontSize={13}
            >
            😦 {analysisResult.label}
          </AutoSizeText>
        </View>
      </View>

      {/* Section 2: Recommended alternatives */}
      <View style={styles.recommendCard}>
        <Text style={styles.recommendTitle}>A healthier option for you!</Text>

        {alternativesUnavailable ? (
          <View style={styles.messageCard}>
            <Text style={styles.messageTitle}>No alternative available at the moment</Text>
            <Text style={styles.messageText}>
              Please try scanning another food later.
            </Text>
          </View>
        ) : alternativesResultFailed ? (
          <View style={styles.messageCard}>
            <Text style={styles.messageTitle}>Unable to retrieve result at the moment</Text>
            <Text style={styles.messageText}>
              We could not load the alternatives right now.
            </Text>
          </View>
        ) : (
          <FlatList
            data={analysisResult.recommendedFoods}
            keyExtractor={(item) => item.id}
            horizontal
            pagingEnabled
            showsHorizontalScrollIndicator={false}
            decelerationRate="fast"
            contentContainerStyle={styles.alternativesListContent}
            renderItem={({ item }) => (
              <TouchableOpacity
                activeOpacity={0.92}
                style={styles.alternativeCard}
                onPress={() => handleSwap(item)}
              >
                {/* Large image area for the healthier alternative */}
                <View style={styles.alternativeImageWrap}>
                  <Image
                    source={{ uri: item.image }}
                    style={styles.alternativeImage}
                    resizeMode="cover"
                  />
                  <View style={styles.starBadge}>
                    <Text>⭐</Text>
                  </View>
                </View>

                {/* Text content for the alternative */}
                <View style={styles.alternativeTextWrap}>
                  <Text style={styles.alternativeName}>{item.name}</Text>
                  <Text style={styles.alternativeDesc}>{item.description}</Text>
                </View>
              </TouchableOpacity>
            )}
          />
        )}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  contentContainer: {
    padding: 16,
    paddingBottom: 100,
    gap: 16,
  },

  // Evaluation card
  evaluationCard: {
    backgroundColor: '#EFEFEF',
    borderRadius: 32,
    padding: 24,
    alignItems: 'center',
    borderWidth: 4,
    borderColor: '#FFFFFF',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 5,
  },
  badge: {
    position: 'absolute',
    top: 16,
    right: 16,
    backgroundColor: '#E8814A',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 999,
  },
  badgeText: {
    color: '#FFFFFF',
    fontSize: 10,
    fontWeight: 'bold',
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  foodImageContainer: {
    width: 160,
    height: 160,
    borderRadius: 80,
    backgroundColor: '#E0E0E0',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 32,
    marginBottom: 16,
  },
  foodImage: {
    width: 120,
    height: 120,
    opacity: 0.8,
  },
  fallbackText: {
    color: '#666',
    fontWeight: '600',
  },
  mascotRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
    paddingHorizontal: 8,
  },
  mascotImage: {
    width: 48,
    height: 48,
    marginRight: 8,
  },
  speechBubble: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 10,
    flex: 1,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    elevation: 2,
  },
  speechText: {
    fontSize: 12,
    color: '#333',
    fontWeight: '600',
  },
  ratingText: {
    fontSize: 36,
    fontWeight: '900',
    marginBottom: 8,
  },
  labelBadge: {
    paddingHorizontal: 16,
    paddingVertical: 6,
    borderRadius: 12,
    marginBottom: 8,
  },
  labelText: {
    fontSize: 13,
    fontWeight: 'bold',
  },

  // Recommended alternatives section
  recommendCard: {
    backgroundColor: '#C8E6C9',
    borderRadius: 32,
    padding: 24,
    borderWidth: 4,
    borderColor: '#FFFFFF',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 5,
    gap: 12,
  },
  recommendTitle: {
    fontSize: 18,
    fontWeight: '900',
    color: '#2E7D32',
    textAlign: 'center',
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: 8,
  },
  alternativesListContent: {
    paddingHorizontal: 4,
  },
  alternativeCard: {
    width: ALTERNATIVE_CARD_WIDTH,
    marginRight: 14,
    backgroundColor: '#FFFFFF',
    borderRadius: 24,
    overflow: 'hidden',
    borderWidth: 2,
    borderColor: '#DCEFD8',
  },
  alternativeImageWrap: {
    height: 180,
    backgroundColor: '#E9F7E7',
    justifyContent: 'center',
    alignItems: 'center',
    position: 'relative',
  },
  alternativeImage: {
    width: '100%',
    height: '100%',
  },
  alternativeTextWrap: {
    padding: 16,
  },
  alternativeName: {
    fontSize: 22,
    fontWeight: '900',
    color: '#2E7D32',
    marginBottom: 8,
  },
  alternativeDesc: {
    fontSize: 15,
    lineHeight: 22,
    color: '#4A7A4E',
    fontWeight: '600',
  },
  starBadge: {
    position: 'absolute',
    top: 10,
    right: 10,
    backgroundColor: '#FF7043',
    borderRadius: 999,
    paddingHorizontal: 6,
    paddingVertical: 4,
  },

  // Shared feedback states
  centered: {
    flex: 1,
    backgroundColor: '#F5F5F5',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  feedbackTitle: {
    fontSize: 24,
    fontWeight: '900',
    color: '#1F1F1F',
    marginTop: 14,
    marginBottom: 8,
    textAlign: 'center',
  },
  feedbackText: {
    fontSize: 16,
    color: '#555',
    textAlign: 'center',
    lineHeight: 24,
    marginBottom: 20,
  },
  primaryAction: {
    backgroundColor: '#E8814A',
    borderRadius: 999,
    paddingHorizontal: 24,
    paddingVertical: 14,
    marginBottom: 10,
  },
  primaryActionText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '900',
  },
  secondaryAction: {
    backgroundColor: '#FFF3E3',
    borderRadius: 999,
    paddingHorizontal: 24,
    paddingVertical: 14,
    borderWidth: 2,
    borderColor: '#F1E3C8',
  },
  secondaryActionText: {
    color: '#B45309',
    fontSize: 16,
    fontWeight: '900',
  },
  messageCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    padding: 18,
  },
  messageTitle: {
    fontSize: 18,
    fontWeight: '900',
    color: '#2E7D32',
    marginBottom: 8,
    textAlign: 'center',
  },
  messageText: {
    fontSize: 14,
    lineHeight: 22,
    color: '#4B6B4F',
    textAlign: 'center',
  },
});
