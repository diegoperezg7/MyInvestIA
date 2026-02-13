"""Market data service using provider chain for stocks/ETFs and CoinGecko for crypto.

Provides real-time and historical price data, plus basic quote information.
Delegates stock/ETF data to the provider chain (yfinance -> alphavantage -> finnhub -> twelvedata).
CoinGecko uses the free public API (no key needed) for crypto.
"""

import asyncio
import logging
from datetime import datetime, timezone

import httpx

from app.schemas.asset import AssetType
from app.services.provider_chain import provider_chain

logger = logging.getLogger(__name__)

# CoinGecko symbol mapping: our symbol -> coingecko id
CRYPTO_ID_MAP: dict[str, str] = {
    # Major / Layer 1
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
    # DeFi
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
    # Layer 2 / Infrastructure
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
    # Other major
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
    # Memecoins
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

COMMODITY_FUTURES_MAP: dict[str, dict] = {
    # Precious Metals
    "GOLD": {"ticker": "GC=F", "name": "Gold", "category": "metals"},
    "SILVER": {"ticker": "SI=F", "name": "Silver", "category": "metals"},
    "PLATINUM": {"ticker": "PL=F", "name": "Platinum", "category": "metals"},
    "PALLADIUM": {"ticker": "PA=F", "name": "Palladium", "category": "metals"},
    "COPPER": {"ticker": "HG=F", "name": "Copper", "category": "metals"},
    # Energy
    "OIL": {"ticker": "CL=F", "name": "Crude Oil WTI", "category": "energy"},
    "BRENT": {"ticker": "BZ=F", "name": "Brent Crude", "category": "energy"},
    "NATGAS": {"ticker": "NG=F", "name": "Natural Gas", "category": "energy"},
    # Agriculture
    "WHEAT": {"ticker": "ZW=F", "name": "Wheat", "category": "agriculture"},
    "CORN": {"ticker": "ZC=F", "name": "Corn", "category": "agriculture"},
    "SOYBEAN": {"ticker": "ZS=F", "name": "Soybeans", "category": "agriculture"},
    "COFFEE": {"ticker": "KC=F", "name": "Coffee", "category": "agriculture"},
    "SUGAR": {"ticker": "SB=F", "name": "Sugar", "category": "agriculture"},
    "COCOA": {"ticker": "CC=F", "name": "Cocoa", "category": "agriculture"},
    "COTTON": {"ticker": "CT=F", "name": "Cotton", "category": "agriculture"},
    "CATTLE": {"ticker": "LE=F", "name": "Live Cattle", "category": "agriculture"},
}

COINGECKO_BASE = "https://api.coingecko.com/api/v3"


class MarketDataService:
    """Fetches live and historical market data via provider chain and CoinGecko."""

    def __init__(self):
        self._http_client: httpx.AsyncClient | None = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=15.0)
        return self._http_client

    async def close(self):
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
        await provider_chain.close()

    # --- Quote (current price) ---

    async def get_crypto_quote(self, symbol: str) -> dict | None:
        """Get current quote for a cryptocurrency via CoinGecko."""
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

    async def get_commodity_quote(self, symbol: str) -> dict | None:
        """Get current quote for a commodity via yfinance futures ticker."""
        info = COMMODITY_FUTURES_MAP.get(symbol.upper())
        if not info:
            logger.warning("Unknown commodity symbol: %s", symbol)
            return None

        result = await provider_chain.get_quote(info["ticker"])
        if result:
            result["symbol"] = symbol.upper()
            result["name"] = info["name"]
        return result

    async def get_quote(self, symbol: str, asset_type: AssetType | str | None = None) -> dict | None:
        """Get a quote for any asset. Uses provider chain for stocks, CoinGecko for crypto,
        yfinance futures for commodities.
        Falls back to yfinance ({SYMBOL}-USD) if CoinGecko is rate-limited."""
        symbol = symbol.upper()
        asset_type_str = asset_type.value if isinstance(asset_type, AssetType) else asset_type

        if asset_type_str == "commodity" or (asset_type_str is None and symbol in COMMODITY_FUTURES_MAP):
            return await self.get_commodity_quote(symbol)
        elif asset_type_str == "crypto" or (asset_type_str is None and symbol in CRYPTO_ID_MAP):
            result = await self.get_crypto_quote(symbol)
            if result:
                return result
            # Fallback: use yfinance with -USD suffix
            logger.info("CoinGecko failed for %s, falling back to yfinance", symbol)
            yf_result = await provider_chain.get_quote(f"{symbol}-USD")
            if yf_result:
                yf_result["symbol"] = symbol  # Keep clean symbol (BTC not BTC-USD)
                return yf_result
            return None
        else:
            # Use provider chain with fallback (already cached in yfinance_provider)
            return await provider_chain.get_quote(symbol)

    async def get_quotes(self, symbols: list[dict]) -> list[dict]:
        """Get quotes for multiple assets. Uses batch fetching for stock symbols."""
        # Separate stocks from crypto/commodity for batch vs individual fetching
        stock_symbols = []
        other_items = []
        for item in symbols:
            sym = item["symbol"].upper()
            asset_type = item.get("type")
            asset_type_str = asset_type.value if isinstance(asset_type, AssetType) else asset_type
            if asset_type_str == "crypto" or (asset_type_str is None and sym in CRYPTO_ID_MAP):
                other_items.append(item)
            elif asset_type_str == "commodity" or (asset_type_str is None and sym in COMMODITY_FUTURES_MAP):
                other_items.append(item)
            else:
                stock_symbols.append(sym)

        results = []

        # Batch-fetch stocks
        if stock_symbols:
            batch = await provider_chain.get_quotes_batch(stock_symbols)
            results.extend(batch.values())

        # Fetch crypto/commodity individually in parallel
        if other_items:
            tasks = [self.get_quote(item["symbol"], item.get("type")) for item in other_items]
            other_results = await asyncio.gather(*tasks, return_exceptions=True)
            results.extend(r for r in other_results if isinstance(r, dict))

        return results

    # --- Historical data ---

    async def get_history(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> list[dict]:
        """Get historical OHLCV data via provider chain (async + cached).

        Crypto symbols (e.g. BTC) are converted to yfinance format (BTC-USD).
        Commodity symbols (e.g. GOLD) are converted to futures tickers (GC=F).
        """
        sym = symbol.upper()
        # Commodity symbols need futures ticker for yfinance
        if sym in COMMODITY_FUTURES_MAP:
            sym = COMMODITY_FUTURES_MAP[sym]["ticker"]
        # Crypto symbols need -USD suffix for yfinance OHLCV data
        elif sym in CRYPTO_ID_MAP:
            sym = f"{sym}-USD"
        return await provider_chain.get_history(sym, period, interval)

    async def get_crypto_history(
        self,
        symbol: str,
        days: int = 30,
    ) -> list[dict]:
        """Get historical price data for crypto via CoinGecko."""
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

    async def get_top_movers(self, symbols: list[str] | None = None) -> dict:
        """Get top gainers and losers from a set of symbols (batch fetch)."""
        if symbols is None:
            symbols = [
                "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
                "SPY", "QQQ", "IWM", "DIA",
            ]

        batch = await provider_chain.get_quotes_batch(symbols)
        quotes = list(batch.values())

        sorted_quotes = sorted(quotes, key=lambda x: x["change_percent"], reverse=True)

        return {
            "gainers": sorted_quotes[:5],
            "losers": sorted_quotes[-5:][::-1] if len(sorted_quotes) >= 5 else [],
        }

    async def get_extended_movers(
        self,
        symbols: list[str] | None = None,
        threshold: float = 2.0,
    ) -> dict:
        """Get movers with sparkline data and threshold filtering (batch fetch)."""
        if symbols is None:
            symbols = [
                "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
                "SPY", "QQQ", "IWM", "DIA", "AMD", "NFLX", "CRM", "ORCL",
                "INTC", "BA", "DIS", "V", "JPM", "GS", "WMT", "KO", "PEP",
            ]

        # Batch-fetch all quotes in a single HTTP call
        batch = await provider_chain.get_quotes_batch(symbols)
        quotes = list(batch.values())

        # Fetch sparklines in parallel for all valid quotes
        async def _add_sparkline(q: dict) -> dict:
            history = await self.get_history(q["symbol"], period="5d", interval="1d")
            q["sparkline"] = [r["close"] for r in history] if history else []
            return q

        sparkline_tasks = [_add_sparkline(q) for q in quotes]
        quotes = await asyncio.gather(*sparkline_tasks, return_exceptions=True)
        quotes = [q for q in quotes if isinstance(q, dict)]

        sorted_quotes = sorted(quotes, key=lambda x: x["change_percent"], reverse=True)

        gainers = [q for q in sorted_quotes if q["change_percent"] >= threshold]
        losers = [q for q in reversed(sorted_quotes) if q["change_percent"] <= -threshold]

        return {"gainers": gainers[:15], "losers": losers[:15]}


# Singleton
market_data_service = MarketDataService()
