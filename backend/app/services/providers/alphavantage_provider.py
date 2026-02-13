"""Alpha Vantage market data provider."""

import logging

import httpx

from app.config import settings
from app.services.providers.base import MarketDataProvider

logger = logging.getLogger(__name__)

BASE_URL = "https://www.alphavantage.co/query"


class AlphaVantageProvider(MarketDataProvider):
    """Market data from Alpha Vantage API."""

    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    @property
    def name(self) -> str:
        return "Alpha Vantage"

    @property
    def is_configured(self) -> bool:
        return bool(settings.alphavantage_api_key)

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
                BASE_URL,
                params={
                    "function": "GLOBAL_QUOTE",
                    "symbol": symbol.upper(),
                    "apikey": settings.alphavantage_api_key,
                },
            )
            resp.raise_for_status()
            data = resp.json().get("Global Quote", {})

            if not data:
                return None

            price = float(data.get("05. price", 0))
            if not price:
                return None

            prev_close = float(data.get("08. previous close", 0))
            change_pct = float(data.get("10. change percent", "0").rstrip("%"))

            return {
                "symbol": symbol.upper(),
                "name": symbol.upper(),
                "price": round(price, 4),
                "change_percent": round(change_pct, 2),
                "volume": int(data.get("06. volume", 0)),
                "previous_close": round(prev_close, 4),
                "market_cap": 0,
            }
        except Exception as e:
            logger.warning("Alpha Vantage quote failed for %s: %s", symbol, e)
            return None

    async def get_history(
        self, symbol: str, period: str = "1mo", interval: str = "1d"
    ) -> list[dict]:
        if not self.is_configured:
            return []

        try:
            client = await self._get_client()
            # Map period to outputsize
            outputsize = "compact" if period in ("1mo", "3mo") else "full"

            resp = await client.get(
                BASE_URL,
                params={
                    "function": "TIME_SERIES_DAILY",
                    "symbol": symbol.upper(),
                    "outputsize": outputsize,
                    "apikey": settings.alphavantage_api_key,
                },
            )
            resp.raise_for_status()
            time_series = resp.json().get("Time Series (Daily)", {})

            if not time_series:
                return []

            records = []
            for date_str, values in sorted(time_series.items()):
                records.append({
                    "date": f"{date_str}T00:00:00",
                    "open": round(float(values["1. open"]), 4),
                    "high": round(float(values["2. high"]), 4),
                    "low": round(float(values["3. low"]), 4),
                    "close": round(float(values["4. close"]), 4),
                    "volume": int(values["5. volume"]),
                })
            return records
        except Exception as e:
            logger.warning("Alpha Vantage history failed for %s: %s", symbol, e)
            return []

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
