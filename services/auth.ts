/**
 * Authentication Service
 *
 * Handles JWT token management for API authentication.
 * Automatically authenticates with hardcoded credentials and caches tokens.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

const TOKEN_KEY = 'auth_token';
const TOKEN_EXPIRY_KEY = 'token_expiry';
// Use your computer's LAN IP for Expo Go testing
//const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;
const BACKEND_URL = 'http://10.192.56.70:8000';
//const BACKEND_URL = 'http://192.168.100.238:8000';

// Hardcoded credentials (for demo only)
const DEMO_USERNAME = 'demo';
//const DEMO_USERNAME = process.env.EXPO_PUBLIC_USERNAME || '';
const DEMO_PASSWORD = 'demo123';
//const DEMO_PASSWORD = process.env.EXPO_PUBLIC_PASSWORD || '';

interface TokenResponse {
  access_token: string;
  token_type: string;
}

/**
 * Request a new token from the backend
 */
async function requestNewToken(): Promise<string> {
  console.log(`Requesting new token at ${BACKEND_URL}/token`);
  console.log('Checking credentials:', DEMO_USERNAME, DEMO_PASSWORD);
  const formData = new URLSearchParams();
  formData.append('username', DEMO_USERNAME);
  formData.append('password', DEMO_PASSWORD);
  formData.append('grant_type', 'password');

  try {
    const response = await fetch(`${BACKEND_URL}/token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData.toString(),
    });

    console.log('Response status:', response.status);
    const responseText = await response.text();
    console.log('Response body:', responseText);

    if (!response.ok) {
      throw new Error(`Authentication failed: ${response.status} - ${responseText}`);
    }

    const data: TokenResponse = JSON.parse(responseText);

    // Calculate expiry time (24 hours from now)
    const expiryTime = Date.now() + (24 * 60 * 60 * 1000);

    // Cache token and expiry
    await AsyncStorage.setItem(TOKEN_KEY, data.access_token);
    await AsyncStorage.setItem(TOKEN_EXPIRY_KEY, expiryTime.toString());

    return data.access_token;
  } catch (error) {
    console.error('Error in requestNewToken:', error);
    throw error;
  }
}

/**
 * Check if cached token is expired
 */
async function isTokenExpired(): Promise<boolean> {
  const expiryStr = await AsyncStorage.getItem(TOKEN_EXPIRY_KEY);
  if (!expiryStr) return true;

  const expiry = parseInt(expiryStr, 10);
  return Date.now() >= expiry;
}

/**
 * Get valid authentication token
 * Returns cached token if valid, otherwise requests new one
 */
export async function getToken(): Promise<string> {
  try {
    // Check if we have a cached token
    const cachedToken = await AsyncStorage.getItem(TOKEN_KEY);

    // If token exists and not expired, return it
    if (cachedToken && !(await isTokenExpired())) {
      console.log('Using cached token', cachedToken);
      return cachedToken;
    }

    // Otherwise, request new token
    return await requestNewToken();
  } catch (error) {
    console.error('Error getting token:', error);
    throw error;
  }
}

/**
 * Clear cached token (for logout or error scenarios)
 */
export async function clearToken(): Promise<void> {
  await AsyncStorage.removeItem(TOKEN_KEY);
  await AsyncStorage.removeItem(TOKEN_EXPIRY_KEY);
}

/**
 * Initialize authentication on app startup
 * Automatically authenticates and caches token
 */
export async function initializeAuth(): Promise<void> {
  try {
    console.log('Getting auth token');
    await getToken();
    console.log('Authentication initialized successfully');
  } catch (error) {
    console.error('Failed to initialize authentication:', error);
    throw error;
  }
}