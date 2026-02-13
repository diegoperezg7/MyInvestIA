"""Twelve Data market data provider."""

import logging

import httpx

from app.config import settings
from app.services.providers.base import MarketDataProvider

logger = logging.getLogger(__name__)

BASE_URL = "https://api.twelvedata.com"


class TwelveDataProvider(MarketDataProvider):
    """Market data from Twelve Data API."""

    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    @property
    def name(self) -> str:
        return "Twelve Data"

    @property
    def is_configured(self) -> bool:
        return bool(settings.twelvedata_api_key)

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
                params={"symbol": symbol.upper(), "apikey": settings.twelvedata_api_key},
            )
            resp.raise_for_status()
            data = resp.json()

            if "code" in data:  # Error response
                return None

            price = float(data.get("close", 0))
            if not price:
                return None

            prev_close = float(data.get("previous_close", 0))
            change_pct = float(data.get("percent_change", 0))

            return {
                "symbol": symbol.upper(),
                "name": data.get("name", symbol.upper()),
                "price": round(price, 4),
                "change_percent": round(change_pct, 2),
                "volume": int(data.get("volume", 0)),
                "previous_close": round(prev_close, 4),
                "market_cap": 0,
            }
        except Exception as e:
            logger.warning("Twelve Data quote failed for %s: %s", symbol, e)
            return None

    async def get_history(
        self, symbol: str, period: str = "1mo", interval: str = "1d"
    ) -> list[dict]:
        if not self.is_configured:
            return []

        # Map period to outputsize
        period_sizes = {
            "1d": 1, "5d": 5, "1mo": 22, "3mo": 66,
            "6mo": 130, "1y": 252, "2y": 504,
        }
        outputsize = period_sizes.get(period, 22)

        # Map interval
        interval_map = {"1d": "1day", "1wk": "1week", "1mo": "1month"}
        td_interval = interval_map.get(interval, "1day")

        try:
            client = await self._get_client()
            resp = await client.get(
                f"{BASE_URL}/time_series",
                params={
                    "symbol": symbol.upper(),
                    "interval": td_interval,
                    "outputsize": outputsize,
                    "apikey": settings.twelvedata_api_key,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            values = data.get("values", [])
            if not values:
                return []

            records = []
            for v in reversed(values):  # API returns newest first
                records.append({
                    "date": f"{v['datetime']}T00:00:00" if "T" not in v["datetime"] else v["datetime"],
                    "open": round(float(v["open"]), 4),
                    "high": round(float(v["high"]), 4),
                    "low": round(float(v["low"]), 4),
                    "close": round(float(v["close"]), 4),
                    "volume": int(v.get("volume", 0)),
                })
            return records
        except Exception as e:
            logger.warning("Twelve Data history failed for %s: %s", symbol, e)
            return []

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
