import { getStoryText, getStoryPageImageUrl, getStoryPageAudioUrl, getAuthHeaders, getStories } from '@/services/stories';
import { router, useLocalSearchParams, useNavigation } from 'expo-router';
import { ArrowLeft, Pause, Play } from 'lucide-react-native';
import React, { useEffect, useRef, useState } from 'react';
import { AutoSizeText, ResizeTextMode } from 'react-native-auto-size-text';
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { Image } from 'expo-image';
import { Audio } from 'expo-av';

interface StoryPage {
  storyText: string;
}

interface StoryTextData {
  pages: StoryPage[];
  outcome: string;
}

interface Story {
  id: string;
  title: string;
  pageCount: number;
}

export default function StoryReaderScreen() {
  const { storyId } = useLocalSearchParams<{ storyId: string }>();
  const navigation = useNavigation();

  const [story, setStory] = useState<Story | null>(null);
  const [storyTextData, setStoryTextData] = useState<StoryTextData | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);
  const [currentPage, setCurrentPage] = useState(0);
  const [authHeaders, setAuthHeaders] = useState<{ Authorization: string } | null>(null);
  const [audioState, setAudioState] = useState<'playing'| 'idle' | 'error'>('idle');

  const soundRef = useRef<Audio.Sound | null>(null);

  const loadStory = async () => {
    setLoading(true);
    setLoadFailed(false);

    try {
      // Fetch story metadata and text content
      const [stories, textData] = await Promise.all([
        getStories(),
        getStoryText(storyId),
      ]);
      const foundStory = stories.find(s => s.id === storyId);
      
      setStory({
        id: storyId,
        title: foundStory?.title || '',
        pageCount: textData.pages.length,
      });
      setStoryTextData(textData);
      setCurrentPage(0);
    } catch (error) {
      console.error('Failed to load story:', error);
      setStory(null);
      setStoryTextData(null);
      setLoadFailed(true);
    } finally {
      setLoading(false);
    }
  };

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

  useEffect(() => {
    if (storyId) {
      loadStory();
    }
    loadAuthHeaders();
    setupAudio();

    return () => {
      cleanupAudio();
    }
  }, [storyId]);

  useEffect(() => {
    return () => {
      // Speech.stop();
    };
  }, []);

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
      if (story?.pageCount && pageNumber + 1 <= story.pageCount) {
        // Making this request will cause it to exist in the cache.
        // This will make the playing of the next audio file smoother.
        await Audio.Sound.createAsync(
          {
            uri: getStoryPageAudioUrl(storyId, pageNumber + 1),
            headers: authHeaders || undefined,
          },
          { shouldPlay: false }
        ).catch((e) => undefined);
      }

      soundRef.current = sound;
      setAudioState('playing');

      // Set up callback for when audio finishes
      sound.setOnPlaybackStatusUpdate((status) => {
        if (status.isLoaded && status.didJustFinish) {
          handleAudioFinished(pageNumber);
        }
      });
    } catch (err) {
      console.error('Failed to play audio:', err);
      setAudioState('error');
    }
  };

  const handleListenPress = async () => {
    if (audioState === 'idle' || audioState === 'error') {
      await playAudioForPage(currentPage + 1);
    } else if (audioState === 'playing') {
      await cleanupAudio();
    }
  };

  const handleAudioFinished = async (pageNumber: number) => {
    setAudioState('idle');
    
    // Auto-advance to next page if available
    if (story && pageNumber < story.pageCount) {
      const nextPage = pageNumber + 1;
      
      // Set flag to prevent scroll handler from interfering
      // isAutoScrolling.current = true;
      
      // Auto-scroll to next page
      // scrollViewRef.current?.scrollTo({
      //   y: (nextPage - 1) * PAGE_HEIGHT,
      //   animated: true,
      // });
      
      // Update current page
      // setCurrentPage(nextPage);
      
      // Wait for scroll animation to complete, then play next page
      // setTimeout(() => {
      //   isAutoScrolling.current = false;
      //   playAudioForPage(nextPage);
      // }, 600);
    }
    // If last page, just stay idle
  };

  const handleOpenFoodFact = () => {
    if (!story) return;

    router.push({
      pathname: '/stories/food-fact',
      params: { storyId: story.id },
    });
  };

  const handleViewOutcome = () => {
    if (!story) return;

    router.push({
      pathname: '/stories/story-outcome',
      params: { storyId: story.id },
    });
  };

  const handleNextPage = () => {
    if (!storyTextData) return;
    if (currentPage < storyTextData.pages.length - 1) {
      setCurrentPage(currentPage + 1);
      cleanupAudio();
    }
  };

  const handlePrevPage = () => {
    if (currentPage > 0) {
      setCurrentPage(currentPage - 1);
    }
  };

  const handleBackPress = async () => {
    await cleanupAudio();
    navigation.goBack();
  };


  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#E77A1F" />
        <Text style={styles.feedbackTitle}>Loading story...</Text>
        <Text style={styles.feedbackText}>
          Please wait while we get your adventure ready.
        </Text>
      </View>
    );
  }

  if (loadFailed || !story || !storyTextData) {
    return (
      <View style={styles.centered}>
        <Text style={styles.feedbackTitle}>Unable to load story</Text>
        <Text style={styles.feedbackText}>
          We could not open this story right now.
        </Text>

        <TouchableOpacity style={styles.primaryAction} onPress={loadStory}>
          <Text style={styles.primaryActionText}>Retry</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.secondaryAction} onPress={() => router.replace('/stories')}>
          <Text style={styles.secondaryActionText}>Go Home</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const currentPageData = storyTextData.pages[currentPage];
  const imageUrl = getStoryPageImageUrl(storyId, currentPage + 1);

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      showsVerticalScrollIndicator={false}
    >
      <View style={styles.heroCard}>
        <Image
          source={{ uri: imageUrl, headers: authHeaders || undefined }}
          style={styles.coverImage}
          resizeMode="cover"
        />

        <View style={styles.heroOverlay} />

        <TouchableOpacity style={styles.backButton} onPress={() => handleBackPress()}>
          <ArrowLeft size={20} color="#2D241F" />
        </TouchableOpacity>

        <View style={styles.heroContent}>
          <View style={styles.titleBubble}>
            <AutoSizeText
              mode={ResizeTextMode.max_lines}
              numberOfLines={2}
              fontSize={24}
              style={styles.storyTitle}>
              {story.title}
            </AutoSizeText>
          </View>

          <TouchableOpacity
            style={[styles.listenButton, { backgroundColor: '#E77A1F' }]}
            onPress={handleListenPress}
          >
            {audioState === 'playing' ? (
              <Pause size={18} color="#FFFFFF" />
            ) : (
              <Play size={18} color="#FFFFFF" />
            )}
            <Text style={styles.listenButtonText}>
              {audioState === 'playing' ? 'Pause' : 'Listen'}
            </Text>
          </TouchableOpacity>
        </View>
      </View>

      <View style={styles.introCard}>
        <Text style={styles.introText}>
          Page {currentPage + 1} of {story.pageCount}
        </Text>
      </View>

      <View style={styles.pagesContainer}>
        <View style={styles.pageCard}>
          <Text style={styles.pageNumber}>
            Page {currentPage + 1}/{story.pageCount}
          </Text>

          <Text style={styles.pageText}>{currentPageData.storyText}</Text>

          <Image
            source={{ uri: imageUrl, headers: authHeaders || undefined }}
            style={styles.pageImage}
            resizeMode="cover"
          />
        </View>

        <View style={styles.navigationRow}>
          <TouchableOpacity
            style={[styles.navButton, currentPage === 0 && styles.navButtonDisabled]}
            onPress={handlePrevPage}
            disabled={currentPage === 0}
          >
            <Text style={[styles.navButtonText, currentPage === 0 && styles.navButtonTextDisabled]}>
              Previous
            </Text>
          </TouchableOpacity>

          {currentPage < story.pageCount - 1 ? (
            <TouchableOpacity
              style={styles.navButton}
              onPress={handleNextPage}
            >
              <Text style={styles.navButtonText}>Next</Text>
            </TouchableOpacity>
          ) : null}
        </View>

        {currentPage === story.pageCount - 1 && (
          <View style={styles.factPromptCard}>
            <Text style={styles.factPromptTitle}>Want to know more?</Text>

            <Text style={styles.factPromptText}>
              Tap to discover something new about this healthy food.
            </Text>

            <TouchableOpacity style={styles.outcomeButton} onPress={handleViewOutcome}>
              <Text style={styles.outcomeButtonText}>View Story Outcome</Text>
            </TouchableOpacity>
          </View>
        )}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F8F5E9',
  },
  content: {
    paddingBottom: 120,
  },
  heroCard: {
    height: 330,
    margin: 16,
    marginTop: 34,
    borderRadius: 28,
    overflow: 'hidden',
    backgroundColor: '#DDD',
  },
  coverImage: {
    width: '100%',
    height: '100%',
  },
  heroOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.18)',
  },
  backButton: {
    position: 'absolute',
    top: 16,
    left: 16,
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: 'rgba(255,255,255,0.92)',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 9999,
  },
  heroContent: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'space-between',
    padding: 20,
    paddingTop: 72,
  },
  titleBubble: {
    alignSelf: 'center',
    backgroundColor: 'rgba(255,255,255,0.95)',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 18,
    maxWidth: '90%',
  },
  storyTitle: {
    fontSize: 26,
    fontWeight: '900',
    color: '#2D241F',
    textAlign: 'center',
    lineHeight: 32,
  },
  listenButton: {
    alignSelf: 'center',
    minWidth: 150,
    paddingHorizontal: 24,
    paddingVertical: 14,
    borderRadius: 999,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  listenButtonText: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: '900',
  },
  introCard: {
    marginHorizontal: 16,
    marginBottom: 16,
    backgroundColor: '#FFF8E1',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderWidth: 2,
    borderColor: '#F2DFC0',
  },
  introText: {
    textAlign: 'center',
    fontSize: 15,
    lineHeight: 22,
    color: '#705D50',
    fontWeight: '700',
  },
  pagesContainer: {
    paddingHorizontal: 16,
  },
  pageCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 24,
    padding: 18,
    borderWidth: 2,
    borderColor: '#F1E3C8',
    marginBottom: 16,
  },
  pageNumber: {
    fontSize: 13,
    fontWeight: '800',
    color: '#8B6F47',
    marginBottom: 12,
  },
  pageText: {
    fontSize: 22,
    lineHeight: 34,
    color: '#2D241F',
    fontWeight: '500',
    marginBottom: 16,
  },
  pageImage: {
    width: '100%',
    height: 220,
    borderRadius: 18,
    backgroundColor: '#EAEAEA',
  },
  factPromptCard: {
    backgroundColor: '#FFF8E8',
    borderRadius: 24,
    padding: 18,
    borderWidth: 2,
    borderColor: '#F2DFC0',
    marginBottom: 12,
  },
  factPromptTitle: {
    fontSize: 22,
    fontWeight: '900',
    color: '#2D241F',
    marginBottom: 8,
    textAlign: 'center',
  },
  factPromptText: {
    fontSize: 15,
    lineHeight: 22,
    color: '#6C5B4F',
    textAlign: 'center',
    marginBottom: 14,
  },
  factButton: {
    backgroundColor: '#E77A1F',
    borderRadius: 999,
    paddingVertical: 14,
    alignItems: 'center',
  },
  factButtonText: {
    color: '#FFFFFF',
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
  navigationRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
    gap: 12,
  },
  navButton: {
    flex: 1,
    backgroundColor: '#FFF3E3',
    borderRadius: 999,
    paddingVertical: 14,
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#F1E3C8',
  },
  navButtonDisabled: {
    opacity: 0.5,
  },
  navButtonText: {
    color: '#705D50',
    fontSize: 16,
    fontWeight: '900',
  },
  navButtonTextDisabled: {
    color: '#A0A0A0',
  },
  outcomeButton: {
    backgroundColor: '#E77A1F',
    borderRadius: 999,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 8,
  },
  outcomeButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '900',
  },
});
