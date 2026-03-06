"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import {
  getToken,
  clearTokens,
  isTokenExpired,
  getUserFromToken,
  setTokens,
  type AuthUser,
} from "@/lib/auth";

const AIDENTITY_API = process.env.NEXT_PUBLIC_API_URL ?? "";

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshAccessToken = useCallback(async (): Promise<string | null> => {
    try {
      const res = await fetch(`${AIDENTITY_API}/api/v1/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
      });
      if (!res.ok) return null;
      const data = await res.json();
      return data.access_token;
    } catch {
      return null;
    }
  }, []);

  // Initialize auth state from stored token or refresh cookie
  useEffect(() => {
    async function init() {
      let token = getToken();

      if (!token || isTokenExpired(token)) {
        // Access token missing or expired — try refresh via HttpOnly cookie
        const refreshed = await refreshAccessToken();
        if (!refreshed) {
          setLoading(false);
          return;
        }
        token = refreshed;
      }

      const parsed = getUserFromToken(token);
      if (parsed) {
        setUser(parsed);
      }
      setLoading(false);
    }
    init();
  }, [refreshAccessToken]);

  // Auto-refresh token before expiry
  useEffect(() => {
    const interval = setInterval(async () => {
      const token = getToken();
      if (!token) return;

      const payload = JSON.parse(atob(token.split(".")[1]));
      const expiresIn = payload.exp * 1000 - Date.now();
      // Refresh if less than 5 minutes remaining
      if (expiresIn < 5 * 60 * 1000) {
        const refreshed = await refreshAccessToken();
        if (refreshed) {
          const parsed = getUserFromToken(refreshed);
          if (parsed) setUser(parsed);
        } else {
          clearTokens();
          setUser(null);
        }
      }
    }, 60_000);
    return () => clearInterval(interval);
  }, [refreshAccessToken]);

  const login = useCallback(async (email: string, password: string) => {
    const res = await fetch(`${AIDENTITY_API}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ login: email, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Error de conexión" }));
      throw new Error(err.detail || "Login failed");
    }
    const data = await res.json();
    if (data.access_token) {
      setTokens(data.access_token, data.refresh_token);
    }
    const parsed = getUserFromToken(data.access_token);
    setUser(parsed);
  }, []);

  const logout = useCallback(() => {
    const token = getToken();
    fetch(`${AIDENTITY_API}/api/v1/auth/logout`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    }).catch(() => {});
    clearTokens();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
