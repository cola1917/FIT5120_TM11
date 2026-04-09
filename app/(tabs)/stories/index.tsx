import AppHeader from '@/components/app_header';
import { getStories, getStoryCoverUrl } from '@/services/stories';
import { router } from 'expo-router';
import { BookOpen } from 'lucide-react-native';
import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Dimensions,
  FlatList,
  Image,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

const { width, height } = Dimensions.get('window');
const CARD_WIDTH = width * 0.74;
const CARD_HEIGHT = height * 0.48;

// Local mascot image used for the bottom reading helper area.
const readingMascot = require('../../../assets/images/nutriheroes_reading.png');

interface Story {
  id: string;
  title: string;
  coverImage: string;
  pageCount: number;
}

export default function StoriesScreen() {
  const [stories, setStories] = useState<Story[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStories();
  }, []);

  const loadStories = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getStories();
      setStories(data);
    } catch (err: any) {
      console.error('Failed to load stories:', err);
      setError(err.message || 'Failed to load stories');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenStory = (storyId?: string) => {
    // Prevent navigation when the story id is missing or invalid.
    if (!storyId || !storyId.trim()) {
      return;
    }

    router.push(`/stories/${storyId}`);
  };

  const renderStoryCard = ({ item }: { item: Story }) => {
    return (
      <View style={styles.cardWrapper}>
        <TouchableOpacity
          activeOpacity={0.92}
          style={styles.card}
          onPress={() => handleOpenStory(item.id)}
        >
          <Image
            source={{ uri: getStoryCoverUrl(item.id) }}
            style={styles.cardImage}
            resizeMode="cover"
          />

          {/* Soft overlay to improve text readability on the image. */}
          <View style={styles.imageOverlay} />

          <View style={styles.cardContent}>
            <View style={styles.titleBubble}>
              <Text style={styles.cardTitle}>{item.title}</Text>
            </View>

            <View style={styles.bottomPanel}>
              <Text style={styles.cardDescription}>
                A {item.pageCount}-page adventure awaits!
              </Text>

              <TouchableOpacity
                style={[styles.readButton, { backgroundColor: '#E77A1F' }]}
                onPress={() => handleOpenStory(item.id)}
              >
                <Text style={styles.readButtonText}>Read Now</Text>
              </TouchableOpacity>
            </View>
          </View>
        </TouchableOpacity>
      </View>
    );
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.centered}>
          <ActivityIndicator size="large" color="#E77A1F" />
          <Text style={styles.loadingText}>Loading stories...</Text>
        </View>
      </SafeAreaView>
    );
  }

  if (error) {
    return (
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.centered}>
          <Text style={styles.errorTitle}>Oops!</Text>
          <Text style={styles.errorText}>{error}</Text>
          <TouchableOpacity style={styles.retryButton} onPress={loadStories}>
            <Text style={styles.retryButtonText}>Try Again</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>
        {/* Shared app header used across main pages */}
        <AppHeader />

        {/* Story title and simple instruction for the child */}
        <View style={styles.storyIntro}>
          <View style={styles.storyIntroRow}>
            <BookOpen size={22} color="#E77A1F" />
            <Text style={styles.storyIntroTitle}>Stories</Text>
          </View>

          <Text style={styles.storyIntroSubtitle}>
            Swipe left or right to choose a story
          </Text>
        </View>

        {/* Fixed-height carousel area keeps the mascot helper stable below */}
        <View style={styles.carouselSection}>
          <FlatList
            data={stories}
            keyExtractor={(item) => item.id}
            renderItem={renderStoryCard}
            horizontal
            pagingEnabled
            showsHorizontalScrollIndicator={false}
            decelerationRate="fast"
            contentContainerStyle={styles.listContent}
          />
        </View>

        {/* Bottom helper area with mascot guidance */}
        <View style={styles.mascotPanel}>
          <Image
            source={readingMascot}
            style={styles.mascotImage}
            resizeMode="contain"
          />
          <View style={styles.mascotBubble}>
            <Text style={styles.mascotText}>
              Tap a big picture and start your story adventure.
            </Text>
          </View>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#F8F5E9',
  },
  container: {
    flex: 1,
    paddingHorizontal: 20,
    paddingTop: 8,
    paddingBottom: 20,
    backgroundColor: '#F8F5E9',
  },
  storyIntro: {
    marginBottom: 18,
  },
  storyIntroRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginBottom: 6,
  },
  storyIntroTitle: {
    fontSize: 28,
    fontWeight: '900',
    color: '#2D241F',
  },
  storyIntroSubtitle: {
    fontSize: 15,
    color: '#6F625A',
    fontWeight: '600',
  },
  carouselSection: {
    height: CARD_HEIGHT + 12,
    marginBottom: 20,
  },
  listContent: {
    paddingRight: 20,
  },
  cardWrapper: {
    width: CARD_WIDTH,
    marginRight: 18,
  },
  card: {
    width: '100%',
    height: CARD_HEIGHT,
    borderRadius: 28,
    overflow: 'hidden',
    backgroundColor: '#FFFFFF',
    borderWidth: 4,
    borderColor: '#FFF2D7',
    shadowColor: '#000',
    shadowOpacity: 0.12,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 6 },
    elevation: 6,
  },
  cardImage: {
    width: '100%',
    height: '100%',
  },
  imageOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.15)',
  },
  cardContent: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'space-between',
    padding: 18,
  },
  titleBubble: {
    alignSelf: 'flex-start',
    backgroundColor: 'rgba(255,255,255,0.95)',
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 18,
    maxWidth: '88%',
  },
  cardTitle: {
    fontSize: 24,
    lineHeight: 28,
    fontWeight: '900',
    color: '#2A1E18',
  },
  bottomPanel: {
    backgroundColor: 'rgba(255,255,255,0.95)',
    borderRadius: 22,
    padding: 16,
  },
  cardDescription: {
    fontSize: 15,
    lineHeight: 21,
    color: '#5A4C42',
    fontWeight: '600',
    marginBottom: 14,
  },
  readButton: {
    borderRadius: 999,
    paddingVertical: 14,
    alignItems: 'center',
  },
  readButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '900',
  },
  mascotPanel: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  mascotImage: {
    width: 92,
    height: 92,
  },
  mascotBubble: {
    flex: 1,
    backgroundColor: '#FFF9E8',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderWidth: 2,
    borderColor: '#F2DFC0',
  },
  mascotText: {
    fontSize: 14,
    lineHeight: 20,
    color: '#745D4E',
    fontWeight: '700',
  },
  centered: {
    flex: 1,
    backgroundColor: '#F8F5E9',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  loadingText: {
    fontSize: 16,
    color: '#6C5B4F',
    marginTop: 16,
    textAlign: 'center',
  },
  errorTitle: {
    fontSize: 24,
    fontWeight: '900',
    color: '#2D241F',
    marginBottom: 8,
    textAlign: 'center',
  },
  errorText: {
    fontSize: 16,
    color: '#6C5B4F',
    textAlign: 'center',
    lineHeight: 24,
    marginBottom: 20,
  },
  retryButton: {
    backgroundColor: '#E77A1F',
    borderRadius: 999,
    paddingHorizontal: 24,
    paddingVertical: 14,
  },
  retryButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '900',
  },
});
