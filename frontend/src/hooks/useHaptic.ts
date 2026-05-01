<<<<<<< HEAD
/**
 * useHaptic — vibration feedback hook for high-stakes confirmations (#420).
 *
 * Maps semantic intensities to `navigator.vibrate(...)` patterns.
 * Honors `prefers-reduced-motion: reduce` by silently no-oping.
 *
 * Usage:
 *   const haptic = useHaptic()
 *   haptic.light()   // 10ms tick
 *   haptic.medium()  // 20ms tick
 *   haptic.heavy()   // 30ms tick
 *   haptic.success() // [15, 30, 15]
 *   haptic.error()   // [40, 50, 40]
 */
export function useHaptic() {
  const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function vibrate(pattern: number | number[]) {
    if (prefersReduced) return;
    if (typeof navigator !== "undefined" && navigator.vibrate) {
      navigator.vibrate(pattern);
    }
  }

  return {
    light: () => vibrate(10),
    medium: () => vibrate(20),
    heavy: () => vibrate(30),
    success: () => vibrate([15, 30, 15]),
    error: () => vibrate([40, 50, 40]),
  };
}
=======
import { useCallback } from 'react';

/**
 * Haptic feedback hook for mobile devices.
 * Maps to navigator.vibrate() with predefined patterns.
 * Respects prefers-reduced-motion: reduce.
 */
export function useHaptic() {
  const canVibrate = typeof navigator !== 'undefined' && 'vibrate' in navigator;

  const prefersReducedMotion =
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const vibrate = useCallback(
    (pattern: number | number[]) => {
      if (!canVibrate || prefersReducedMotion) return;
      try {
        navigator.vibrate(pattern);
      } catch {
        // Silently ignore vibration errors
      }
    },
    [canVibrate, prefersReducedMotion]
  );

  const light = useCallback(() => {
    vibrate(10);
  }, [vibrate]);

  const medium = useCallback(() => {
    vibrate(20);
  }, [vibrate]);

  const heavy = useCallback(() => {
    vibrate([0, 30, 50, 30]);
  }, [vibrate]);

  const success = useCallback(() => {
    vibrate([0, 20, 50, 20]);
  }, [vibrate]);

  const error = useCallback(() => {
    vibrate([0, 50, 30, 50, 30, 50]);
  }, [vibrate]);

  return { light, medium, heavy, success, error };
}

export type HapticFeedback = ReturnType<typeof useHaptic>;
>>>>>>> main
