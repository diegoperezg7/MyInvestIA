"""Yahoo Finance provider using yfinance library."""

import asyncio
import logging
import time

import yfinance as yf

from app.services.cache import HISTORY_TTL, QUOTE_TTL, get_or_fetch, set as cache_set, get as cache_get
from app.services.providers.base import MarketDataProvider

logger = logging.getLogger(__name__)

VALID_PERIODS = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "ytd", "max"}
VALID_INTERVALS = {"1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"}


def _sync_get_quote(symbol: str, attempt: int = 0) -> dict | None:
    """Synchronous yfinance quote fetch (runs in thread) with retry on rate limit."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        price = info.get("lastPrice", 0.0) or info.get("regularMarketPrice", 0.0)
        prev_close = info.get("previousClose", 0.0) or info.get("regularMarketPreviousClose", 0.0)
        volume = info.get("lastVolume", 0) or info.get("regularMarketVolume", 0)
        market_cap = info.get("marketCap", 0) or 0
        currency = info.get("currency", "USD")

        if not price:
            if attempt < _MAX_RETRIES:
                logger.info("No price for %s, retrying in %.1fs (attempt %d)", symbol, _RETRY_DELAY * (attempt + 1), attempt + 1)
                time.sleep(_RETRY_DELAY * (attempt + 1))
                return _sync_get_quote(symbol, attempt + 1)
            return None

        change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0.0

        return {
            "symbol": symbol,
            "name": symbol,
            "price": round(price, 4),
            "change_percent": round(change_pct, 2),
            "volume": volume or 0,
            "previous_close": round(prev_close, 4),
            "market_cap": market_cap,
            "currency": currency,
        }
    except Exception as e:
        if attempt < _MAX_RETRIES:
            delay = _RETRY_DELAY * (attempt + 1)
            logger.warning("Quote fetch for %s failed (%s), retrying in %.1fs", symbol, e, delay)
            time.sleep(delay)
            return _sync_get_quote(symbol, attempt + 1)
        raise


_BATCH_CHUNK_SIZE = 50  # keep chunks small to avoid yfinance rate limits
_MAX_RETRIES = 2
_RETRY_DELAY = 3.0  # seconds between retries


def _sync_download_chunk(symbols: list[str], attempt: int = 0):
    """Download a chunk of symbols with retry on rate limit."""
    try:
        df = yf.download(
            symbols,
            period="2d",
            interval="1d",
            group_by="ticker",
            progress=False,
            threads=False,
        )
        return df
    except Exception as e:
        if "rate" in str(e).lower() and attempt < _MAX_RETRIES:
            delay = _RETRY_DELAY * (attempt + 1)
            logger.info("Rate limited, retrying chunk in %.1fs (attempt %d)", delay, attempt + 1)
            time.sleep(delay)
            return _sync_download_chunk(symbols, attempt + 1)
        raise


def _sync_get_quotes_batch(symbols: list[str]) -> dict[str, dict]:
    """Batch-fetch quotes using yf.download() — chunked with retry on rate limit."""
    results: dict[str, dict] = {}
    if not symbols:
        return results

    for i in range(0, len(symbols), _BATCH_CHUNK_SIZE):
        if i > 0:
            time.sleep(1.0)  # pause between chunks
        chunk = symbols[i : i + _BATCH_CHUNK_SIZE]
        try:
            df = _sync_download_chunk(chunk)
            if df is None or df.empty:
                continue

            for sym in chunk:
                try:
                    if len(chunk) == 1:
                        ticker_df = df
                    else:
                        ticker_df = df[sym]

                    ticker_df = ticker_df.dropna(subset=["Close"])
                    if len(ticker_df) < 1:
                        continue

                    price = float(ticker_df["Close"].iloc[-1])
                    prev_close = float(ticker_df["Close"].iloc[-2]) if len(ticker_df) >= 2 else price
                    volume = int(ticker_df["Volume"].iloc[-1]) if "Volume" in ticker_df.columns else 0

                    if price > 0:
                        change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0.0
                        results[sym] = {
                            "symbol": sym,
                            "name": sym,
                            "price": round(price, 4),
                            "change_percent": round(change_pct, 2),
                            "volume": volume,
                            "previous_close": round(prev_close, 4),
                            "market_cap": 0,
                        }
                except Exception as e:
                    logger.debug("Batch quote: failed to extract %s: %s", sym, e)
        except Exception as e:
            logger.warning("yf.download batch chunk failed: %s", e)

    return results


def _sync_get_history(symbol: str, period: str, interval: str) -> list[dict]:
    """Synchronous yfinance history fetch (runs in thread)."""
    ticker = yf.Ticker(symbol)
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


class YFinanceProvider(MarketDataProvider):
    """Market data from Yahoo Finance (no API key needed)."""

    @property
    def name(self) -> str:
        return "Yahoo Finance"

    @property
    def is_configured(self) -> bool:
        return True  # No API key required

    async def get_quote(self, symbol: str) -> dict | None:
        symbol = symbol.upper()
        cache_key = f"quote:{symbol}"

        async def _fetch():
            try:
                return await asyncio.to_thread(_sync_get_quote, symbol)
            except Exception as e:
                logger.warning("yfinance quote failed for %s: %s", symbol, e)
                return None

        return await get_or_fetch(cache_key, _fetch, QUOTE_TTL)

    async def get_quotes_batch(self, symbols: list[str]) -> dict[str, dict]:
        """Batch-fetch quotes for multiple symbols using a single yf.download() call.

        Returns dict mapping symbol -> quote dict. Results are cached individually.
        """
        symbols = [s.upper() for s in symbols]

        # Check which symbols are already cached
        uncached = []
        results: dict[str, dict] = {}
        for sym in symbols:
            cached = cache_get(f"quote:{sym}")
            if cached is not None:
                results[sym] = cached
            else:
                uncached.append(sym)

        if not uncached:
            return results

        # Batch-fetch uncached symbols
        try:
            batch_results = await asyncio.to_thread(_sync_get_quotes_batch, uncached)
            for sym, quote in batch_results.items():
                cache_set(f"quote:{sym}", quote, QUOTE_TTL)
                results[sym] = quote
        except Exception as e:
            logger.warning("Batch quote fetch failed: %s", e)

        return results

    async def get_history(
        self, symbol: str, period: str = "1mo", interval: str = "1d"
    ) -> list[dict]:
        symbol = symbol.upper()
        if period not in VALID_PERIODS:
            period = "1mo"
        if interval not in VALID_INTERVALS:
            interval = "1d"

        cache_key = f"history:{symbol}:{period}:{interval}"

        async def _fetch():
            try:
                result = await asyncio.to_thread(_sync_get_history, symbol, period, interval)
                return result if result else None
            except Exception as e:
                logger.warning("yfinance history failed for %s: %s", symbol, e)
                return None

        result = await get_or_fetch(cache_key, _fetch, HISTORY_TTL)
        return result if result is not None else []
