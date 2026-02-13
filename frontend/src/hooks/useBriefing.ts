"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { fetchAPI } from "@/lib/api";
import type { BriefingData } from "@/types";

const REFRESH_INTERVAL = 5 * 60 * 1000; // 5 minutes

export function useBriefing() {
  const [data, setData] = useState<BriefingData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await fetchAPI<BriefingData>("/api/v1/chat/briefing");
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load briefing");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();

    intervalRef.current = setInterval(refresh, REFRESH_INTERVAL);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [refresh]);

  return { data, loading, error, refresh };
}
