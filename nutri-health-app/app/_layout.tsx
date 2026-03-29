import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { Drawer } from 'expo-router/drawer';
import { Colors } from '../constants/Colors';
import { Typography } from '../constants/Typography';

export default function RootLayout() {
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
      </Drawer>
    </GestureHandlerRootView>
  );
}
