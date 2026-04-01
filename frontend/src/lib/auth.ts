const COOKIE_TOKEN = "darc3_token";

export interface AuthUser {
  id: string;
  email: string;
  role: "admin" | "user";
}

function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? match[1] : null;
}

const COOKIE_DOMAIN = process.env.NEXT_PUBLIC_COOKIE_DOMAIN || "";

function setCookie(name: string, value: string, maxAge: number = 86400) {
  if (typeof document === "undefined") return;
  const domainPart = COOKIE_DOMAIN ? `; domain=${COOKIE_DOMAIN}` : "";
  document.cookie = `${name}=${value}${domainPart}; path=/; max-age=${maxAge}; secure; samesite=lax`;
}

function deleteCookie(name: string) {
  if (typeof document === "undefined") return;
  const domainPart = COOKIE_DOMAIN ? `; domain=${COOKIE_DOMAIN}` : "";
  document.cookie = `${name}=${domainPart}; path=/; max-age=0`;
}

/** Read access token from cookie (JS-readable, short-lived). */
export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return getCookie(COOKIE_TOKEN);
}

/** Store tokens in cookies for cross-app SSO. */
export function setTokens(access: string, refresh: string) {
  void refresh;
  setCookie(COOKIE_TOKEN, access, 86400);
}

/** Clear auth cookies. */
export function clearTokens() {
  deleteCookie(COOKIE_TOKEN);
}

export function getRefreshToken(): string | null {
  // Refresh token is HttpOnly — JS cannot read it.
  return null;
}

export function parseJwt(token: string): Record<string, unknown> | null {
  try {
    const base64 = token.split(".")[1];
    const json = atob(base64.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(json);
  } catch {
    return null;
  }
}

export function isTokenExpired(token: string): boolean {
  const payload = parseJwt(token);
  if (!payload || typeof payload.exp !== "number") return true;
  return Date.now() >= payload.exp * 1000;
}

export function getUserFromToken(token: string): AuthUser | null {
  const payload = parseJwt(token);
  if (!payload || !payload.sub) return null;
  const appMeta = (payload.app_metadata as Record<string, unknown>) || {};
  const userMeta = (payload.user_metadata as Record<string, unknown>) || {};
  const topLevelRole = payload.role;
  return {
    id: payload.sub as string,
    email: (payload.email as string) || "",
    role: ((topLevelRole || appMeta.role || userMeta.role) as "admin" | "user") || "user",
  };
}
