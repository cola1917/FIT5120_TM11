import { getStoryText, getStoryPageImageUrl, getStoryPageAudioUrl, getAuthHeaders, getStories } from '@/services/stories';
import { router, useLocalSearchParams, useNavigation } from 'expo-router';
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

  const iconForAudioState = () => {
    if (audioState === 'playing') return (<Pause size={18} color="#FFFFFF" />);
    if (audioState === 'idle') return (<Play size={18} color="#FFFFFF" />);
    if (audioState === 'loading') return (<Loader size={18} color={'#FFFFFF'} />);
    if (audioState === 'error') return (<TriangleAlert size={18} color={'#FFFFFF'} />);
  }


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
        <TouchableOpacity style={styles.backButton} onPress={() => handleBackPress()}>
          <ArrowLeft size={20} color="#2D241F" />
        </TouchableOpacity>

        {/* Spacer */}
        {/* <View style={{flex: 1}}></View> */}

        <TouchableOpacity
          style={[styles.listenButton, { backgroundColor: '#E77A1F' }]}
          onPress={handleListenPress}
          disabled={audioState === 'loading'}
        >
          {iconForAudioState()}
          <Text style={styles.listenButtonText}>
            {audioState === 'playing' ? 'Pause' : 'Listen'}
          </Text>
        </TouchableOpacity>
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
    backgroundColor: Colors.surface,
  },
  content: {
    paddingBottom: 120,
  },
  heroCard: {
    margin: 16,
    marginTop: 34,
    borderRadius: 28,
    overflow: 'hidden',
    backgroundColor: Colors.surface_dim,
    flexDirection: 'row',
    alignItems: 'center'
  },
  backButton: {
    margin: Spacing.sm,
    width: 44,
    height: 44,
    borderRadius: Radius.badge,
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
  listenButton: {
    alignSelf: 'center',
    margin: Spacing.sm,
    marginLeft: 'auto',
    minWidth: 150,
    paddingVertical: 14,
    borderRadius: Radius.button_primary,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  listenButtonText: {
    color: Colors.on_secondary,
    fontSize: 18,
    fontWeight: '900',
  },
  pagesContainer: {
    paddingHorizontal: 16,
  },
  pageCard: {
    backgroundColor: Colors.surface_bright,
    borderRadius: 24,
    borderWidth: 2,
    borderColor: '#F1E3C8',
    marginBottom: 16,
  },
  pageNumber: {
    paddingLeft: Spacing.spacing_4,
    paddingTop: Spacing.spacing_4,
    fontSize: 13,
    fontWeight: '800',
    color: '#8B6F47',
  },
  pageText: {
    fontSize: 22,
    lineHeight: 34,
    color: '#2D241F',
    fontWeight: '500',
    marginBottom: 16,
    padding: Spacing.spacing_4
  },
  pageImage: {
    width: '100%',
    aspectRatio: 1,
    borderBottomLeftRadius: Radius.card,
    borderBottomRightRadius: Radius.card,
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
