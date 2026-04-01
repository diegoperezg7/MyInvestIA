"use client";

import { useCallback, useEffect, useState } from "react";

import { fetchAPI, patchAPI, postAPI } from "@/lib/api";
import type { InboxItem, InboxResponse } from "@/types";

export interface InboxFilters {
  scope?: string;
  status?: string;
  kind?: string;
  symbol?: string;
}

function buildQuery(filters: InboxFilters, refresh = false): string {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  if (refresh) params.set("refresh", "true");
  const query = params.toString();
  return query ? `?${query}` : "";
}

export function useInbox(initialFilters: InboxFilters = {}) {
  const [filters, setFilters] = useState<InboxFilters>(initialFilters);
  const [data, setData] = useState<InboxResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (nextFilters = filters, refresh = false) => {
      try {
        setLoading(true);
        setError(null);
        const result = await fetchAPI<InboxResponse>(
          `/api/v1/inbox/${buildQuery(nextFilters, refresh)}`,
          { skipCache: refresh }
        );
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load inbox");
      } finally {
        setLoading(false);
      }
    },
    [filters]
  );

  useEffect(() => {
    load(filters);
  }, [filters, load]);

  const refresh = useCallback(async () => {
    const result = await postAPI<InboxResponse>("/api/v1/inbox/refresh", {});
    setData(result);
    return result;
  }, []);

  const mutateItem = useCallback(
    async (itemId: string, action: "save" | "dismiss" | "snooze" | "done" | "link_thesis", thesisId?: string) => {
      const updated = await patchAPI<InboxItem>(`/api/v1/inbox/${itemId}`, {
        action,
        thesis_id: thesisId,
      });
      setData((current) =>
        current
          ? {
              ...current,
              items: current.items.map((item) => (item.id === itemId ? updated : item)),
            }
          : current
      );
      return updated;
    },
    []
  );

  return { data, loading, error, filters, setFilters, refresh, mutateItem, reload: load };
}
