"""Finnhub market data provider."""

import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.config import settings
from app.services.providers.base import MarketDataProvider

logger = logging.getLogger(__name__)

BASE_URL = "https://finnhub.io/api/v1"


class FinnhubProvider(MarketDataProvider):
    """Market data from Finnhub API."""

    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    @property
    def name(self) -> str:
        return "Finnhub"

    @property
    def is_configured(self) -> bool:
        return bool(settings.finnhub_api_key)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=15.0)
        return self._client

    async def get_quote(self, symbol: str) -> dict | None:
        if not self.is_configured:
            return None

        try:
            client = await self._get_client()
            resp = await client.get(
                f"{BASE_URL}/quote",
                params={"symbol": symbol.upper(), "token": settings.finnhub_api_key},
            )
            resp.raise_for_status()
            data = resp.json()

            price = data.get("c", 0)
            if not price:
                return None

            prev_close = data.get("pc", 0)
            change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0

            return {
                "symbol": symbol.upper(),
                "name": symbol.upper(),
                "price": round(price, 4),
                "change_percent": round(change_pct, 2),
                "volume": 0,  # Not available in basic quote
                "previous_close": round(prev_close, 4),
                "market_cap": 0,
            }
        except Exception as e:
            logger.warning("Finnhub quote failed for %s: %s", symbol, e)
            return None

    async def get_history(
        self, symbol: str, period: str = "1mo", interval: str = "1d"
    ) -> list[dict]:
        if not self.is_configured:
            return []

        # Map period to days
        period_days = {
            "1d": 1, "5d": 5, "1mo": 30, "3mo": 90,
            "6mo": 180, "1y": 365, "2y": 730, "5y": 1825,
        }
        days = period_days.get(period, 30)

        try:
            client = await self._get_client()
            now = datetime.now(timezone.utc)
            start = int((now - timedelta(days=days)).timestamp())
            end = int(now.timestamp())

            resp = await client.get(
                f"{BASE_URL}/stock/candle",
                params={
                    "symbol": symbol.upper(),
                    "resolution": "D",
                    "from": start,
                    "to": end,
                    "token": settings.finnhub_api_key,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("s") != "ok":
                return []

            records = []
            timestamps = data.get("t", [])
            opens = data.get("o", [])
            highs = data.get("h", [])
            lows = data.get("l", [])
            closes = data.get("c", [])
            volumes = data.get("v", [])

            for i in range(len(timestamps)):
                dt = datetime.fromtimestamp(timestamps[i], tz=timezone.utc)
                records.append({
                    "date": dt.isoformat(),
                    "open": round(opens[i], 4),
                    "high": round(highs[i], 4),
                    "low": round(lows[i], 4),
                    "close": round(closes[i], 4),
                    "volume": int(volumes[i]) if i < len(volumes) else 0,
                })
            return records
        except Exception as e:
            logger.warning("Finnhub history failed for %s: %s", symbol, e)
            return []

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
