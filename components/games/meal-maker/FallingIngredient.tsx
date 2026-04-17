/**
 * FallingIngredient — Animated ingredient that falls from top to bottom.
 *
 * Uses React Native's native touch responder system (onResponderGrant/Move/Release)
 * instead of react-native-gesture-handler's Pan gesture. This allows multiple
 * ingredients to be dragged simultaneously with different fingers, since each
 * View has its own independent responder — no shared gesture state.
 *
 * On missed drop: shrinks and despawns.
 *
 * Performance: Wrapped in React.memo so parent re-renders (timer ticks,
 * other ingredient spawns/despawns) don't interrupt this component's
 * Reanimated animations running on the UI thread.
 */

import React, { useEffect, useRef, useCallback } from 'react';
import { StyleSheet, Dimensions, Text, GestureResponderEvent } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
  withRepeat,
  runOnJS,
  Easing,
} from 'react-native-reanimated';
import { IngredientDefinition, NUM_LANES } from '@/constants/GameConfig';
import { Radius } from '@/constants/radius';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');
const INGREDIENT_SIZE = 70;
const LANE_WIDTH = SCREEN_WIDTH / NUM_LANES;

// Plate zone detection radius around the plate center
const PLATE_CATCH_RADIUS = 120;

interface PlateZone {
  x: number;
  y: number;
  width: number;
  height: number;
}

interface FallingIngredientProps {
  id: string;
  ingredient: IngredientDefinition;
  laneIndex: number;
  fallDuration: number;
  plateZone: PlateZone | null;
  onCatch: (id: string) => void;
  onDespawn: (id: string) => void;
}

function FallingIngredientInner({
  id,
  ingredient,
  laneIndex,
  fallDuration,
  plateZone,
  onCatch,
  onDespawn,
}: FallingIngredientProps) {
  const laneX = laneIndex * LANE_WIDTH + LANE_WIDTH / 2 - INGREDIENT_SIZE / 2;

  // Fall animation
  const fallY = useSharedValue(-INGREDIENT_SIZE);
  // Spin animation
  const rotation = useSharedValue(0);
  // Drag offset
  const dragX = useSharedValue(0);
  const dragY = useSharedValue(0);
  // Scale — used for shrink-on-miss despawn
  const scale = useSharedValue(1);
  // Whether caught (hide after catch)
  const isCaught = useSharedValue(false);

  const isCaughtRef = useRef(false);
  const isDespawningRef = useRef(false);

  // Store callbacks in refs so animation completion callbacks always use latest
  const onDespawnRef = useRef(onDespawn);
  onDespawnRef.current = onDespawn;
  const onCatchRef = useRef(onCatch);
  onCatchRef.current = onCatch;

  // Store plateZone in ref so responder handlers always see latest value
  const plateZoneRef = useRef(plateZone);
  plateZoneRef.current = plateZone;

  // Touch start position (absolute screen coords) for computing drag delta
  const touchStartX = useRef(0);
  const touchStartY = useRef(0);
  // Fall Y value at the moment the drag started
  const fallYAtDragStart = useRef(0);

  const handleDespawn = useCallback((ingredientId: string) => {
    onDespawnRef.current(ingredientId);
  }, []);

  useEffect(() => {
    // Start fall animation
    fallY.value = withTiming(
      SCREEN_HEIGHT + INGREDIENT_SIZE,
      { duration: fallDuration, easing: Easing.linear },
      (finished) => {
        if (finished && !isCaughtRef.current && !isDespawningRef.current) {
          runOnJS(handleDespawn)(id);
        }
      }
    );

    // Random spin direction and speed
    const spinDuration = 3200 + Math.random() * 600;
    const spinDirection = Math.random() > 0.5 ? 360 : -360;
    rotation.value = withRepeat(
      withTiming(spinDirection, { duration: spinDuration, easing: Easing.linear }),
      -1,
      false
    );
  }, []);

  const isInsidePlateZone = useCallback((fingerX: number, fingerY: number): boolean => {
    const zone = plateZoneRef.current;
    if (!zone) return false;
    const cx = zone.x + zone.width / 2;
    const cy = zone.y + zone.height / 2;
    const dx = fingerX - cx;
    const dy = fingerY - cy;
    return Math.sqrt(dx * dx + dy * dy) <= PLATE_CATCH_RADIUS;
  }, []);

  // ─── Responder handlers ──────────────────────────────────────────────────────

  const handleGrant = useCallback((evt: GestureResponderEvent) => {
    if (isCaughtRef.current || isDespawningRef.current) return;

    touchStartX.current = evt.nativeEvent.pageX;
    touchStartY.current = evt.nativeEvent.pageY;
    // Snapshot the current fall position so we can compute drag delta correctly
    fallYAtDragStart.current = fallY.value;
    // Pause fall at current position
    fallY.value = fallY.value;
  }, []);

  const handleMove = useCallback((evt: GestureResponderEvent) => {
    if (isCaughtRef.current || isDespawningRef.current) return;

    dragX.value = evt.nativeEvent.pageX - touchStartX.current;
    dragY.value = evt.nativeEvent.pageY - touchStartY.current;
  }, []);

  const handleRelease = useCallback((evt: GestureResponderEvent) => {
    if (isCaughtRef.current || isDespawningRef.current) return;

    const fingerX = evt.nativeEvent.pageX;
    const fingerY = evt.nativeEvent.pageY;

    if (isInsidePlateZone(fingerX, fingerY)) {
      // Caught!
      isCaught.value = true;
      isCaughtRef.current = true;
      dragX.value = 0;
      dragY.value = 0;
      onCatchRef.current(id);
    } else {
      // Missed — shrink and despawn
      isDespawningRef.current = true;
      dragX.value = 0;
      dragY.value = 0;
      scale.value = withTiming(0, { duration: 150, easing: Easing.in(Easing.ease) }, (finished) => {
        if (finished) {
          runOnJS(handleDespawn)(id);
        }
      });
    }
  }, [id, isInsidePlateZone, handleDespawn]);

  const handleTerminate = useCallback(() => {
    // Gesture was stolen by another responder — reset drag state
    if (!isCaughtRef.current && !isDespawningRef.current) {
      dragX.value = 0;
      dragY.value = 0;
    }
  }, []);

  const shouldSetResponder = useCallback(() => !isCaughtRef.current && !isDespawningRef.current, []);

  // ─── Animated style ──────────────────────────────────────────────────────────

  const animatedStyle = useAnimatedStyle(() => {
    if (isCaught.value) {
      return { opacity: 0 };
    }
    return {
      transform: [
        { translateX: laneX + dragX.value },
        { translateY: fallY.value + dragY.value },
        { rotate: `${rotation.value}deg` },
        { scale: scale.value },
      ],
      opacity: 1,
    };
  });

  return (
    <Animated.View
      style={[
        styles.ingredient,
        { backgroundColor: ingredient.color },
        animatedStyle,
      ]}
      // Native responder system — each View is an independent responder
      onStartShouldSetResponder={shouldSetResponder}
      onMoveShouldSetResponder={shouldSetResponder}
      onResponderGrant={handleGrant}
      onResponderMove={handleMove}
      onResponderRelease={handleRelease}
      onResponderTerminate={handleTerminate}
    >
      <Text style={styles.emoji}>{ingredient.emoji}</Text>
    </Animated.View>
  );
}

/**
 * Memoized FallingIngredient — only re-renders when its own identity props change.
 * Since id, ingredient, laneIndex, and fallDuration are stable for the lifetime
 * of a given ingredient, this effectively prevents re-renders from parent state
 * changes (timer ticks, other ingredient spawns/despawns).
 */
const FallingIngredient = React.memo(FallingIngredientInner, (prev, next) => {
  // Only re-render if the ingredient identity changes (which shouldn't happen)
  return prev.id === next.id;
});

export default FallingIngredient;

const styles = StyleSheet.create({
  ingredient: {
    position: 'absolute',
    width: INGREDIENT_SIZE,
    height: INGREDIENT_SIZE,
    borderRadius: Radius.lg,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 10,
    top: 0,
    left: 0,
    zIndex: 10,
  },
  emoji: {
    fontSize: 36,
  },
});
