const LOCAL_API_HOSTS = new Set(["localhost", "127.0.0.1", "0.0.0.0", "backend"]);

function trimTrailingSlashes(value: string): string {
  return value.replace(/\/+$/, "");
}

export function resolveApiBase(rawBase = process.env.NEXT_PUBLIC_API_URL ?? ""): string {
  const configuredBase = trimTrailingSlashes(rawBase.trim());
  if (!configuredBase) return "";

  if (typeof window === "undefined") {
    return configuredBase;
  }

  try {
    const currentUrl = new URL(window.location.origin);
    const resolvedUrl = new URL(configuredBase, currentUrl.origin);
    const resolvedPath = resolvedUrl.pathname === "/" ? "" : trimTrailingSlashes(resolvedUrl.pathname);
    const sameHost = resolvedUrl.hostname === currentUrl.hostname;
    const localLikeHost =
      LOCAL_API_HOSTS.has(resolvedUrl.hostname) || resolvedUrl.hostname.endsWith(".local");

    if (currentUrl.protocol === "https:" && resolvedUrl.protocol === "http:") {
      if (sameHost || localLikeHost) {
        return resolvedPath;
      }
      resolvedUrl.protocol = "https:";
    }

    if (resolvedUrl.origin === currentUrl.origin) {
      return resolvedPath;
    }

    return `${resolvedUrl.origin}${resolvedPath}`;
  } catch {
    return configuredBase;
  }
}

export const API_BASE = resolveApiBase();
