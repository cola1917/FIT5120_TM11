/**
 * useUserProfile — Custom hook for accessing and managing the user profile.
 *
 * Provides reactive access to the user profile stored locally.
 * Components using this hook will re-render when the profile changes.
 */

import { useCallback, useEffect, useState } from 'react';
import {
  UserProfile,
  createUserProfile,
  deleteUserProfile,
  getUserProfile,
  AvatarId,
  FoodPreferences,
} from '@/services/userProfile';

export interface UseUserProfileResult {
  profile: UserProfile | null;
  loading: boolean;
  reload: () => Promise<void>;
  create: (username: string, avatarId: AvatarId, age: number, foodPreferences?: FoodPreferences) => Promise<void>;
  remove: () => Promise<void>;
}

export function useUserProfile(): UseUserProfileResult {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const p = await getUserProfile();
      setProfile(p);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const create = useCallback(
    async (username: string, avatarId: AvatarId, age: number, foodPreferences?: FoodPreferences) => {
      const p = await createUserProfile(username, avatarId, age, foodPreferences);
      setProfile(p);
    },
    []
  );

  const remove = useCallback(async () => {
    await deleteUserProfile();
    setProfile(null);
  }, []);

  return { profile, loading, reload, create, remove };
}
