import { getStoryText, getStoryPageImageUrl, getStoryPageAudioUrl, getAuthHeaders, getStories } from '@/services/stories';
import { router, useLocalSearchParams, useNavigation, Stack } from 'expo-router';
import { ArrowLeft, Loader, Pause, Play, TriangleAlert } from 'lucide-react-native';
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
  NativeScrollEvent,
  NativeSyntheticEvent,
} from 'react-native';
import { Image } from 'expo-image';
import { Audio } from 'expo-av';
import { Spacing } from '@/constants/spacing';
import { Radius } from '@/constants/radius';
import { Colors } from '@/constants/colors';

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
  const [audioState, setAudioState] = useState<'playing' | 'loading' | 'idle' | 'error'>('idle');

  const scrollViewRef = useRef<ScrollView | null>(null);
  const soundRef = useRef<Audio.Sound | null>(null);
  const pageHeightsRef = useRef<number[]>([]);
  const isAutoScrollingRef = useRef(false);

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

    // Stop audio whenever the screen loses focus (e.g. navigating away via
    // swipe-back, tab switch, or any other navigation gesture).
    const unsubscribeBlur = navigation.addListener('blur', () => {
      cleanupAudio();
    });

    return () => {
      unsubscribeBlur();
      cleanupAudio();
    };
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
      setAudioState('loading');

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
      // Play audio for the current page being displayed (currentPage is 0-indexed, but pages are 1-indexed)
      await playAudioForPage(currentPage + 1);
    } else if (audioState === 'playing') {
      await cleanupAudio();
    }
  };

  const handleAudioFinished = async (pageNumber: number) => {
    setAudioState('idle');
    
    // Auto-advance to next page if available (pageNumber is 1-indexed)
    if (story && pageNumber < story.pageCount) {
      const nextPageIndex = pageNumber; // Next page index in 0-indexed array
      
      // Set flag to prevent scroll handler from interfering
      isAutoScrollingRef.current = true;
      
      // Calculate scroll position for next page
      const scrollY = pageHeightsRef.current.slice(0, nextPageIndex).reduce((sum, height) => sum + height, 0);
      
      // Auto-scroll to next page
      scrollViewRef.current?.scrollTo({
        y: scrollY,
        animated: true,
      });
      
      // Update current page (0-indexed)
      setCurrentPage(nextPageIndex);
      
      // Wait for scroll animation to complete, then play next page (1-indexed)
      setTimeout(() => {
        isAutoScrollingRef.current = false;
        playAudioForPage(pageNumber + 1);
      }, 600);
    }
    // If last page, just stay idle
  };

  const handleViewOutcome = () => {
    if (!story) return;

    router.push({
      pathname: '/stories/story-outcome',
      params: { storyId: story.id },
    });
  };

  const handleBackPress = async () => {
    await cleanupAudio();
    navigation.goBack();
  };

  const iconForAudioState = () => {
    if (audioState === 'playing') return (<Pause size={18} color="#FFFFFF" />);
    if (audioState === 'idle') return (<Play size={18} color="#FFFFFF" />);
    if (audioState === 'loading') return (<Loader size={18} color={'#FFFFFF'} />);
    if (audioState === 'error') return (<TriangleAlert size={18} color={'#FFFFFF'} />);
  }

  const handleScroll = (event: NativeSyntheticEvent<NativeScrollEvent>) => {
    if (isAutoScrollingRef.current) return;

    const scrollY = event.nativeEvent.contentOffset.y;
    let accumulatedHeight = 0;
    let newPageIndex = 0;

    for (let i = 0; i < pageHeightsRef.current.length; i++) {
      if (scrollY < accumulatedHeight + pageHeightsRef.current[i] / 2) {
        newPageIndex = i;
        break;
      }
      accumulatedHeight += pageHeightsRef.current[i];
      newPageIndex = i + 1;
    }

    if (newPageIndex !== currentPage && newPageIndex < (story?.pageCount || 0)) {
      setCurrentPage(newPageIndex);
    }
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
          Unable to open this story right now.
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

  return (
    <>
      <Stack.Screen
        options={{
          headerShown: true,
          headerTitle: () => (
            <AutoSizeText
              style={styles.headerTitle}
              numberOfLines={1}
              fontSize={18}
              mode={ResizeTextMode.max_lines}
            >
              {story?.title || 'Story'}
            </AutoSizeText>
          ),
          headerLeft: () => (
            <TouchableOpacity onPress={handleBackPress} style={{ marginLeft: 8 }}>
              <ArrowLeft size={24} color="#2D241F" />
            </TouchableOpacity>
          ),
          headerRight: () => (
            <TouchableOpacity
              style={[styles.headerListenButton, { backgroundColor: '#E77A1F' }]}
              onPress={handleListenPress}
              disabled={audioState === 'loading'}
            >
              {iconForAudioState()}
              <Text style={styles.headerListenButtonText}>
                {audioState === 'playing' ? 'Pause' : 'Listen'}
              </Text>
            </TouchableOpacity>
          ),
          headerStyle: {
            backgroundColor: Colors.surface,
          },
        }}
      />
      <ScrollView
        ref={scrollViewRef}
        style={styles.container}
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
        onScroll={handleScroll}
        scrollEventThrottle={16}
      >
        <View style={styles.pagesContainer}>
          {storyTextData.pages.map((p, i) => (
            <View
              key={i}
              onLayout={(event) => {
                const { height } = event.nativeEvent.layout;
                pageHeightsRef.current[i] = height;
              }}
            >
              <Text style={styles.pageText}>{p.storyText}</Text>
              <Image
                source={{ uri: getStoryPageImageUrl(storyId, i + 1), headers: authHeaders || undefined }}
                style={styles.pageImage}
                resizeMode="cover"
              />
            </View>
          ))}

          <View style={styles.factPromptCard}>
            <Text style={styles.factPromptTitle}>Want to know more?</Text>

            <Text style={styles.factPromptText}>
              Tap to discover something new about this healthy food.
            </Text>

            <TouchableOpacity style={styles.outcomeButton} onPress={handleViewOutcome}>
              <Text style={styles.outcomeButtonText}>View Story Outcome</Text>
            </TouchableOpacity>
          </View>
        </View>
      </ScrollView>
    </>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.surface,
  },
  content: {
    paddingBottom: 120,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#2D241F',
    maxWidth: 200,
  },
  headerListenButton: {
    marginRight: 12,
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: Radius.button_primary,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
  },
  headerListenButtonText: {
    color: Colors.on_secondary,
    fontSize: 16,
    fontWeight: '900',
  },
  pagesContainer: {

  },
  pageText: {
    fontSize: 22,
    lineHeight: 34,
    color: '#2D241F',
    fontWeight: '500',
    paddingVertical: Spacing.spacing_4,
    paddingHorizontal: Spacing.spacing_6
  },
  pageImage: {
    width: '100%',
    aspectRatio: 1,
    backgroundColor: '#EAEAEA',
  },
  factPromptCard: {
    margin: Spacing.lg,
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
