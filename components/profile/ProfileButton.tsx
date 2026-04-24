/**
 * ProfileButton — Round avatar button shown in the app header.
 *
 * Navigates to the profile page when pressed.
 * Shows the avatar button emoji if a profile exists, or a generic user icon.
 */

import React, { useCallback, useEffect, useState } from 'react';
import { StyleSheet, Text, TouchableOpacity } from 'react-native';
import { router, useFocusEffect } from 'expo-router';
import { Colors } from '@/constants/colors';
import { getUserProfile, UserProfile } from '@/services/userProfile';
import { Radius } from '@/constants/radius';
import { Image } from 'expo-image';

export default function ProfileButton() {
  const [profile, setProfile] = useState<UserProfile>();

  const getAvatarButtonImage = () => {
    switch (profile?.avatarId) {
      case 'hero':
        if (profile.totalPoints > 300) return (<Image source={require('../../assets/images/avatar/hero-4.png')} style={styles.avatarButtonImage}/>);
        if (profile.totalPoints > 200) return (<Image source={require('../../assets/images/avatar/hero-3.png')} style={styles.avatarButtonImage}/>);
        if (profile.totalPoints > 100) return (<Image source={require('../../assets/images/avatar/hero-2.png')} style={styles.avatarButtonImage}/>);
        return (<Image source={require('../../assets/images/avatar/hero-1.png')} style={styles.avatarButtonImage}/>);
      case 'princess':
        if (profile.totalPoints > 300) return (<Image source={require('../../assets/images/avatar/princess-4.png')} style={styles.avatarButtonImage}/>);
        if (profile.totalPoints > 200) return (<Image source={require('../../assets/images/avatar/princess-3.png')} style={styles.avatarButtonImage}/>);
        if (profile.totalPoints > 100) return (<Image source={require('../../assets/images/avatar/princess-2.png')} style={styles.avatarButtonImage}/>);
        return (<Image source={require('../../assets/images/avatar/princess-1.png')} style={styles.avatarButtonImage}/>);
      default:
        break;
    }
  }

  const loadAvatar = useCallback(async () => {
    const profile = await getUserProfile();
    setProfile(profile ?? undefined);
  }, []);

  useFocusEffect(
    useCallback(() => {
      loadAvatar();
    }, [loadAvatar])
  );

  const handlePress = () => {
    router.push('/profile');
  };

  return (
    <TouchableOpacity style={styles.button} onPress={handlePress} activeOpacity={0.8}>
      {profile ? getAvatarButtonImage() : <Text style={styles.emoji}>{'👤'}</Text>}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  button: {
    width: 44,
    height: 44,
    borderRadius: Radius.full,
    backgroundColor: Colors.primary_container,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: Colors.primary,
  },
  avatarButtonImage: {
    width: '100%',
    height: '100%',
    borderRadius: Radius.full
  },
  emoji: {
    fontSize: 22,
  },
});
