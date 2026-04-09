/**
 * API Service
 * 
 * Handles communication with the NutriHealth backend server.
 * Includes image upload, authentication, error handling, and timeout management.
 */

import { getToken, clearToken } from './auth';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';

const API_TIMEOUT = 30000; // 30 seconds

/**
 * Response from the /scan endpoint
 */
export interface ScanResponse {
  confidence: number;
  food_name: string;
  nutritional_info: {
    calories?: number;
    carbohydrates?: number;
    protein?: number;
    fats?: number;
    [key: string]: any;
  };
  assessment_score: number;
  assessment: string;
  alternatives: Array<{
    name: string;
    description?: string;
    [key: string]: any;
  }>;
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
 * Upload an image to the backend for food scanning
 * 
 * @param imageUri - Local URI of the image to upload
 * @returns Scan results from the backend
 * @throws ApiError if the upload fails
 */
export async function scanFood(imageUri: string): Promise<ScanResponse> {
  try {
    // Get valid authentication token
    const token = await getToken();
    
    // Create form data
    const formData = new FormData();
    
    // Extract filename from URI
    const filename = imageUri.split('/').pop() || 'photo.jpg';
    const match = /\.(\w+)$/.exec(filename);
    const type = match ? `image/${match[1]}` : 'image/jpeg';

    // Append image to form data
    formData.append('file', {
      uri: imageUri,
      name: filename,
      type,
    } as any);

    // Create abort controller for timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT);

    try {
      console.log('Requesting', `${BACKEND_URL}/scan`)
      const response = await fetch(`${BACKEND_URL}/scan`, {
        method: 'POST',
        body: formData,
        headers: {
          'Content-Type': 'multipart/form-data',
          'Authorization': `Bearer ${token}`,
        },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      // Handle 401 - token expired or invalid
      if (response.status === 401) {
        console.log('Token expired, refreshing...');
        // Clear cached token and retry once
        await clearToken();
        const newToken = await getToken();
        
        const retryResponse = await fetch(`${BACKEND_URL}/scan`, {
          method: 'POST',
          body: formData,
          headers: {
            'Content-Type': 'multipart/form-data',
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
        
        return await retryResponse.json();
      }

      // Handle other non-OK responses
      console.log('Response:', JSON.stringify(response));
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new ApiError(
          errorData.detail || 'Failed to scan food',
          response.status,
          errorData
        );
      }

      // Parse and return response
      const data: ScanResponse = await response.json();
      return data;
    } catch (error) {
      clearTimeout(timeoutId);
      throw error;
    }
  } catch (error: any) {
    console.log(error);

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
 * Health check endpoint
 * Tests if the backend is reachable
 */
export async function healthCheck(): Promise<boolean> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    const response = await fetch(`${BACKEND_URL}/health`, {
      method: 'GET',
      signal: controller.signal,
    });

    clearTimeout(timeoutId);
    return response.ok;
  } catch {
    return false;
  }
}

/**
 * Get the configured backend URL
 */
export function getBackendUrl(): string {
  return BACKEND_URL;
}
