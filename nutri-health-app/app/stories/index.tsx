import React, { useEffect, useState, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  Dimensions,
  Animated,
  Easing,
} from 'react-native';
import { AutoSizeText, ResizeTextMode } from 'react-native-auto-size-text';
import { Image } from 'expo-image';
import { useRouter } from 'expo-router';
import { Colors } from '../../constants/Colors';
import { Typography } from '../../constants/Typography';
import { Radius } from '../../constants/Radius';
import { Spacing } from '../../constants/Spacing';
import { getStories, getStoryCoverUrl, getAuthHeaders, Story, ApiError } from '../../services/stories';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');
const CARD_HEIGHT = SCREEN_HEIGHT * 0.6;
const CARD_WIDTH = SCREEN_WIDTH * 0.9;
const CARD_SPACING = (SCREEN_WIDTH - CARD_WIDTH) / 2;

const AUTO_SCROLL_INTERVAL = 4000;

export default function StoriesListScreen() {
  const router = useRouter();

  const [stories, setStories] = useState<Story[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [authHeaders, setAuthHeaders] = useState<{ Authorization: string } | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);

  const flatListRef = useRef<FlatList>(null);
  const intervalRef = useRef<number | null>(null);

  // 🔥 Progress animation
  const progress = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    loadStories();
    loadAuthHeaders();
  }, []);

  /** ---------------- Progress Animation ---------------- */

  const animateProgress = () => {
    progress.setValue(0);

    Animated.timing(progress, {
      toValue: 1,
      duration: AUTO_SCROLL_INTERVAL,
      easing: Easing.linear,
      useNativeDriver: false,
    }).start();
  };

  useEffect(() => {
    if (stories.length > 0) {
      animateProgress();
    }
  }, [currentIndex]);

  /** ---------------- Auto Scroll ---------------- */

  const startAutoScroll = () => {
    stopAutoScroll();

    if (stories.length <= 1) return;

    intervalRef.current = setInterval(() => {
      setCurrentIndex((prev) => {
        const nextIndex = (prev + 1) % stories.length;

        flatListRef.current?.scrollToIndex({
          index: nextIndex,
          animated: true,
        });

        return nextIndex;
      });
    }, AUTO_SCROLL_INTERVAL);
  };

  const stopAutoScroll = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    progress.stopAnimation();
    progress.setValue(0);
  };

  useEffect(() => {
    if (stories.length > 0) {
      startAutoScroll();
      animateProgress();
    }
    return stopAutoScroll;
  }, [stories]);

  /** ---------------- Viewability ---------------- */

  const onViewableItemsChanged = useRef(({ viewableItems }: any) => {
    if (viewableItems.length > 0) {
      setCurrentIndex(viewableItems[0].index);
    }
  }).current;

  const viewabilityConfig = {
    itemVisiblePercentThreshold: 50,
  };

  /** ---------------- Data ---------------- */

  const loadAuthHeaders = async () => {
    try {
      const headers = await getAuthHeaders();
      setAuthHeaders(headers);
    } catch (err) {
      console.error(err);
    }
  };

  const loadStories = async () => {
    try {
      setLoading(true);
      setError(null);
      const fetchedStories = await getStories();
      setStories(fetchedStories);
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else setError('Failed to load stories.');
    } finally {
      setLoading(false);
    }
  };

  const handleStoryPress = (story: Story) => {
    stopAutoScroll();
    router.push({
      pathname: `/stories/[id]`,
      params: { id: story.id },
    });
  };

  /** ---------------- Render ---------------- */

  const renderStoryCard = ({ item }: { item: Story }) => {
    const coverUrl = getStoryCoverUrl(item.id);

    return (
      <TouchableOpacity
        style={styles.card}
        onPress={() => handleStoryPress(item)}
        activeOpacity={0.8}
      >
        <View style={styles.cardInner}>
          <Image
            source={{
              uri: coverUrl,
              headers: authHeaders || undefined,
            }}
            style={styles.coverImage}
          />
          <AutoSizeText
            fontSize={24}
            numberOfLines={1}
            mode={ResizeTextMode.max_lines}
            style={styles.title}>
            {item.title}
          </AutoSizeText>
        </View>
      </TouchableOpacity>
    );
  };

  /** ---------------- States ---------------- */

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color={Colors.primary} />
        <Text style={styles.loadingText}>Loading stories...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.centerContainer}>
        <Text style={styles.errorText}>{error}</Text>
        <TouchableOpacity style={styles.retryButton} onPress={loadStories}>
          <Text style={styles.retryButtonText}>Try Again</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (stories.length === 0) {
    return (
      <View style={styles.centerContainer}>
        <Text style={styles.emptyText}>No stories available yet.</Text>
      </View>
    );
  }

  /** ---------------- UI ---------------- */

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Choose a Story</Text>
        <Text style={styles.headerSubtitle}>Tap a story to begin reading</Text>
      </View>

      <View>
        <FlatList
          ref={flatListRef}
          data={stories}
          renderItem={renderStoryCard}
          keyExtractor={(item) => item.id}
          horizontal
          showsHorizontalScrollIndicator={false}
          snapToInterval={CARD_WIDTH + CARD_SPACING - Spacing.xs}
          decelerationRate="fast"
          contentContainerStyle={styles.listContent}
          onTouchStart={stopAutoScroll}
          onMomentumScrollEnd={() => {
            startAutoScroll();
            animateProgress();
          }}
          onViewableItemsChanged={onViewableItemsChanged}
          viewabilityConfig={viewabilityConfig}
          getItemLayout={(_, index) => ({
            length: (CARD_WIDTH + CARD_SPACING - Spacing.xs),
            offset: (CARD_WIDTH + CARD_SPACING - Spacing.xs) * index,
            index,
          })}
        />

        <View style={styles.progressContainer}>
          <View style={styles.progressTrack}>
            <Animated.View
              style={[
                styles.progressFill,
                {
                  width: progress.interpolate({
                    inputRange: [0, 1],
                    outputRange: ['0%', '100%'],
                  }),
                },
              ]}
            />
          </View>
        </View>
      </View>
    </View>
  );
}

/** ---------------- Styles ---------------- */

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.surface,
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: Colors.surface,
    padding: Spacing.xl,
  },
  header: {
    paddingHorizontal: Spacing.xl,
    paddingTop: Spacing.xl,
    paddingBottom: Spacing.lg,
  },
  headerTitle: {
    ...Typography.displayMedium,
    color: Colors.on_surface,
  },
  headerSubtitle: {
    ...Typography.bodyLarge,
    color: Colors.on_surface_variant,
  },
  listContent: {
    paddingHorizontal: CARD_SPACING,
    paddingVertical: Spacing.md,
  },
  card: {
    width: CARD_WIDTH,
    height: CARD_HEIGHT,
    marginHorizontal: Spacing.xs,
  },
  cardInner: {
    flex: 1,
    backgroundColor: Colors.surface_container_lowest,
    borderRadius: Radius.lg,
    overflow: 'hidden',
  },
  coverImage: {
    width: '100%',
    height: '88%',
  },
  title: {
    ...Typography.headlineMedium,
    padding: Spacing.sm,
    color: Colors.on_surface,
  },

  /** Progress bars */
  paginationContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: Spacing.md,
    paddingHorizontal: Spacing.lg,
  },
  progressContainer: {
    marginTop: 6, // tight under carousel
    paddingHorizontal: Spacing.xl,
    alignItems: 'center'
  },
  progressTrack: {
    width: '50%',
    height: 4,
    backgroundColor: Colors.surface_container,
    borderRadius: 2,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    backgroundColor: Colors.primary,
  },

  loadingText: {
    ...Typography.bodyLarge,
    color: Colors.on_surface_variant,
    marginTop: Spacing.md,
  },
  errorText: {
    ...Typography.bodyLarge,
    color: Colors.error,
    textAlign: 'center',
    marginBottom: Spacing.lg,
  },
  emptyText: {
    ...Typography.bodyLarge,
    color: Colors.on_surface_variant,
    textAlign: 'center',
  },
  retryButton: {
    backgroundColor: Colors.primary,
    paddingHorizontal: Spacing.xl,
    paddingVertical: Spacing.md,
    borderRadius: Radius.full,
  },
  retryButtonText: {
    ...Typography.labelLarge,
    color: Colors.on_primary,
  },
});