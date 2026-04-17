/**
 * Plate — The player's plate at the bottom of the screen
 * Shows up to 3 caught ingredient slots in a triangle arrangement.
 *
 * Performance: Wrapped in React.memo so it only re-renders when
 * plateIngredients actually change, not on timer ticks or ingredient spawns.
 */

import React, { useEffect, useRef } from 'react';
import { View, Text, StyleSheet, LayoutChangeEvent } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
} from 'react-native-reanimated';
import { Colors } from '@/constants/colors';
import { Radius } from '@/constants/radius';
import { Spacing } from '@/constants/spacing';
import { IngredientDefinition } from '@/constants/GameConfig';

const PLATE_SIZE = 200;
const SLOT_SIZE = 56;

// Triangle positions for 3 slots within the plate
// Slot 0: top-center, Slot 1: bottom-left, Slot 2: bottom-right
const SLOT_POSITIONS = [
  { top: 16, left: PLATE_SIZE / 2 - SLOT_SIZE / 2 },
  { top: PLATE_SIZE / 2 - 4, left: 16 },
  { top: PLATE_SIZE / 2 - 4, left: PLATE_SIZE - SLOT_SIZE - 16 },
];

interface PlateZone {
  x: number;
  y: number;
  width: number;
  height: number;
}

interface PlateProps {
  plateIngredients: IngredientDefinition[];
  onPlateLayout: (zone: PlateZone) => void;
}

interface IngredientSlotProps {
  ingredient: IngredientDefinition | null;
  position: { top: number; left: number };
}

function IngredientSlot({ ingredient, position }: IngredientSlotProps) {
  const scale = useSharedValue(0);
  const prevIngredient = useRef<IngredientDefinition | null>(null);

  useEffect(() => {
    if (ingredient && ingredient !== prevIngredient.current) {
      scale.value = 0;
      scale.value = withSpring(1, { damping: 10, stiffness: 200 });
    } else if (!ingredient) {
      scale.value = 0;
    }
    prevIngredient.current = ingredient;
  }, [ingredient]);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));

  return (
    <View
      style={[
        styles.slot,
        {
          top: position.top,
          left: position.left,
          borderStyle: ingredient ? 'solid' : 'dashed',
          borderColor: ingredient ? 'transparent' : Colors.outline_variant,
          backgroundColor: ingredient ? ingredient.color : 'transparent',
        },
      ]}
    >
      {ingredient ? (
        <Animated.Text style={[styles.slotEmoji, animatedStyle]}>
          {ingredient.emoji}
        </Animated.Text>
      ) : null}
    </View>
  );
}

function PlateInner({ plateIngredients, onPlateLayout }: PlateProps) {
  const handleLayout = (event: LayoutChangeEvent) => {
    const { x, y, width, height } = event.nativeEvent.layout;
    onPlateLayout({ x, y, width, height });
  };

  return (
    <View style={styles.wrapper} onLayout={handleLayout}>
      <View style={styles.plate}>
        {SLOT_POSITIONS.map((pos, idx) => (
          <IngredientSlot
            key={idx}
            ingredient={plateIngredients[idx] ?? null}
            position={pos}
          />
        ))}
      </View>
      <Text style={styles.hint}>
        {plateIngredients.length === 0 ? 'Drag ingredients here!' : `${plateIngredients.length}/3`}
      </Text>
    </View>
  );
}

const Plate = React.memo(PlateInner);
export default Plate;

const styles = StyleSheet.create({
  wrapper: {
    alignItems: 'center',
    gap: Spacing.xs,
  },
  plate: {
    width: PLATE_SIZE,
    height: PLATE_SIZE,
    borderRadius: PLATE_SIZE / 2,
    backgroundColor: Colors.surface_container_lowest,
    shadowColor: Colors.shadow,
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.1,
    shadowRadius: 20,
    elevation: 6,
    position: 'relative',
    borderWidth: 3,
    borderColor: Colors.surface_container_high,
  },
  slot: {
    position: 'absolute',
    width: SLOT_SIZE,
    height: SLOT_SIZE,
    borderRadius: Radius.lg,
    borderWidth: 2,
    justifyContent: 'center',
    alignItems: 'center',
  },
  slotEmoji: {
    fontSize: 30,
  },
  hint: {
    fontSize: 13,
    color: Colors.on_surface_variant,
    fontStyle: 'italic',
  },
});
