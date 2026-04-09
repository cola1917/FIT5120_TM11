import { getStoryText, getStoryPageImageUrl, getStoryPageAudioUrl } from '@/services/stories';
import { router, useLocalSearchParams } from 'expo-router';
import * as Speech from 'expo-speech';
import { ArrowLeft, Pause, Play } from 'lucide-react-native';
import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Image,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';

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

  const [story, setStory] = useState<Story | null>(null);
  const [storyTextData, setStoryTextData] = useState<StoryTextData | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [currentPage, setCurrentPage] = useState(0);

  const loadStory = async () => {
    setLoading(true);
    setLoadFailed(false);

    try {
      // Fetch story metadata and text content
      const textData = await getStoryText(storyId);
      
      setStory({
        id: storyId,
        title: storyId.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
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

  useEffect(() => {
    if (storyId) {
      loadStory();
    }
  }, [storyId]);

  useEffect(() => {
    return () => {
      Speech.stop();
    };
  }, []);

  const handleToggleListen = () => {
    if (!storyTextData) return;

    if (isSpeaking) {
      Speech.stop();
      setIsSpeaking(false);
      return;
    }

    const fullStoryText = storyTextData.pages.map((page) => page.storyText).join(' ');

    if (!fullStoryText.trim()) {
      Alert.alert('Audio unavailable', 'Audio is unavailable at the moment.');
      return;
    }

    try {
      Speech.speak(fullStoryText, {
        language: 'en-US',
        rate: 0.9,
        pitch: 1.0,
        onStart: () => setIsSpeaking(true),
        onDone: () => setIsSpeaking(false),
        onStopped: () => setIsSpeaking(false),
        onError: () => {
          setIsSpeaking(false);
          Alert.alert('Audio unavailable', 'Audio is unavailable at the moment.');
        },
      });
    } catch {
      setIsSpeaking(false);
      Alert.alert('Audio unavailable', 'Audio is unavailable at the moment.');
    }
  };

  const handleOpenFoodFact = () => {
    if (!story) return;

    router.push({
      pathname: '/stories/food-fact',
      params: { storyId: story.id },
    });
  };

  const handleNextPage = () => {
    if (!storyTextData) return;
    if (currentPage < storyTextData.pages.length - 1) {
      setCurrentPage(currentPage + 1);
    }
  };

  const handlePrevPage = () => {
    if (currentPage > 0) {
      setCurrentPage(currentPage - 1);
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
          source={{ uri: imageUrl }}
          style={styles.coverImage}
          resizeMode="cover"
        />

        <View style={styles.heroOverlay} />

        <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
          <ArrowLeft size={20} color="#2D241F" />
        </TouchableOpacity>

        <View style={styles.heroContent}>
          <View style={styles.titleBubble}>
            <Text style={styles.storyTitle}>{story.title}</Text>
          </View>

          <TouchableOpacity
            style={[styles.listenButton, { backgroundColor: '#E77A1F' }]}
            onPress={handleToggleListen}
          >
            {isSpeaking ? (
              <Pause size={18} color="#FFFFFF" />
            ) : (
              <Play size={18} color="#FFFFFF" />
            )}
            <Text style={styles.listenButtonText}>
              {isSpeaking ? 'Pause' : 'Listen'}
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
            source={{ uri: imageUrl }}
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
          ) : (
            <TouchableOpacity style={styles.factButton} onPress={handleOpenFoodFact}>
              <Text style={styles.factButtonText}>Let's Explore!</Text>
            </TouchableOpacity>
          )}
        </View>

        {currentPage === story.pageCount - 1 && (
          <View style={styles.factPromptCard}>
            <Text style={styles.factPromptTitle}>Want to know more?</Text>

            <Text style={styles.factPromptText}>
              Tap to discover something new about this healthy food.
            </Text>

            <Text style={styles.outcomeTitle}>Story Outcome:</Text>
            <Text style={styles.outcomeText}>{storyTextData.outcome}</Text>
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
  outcomeTitle: {
    fontSize: 18,
    fontWeight: '900',
    color: '#2D241F',
    marginTop: 16,
    marginBottom: 8,
    textAlign: 'center',
  },
  outcomeText: {
    fontSize: 15,
    lineHeight: 22,
    color: '#6C5B4F',
    textAlign: 'center',
    fontWeight: '600',
  },
});
