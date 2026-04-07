import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { Drawer } from 'expo-router/drawer';
import { Colors } from '../constants/Colors';
import { Typography } from '../constants/Typography';
import { useEffect, useState } from 'react';
import { View, ActivityIndicator, Text } from 'react-native';
import { initializeAuth } from '../services/auth';

export default function RootLayout() {
  const [isAuthReady, setIsAuthReady] = useState(false);
  
  useEffect(() => {
    // Initialize authentication on app launch
    initializeAuth()
      .then(() => {
        console.log('Auth ready');
        setIsAuthReady(true);
      })
      .catch((error) => {
        console.error('Auth initialization failed:', error);
        // Still set ready to true to show app, errors will be handled per-request
        setIsAuthReady(true);
      });
  }, []);
  
  // Show loading screen while authenticating
  if (!isAuthReady) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: Colors.surface }}>
        <ActivityIndicator size="large" color={Colors.primary} />
        <Text style={{ marginTop: 16, color: Colors.on_surface, ...Typography.bodyLarge }}>
          Initializing...
        </Text>
      </View>
    );
  }
  
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <Drawer
        screenOptions={{
          drawerPosition: 'right',
          headerStyle: {
            backgroundColor: Colors.surface,
          },
          headerTintColor: Colors.on_surface,
          headerTitleStyle: {
            ...Typography.headlineMedium,
          },
          drawerStyle: {
            backgroundColor: Colors.surface_container,
            width: 280,
          },
          drawerActiveTintColor: Colors.primary,
          drawerInactiveTintColor: Colors.on_surface_variant,
          drawerLabelStyle: {
            ...Typography.titleMedium,
          },
        }}
      >
        <Drawer.Screen
          name="index"
          options={{
            drawerLabel: 'Daily Tracker',
            title: 'Daily Tracker',
          }}
        />
        <Drawer.Screen
          name="scanner/index"
          options={{
            drawerLabel: 'Scanner',
            title: 'Scanner',
          }}
        />
        <Drawer.Screen
          name="scanner/results"
          options={{
            drawerLabel: 'Results',
            title: 'Results',
          }}
        />
        <Drawer.Screen
          name="stories"
          options={{
            drawerLabel: 'Stories',
            title: 'Stories',
          }}
        />
      </Drawer>
    </GestureHandlerRootView>
  );
}
