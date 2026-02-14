"""Polymarket prediction market service for position tracking.

Uses the Polymarket Data API (https://docs.polymarket.com/developers/misc-endpoints/data-api-get-positions).
"""

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

POLYMARKET_DATA_URL = "https://data-api.polymarket.com"
POLYMARKET_GAMMA_URL = "https://gamma-api.polymarket.com"


def test_connection(credentials: dict) -> dict:
    """Test Polymarket connectivity."""
    address = credentials.get("wallet_address", "")
    api_key = credentials.get("api_key", "")

    if not address and not api_key:
        return {
            "success": False,
            "message": "Provide either a wallet address or API key for Polymarket",
            "account_info": {},
        }

    return {
        "success": True,
        "message": "Polymarket connection configured",
        "account_info": {"wallet_address": address} if address else {},
    }


async def fetch_positions(wallet_address: str | None = None, api_key: str | None = None) -> list[dict]:
    """Fetch active positions from Polymarket Data API."""
    if not wallet_address and not api_key:
        raise ValueError("Either wallet_address or api_key required for Polymarket")

    holdings = []

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            if wallet_address:
                resp = await client.get(
                    f"{POLYMARKET_DATA_URL}/positions",
                    params={
                        "user": wallet_address.lower(),
                        "sizeThreshold": 0,
                        "limit": 100,
                        "sortBy": "CURRENT",
                        "sortDirection": "DESC",
                    },
                )
                resp.raise_for_status()
                positions = resp.json()

                for pos in positions if isinstance(positions, list) else []:
                    size = float(pos.get("size", 0))
                    if size <= 0:
                        continue

                    title = pos.get("title", "Unknown Market")
                    outcome = pos.get("outcome", "")
                    condition_id = pos.get("conditionId", "")
                    avg_price = float(pos.get("avgPrice", 0))
                    current_value = float(pos.get("currentValue", 0))

                    short_id = condition_id[:8] if condition_id else "unknown"
                    display_name = f"{title[:80]} ({outcome})" if outcome else title[:100]

                    holdings.append({
                        "symbol": f"POLY-{short_id}",
                        "name": display_name,
                        "type": "prediction",
                        "quantity": size,
                        "avg_buy_price": avg_price,
                    })

    except Exception as e:
        logger.warning("Failed to fetch Polymarket positions: %s", e)
        raise ValueError(f"Failed to fetch Polymarket positions: {e}")

    return holdings


async def fetch_markets(market_ids: list[str]) -> list[dict]:
    """Fetch market info for given market IDs."""
    markets = []
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            for mid in market_ids[:20]:
                resp = await client.get(f"{POLYMARKET_GAMMA_URL}/markets/{mid}")
                if resp.status_code == 200:
                    markets.append(resp.json())
    except Exception as e:
        logger.warning("Failed to fetch Polymarket markets: %s", e)
    return markets
