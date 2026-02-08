"""Market data service using yfinance for stocks/ETFs and CoinGecko for crypto.

Provides real-time and historical price data, plus basic quote information.
CoinGecko uses the free public API (no key needed).
yfinance uses Yahoo Finance (no key needed).
"""

import logging
from datetime import datetime, timezone

import httpx
import yfinance as yf

from app.schemas.asset import AssetType

logger = logging.getLogger(__name__)

# CoinGecko symbol mapping: our symbol -> coingecko id
CRYPTO_ID_MAP: dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "ADA": "cardano",
    "DOT": "polkadot",
    "AVAX": "avalanche-2",
    "MATIC": "matic-network",
    "LINK": "chainlink",
    "UNI": "uniswap",
    "ATOM": "cosmos",
    "XRP": "ripple",
    "DOGE": "dogecoin",
    "SHIB": "shiba-inu",
    "LTC": "litecoin",
    "BNB": "binancecoin",
}

COINGECKO_BASE = "https://api.coingecko.com/api/v3"

VALID_PERIODS = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "ytd", "max"}
VALID_INTERVALS = {"1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"}


class MarketDataService:
    """Fetches live and historical market data from Yahoo Finance and CoinGecko."""

    def __init__(self):
        self._http_client: httpx.AsyncClient | None = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=15.0)
        return self._http_client

    async def close(self):
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    # --- Quote (current price) ---

    def get_stock_quote(self, symbol: str) -> dict | None:
        """Get current quote for a stock/ETF/commodity via yfinance.

        Returns dict with: symbol, name, price, change_percent, volume, previous_close, market_cap
        """
        try:
            ticker = yf.Ticker(symbol.upper())
            info = ticker.fast_info
            price = info.get("lastPrice", 0.0) or info.get("regularMarketPrice", 0.0)
            prev_close = info.get("previousClose", 0.0) or info.get("regularMarketPreviousClose", 0.0)
            volume = info.get("lastVolume", 0) or info.get("regularMarketVolume", 0)
            market_cap = info.get("marketCap", 0)

            if not price:
                return None

            change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0.0

            return {
                "symbol": symbol.upper(),
                "name": symbol.upper(),
                "price": round(price, 4),
                "change_percent": round(change_pct, 2),
                "volume": volume,
                "previous_close": round(prev_close, 4),
                "market_cap": market_cap,
            }
        except Exception as e:
            logger.warning("yfinance quote failed for %s: %s", symbol, e)
            return None

    async def get_crypto_quote(self, symbol: str) -> dict | None:
        """Get current quote for a cryptocurrency via CoinGecko.

        Returns dict with: symbol, name, price, change_percent, volume, market_cap
        """
        coin_id = CRYPTO_ID_MAP.get(symbol.upper())
        if not coin_id:
            logger.warning("Unknown crypto symbol: %s", symbol)
            return None

        try:
            client = await self._get_http_client()
            resp = await client.get(
                f"{COINGECKO_BASE}/simple/price",
                params={
                    "ids": coin_id,
                    "vs_currencies": "usd",
                    "include_24hr_change": "true",
                    "include_24hr_vol": "true",
                    "include_market_cap": "true",
                },
            )
            resp.raise_for_status()
            data = resp.json().get(coin_id, {})

            price = data.get("usd", 0.0)
            if not price:
                return None

            return {
                "symbol": symbol.upper(),
                "name": coin_id.replace("-", " ").title(),
                "price": price,
                "change_percent": round(data.get("usd_24h_change", 0.0), 2),
                "volume": data.get("usd_24h_vol", 0),
                "market_cap": data.get("usd_market_cap", 0),
            }
        except Exception as e:
            logger.warning("CoinGecko quote failed for %s: %s", symbol, e)
            return None

    async def get_quote(self, symbol: str, asset_type: AssetType | str | None = None) -> dict | None:
        """Get a quote for any asset. Auto-detects crypto if asset_type not specified."""
        symbol = symbol.upper()
        asset_type_str = asset_type.value if isinstance(asset_type, AssetType) else asset_type

        if asset_type_str == "crypto" or (asset_type_str is None and symbol in CRYPTO_ID_MAP):
            return await self.get_crypto_quote(symbol)
        else:
            return self.get_stock_quote(symbol)

    async def get_quotes(self, symbols: list[dict]) -> list[dict]:
        """Get quotes for multiple assets. Each item: {"symbol": str, "type": str}.

        Returns list of quote dicts (only successful ones).
        """
        results = []
        for item in symbols:
            quote = await self.get_quote(item["symbol"], item.get("type"))
            if quote:
                results.append(quote)
        return results

    # --- Historical data ---

    def get_history(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> list[dict]:
        """Get historical OHLCV data for a stock/ETF via yfinance.

        Args:
            symbol: Ticker symbol
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, ytd, max)
            interval: Data interval (1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo)

        Returns:
            List of dicts with: date, open, high, low, close, volume
        """
        if period not in VALID_PERIODS:
            period = "1mo"
        if interval not in VALID_INTERVALS:
            interval = "1d"

        try:
            ticker = yf.Ticker(symbol.upper())
            df = ticker.history(period=period, interval=interval)

            if df.empty:
                return []

            records = []
            for ts, row in df.iterrows():
                records.append({
                    "date": ts.isoformat(),
                    "open": round(float(row["Open"]), 4),
                    "high": round(float(row["High"]), 4),
                    "low": round(float(row["Low"]), 4),
                    "close": round(float(row["Close"]), 4),
                    "volume": int(row["Volume"]),
                })
            return records
        except Exception as e:
            logger.warning("yfinance history failed for %s: %s", symbol, e)
            return []

    async def get_crypto_history(
        self,
        symbol: str,
        days: int = 30,
    ) -> list[dict]:
        """Get historical price data for crypto via CoinGecko.

        Args:
            symbol: Crypto symbol (BTC, ETH, etc.)
            days: Number of days of history (1, 7, 14, 30, 90, 180, 365, max)

        Returns:
            List of dicts with: date, price, volume, market_cap
        """
        coin_id = CRYPTO_ID_MAP.get(symbol.upper())
        if not coin_id:
            return []

        try:
            client = await self._get_http_client()
            resp = await client.get(
                f"{COINGECKO_BASE}/coins/{coin_id}/market_chart",
                params={"vs_currency": "usd", "days": str(days)},
            )
            resp.raise_for_status()
            data = resp.json()

            prices = data.get("prices", [])
            volumes = data.get("total_volumes", [])
            market_caps = data.get("market_caps", [])

            records = []
            for i, (ts, price) in enumerate(prices):
                dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
                records.append({
                    "date": dt.isoformat(),
                    "price": round(price, 4),
                    "volume": volumes[i][1] if i < len(volumes) else 0,
                    "market_cap": market_caps[i][1] if i < len(market_caps) else 0,
                })
            return records
        except Exception as e:
            logger.warning("CoinGecko history failed for %s: %s", symbol, e)
            return []

    # --- Top movers (for market overview) ---

    def get_top_movers(self, symbols: list[str] | None = None) -> dict:
        """Get top gainers and losers from a set of symbols.

        If no symbols provided, uses a default watchlist of popular tickers.
        Returns: {"gainers": [...], "losers": [...]}
        """
        if symbols is None:
            symbols = [
                "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
                "SPY", "QQQ", "IWM", "DIA",
            ]

        quotes = []
        for sym in symbols:
            q = self.get_stock_quote(sym)
            if q:
                quotes.append(q)

        sorted_quotes = sorted(quotes, key=lambda x: x["change_percent"], reverse=True)

        return {
            "gainers": sorted_quotes[:5],
            "losers": sorted_quotes[-5:][::-1] if len(sorted_quotes) >= 5 else [],
        }


# Singleton
market_data_service = MarketDataService()
