/**
 * Stories List Screen
 * Displays a carousel of available stories with cover images
 */

import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  Dimensions,
} from 'react-native';
import { Image } from 'expo-image';
import { useRouter } from 'expo-router';
import { Colors } from '../../constants/Colors';
import { Typography } from '../../constants/Typography';
import { Radius } from '../../constants/Radius';
import { Spacing } from '../../constants/Spacing';
import { getStories, getStoryCoverUrl, getAuthHeaders, Story, ApiError } from '../../services/stories';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');
const CARD_HEIGHT = SCREEN_HEIGHT * 0.6; // 60% of screen height
const CARD_WIDTH = SCREEN_WIDTH * 0.9; // Maintain good proportions

export default function StoriesListScreen() {
  const router = useRouter();
  const [stories, setStories] = useState<Story[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [authHeaders, setAuthHeaders] = useState<{ Authorization: string } | null>(null);

  useEffect(() => {
    loadStories();
    loadAuthHeaders();
  }, []);

  const loadAuthHeaders = async () => {
    try {
      const headers = await getAuthHeaders();
      console.log('Setting auth headers:', headers);
      setAuthHeaders(headers);
    } catch (err) {
      console.error('Failed to load auth headers:', err);
    }
  };

  const loadStories = async () => {
    try {
      setLoading(true);
      setError(null);
      const fetchedStories = await getStories();
      setStories(fetchedStories);
    } catch (err) {
      console.error('Failed to load stories:', err);
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Failed to load stories. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleStoryPress = (story: Story) => {
    router.push({
      pathname: `/stories/[id]`,
      params: {id: story.id}
    });
  };

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
          <Text style={styles.title} numberOfLines={3} ellipsizeMode="tail">
            {item.title}
          </Text>
        </View>
      </TouchableOpacity>
    );
  };

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

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Choose a Story</Text>
        <Text style={styles.headerSubtitle}>Tap a story to begin reading</Text>
      </View>

      <FlatList
        data={stories}
        renderItem={renderStoryCard}
        keyExtractor={(item) => item.id}
        horizontal
        showsHorizontalScrollIndicator={false}
        snapToInterval={CARD_WIDTH + Spacing.lg}
        decelerationRate="fast"
        contentContainerStyle={styles.listContent}
      />
    </View>
  );
}

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
    marginBottom: Spacing.xs,
  },
  headerSubtitle: {
    ...Typography.bodyLarge,
    color: Colors.on_surface_variant,
  },
  listContent: {
    paddingHorizontal: (SCREEN_WIDTH - CARD_WIDTH - Spacing.xs * 2) / 2, // Align the current story in the center
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
    // Elevation for shadow effect
    shadowColor: Colors.on_surface,
    shadowOffset: {
      width: 0,
      height: 20,
    },
    shadowOpacity: 0.06,
    shadowRadius: 40,
    elevation: 8,
  },
  coverImage: {
    width: '100%',
    height: '88%',
    backgroundColor: Colors.surface_container,
    resizeMode: 'cover',
  },
  titleContainer: {
    height: '12%',
    padding: Spacing.lg,
    justifyContent: 'center',
    backgroundColor: Colors.surface_container_lowest,
  },
  title: {
    ...Typography.headlineMedium,
    padding: Spacing.sm,
    color: Colors.on_surface,
    marginBottom: Spacing.xs,
    flexWrap: 'wrap',
  },
  pageCount: {
    ...Typography.bodyMedium,
    color: Colors.on_surface_variant,
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
