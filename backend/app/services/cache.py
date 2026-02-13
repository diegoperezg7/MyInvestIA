"""In-memory TTL cache with per-key async locks and stale-while-revalidate."""

import asyncio
import logging
import time
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)

_cache: dict[str, tuple[Any, float]] = {}  # key -> (value, expires_at)
_locks: dict[str, asyncio.Lock] = {}
_revalidating: set[str] = set()  # keys currently being refreshed in background

# Default TTLs (seconds)
QUOTE_TTL = 120       # was 60
HISTORY_TTL = 600     # was 300
MACRO_TTL = 180       # macro indicators change slowly

# Stale grace multiplier: serve stale data up to TTL * STALE_GRACE_FACTOR
STALE_GRACE_FACTOR = 2


def _get_lock(key: str) -> asyncio.Lock:
    if key not in _locks:
        _locks[key] = asyncio.Lock()
    return _locks[key]


def get(key: str) -> Any | None:
    """Return cached value if present and not expired, else None."""
    entry = _cache.get(key)
    if entry is None:
        return None
    value, expires_at = entry
    if time.monotonic() > expires_at:
        _cache.pop(key, None)
        return None
    return value


def get_stale(key: str, ttl: int) -> Any | None:
    """Return cached value even if expired, as long as within stale grace window.

    The grace window is TTL * STALE_GRACE_FACTOR from the original expiry.
    """
    entry = _cache.get(key)
    if entry is None:
        return None
    value, expires_at = entry
    now = time.monotonic()
    # Within normal TTL — still fresh
    if now <= expires_at:
        return value
    # Within stale grace window
    stale_deadline = expires_at + ttl * (STALE_GRACE_FACTOR - 1)
    if now <= stale_deadline:
        return value
    # Too stale — evict
    _cache.pop(key, None)
    return None


def set(key: str, value: Any, ttl: int) -> None:
    """Store a value with a TTL in seconds."""
    _cache[key] = (value, time.monotonic() + ttl)


async def get_or_fetch(
    key: str,
    fetch_fn: Callable[[], Coroutine[Any, Any, Any]],
    ttl: int = QUOTE_TTL,
) -> Any:
    """Return cached value or call fetch_fn. Supports stale-while-revalidate.

    If the cache entry is expired but within the stale grace window,
    returns stale data immediately and spawns a background refresh.
    """
    # Fast path: still fresh
    cached = get(key)
    if cached is not None:
        return cached

    # Check for stale data we can serve while revalidating
    stale = get_stale(key, ttl)
    if stale is not None:
        # Spawn background revalidation (if not already running)
        if key not in _revalidating:
            _revalidating.add(key)

            async def _revalidate():
                try:
                    value = await fetch_fn()
                    if value is not None:
                        set(key, value, ttl)
                except Exception as e:
                    logger.debug("Background revalidation failed for %s: %s", key, e)
                finally:
                    _revalidating.discard(key)

            asyncio.create_task(_revalidate())
        return stale

    # No cached data at all — must fetch synchronously
    lock = _get_lock(key)
    async with lock:
        # Double-check after acquiring lock
        cached = get(key)
        if cached is not None:
            return cached
        value = await fetch_fn()
        if value is not None:
            set(key, value, ttl)
        return value
