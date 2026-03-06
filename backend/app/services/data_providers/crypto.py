"""Crypto providers and fallback chain."""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.config import settings
from app.services.cache import QUOTE_TTL, get_or_fetch
from app.services.data_providers.base import CryptoProvider
from app.services.data_providers.chain import FallbackProviderChain, parse_provider_order
from app.services.data_providers.normalization import (
    normalize_history_rows,
    normalize_quote_payload,
    normalize_symbol,
    to_utc_iso,
)
from app.services.providers.yfinance_provider import YFinanceProvider as LegacyYFinanceProvider

CRYPTO_ID_MAP: dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "ADA": "cardano",
    "DOT": "polkadot",
    "AVAX": "avalanche-2",
    "MATIC": "matic-network",
    "ATOM": "cosmos",
    "XRP": "ripple",
    "BNB": "binancecoin",
    "TRX": "tron",
    "TON": "the-open-network",
    "NEAR": "near",
    "SUI": "sui",
    "APT": "aptos",
    "SEI": "sei-network",
    "INJ": "injective-protocol",
    "FTM": "fantom",
    "ALGO": "algorand",
    "HBAR": "hedera-hashgraph",
    "ICP": "internet-computer",
    "FIL": "filecoin",
    "EGLD": "elrond-erd-2",
    "FLOW": "flow",
    "LINK": "chainlink",
    "UNI": "uniswap",
    "AAVE": "aave",
    "MKR": "maker",
    "LDO": "lido-dao",
    "CRV": "curve-dao-token",
    "SNX": "havven",
    "COMP": "compound-governance-token",
    "SUSHI": "sushi",
    "DYDX": "dydx",
    "GMX": "gmx",
    "PENDLE": "pendle",
    "JUP": "jupiter-exchange-solana",
    "RAY": "raydium",
    "ARB": "arbitrum",
    "OP": "optimism",
    "STRK": "starknet",
    "IMX": "immutable-x",
    "RNDR": "render-token",
    "GRT": "the-graph",
    "FET": "fetch-ai",
    "AGIX": "singularitynet",
    "THETA": "theta-token",
    "AR": "arweave",
    "OCEAN": "ocean-protocol",
    "AKT": "akash-network",
    "LTC": "litecoin",
    "BCH": "bitcoin-cash",
    "ETC": "ethereum-classic",
    "XLM": "stellar",
    "VET": "vechain",
    "SAND": "the-sandbox",
    "MANA": "decentraland",
    "AXS": "axie-infinity",
    "ENJ": "enjincoin",
    "GALA": "gala",
    "APE": "apecoin",
    "BLUR": "blur",
    "CRO": "crypto-com-chain",
    "OKB": "okb",
    "LEO": "leo-token",
    "DOGE": "dogecoin",
    "SHIB": "shiba-inu",
    "PEPE": "pepe",
    "WIF": "dogwifcoin",
    "BONK": "bonk",
    "FLOKI": "floki",
    "TRUMP": "official-trump",
    "MEME": "memecoin-2",
    "MYRO": "myro",
    "POPCAT": "popcat",
    "BRETT": "brett",
    "MOG": "mog-coin",
    "SPX": "spx6900",
    "TURBO": "turbo",
    "NEIRO": "neiro-on-eth",
}

COINGECKO_BASE = "https://api.coingecko.com/api/v3"


class CoinGeckoCryptoProvider(CryptoProvider):
    provider_id = "coingecko"
    display_name = "CoinGecko"
    retrieval_mode = "public_api"
    note = "Primary free crypto market data provider"
    is_core = True
    is_free = True
    capabilities = ("quote", "history", "market_chart")

    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    @property
    def is_configured(self) -> bool:
        return True

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {}
            if settings.coingecko_api_key:
                headers["x-cg-demo-api-key"] = settings.coingecko_api_key
            self._client = httpx.AsyncClient(timeout=15.0, headers=headers)
        return self._client

    async def get_quote(self, symbol: str) -> dict | None:
        normalized_symbol = normalize_symbol(symbol)
        coin_id = CRYPTO_ID_MAP.get(normalized_symbol)
        if not coin_id:
            return None

        async def _fetch():
            client = await self._get_client()
            response = await client.get(
                f"{COINGECKO_BASE}/simple/price",
                params={
                    "ids": coin_id,
                    "vs_currencies": "usd",
                    "include_24hr_change": "true",
                    "include_24hr_vol": "true",
                    "include_market_cap": "true",
                    "include_last_updated_at": "true",
                },
            )
            response.raise_for_status()
            payload = response.json().get(coin_id, {})
            if not payload:
                return None
            return normalize_quote_payload(
                {
                    "symbol": normalized_symbol,
                    "name": coin_id.replace("-", " ").title(),
                    "price": payload.get("usd"),
                    "change_percent": payload.get("usd_24h_change"),
                    "volume": payload.get("usd_24h_vol"),
                    "market_cap": payload.get("usd_market_cap"),
                    "timestamp": payload.get("last_updated_at"),
                },
                symbol=normalized_symbol,
                provider_id=self.provider_id,
                provider_name=self.display_name,
                retrieval_mode=self.retrieval_mode,
            )

        return await get_or_fetch(
            f"crypto:quote:{normalized_symbol}",
            _fetch,
            QUOTE_TTL,
        )

    async def get_history(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> list[dict]:
        days_map = {
            "1d": 1,
            "5d": 5,
            "1mo": 30,
            "3mo": 90,
            "6mo": 180,
            "1y": 365,
            "2y": 730,
            "5y": 1825,
        }
        return await self._market_chart_to_ohlcv(symbol, days=days_map.get(period, 30))

    async def get_market_chart(self, symbol: str, days: int = 30) -> list[dict]:
        normalized_symbol = normalize_symbol(symbol)
        coin_id = CRYPTO_ID_MAP.get(normalized_symbol)
        if not coin_id:
            return []

        async def _fetch():
            client = await self._get_client()
            response = await client.get(
                f"{COINGECKO_BASE}/coins/{coin_id}/market_chart",
                params={"vs_currency": "usd", "days": str(days)},
            )
            response.raise_for_status()
            payload = response.json()
            prices = payload.get("prices", [])
            volumes = payload.get("total_volumes", [])
            market_caps = payload.get("market_caps", [])

            records = []
            for index, (timestamp_ms, price) in enumerate(prices):
                records.append(
                    {
                        "date": datetime.fromtimestamp(
                            timestamp_ms / 1000, tz=timezone.utc
                        ).isoformat(),
                        "price": round(float(price), 4),
                        "volume": volumes[index][1] if index < len(volumes) else 0,
                        "market_cap": market_caps[index][1] if index < len(market_caps) else 0,
                        "source_provider": self.provider_id,
                        "retrieval_mode": self.retrieval_mode,
                    }
                )
            return records

        return await get_or_fetch(
            f"crypto:chart:{normalized_symbol}:{days}",
            _fetch,
            QUOTE_TTL * 2,
        ) or []

    async def _market_chart_to_ohlcv(self, symbol: str, days: int = 30) -> list[dict]:
        chart = await self.get_market_chart(symbol, days=days)
        rows = []
        for point in chart:
            price = point.get("price", 0.0)
            rows.append(
                {
                    "date": point.get("date"),
                    "open": price,
                    "high": price,
                    "low": price,
                    "close": price,
                    "volume": point.get("volume", 0),
                }
            )
        return normalize_history_rows(
            rows,
            provider_id=self.provider_id,
            retrieval_mode=self.retrieval_mode,
        )

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()


class YFinanceCryptoProvider(CryptoProvider):
    provider_id = "yfinance"
    display_name = "Yahoo Finance"
    retrieval_mode = "library"
    note = "Fallback crypto provider via ticker-USD pairs"
    is_core = False
    is_free = True
    capabilities = ("quote", "history")

    def __init__(self):
        self._provider = LegacyYFinanceProvider()

    @property
    def is_configured(self) -> bool:
        return True

    async def get_quote(self, symbol: str) -> dict | None:
        normalized_symbol = normalize_symbol(symbol)
        raw = await self._provider.get_quote(f"{normalized_symbol}-USD")
        normalized = normalize_quote_payload(
            raw,
            symbol=normalized_symbol,
            provider_id=self.provider_id,
            provider_name=self.display_name,
            retrieval_mode=self.retrieval_mode,
        )
        if normalized:
            normalized["symbol"] = normalized_symbol
        return normalized

    async def get_history(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> list[dict]:
        normalized_symbol = normalize_symbol(symbol)
        rows = await self._provider.get_history(
            f"{normalized_symbol}-USD",
            period,
            interval,
        )
        return normalize_history_rows(
            rows,
            provider_id=self.provider_id,
            retrieval_mode=self.retrieval_mode,
        )

    async def close(self) -> None:
        await self._provider.close()


class CryptoProviderChain(FallbackProviderChain):
    def __init__(self):
        super().__init__(
            "crypto",
            [CoinGeckoCryptoProvider(), YFinanceCryptoProvider()],
            parse_provider_order(settings.crypto_provider_order),
        )

    async def get_quote(self, symbol: str) -> dict | None:
        return await self.call_first("get_quote", symbol)

    async def get_history(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> list[dict]:
        return await self.call_first("get_history", symbol, period, interval) or []

    async def get_market_chart(self, symbol: str, days: int = 30) -> list[dict]:
        for provider in self.active_providers:
            if "market_chart" not in provider.capabilities:
                continue
            result = await provider.get_market_chart(symbol, days=days)
            if result:
                return result
        return []


crypto_provider_chain = CryptoProviderChain()
