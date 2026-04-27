import { Stack } from 'expo-router';
import React from 'react';

export default function StoriesLayout() {
  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="index" />
      <Stack.Screen name="[storyId]" options={{headerShown: true}}/>
      <Stack.Screen name="food-fact" />
    </Stack>
  );
}
