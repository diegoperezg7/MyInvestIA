import { getToken, clearTokens } from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

const CACHE_TTL = 30_000; // 30 seconds — reduced polling means we can cache longer

interface CacheEntry {
  data: unknown;
  timestamp: number;
}

const cache = new Map<string, CacheEntry>();
const inflight = new Map<string, Promise<unknown>>();

function authHeaders(): Record<string, string> {
  const token = getToken();
  if (token) return { Authorization: `Bearer ${token}` };
  return {};
}

function handle401() {
  clearTokens();
  window.location.reload();
}

export async function fetchAPI<T>(endpoint: string, { skipCache = false }: { skipCache?: boolean } = {}): Promise<T> {
  const url = `${API_BASE}${endpoint}`;

  // Return cached data if fresh
  if (!skipCache) {
    const cached = cache.get(url);
    if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
      return cached.data as T;
    }

    // Deduplicate inflight requests (only for normal fetches, not manual refreshes)
    const existing = inflight.get(url);
    if (existing) {
      return existing as Promise<T>;
    }
  }

  const promise = fetch(url, { headers: authHeaders(), credentials: "include" }).then(async (response) => {
    inflight.delete(url);
    if (response.status === 401) {
      handle401();
      throw new Error("Unauthorized");
    }
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    const data = await response.json();
    cache.set(url, { data, timestamp: Date.now() });
    return data as T;
  }).catch((err) => {
    inflight.delete(url);
    throw err;
  });

  inflight.set(url, promise);
  return promise;
}

export async function postAPI<T>(endpoint: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    credentials: "include",
    body: JSON.stringify(body),
  });
  if (response.status === 401) {
    handle401();
    throw new Error("Unauthorized");
  }
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}

export async function patchAPI<T>(endpoint: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    credentials: "include",
    body: JSON.stringify(body),
  });
  if (response.status === 401) {
    handle401();
    throw new Error("Unauthorized");
  }
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}

export async function deleteAPI(endpoint: string): Promise<void> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: "DELETE",
    headers: authHeaders(),
    credentials: "include",
  });
  if (response.status === 401) {
    handle401();
    throw new Error("Unauthorized");
  }
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
}

/**
 * Fetch Server-Sent Events and call onMessage for each event.
 * Returns an EventSource that can be closed to cancel.
 */
export function fetchSSE(
  endpoint: string,
  onMessage: (data: unknown) => void,
  onError?: (error: Event) => void,
): EventSource {
  // EventSource doesn't support custom headers, so pass token as query param
  const token = getToken();
  const sep = endpoint.includes("?") ? "&" : "?";
  const url = token
    ? `${API_BASE}${endpoint}${sep}token=${encodeURIComponent(token)}`
    : `${API_BASE}${endpoint}`;

  const es = new EventSource(url);

  es.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch {
      // Ignore parse errors
    }
  };

  if (onError) {
    es.onerror = onError;
  }

  return es;
}
