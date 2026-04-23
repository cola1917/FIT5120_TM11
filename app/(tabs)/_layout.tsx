import { Tabs } from 'expo-router';
import { BookOpen, Compass, Flag, ScanLine } from 'lucide-react-native';
import React from 'react';

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarStyle: {
          backgroundColor: '#111111',
          borderTopWidth: 0,
          height: 110,
          paddingTop: 8,
          // paddingBottom: 8,
        },
        tabBarActiveTintColor: '#1E90FF',
        tabBarInactiveTintColor: '#8E8E93',
        tabBarLabelStyle: {
          fontSize: 11,
          fontWeight: '700',
        },
      }}
      initialRouteName="scan"
    >
      <Tabs.Screen
        name="goal"
        options={{
          title: 'Goal',
          tabBarIcon: ({ color, size }) => <Flag color={color} size={size} />,
        }}
      />

      <Tabs.Screen
        name="scan"
        options={{
          title: 'Scan',
          tabBarIcon: ({ color, size }) => <ScanLine color={color} size={size} />,
        }}
      />

      <Tabs.Screen
        name="stories"
        options={{
          title: 'Stories',
          tabBarIcon: ({ color, size }) => <BookOpen color={color} size={size} />,
        }}
      />

      <Tabs.Screen
        name="heroWorld"
        options={{
          title: "Hero World",
          tabBarIcon: ({ color, size}) => <Compass color={color} size={size}/>,
        }}
      />
    </Tabs>
  );
}
