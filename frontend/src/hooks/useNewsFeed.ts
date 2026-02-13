"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { fetchAPI } from "@/lib/api";
import type { AnalyzedArticle, NewsFeedResponse } from "@/types";

const REFRESH_INTERVAL = 5 * 60 * 1000; // 5 minutes

export function useNewsFeed() {
  const [articles, setArticles] = useState<AnalyzedArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async (skipCache = false) => {
    try {
      setLoading(true);
      setError(null);
      const result = await fetchAPI<NewsFeedResponse>("/api/v1/news/feed", { skipCache });
      setArticles(result.articles || []);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Error al cargar noticias"
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

  return { articles, loading, error, refresh };
}
