"use client";

import { useCallback, useEffect, useState } from "react";

import { fetchAPI, patchAPI, postAPI } from "@/lib/api";
import type {
  Thesis,
  ThesisEvent,
  ThesisListResponse,
  ThesisReviewResponse,
} from "@/types";

export function useTheses(symbol?: string) {
  const [data, setData] = useState<ThesisListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const query = symbol ? `?symbol=${encodeURIComponent(symbol)}` : "";
      const result = await fetchAPI<ThesisListResponse>(`/api/v1/theses/${query}`);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load theses");
    } finally {
      setLoading(false);
    }
  }, [symbol]);

  useEffect(() => {
    load();
  }, [load]);

  const createFromInbox = useCallback(async (itemId: string) => {
    const result = await postAPI<{ thesis: Thesis; event: ThesisEvent }>(
      `/api/v1/inbox/${itemId}/thesis`,
      {}
    );
    setData((current) =>
      current
        ? { ...current, theses: [result.thesis, ...current.theses], total: current.total + 1 }
        : { theses: [result.thesis], total: 1 }
    );
    return result;
  }, []);

  const createManual = useCallback(async (payload: Partial<Thesis>) => {
    const thesis = await postAPI<Thesis>("/api/v1/theses/", payload);
    setData((current) =>
      current ? { ...current, theses: [thesis, ...current.theses], total: current.total + 1 } : { theses: [thesis], total: 1 }
    );
    return thesis;
  }, []);

  const update = useCallback(async (thesisId: string, payload: Partial<Thesis>) => {
    const thesis = await patchAPI<Thesis>(`/api/v1/theses/${thesisId}`, payload);
    setData((current) =>
      current
        ? {
            ...current,
            theses: current.theses.map((item) => (item.id === thesisId ? thesis : item)),
          }
        : current
    );
    return thesis;
  }, []);

  const review = useCallback(async (thesisId: string, notes: string) => {
    const result = await postAPI<ThesisReviewResponse>(`/api/v1/theses/${thesisId}/review`, { notes });
    setData((current) =>
      current
        ? {
            ...current,
            theses: current.theses.map((item) => (item.id === thesisId ? result.thesis : item)),
          }
        : current
    );
    return result;
  }, []);

  return { data, loading, error, reload: load, createFromInbox, createManual, update, review };
}
