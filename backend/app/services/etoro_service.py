"""eToro broker service for portfolio synchronization.

Note: eToro API was launched in Oct 2025 with limited access.
This service provides the architecture for when access is available.
"""

import logging

import httpx

from app.config import settings
from app.services.encryption_service import decrypt

logger = logging.getLogger(__name__)

ETORO_BASE_URL = "https://api.etoro.com/api/v1"


def _get_headers(credentials: dict) -> dict:
    """Build eToro API headers."""
    return {
        "Authorization": f"Bearer {credentials.get('api_key', '')}",
        "Content-Type": "application/json",
    }


def test_connection(credentials: dict) -> dict:
    """Test eToro API connectivity."""
    if not settings.etoro_api_key and not credentials.get("api_key"):
        return {
            "success": False,
            "message": "eToro API access is currently limited. "
                       "The API was launched in Oct 2025 and requires approved access. "
                       "Your connection will be saved and activated once access is granted.",
            "account_info": {},
        }

    # When access is available, this will validate credentials
    return {
        "success": False,
        "message": "eToro API integration is ready but awaiting API access approval. "
                   "Connection saved — will auto-activate when available.",
        "account_info": {},
    }


async def fetch_portfolio(credentials_encrypted: str) -> list[dict]:
    """Fetch open positions from eToro."""
    credentials = decrypt(credentials_encrypted)

    if not credentials.get("api_key"):
        raise ValueError(
            "eToro API access not configured. "
            "The API requires approved access — contact eToro for developer access."
        )

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{ETORO_BASE_URL}/portfolio/positions",
                headers=_get_headers(credentials),
            )
            resp.raise_for_status()
            positions = resp.json()

        holdings = []
        for pos in positions.get("positions", []):
            asset_type = "stock"
            instrument_type = pos.get("instrument_type", "").lower()
            if instrument_type == "crypto":
                asset_type = "crypto"
            elif instrument_type == "etf":
                asset_type = "etf"

            holdings.append({
                "symbol": pos.get("ticker", pos.get("instrument_id", "UNKNOWN")),
                "name": pos.get("instrument_name", ""),
                "type": asset_type,
                "quantity": float(pos.get("units", 0)),
                "avg_buy_price": float(pos.get("open_rate", 0)),
            })

        return holdings
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise ValueError("eToro authentication failed — check API credentials")
        raise ValueError(f"eToro API error: {e.response.status_code}")
    except Exception as e:
        raise ValueError(f"Failed to fetch eToro portfolio: {e}")


async def fetch_account_info(credentials_encrypted: str) -> dict:
    """Fetch eToro account summary."""
    credentials = decrypt(credentials_encrypted)

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{ETORO_BASE_URL}/account",
                headers=_get_headers(credentials),
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        return {"error": str(e)}
