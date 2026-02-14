"""Currency conversion service with fallback API chain.

Tries multiple free currency APIs in order:
1. Open Exchange Rates (open.er-api.com)
2. ExchangeRate-API (exchangerate-api.com)
3. Frankfurter (api.frankfurter.app)
"""

import logging
from datetime import date

import httpx

logger = logging.getLogger(__name__)

SUPPORTED_CURRENCIES = [
    "USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD",
    "CNY", "HKD", "SGD", "SEK", "NOK", "DKK", "KRW", "INR",
    "BRL", "MXN", "ZAR", "TRY", "PLN", "CZK", "HUF", "ILS",
]


def get_supported_currencies() -> list[str]:
    """Return list of supported currency codes."""
    return SUPPORTED_CURRENCIES


async def _try_open_er_api(
    client: httpx.AsyncClient, amount: float, from_currency: str, to_currency: str
) -> dict | None:
    """Try open.er-api.com (free, no key)."""
    resp = await client.get(f"https://open.er-api.com/v6/latest/{from_currency}")
    resp.raise_for_status()
    data = resp.json()
    rate = data.get("rates", {}).get(to_currency)
    if rate is None:
        return None
    converted = amount * rate
    return {
        "amount": amount,
        "from": from_currency,
        "to": to_currency,
        "converted": round(converted, 4),
        "rate": round(rate, 6),
        "date": data.get("time_last_update_utc", str(date.today())),
    }


async def _try_exchangerate_api(
    client: httpx.AsyncClient, amount: float, from_currency: str, to_currency: str
) -> dict | None:
    """Try exchangerate-api.com (free, no key)."""
    resp = await client.get(f"https://api.exchangerate-api.com/v4/latest/{from_currency}")
    resp.raise_for_status()
    data = resp.json()
    rate = data.get("rates", {}).get(to_currency)
    if rate is None:
        return None
    converted = amount * rate
    return {
        "amount": amount,
        "from": from_currency,
        "to": to_currency,
        "converted": round(converted, 4),
        "rate": round(rate, 6),
        "date": data.get("date", str(date.today())),
    }


async def _try_frankfurter(
    client: httpx.AsyncClient, amount: float, from_currency: str, to_currency: str
) -> dict | None:
    """Try Frankfurter API (free, no key)."""
    resp = await client.get(
        "https://api.frankfurter.app/latest",
        params={"amount": amount, "from": from_currency, "to": to_currency},
    )
    resp.raise_for_status()
    data = resp.json()
    converted = data.get("rates", {}).get(to_currency)
    if converted is None:
        return None
    return {
        "amount": amount,
        "from": from_currency,
        "to": to_currency,
        "converted": round(converted, 4),
        "rate": round(converted / amount, 6) if amount else 0,
        "date": data.get("date", str(date.today())),
    }


_PROVIDERS = [
    ("open.er-api.com", _try_open_er_api),
    ("exchangerate-api.com", _try_exchangerate_api),
    ("frankfurter.app", _try_frankfurter),
]


async def convert_currency(
    amount: float,
    from_currency: str = "USD",
    to_currency: str = "EUR",
) -> dict | None:
    """Convert between currencies using fallback API chain.

    Returns dict with: amount, from, to, converted, rate, date
    """
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    async with httpx.AsyncClient(timeout=10.0) as client:
        for name, provider_fn in _PROVIDERS:
            try:
                result = await provider_fn(client, amount, from_currency, to_currency)
                if result is not None:
                    logger.debug("Currency conversion via %s succeeded", name)
                    return result
            except Exception as e:
                logger.warning("Currency provider %s failed: %s", name, e)
                continue

    logger.error("All currency conversion providers failed for %s->%s", from_currency, to_currency)
    return None
