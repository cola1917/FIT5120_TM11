/**
 * Daily Challenge API Service
 * 
 * Handles communication with the Daily Challenge backend endpoints.
 */

import { getToken } from './auth';

const BACKEND_URL = 'https://fit5120-tm11.onrender.com';

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
