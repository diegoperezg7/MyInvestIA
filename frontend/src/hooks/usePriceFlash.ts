import { useEffect, useRef, useState } from "react";

type FlashDirection = "up" | "down" | null;

/**
 * Track previous value and return flash direction when it changes.
 * Returns [flashDirection, flashKey] - flashKey changes on each flash to re-trigger CSS animation.
 */
export function usePriceFlash(value: number | undefined): [FlashDirection, number] {
  const prevRef = useRef<number | undefined>(undefined);
  const [flash, setFlash] = useState<FlashDirection>(null);
  const [flashKey, setFlashKey] = useState(0);

  useEffect(() => {
    if (value === undefined) return;
    if (prevRef.current !== undefined && value !== prevRef.current) {
      const direction: FlashDirection = value > prevRef.current ? "up" : "down";
      setFlash(direction);
      setFlashKey((k) => k + 1);

      const timer = setTimeout(() => setFlash(null), 800);
      return () => clearTimeout(timer);
    }
    prevRef.current = value;
  }, [value]);

  return [flash, flashKey];
}
