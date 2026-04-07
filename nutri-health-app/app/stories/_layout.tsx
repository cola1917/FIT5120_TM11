import { Stack } from 'expo-router';

export default function StoriesLayout() {
  return (
    <Stack screenOptions={{headerShown: false}}>
      <Stack.Screen name="index" options={{ title: 'Stories' }} />
      <Stack.Screen name="[id]" options={{ title: 'Story', animation: 'fade' }} />
    </Stack>
  );
}
