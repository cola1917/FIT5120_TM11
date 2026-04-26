import React from 'react';

export interface Food {
  name: string;
  description: string;
  image: string;
  rating?: number;
}

// Alias for backward compatibility with existing code using SuperFood
export type SuperFood = Food;

export interface Alternative {
  name: string;
  image: string;
  tip: string;
}

export interface TryLess {
  name: string;
  image: string;
  alternative: Alternative;
}

export interface Goal {
  id: string;
  title: string;
  subtitle: string;
  icon: React.ComponentType<{ size?: number; color?: string; strokeWidth?: number }>;
  gradient: string[];
  tilt: 'left' | 'right';
  bgIcon: string;
  description: string;
  superFoods: Food[];
  tryLess: TryLess;
}
