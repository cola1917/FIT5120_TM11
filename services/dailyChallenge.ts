/**
 * Daily Challenge API Service
 * 
 * Handles communication with the Daily Challenge backend endpoints.
 * Also manages local storage for tracking completed challenges per user.
 */

import { getToken } from './auth';
import { getUserProfile } from './userProfile';
import AsyncStorage from '@react-native-async-storage/async-storage';

const BACKEND_URL = 'https://fit5120-tm11.onrender.com';
const DAILY_CHALLENGE_COMPLETED_KEY = 'daily_challenge_completed_';

/**
 * Get the storage key for a specific date and user
 */
async function getStorageKeyForDate(date: Date): Promise<string> {
  const dateStr = date.toISOString().split('T')[0]; // Format: YYYY-MM-DD
  
  // Get current user profile to bind to user
  const profile = await getUserProfile();
  const userId = profile?.username || 'anonymous';
  
  return `${DAILY_CHALLENGE_COMPLETED_KEY}${userId}_${dateStr}`;
}

/**
 * Check if the daily challenge has been completed today
 */
export async function isDailyChallengeCompletedToday(): Promise<boolean> {
  try {
    const todayKey = await getStorageKeyForDate(new Date());
    const value = await AsyncStorage.getItem(todayKey);
    return value === 'true';
  } catch (error) {
    console.error('Error checking daily challenge completion:', error);
    return false;
  }
}

/**
 * Mark the daily challenge as completed for today
 */
export async function markDailyChallengeCompletedToday(): Promise<void> {
  try {
    const todayKey = await getStorageKeyForDate(new Date());
    await AsyncStorage.setItem(todayKey, 'true');
  } catch (error) {
    console.error('Error marking daily challenge as completed:', error);
  }
}

export interface DailyChallengeTask {
  id: number;
  task_name: string;
  tips: string;
}

export interface DailyChallengeCompleteResponse {
  id: number;
  task_name: string;
  feedback: string;
}

/**
 * Get the next daily challenge task
 * 
 * @param excludeId - Optional task ID to exclude (to avoid getting the same task)
 * @returns The next daily challenge task
 * @throws Error if the request fails
 */
export async function getNextDailyChallenge(excludeId?: number): Promise<DailyChallengeTask> {
  try {
    const token = await getToken();
    
    let url = `${BACKEND_URL}/daily-challenge/next`;
    if (excludeId !== undefined && excludeId !== null) {
      url += `?exclude_id=${excludeId}`;
    }

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || 'Failed to get daily challenge');
    }

    const data: DailyChallengeTask = await response.json();
    return data;
  } catch (error: any) {
    console.error('Error fetching daily challenge:', error);
    throw error;
  }
}

/**
 * Complete a daily challenge and get feedback
 * 
 * @param taskId - The ID of the task to complete
 * @returns The completion response with feedback
 * @throws Error if the request fails
 */
export async function completeDailyChallenge(taskId: number): Promise<DailyChallengeCompleteResponse> {
  try {
    const token = await getToken();

    const response = await fetch(`${BACKEND_URL}/daily-challenge/complete`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        id: taskId,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || 'Failed to complete daily challenge');
    }

    const data: DailyChallengeCompleteResponse = await response.json();
    return data;
  } catch (error: any) {
    console.error('Error completing daily challenge:', error);
    throw error;
  }
}
