"""Market data service backed by normalized provider chains."""

from __future__ import annotations

import asyncio
import logging

from app.schemas.asset import AssetType
from app.services.data_providers import (
    COMMODITY_FUTURES_MAP,
    CRYPTO_ID_MAP,
    crypto_provider_chain,
    market_provider_chain,
)

logger = logging.getLogger(__name__)


def _period_from_days(days: int) -> str:
    if days <= 1:
        return "1d"
    if days <= 5:
        return "5d"
    if days <= 30:
        return "1mo"
    if days <= 90:
        return "3mo"
    if days <= 180:
        return "6mo"
    if days <= 365:
        return "1y"
    if days <= 730:
        return "2y"
    return "5y"


class MarketDataService:
    """Fetch quotes and historical data through free-first provider chains."""

    async def close(self) -> None:
        await market_provider_chain.close()
        await crypto_provider_chain.close()

    async def get_crypto_quote(self, symbol: str) -> dict | None:
        quote = await crypto_provider_chain.get_quote(symbol)
        if quote:
            return quote
        logger.warning("No crypto quote available for %s", symbol.upper())
        return None

    async def get_commodity_quote(self, symbol: str) -> dict | None:
        info = COMMODITY_FUTURES_MAP.get(symbol.upper())
        if not info:
            logger.warning("Unknown commodity symbol: %s", symbol)
            return None

        result = await market_provider_chain.get_quote(info["ticker"])
        if not result:
            return None

        normalized = dict(result)
        normalized["symbol"] = symbol.upper()
        normalized["name"] = info["name"]
        return normalized

    async def get_quote(
        self,
        symbol: str,
        asset_type: AssetType | str | None = None,
    ) -> dict | None:
        symbol_upper = symbol.upper()
        asset_type_str = asset_type.value if isinstance(asset_type, AssetType) else asset_type

        if asset_type_str == "commodity" or (
            asset_type_str is None and symbol_upper in COMMODITY_FUTURES_MAP
        ):
            return await self.get_commodity_quote(symbol_upper)

        if asset_type_str == "crypto" or (
            asset_type_str is None and symbol_upper in CRYPTO_ID_MAP
        ):
            return await self.get_crypto_quote(symbol_upper)

        return await market_provider_chain.get_quote(symbol_upper)

    async def get_quotes(self, symbols: list[dict]) -> list[dict]:
        stock_symbols: list[str] = []
        other_items: list[dict] = []

        for item in symbols:
            symbol = item["symbol"].upper()
            asset_type = item.get("type")
            asset_type_str = asset_type.value if isinstance(asset_type, AssetType) else asset_type

            if asset_type_str == "crypto" or (
                asset_type_str is None and symbol in CRYPTO_ID_MAP
            ):
                other_items.append(item)
                continue
            if asset_type_str == "commodity" or (
                asset_type_str is None and symbol in COMMODITY_FUTURES_MAP
            ):
                other_items.append(item)
                continue
            stock_symbols.append(symbol)

        results: list[dict] = []
        if stock_symbols:
            batch = await market_provider_chain.get_quotes_batch(stock_symbols)
            results.extend(batch.values())

        if other_items:
            tasks = [self.get_quote(item["symbol"], item.get("type")) for item in other_items]
            other_results = await asyncio.gather(*tasks, return_exceptions=True)
            results.extend(result for result in other_results if isinstance(result, dict))

        return results

    async def get_history(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> list[dict]:
        symbol_upper = symbol.upper()
        if symbol_upper in COMMODITY_FUTURES_MAP:
            return await market_provider_chain.get_history(
                COMMODITY_FUTURES_MAP[symbol_upper]["ticker"],
                period,
                interval,
            )
        if symbol_upper in CRYPTO_ID_MAP:
            return await crypto_provider_chain.get_history(symbol_upper, period, interval)
        return await market_provider_chain.get_history(symbol_upper, period, interval)

    async def get_crypto_history(
        self,
        symbol: str,
        days: int = 30,
    ) -> list[dict]:
        symbol_upper = symbol.upper()
        records = await crypto_provider_chain.get_market_chart(symbol_upper, days=days)
        if records:
            return records

        history = await crypto_provider_chain.get_history(
            symbol_upper,
            period=_period_from_days(days),
            interval="1d",
        )
        return [
            {
                "date": row.get("date"),
                "price": row.get("close", 0.0),
                "volume": row.get("volume", 0),
                "market_cap": row.get("market_cap", 0),
                "source_provider": row.get("source_provider", ""),
                "retrieval_mode": row.get("retrieval_mode", "unknown"),
            }
            for row in history
        ]

    async def get_top_movers(self, symbols: list[str] | None = None) -> dict:
        if symbols is None:
            symbols = [
                "AAPL",
                "MSFT",
                "GOOGL",
                "AMZN",
                "NVDA",
                "META",
                "TSLA",
                "SPY",
                "QQQ",
                "IWM",
                "DIA",
            ]

        batch = await market_provider_chain.get_quotes_batch(symbols)
        quotes = list(batch.values())
        sorted_quotes = sorted(
            quotes,
            key=lambda item: item["change_percent"],
            reverse=True,
        )

        return {
            "gainers": sorted_quotes[:5],
            "losers": sorted_quotes[-5:][::-1] if len(sorted_quotes) >= 5 else [],
        }

    async def get_extended_movers(
        self,
        symbols: list[str] | None = None,
        threshold: float = 2.0,
    ) -> dict:
        if symbols is None:
            symbols = [
                "AAPL",
                "MSFT",
                "GOOGL",
                "AMZN",
                "NVDA",
                "META",
                "TSLA",
                "SPY",
                "QQQ",
                "IWM",
                "DIA",
                "AMD",
                "NFLX",
                "CRM",
                "ORCL",
                "INTC",
                "BA",
                "DIS",
                "V",
                "JPM",
                "GS",
                "WMT",
                "KO",
                "PEP",
            ]

        batch = await market_provider_chain.get_quotes_batch(symbols)
        quotes = list(batch.values())
        sorted_quotes = sorted(
            quotes,
            key=lambda item: item["change_percent"],
            reverse=True,
        )
        gainers = [item for item in sorted_quotes if item["change_percent"] >= threshold][:15]
        losers = [
            item for item in reversed(sorted_quotes) if item["change_percent"] <= -threshold
        ][:15]

        top_movers = gainers + losers

        async def _add_sparkline(quote: dict) -> dict:
            try:
                history = await self.get_history(quote["symbol"], period="5d", interval="1d")
                quote["sparkline"] = [row["close"] for row in history] if history else []
            except Exception:
                quote["sparkline"] = []
            return quote

        await asyncio.gather(
            *[_add_sparkline(quote) for quote in top_movers],
            return_exceptions=True,
        )

        return {"gainers": gainers, "losers": losers}


market_data_service = MarketDataService()
