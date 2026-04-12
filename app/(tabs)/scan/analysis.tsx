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
/**
 * Get image URL for a food item from a fast, reliable image API
 * Uses Placehold.co with food-specific colors and emojis
 * This ensures instant loading and healthy food themed visuals
 * 
 * @param foodName - Name of the food item
 * @returns Image URL string
 */
function getImageUrlForFood(foodName: string): string {
  // Clean and format the food name
  const cleanName = foodName.toLowerCase().trim();
  
  // Use placehold.co - creates custom placeholders with emoji
  // This is extremely reliable, loads instantly, and always works
  // We use healthy, vibrant colors that match the health theme
  const colors = ['4CAF50', '8BC34A', 'CDDC39', 'FFEB3B', 'FFC107', 'FF9800'];
  const colorIndex = cleanName.length % colors.length;
  const emoji = getFoodEmoji(foodName);
  const placeholderUrl = `https://placehold.co/800x600/${colors[colorIndex]}/FFFFFF?text=${encodeURIComponent(emoji + ' ' + foodName)}`;
  
  return placeholderUrl;
}

/**
 * Get food category for potential future API integration
 */
function getFoodCategory(foodName: string): string {
  const lowerName = foodName.toLowerCase();
  
  const categories: Record<string, string[]> = {
    'pizza': ['pizza', 'pepperoni', 'margherita'],
    'burger': ['burger', 'hamburger', 'cheeseburger'],
    'pasta': ['pasta', 'spaghetti', 'noodles', 'lasagna', 'fettuccine'],
    'rice': ['rice', 'fried-rice', 'sushi', 'biryani'],
    'salad': ['salad', 'caesar-salad', 'greek-salad'],
    'soup': ['soup', 'tomato-soup', 'chicken-soup', 'ramen'],
    'sandwich': ['sandwich', 'sub', 'wrap', 'panini'],
    'taco': ['taco', 'burrito', 'quesadilla', 'nachos'],
    'chicken': ['chicken', 'grilled-chicken', 'fried-chicken'],
    'fish': ['fish', 'salmon', 'tuna', 'cod'],
    'steak': ['steak', 'beef', 'meat'],
    'vegetable': ['vegetable', 'broccoli', 'carrot', 'spinach'],
    'fruit': ['fruit', 'apple', 'banana', 'orange'],
    'dessert': ['cake', 'cookie', 'ice-cream', 'pie'],
    'bread': ['bread', 'toast', 'bagel', 'croissant'],
  };
  
  for (const [category, keywords] of Object.entries(categories)) {
    if (keywords.some(keyword => lowerName.includes(keyword))) {
      return category;
    }
  }
  
  return 'misc';
}

/**
 * Get a relevant emoji for common food items
 * Used for placeholder images when API fails
 */
function getFoodEmoji(foodName: string): string {
  const lowerName = foodName.toLowerCase();
  
  const emojiMap: Record<string, string> = {
    'apple': '🍎',
    'banana': '🍌',
    'orange': '🍊',
    'grape': '🍇',
    'strawberry': '🍓',
    'watermelon': '🍉',
    'rice': '🍚',
    'bread': '🍞',
    'croissant': '🥐',
    'baguette': '🥖',
    'pancake': '🥞',
    'waffle': '🧇',
    'cheese': '🧀',
    'meat': '🥩',
    'poultry': '🍗',
    'bacon': '🥓',
    'hamburger': '🍔',
    'fries': '🍟',
    'pizza': '🍕',
    'hotdog': '🌭',
    'sandwich': '🥪',
    'taco': '🌮',
    'burrito': '🌯',
    'salad': '🥗',
    'soup': '🍲',
    'noodles': '🍜',
    'spaghetti': '🍝',
    'sushi': '🍣',
    'bento': '🍱',
    'curry': '🍛',
    'ramen': '🍜',
    'steak': '🥩',
    'chicken': '🍗',
    'fish': '🐟',
    'shrimp': '🍤',
    'egg': '🥚',
    'avocado': '🥑',
    'broccoli': '🥦',
    'carrot': '🥕',
    'corn': '🌽',
    'cucumber': '🥒',
    'tomato': '🍅',
    'potato': '🥔',
    'mushroom': '🍄',
    'pepper': '🫑',
    'onion': '🧅',
    'garlic': '🧄',
    'ice cream': '🍦',
    'cake': '🍰',
    'cookie': '🍪',
    'chocolate': '🍫',
    'candy': '🍬',
    'donut': '🍩',
    'pie': '🥧',
    'coffee': '☕',
    'tea': '🍵',
    'juice': '🧃',
    'wine': '🍷',
    'beer': '🍺',
    'cocktail': '🍹',
    'milk': '🥛',
    'smoothie': '🥤',
  };
  
  // Find matching emoji
  for (const [key, emoji] of Object.entries(emojiMap)) {
    if (lowerName.includes(key)) {
      return emoji;
    }
  }
  
  // Default food emoji
  return '🍽️';
}

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

      // Map alternatives from backend with health-focused descriptions
      const recommendedFoods: RecommendedFood[] = scanResponse.alternatives && scanResponse.alternatives.length > 0
        ? scanResponse.alternatives.map((alt, index) => {
            // Generate health-focused description if not provided
            const healthDescriptions: Record<string, string> = {
              'default': 'A nutritious and delicious healthier option!',
              'vegetable': 'Packed with vitamins and fiber for optimal health!',
              'fruit': "Nature's candy - full of antioxidants and natural sweetness!",
              'whole grain': 'Rich in fiber and essential nutrients!',
              'lean protein': 'Builds muscle while keeping you energized!',
              'salad': 'Fresh, crisp, and loaded with goodness!',
              'smoothie': 'A refreshing blend of nutrients in every sip!',
            };
            
            let description = alt.description;
            if (!description) {
              // Try to match based on food name
              const lowerName = alt.name.toLowerCase();
              if (lowerName.includes('salad') || lowerName.includes('vegetable') || lowerName.includes('veggie')) {
                description = healthDescriptions['vegetable'];
              } else if (lowerName.includes('fruit') || lowerName.includes('apple') || lowerName.includes('banana')) {
                description = healthDescriptions['fruit'];
              } else if (lowerName.includes('brown rice') || lowerName.includes('quinoa') || lowerName.includes('oat') || lowerName.includes('whole')) {
                description = healthDescriptions['whole grain'];
              } else if (lowerName.includes('chicken') || lowerName.includes('fish') || lowerName.includes('tofu') || lowerName.includes('bean')) {
                description = healthDescriptions['lean protein'];
              } else if (lowerName.includes('smoothie') || lowerName.includes('shake')) {
                description = healthDescriptions['smoothie'];
              } else {
                description = healthDescriptions['default'];
              }
            }
            
            return {
              id: `alt-${index}`,
              name: alt.name,
              description: description,
              image: alt.image_url || getImageUrlForFood(alt.name)
            };
          })
        : [];

      const result: AnalysisResult = {
        rating,
        label: labelMap[rating],
        mascotMessage: mascotMessages[rating],
        recommendedFoods
      };

      // Handle empty alternatives
      if (recommendedFoods.length === 0) {
        if (DEBUG_FORCE_NO_ALTERNATIVES_AVAILABLE) {
          setAlternativesUnavailable(true);
        } else if (DEBUG_FORCE_NO_ALTERNATIVES_RESULT) {
          setAlternativesResultFailed(true);
        }
      }

      setAnalysisResult(result);
    } catch (error) {
      console.error('Error scanning food:', error);
      
      if (error instanceof ApiError) {
        if (error.statusCode === 408) {
          setApiError('Request timed out. Please try again!');
        } else if (error.statusCode === 0) {
          setApiError('Network error. Please check your connection!');
        } else if (error.statusCode === 401) {
          setApiError('Authentication failed. Please log in again!');
        } else {
          setApiError(error.message || 'Failed to analyze image. Please try again.');
        }
      } else {
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
        <Text style={styles.feedbackTitle}>Unable to recognise this food</Text>
        <Text style={styles.feedbackText}>
          Please try scanning again with the food clearly inside the frame.
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
          <Text style={[styles.labelText, { color: ratingColor }]}>
            😦 {analysisResult.label}
          </Text>
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
    borderRadius: 999,
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
