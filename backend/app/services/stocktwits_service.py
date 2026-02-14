"""StockTwits service — fetch trending and symbol-specific streams.

Uses the free public API (no key required).
"""

import logging
import time

import httpx

from app.services.cache import get_or_fetch

logger = logging.getLogger(__name__)

STOCKTWITS_TTL = 300  # 5 minutes

BASE_URL = "https://api.stocktwits.com/api/2"

USER_AGENT = "InvestIA-Dashboard/1.0"


def _parse_messages(messages: list[dict], source_label: str = "StockTwits") -> list[dict]:
    """Parse StockTwits messages into article-like dicts."""
    posts = []
    for msg in messages:
        body = msg.get("body", "").strip()
        if not body:
            continue

        created = msg.get("created_at", "")
        # StockTwits uses ISO format; convert to unix timestamp
        dt = int(time.time())
        if created:
            try:
                from datetime import datetime, timezone
                # Format: "2024-01-15T10:30:00Z"
                parsed = datetime.fromisoformat(created.replace("Z", "+00:00"))
                dt = int(parsed.timestamp())
            except Exception:
                pass

        # Extract sentiment
        sentiment_data = msg.get("entities", {}).get("sentiment", {})
        sentiment_label = sentiment_data.get("basic") if sentiment_data else None

        user = msg.get("user", {})
        author = user.get("username", "")

        # Extract symbols mentioned
        symbols = [
            s.get("symbol", "") for s in msg.get("symbols", []) if s.get("symbol")
        ]

        posts.append({
            "headline": body[:200],
            "summary": body if len(body) > 200 else "",
            "source": source_label,
            "url": f"https://stocktwits.com/message/{msg.get('id', '')}",
            "datetime": dt,
            "source_category": "social",
            "author": author,
            "sentiment_label": sentiment_label,  # "Bullish" | "Bearish" | None
            "mentioned_symbols": symbols,
        })
    return posts


async def get_trending(limit: int = 20) -> list[dict]:
    """Fetch trending stream from StockTwits."""

    async def _fetch():
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{BASE_URL}/streams/trending.json",
                    headers={"User-Agent": USER_AGENT},
                    follow_redirects=True,
                )
                resp.raise_for_status()
                data = resp.json()

            messages = data.get("messages", [])
            return _parse_messages(messages, "StockTwits")[:limit]
        except Exception as e:
            logger.debug("StockTwits trending unavailable: %s", e)
            return []

    return await get_or_fetch("stocktwits:trending", _fetch, STOCKTWITS_TTL) or []


async def get_symbol_stream(symbol: str, limit: int = 15) -> list[dict]:
    """Fetch stream for a specific symbol."""

    async def _fetch():
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{BASE_URL}/streams/symbol/{symbol.upper()}.json",
                    headers={"User-Agent": USER_AGENT},
                    follow_redirects=True,
                )
                resp.raise_for_status()
                data = resp.json()

            messages = data.get("messages", [])
            return _parse_messages(messages, f"StockTwits/{symbol.upper()}")[:limit]
        except Exception as e:
            logger.debug("StockTwits symbol %s unavailable: %s", symbol, e)
            return []

    return await get_or_fetch(f"stocktwits:sym:{symbol.upper()}", _fetch, STOCKTWITS_TTL) or []
