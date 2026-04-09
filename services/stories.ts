/**
 * Stories API Service
 * 
 * Handles communication with the stories endpoints on the NutriHealth backend.
 * Includes story fetching, image and audio URL generation.
 */

import { getToken, clearToken } from './auth';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

const API_TIMEOUT = 30000; // 30 seconds

/**
 * Story interface
 */
export interface Story {
  id: string;
  title: string;
  coverImage: string;
  pageCount: number;
}

/**
 * Story page interface - represents a single page's text content
 */
export interface StoryPage {
  storyText: string;
}

/**
 * Story text data interface - contains all pages' text content
 */
export interface StoryTextData {
  pages: StoryPage[];
  outcome: string;
}

/**
 * Stories response from the API
 */
export interface StoriesResponse {
  stories: Story[];
}

/**
 * API Error class
 */
export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public details?: any
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * Fetch the list of available stories
 * 
 * @returns Array of stories with metadata
 * @throws ApiError if the request fails
 */
export async function getStories(): Promise<Story[]> {
  try {
    // Get valid authentication token
    const token = await getToken();

    // Create abort controller for timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT);

    try {
      const response = await fetch(`${BACKEND_URL}/stories`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      // Handle 401 - token expired or invalid
      if (response.status === 401) {
        console.log('Token expired, refreshing...');
        await clearToken();
        const newToken = await getToken();
        
        const retryResponse = await fetch(`${BACKEND_URL}/stories`, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${newToken}`,
          },
        });
        
        if (!retryResponse.ok) {
          const errorData = await retryResponse.json().catch(() => ({}));
          throw new ApiError(
            errorData.detail || 'Authentication failed',
            retryResponse.status,
            errorData
          );
        }
        
        const data: StoriesResponse = await retryResponse.json();
        return data.stories;
      }

      // Handle other non-OK responses
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new ApiError(
          errorData.detail || 'Failed to fetch stories',
          response.status,
          errorData
        );
      }

      // Parse and return response
      const data: StoriesResponse = await response.json();
      return data.stories;
    } catch (error) {
      clearTimeout(timeoutId);
      throw error;
    }
  } catch (error: any) {
    // Handle abort (timeout)
    if (error.name === 'AbortError') {
      throw new ApiError(
        'Request timed out. Please try again!',
        408
      );
    }

    // Handle network errors
    if (error.message === 'Network request failed') {
      throw new ApiError(
        'Network error. Please check your internet connection!',
        0
      );
    }

    // Re-throw ApiError
    if (error instanceof ApiError) {
      throw error;
    }

    // Handle unknown errors
    throw new ApiError(
      'Something went wrong. Please try again!',
      500,
      error
    );
  }
}

/**
 * Get URL for story cover image
 * 
 * @param storyId The story ID
 * @returns URL string for the cover image
 */
export function getStoryCoverUrl(storyId: string): string {
  return `${BACKEND_URL}/stories/${storyId}/cover`;
}

/**
 * Get URL for story page image
 * 
 * @param storyId The story ID
 * @param pageNumber The page number (1-indexed)
 * @returns URL string for the page image
 */
export function getStoryPageImageUrl(storyId: string, pageNumber: number): string {
  return `${BACKEND_URL}/stories/${storyId}/pages/${pageNumber}/image`;
}

/**
 * Get URL for story page audio
 * 
 * @param storyId The story ID
 * @param pageNumber The page number (1-indexed)
 * @returns URL string for the page audio
 */
export function getStoryPageAudioUrl(storyId: string, pageNumber: number): string {
  return `${BACKEND_URL}/stories/${storyId}/pages/${pageNumber}/audio`;
}

/**
 * Get authorization headers for authenticated requests
 * Used when loading images/audio that require authentication
 */
export async function getAuthHeaders(): Promise<{ Authorization: string }> {
  const token = await getToken();
  return {
    Authorization: `Bearer ${token}`,
  };
}

/**
 * Fetch text content for a story
 * 
 * @param storyId The story ID
 * @returns Story text data with all pages
 * @throws ApiError if the request fails
 */
export async function getStoryText(storyId: string): Promise<StoryTextData> {
  try {
    const headers = await getAuthHeaders();
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT);
    
    try {
      const response = await fetch(
        `${BACKEND_URL}/stories/${storyId}/text`,
        {
          method: 'GET',
          headers,
          signal: controller.signal,
        }
      );
      
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        throw new ApiError(
          'Failed to fetch story text',
          response.status
        );
      }
      
      const data: StoryTextData = await response.json();
      return data;
    } catch (error) {
      clearTimeout(timeoutId);
      throw error;
    }
  } catch (error: any) {
    if (error.name === 'AbortError') {
      throw new ApiError('Request timed out. Please try again!', 408);
    }
    
    if (error.message === 'Network request failed') {
      throw new ApiError(
        'Network error. Please check your internet connection!',
        0
      );
    }
    
    if (error instanceof ApiError) {
      throw error;
    }
    
    throw new ApiError('Unable to load story', 500, error);
  }
}
