"use client";

import { useCallback, useEffect, useState } from "react";

import { fetchAPI, postAPI } from "@/lib/api";
import type {
  ResearchFactorResponse,
  ResearchRankingsResponse,
  ResearchScreen,
  ResearchSnapshotListResponse,
} from "@/types";

export function useResearch(symbols: string[] = []) {
  const [rankings, setRankings] = useState<ResearchRankingsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSymbol, setSelectedSymbol] = useState<string>("");
  const [factors, setFactors] = useState<ResearchFactorResponse | null>(null);
  const [snapshots, setSnapshots] = useState<ResearchSnapshotListResponse | null>(null);

  const loadRankings = useCallback(
    async (saveSnapshot = false) => {
      try {
        setLoading(true);
        setError(null);
        const params = new URLSearchParams();
        if (symbols.length > 0) params.set("symbols", symbols.join(","));
        if (saveSnapshot) params.set("save_snapshot", "true");
        const query = params.toString();
        const result = await fetchAPI<ResearchRankingsResponse>(
          `/api/v1/research/rankings${query ? `?${query}` : ""}`,
          { skipCache: saveSnapshot }
        );
        setRankings(result);
        setSelectedSymbol((current) => current || result.rankings[0]?.symbol || "");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load research rankings");
      } finally {
        setLoading(false);
      }
    },
    [symbols]
  );

  const loadFactors = useCallback(async (symbol: string) => {
    if (!symbol) return;
    const result = await fetchAPI<ResearchFactorResponse>(
      `/api/v1/research/factors/${encodeURIComponent(symbol)}`
    );
    setFactors(result);
    setSelectedSymbol(symbol);
  }, []);

  const loadSnapshots = useCallback(async () => {
    const result = await fetchAPI<ResearchSnapshotListResponse>("/api/v1/research/snapshots");
    setSnapshots(result);
  }, []);

  const saveScreen = useCallback(async (screen: Pick<ResearchScreen, "name" | "symbols" | "notes">) => {
    return postAPI<ResearchScreen>("/api/v1/research/screens", screen);
  }, []);

  useEffect(() => {
    loadRankings();
    loadSnapshots().catch(() => undefined);
  }, [loadRankings, loadSnapshots]);

  useEffect(() => {
    if (!selectedSymbol) return;
    loadFactors(selectedSymbol).catch(() => undefined);
  }, [loadFactors, selectedSymbol]);

  return {
    rankings,
    factors,
    snapshots,
    loading,
    error,
    selectedSymbol,
    setSelectedSymbol,
    loadRankings,
    loadFactors,
    loadSnapshots,
    saveScreen,
  };
}
