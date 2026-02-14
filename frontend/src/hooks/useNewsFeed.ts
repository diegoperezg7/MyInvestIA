"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { fetchAPI } from "@/lib/api";
import type { AnalyzedArticle, NewsFeedResponse, SourceCategory } from "@/types";

const REFRESH_INTERVAL = 5 * 60 * 1000; // 5 minutes

export type NewsTab = "all" | SourceCategory;

export function useNewsFeed() {
  const [articles, setArticles] = useState<AnalyzedArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [categoryCounts, setCategoryCounts] = useState<Record<string, number>>({
    news: 0,
    social: 0,
    blog: 0,
  });
  const [activeTab, setActiveTab] = useState<NewsTab>("all");
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async (skipCache = false) => {
    try {
      setLoading(true);
      setError(null);
      const result = await fetchAPI<NewsFeedResponse>("/api/v1/news/feed", { skipCache });
      setArticles(result.articles || []);
      setCategoryCounts(
        result.category_counts || { news: 0, social: 0, blog: 0 }
      );
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

  // Client-side filtering by category
  const filteredArticles = useMemo(() => {
    if (activeTab === "all") return articles;
    return articles.filter((a) => a.source_category === activeTab);
  }, [articles, activeTab]);

  return {
    articles: filteredArticles,
    allArticles: articles,
    loading,
    error,
    refresh,
    activeTab,
    setActiveTab,
    categoryCounts,
  };
}
