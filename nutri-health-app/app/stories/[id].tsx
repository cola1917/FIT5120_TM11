/**
 * Story Viewer Screen
 * Displays story pages with text and images, continuous scrolling with audio playback
 */

import React, { useEffect, useState, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Dimensions,
} from 'react-native';
import { Image } from 'expo-image';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Audio } from 'expo-av';
import { Ionicons } from '@expo/vector-icons';
import { Colors } from '../../constants/Colors';
import { Typography } from '../../constants/Typography';
import { Radius } from '../../constants/Radius';
import { Spacing } from '../../constants/Spacing';
import {
  getStories,
  getStoryPageImageUrl,
  getStoryPageAudioUrl,
  getAuthHeaders,
  getStoryText,
  Story,
  StoryTextData,
  ApiError,
  StoryPage,
} from '../../services/stories';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');
const HEADER_HEIGHT = 80;
const PAGE_HEIGHT = SCREEN_HEIGHT - HEADER_HEIGHT;

// Story text styling - future-proof for per-story customization
const getStoryTextStyle = (storyId: string) => {
  // Future: return story-specific styles based on storyId
  return {
    fontSize: 20,
    lineHeight: 32,
    letterSpacing: 0.5,
    color: Colors.on_surface,
    textAlign: 'left' as const,
  };
};

export default function StoryViewerScreen() {
  const params = useLocalSearchParams();
  const router = useRouter();
  const storyId = params.id as string;

  const [story, setStory] = useState<Story | null>(null);
  const [storyText, setStoryText] = useState<StoryPage[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [isPlaying, setIsPlaying] = useState(false);
  const [authHeaders, setAuthHeaders] = useState<{ Authorization: string } | null>(null);

  const soundRef = useRef<Audio.Sound | null>(null);
  const scrollViewRef = useRef<ScrollView>(null);
  const isAutoScrolling = useRef(false);

  useEffect(() => {
    loadStoryData();
    loadAuthHeaders();
    setupAudio();

    return () => {
      cleanupAudio();
    };
  }, []);

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
      setIsPlaying(false);
    } catch (err) {
      console.error('Failed to cleanup audio:', err);
    }
  };

  const loadAuthHeaders = async () => {
    try {
      const headers = await getAuthHeaders();
      setAuthHeaders(headers);
    } catch (err) {
      console.error('Failed to load auth headers:', err);
    }
  };

  const loadStoryData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Load both story metadata and text content
      const [stories, textData] = await Promise.all([
        getStories(),
        getStoryText(storyId),
      ]);
      
      const foundStory = stories.find(s => s.id === storyId);
      
      if (!foundStory) {
        setError('Story not found');
      } else {
        setStory(foundStory);
        setStoryText(textData);
      }
    } catch (err) {
      console.error('Failed to load story:', err);
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Failed to load story. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleScroll = (event: any) => {
    if (isAutoScrolling.current) return;
    
    const scrollY = event.nativeEvent.contentOffset.y;
    const pageIndex = Math.floor(scrollY / PAGE_HEIGHT);
    const newPage = pageIndex + 1;
    
    if (newPage !== currentPage && story && newPage >= 1 && newPage <= story.pageCount) {
      setCurrentPage(newPage);
    }
  };

  const playAudioForPage = async (pageNumber: number) => {
    try {
      // Stop any currently playing audio
      await cleanupAudio();

      const audioUrl = getStoryPageAudioUrl(storyId, pageNumber);
      
      // Create and load the sound
      const { sound } = await Audio.Sound.createAsync(
        {
          uri: audioUrl,
          headers: authHeaders || undefined,
        },
        { shouldPlay: true }
      );

      soundRef.current = sound;
      setIsPlaying(true);

      // Set up callback for when audio finishes
      sound.setOnPlaybackStatusUpdate((status) => {
        if (status.isLoaded && status.didJustFinish) {
          handleAudioFinished(pageNumber);
        }
      });
    } catch (err) {
      console.error('Failed to play audio:', err);
      setIsPlaying(false);
    }
  };

  const handleAudioFinished = async (pageNumber: number) => {
    setIsPlaying(false);
    
    // Auto-advance to next page if available
    if (story && pageNumber < story.pageCount) {
      const nextPage = pageNumber + 1;
      
      // Set flag to prevent scroll handler from interfering
      isAutoScrolling.current = true;
      
      // Auto-scroll to next page
      scrollViewRef.current?.scrollTo({
        y: (nextPage - 1) * PAGE_HEIGHT,
        animated: true,
      });
      
      // Update current page
      setCurrentPage(nextPage);
      
      // Wait for scroll animation to complete, then play next page
      setTimeout(() => {
        isAutoScrolling.current = false;
        playAudioForPage(nextPage);
      }, 600);
    }
    // If last page, just stay idle
  };

  const handleListenPress = async () => {
    if (isPlaying) {
      await cleanupAudio();
    } else {
      await playAudioForPage(currentPage);
    }
  };

  const handleBackPress = async () => {
    await cleanupAudio();
    router.push('/stories/index' as any);
  };

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color={Colors.primary} />
        <Text style={styles.loadingText}>Loading story...</Text>
      </View>
    );
  }

  if (error || !story || !storyText) {
    return (
      <View style={styles.centerContainer}>
        <Text style={styles.errorText}>{error || 'Story not found'}</Text>
        <TouchableOpacity style={styles.backButton} onPress={handleBackPress}>
          <Text style={styles.backButtonText}>Back to Stories</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const textStyle = getStoryTextStyle(storyId);

  return (
    <View style={styles.container}>
      {/* Fixed Listen Button Header */}
      <View style={styles.fixedHeader}>
        <TouchableOpacity
          style={styles.listenButton}
          onPress={handleListenPress}
          activeOpacity={0.8}
        >
          <Ionicons 
            name={isPlaying ? "stop-circle" : "volume-high"} 
            size={24} 
            color={Colors.on_primary} 
          />
          <Text style={styles.listenButtonText}>
            {isPlaying ? 'Stop' : 'Listen'}
          </Text>
        </TouchableOpacity>
      </View>

      {/* Continuous Scroll Story Content */}
      <ScrollView
        ref={scrollViewRef}
        showsVerticalScrollIndicator={false}
        onScroll={handleScroll}
        scrollEventThrottle={16}
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
      >
        {storyText.map((page, index) => {
          const pageNumber = index + 1;
          const imageUrl = getStoryPageImageUrl(storyId, pageNumber);

          return (
            <View key={pageNumber} style={styles.page}>
              {/* Text Section - Top Half */}
              <View style={styles.textSection}>
                <Text style={[styles.storyText, textStyle]}>
                  {page.storyText}
                </Text>
              </View>

              {/* Image Section - Bottom Half */}
              <View style={styles.imageSection}>
                <Image
                  source={{
                    uri: imageUrl,
                    headers: authHeaders || undefined,
                  }}
                  style={styles.pageImage}
                  resizeMode="contain"
                />
              </View>
            </View>
          );
        })}
      </ScrollView>
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
  fixedHeader: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: HEADER_HEIGHT,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    zIndex: 1000,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: Spacing.xl,
  },
  listenButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.primary,
    paddingHorizontal: Spacing.xl * 1.5,
    paddingVertical: Spacing.md,
    borderRadius: Radius.full,
    shadowColor: Colors.on_surface,
    shadowOffset: {
      width: 0,
      height: 4,
    },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  listenButtonText: {
    ...Typography.labelLarge,
    color: Colors.on_primary,
    fontWeight: '600',
    marginLeft: Spacing.sm,
    fontSize: 18,
  },
  scrollView: {
    flex: 1,
    marginTop: HEADER_HEIGHT,
  },
  scrollContent: {
    paddingBottom: Spacing.xl,
  },
  page: {
    height: PAGE_HEIGHT,
    width: SCREEN_WIDTH,
  },
  textSection: {
    height: PAGE_HEIGHT * 0.5,
    paddingHorizontal: Spacing.xl,
    paddingVertical: Spacing.xl,
    justifyContent: 'center',
    backgroundColor: Colors.surface,
  },
  storyText: {
    ...Typography.bodyLarge,
  },
  imageSection: {
    height: PAGE_HEIGHT * 0.5,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: Colors.surface,
  },
  pageImage: {
    width: SCREEN_WIDTH * 0.9,
    height: PAGE_HEIGHT * 0.45,
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
  backButton: {
    backgroundColor: Colors.primary,
    paddingHorizontal: Spacing.xl,
    paddingVertical: Spacing.md,
    borderRadius: Radius.full,
  },
  backButtonText: {
    ...Typography.labelLarge,
    color: Colors.on_primary,
  },
});
