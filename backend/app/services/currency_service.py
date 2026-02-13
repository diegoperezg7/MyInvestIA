"""Currency conversion service using Frankfurter API (free, no key needed)."""

import logging

import httpx

logger = logging.getLogger(__name__)

FRANKFURTER_BASE = "https://api.frankfurter.app"

SUPPORTED_CURRENCIES = [
    "USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD",
    "CNY", "HKD", "SGD", "SEK", "NOK", "DKK", "KRW", "INR",
    "BRL", "MXN", "ZAR", "TRY", "PLN", "CZK", "HUF", "ILS",
]


def get_supported_currencies() -> list[str]:
    """Return list of supported currency codes."""
    return SUPPORTED_CURRENCIES


async def convert_currency(
    amount: float,
    from_currency: str = "USD",
    to_currency: str = "EUR",
) -> dict | None:
    """Convert between currencies using Frankfurter API.

    Returns dict with: amount, from, to, converted, rate
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{FRANKFURTER_BASE}/latest",
                params={
                    "amount": amount,
                    "from": from_currency.upper(),
                    "to": to_currency.upper(),
                },
            )
            resp.raise_for_status()
            data = resp.json()

            rates = data.get("rates", {})
            converted = rates.get(to_currency.upper())

            if converted is None:
                return None

            return {
                "amount": amount,
                "from": from_currency.upper(),
                "to": to_currency.upper(),
                "converted": round(converted, 4),
                "rate": round(converted / amount, 6) if amount else 0,
                "date": data.get("date", ""),
            }
    except Exception as e:
        logger.warning("Currency conversion failed: %s", e)
        return None
