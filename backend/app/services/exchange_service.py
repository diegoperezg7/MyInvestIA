"""Exchange service using CCXT for Binance and other exchanges."""

import logging

import ccxt

from app.services.encryption_service import decrypt

logger = logging.getLogger(__name__)

# Map of supported exchange providers to CCXT exchange IDs
EXCHANGE_MAP: dict[str, str] = {
    "binance": "binance",
    "coinbase": "coinbase",
    "kraken": "kraken",
    "kucoin": "kucoin",
    "bybit": "bybit",
    "okx": "okx",
    "gateio": "gateio",
    "bitfinex": "bitfinex",
    "gemini": "gemini",
    "cryptocom": "cryptocom",
    "htx": "htx",
    "bitget": "bitget",
    "mexc": "mexc",
}


def _create_exchange(provider: str, credentials: dict) -> ccxt.Exchange:
    """Create an authenticated CCXT exchange instance."""
    exchange_id = EXCHANGE_MAP.get(provider)
    if not exchange_id:
        raise ValueError(f"Unsupported exchange provider: {provider}")

    exchange_class = getattr(ccxt, exchange_id)
    config = {
        "apiKey": credentials.get("api_key", ""),
        "secret": credentials.get("api_secret", ""),
        "enableRateLimit": True,
    }
    if credentials.get("passphrase"):
        config["password"] = credentials["passphrase"]

    return exchange_class(config)


def test_connection(provider: str, credentials: dict) -> dict:
    """Test exchange connectivity and return account info."""
    try:
        exchange = _create_exchange(provider, credentials)
        balance = exchange.fetch_balance()
        return {
            "success": True,
            "message": f"Connected to {provider} successfully",
            "account_info": {
                "exchange": provider,
                "currencies_with_balance": len([
                    k for k, v in balance.get("total", {}).items()
                    if v and v > 0
                ]),
            },
        }
    except ccxt.AuthenticationError:
        return {"success": False, "message": "Authentication failed — check API key and secret", "account_info": {}}
    except ccxt.NetworkError as e:
        return {"success": False, "message": f"Network error: {e}", "account_info": {}}
    except Exception as e:
        return {"success": False, "message": f"Connection failed: {e}", "account_info": {}}


def fetch_balances(provider: str, credentials_encrypted: str) -> list[dict]:
    """Fetch all non-zero balances from an exchange."""
    credentials = decrypt(credentials_encrypted)
    exchange = _create_exchange(provider, credentials)

    try:
        balance = exchange.fetch_balance()
    except ccxt.AuthenticationError:
        raise ValueError("Authentication failed — API credentials may be invalid or expired")
    except Exception as e:
        raise ValueError(f"Failed to fetch balances from {provider}: {e}")

    holdings = []
    total = balance.get("total", {})
    for symbol, amount in total.items():
        if not amount or amount <= 0:
            continue
        # Skip fiat currencies
        if symbol in ("USD", "EUR", "GBP", "USDT", "USDC", "BUSD"):
            continue

        holdings.append({
            "symbol": symbol,
            "name": symbol,
            "type": "crypto",
            "quantity": float(amount),
            "avg_buy_price": 0.0,  # CCXT doesn't provide cost basis
        })

    return holdings


def get_supported_exchanges() -> list[str]:
    """Return list of supported exchange provider IDs."""
    return list(EXCHANGE_MAP.keys())
