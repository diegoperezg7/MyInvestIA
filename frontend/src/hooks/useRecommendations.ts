"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { fetchAPI } from "@/lib/api";
import type { RecommendationsResponse } from "@/types";

const REFRESH_INTERVAL = 15 * 60 * 1000; // 15 minutes

export function useRecommendations() {
  const [data, setData] = useState<RecommendationsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async (skipCache = false) => {
    try {
      setLoading(true);
      setError(null);
      const result = await fetchAPI<RecommendationsResponse>(
        "/api/v1/chat/recommendations",
        { skipCache }
      );
      setData(result);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Error al cargar recomendaciones"
      );
    } finally {
      setLoading(false);
    }
  }, []);

  const refresh = useCallback(() => load(true), [load]);

  useEffect(() => {
    load();

    intervalRef.current = setInterval(() => load(), REFRESH_INTERVAL);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [load]);

  return { data, loading, error, refresh };
}
