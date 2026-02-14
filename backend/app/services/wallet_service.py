"""Wallet service using Moralis for MetaMask and EVM wallet tracking."""

import logging
import re

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Map chain names to Moralis chain identifiers
CHAIN_MAP: dict[str, str] = {
    "ethereum": "eth",
    "polygon": "polygon",
    "bsc": "bsc",
    "arbitrum": "arbitrum",
    "optimism": "optimism",
    "avalanche": "avalanche",
    "base": "base",
}

MORALIS_BASE_URL = "https://deep-index.moralis.io/api/v2.2"


def _get_headers() -> dict:
    """Get Moralis API headers."""
    if not settings.moralis_api_key:
        raise ValueError("MORALIS_API_KEY not configured — set it in .env")
    return {
        "Accept": "application/json",
        "X-API-Key": settings.moralis_api_key,
    }


def _resolve_chain(chain: str) -> str:
    """Resolve chain name to Moralis chain identifier."""
    resolved = CHAIN_MAP.get(chain.lower(), chain.lower())
    return resolved


def validate_address(address: str, chain: str = "ethereum") -> bool:
    """Validate an EVM address format."""
    return bool(re.match(r"^0x[0-9a-fA-F]{40}$", address))


async def get_native_balance(address: str, chain: str = "ethereum") -> dict | None:
    """Get native token balance (ETH, MATIC, BNB, etc.)."""
    chain_id = _resolve_chain(chain)
    url = f"{MORALIS_BASE_URL}/{address}/balance"

    native_names = {
        "eth": ("ETH", "Ethereum"),
        "polygon": ("MATIC", "Polygon"),
        "bsc": ("BNB", "BNB Chain"),
        "arbitrum": ("ETH", "Ethereum (Arbitrum)"),
        "optimism": ("ETH", "Ethereum (Optimism)"),
        "avalanche": ("AVAX", "Avalanche"),
        "base": ("ETH", "Ethereum (Base)"),
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=_get_headers(), params={"chain": chain_id})
            resp.raise_for_status()
            data = resp.json()

        balance_wei = int(data.get("balance", "0"))
        balance = balance_wei / 1e18

        if balance <= 0:
            return None

        symbol, name = native_names.get(chain_id, ("ETH", "Native Token"))
        return {
            "symbol": symbol,
            "name": name,
            "type": "crypto",
            "quantity": balance,
            "avg_buy_price": 0.0,
        }
    except Exception as e:
        logger.warning("Failed to get native balance for %s on %s: %s", address, chain, e)
        return None


async def get_erc20_balances(address: str, chain: str = "ethereum") -> list[dict]:
    """Get ERC-20 token balances with prices."""
    chain_id = _resolve_chain(chain)
    url = f"{MORALIS_BASE_URL}/{address}/erc20"

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=_get_headers(), params={"chain": chain_id})
            resp.raise_for_status()
            tokens = resp.json()

        holdings = []
        for token in tokens:
            decimals = int(token.get("decimals", 18))
            raw_balance = int(token.get("balance", "0"))
            balance = raw_balance / (10 ** decimals)

            if balance <= 0:
                continue

            symbol = token.get("symbol", "UNKNOWN")
            name = token.get("name", symbol)

            # Skip known spam/dust tokens
            if len(symbol) > 20 or balance < 0.0001:
                continue

            holdings.append({
                "symbol": symbol,
                "name": name,
                "type": "crypto",
                "quantity": balance,
                "avg_buy_price": 0.0,
            })

        return holdings
    except Exception as e:
        logger.warning("Failed to get ERC-20 balances for %s on %s: %s", address, chain, e)
        return []


async def fetch_balances(address: str, chain: str = "ethereum") -> list[dict]:
    """Fetch all token balances (native + ERC-20) for a wallet."""
    holdings = []

    native = await get_native_balance(address, chain)
    if native:
        holdings.append(native)

    erc20 = await get_erc20_balances(address, chain)
    holdings.extend(erc20)

    return holdings


def get_supported_chains() -> list[str]:
    """Return list of supported chain names."""
    return list(CHAIN_MAP.keys())
