"""Dividend tracking service.

Fetches dividend data from yfinance for portfolio holdings.
"""

import logging

import yfinance as yf

logger = logging.getLogger(__name__)


def get_dividends(symbol: str, period: str = "1y") -> list[dict]:
    """Get dividend history for a symbol.

    Args:
        symbol: Stock ticker
        period: History period (1y, 2y, 5y, max)

    Returns:
        List of dicts with date, amount, symbol
    """
    try:
        ticker = yf.Ticker(symbol.upper())
        divs = ticker.dividends

        if divs.empty:
            return []

        records = []
        for date, amount in divs.items():
            records.append({
                "date": date.isoformat(),
                "amount": round(float(amount), 4),
                "symbol": symbol.upper(),
            })

        return records
    except Exception as e:
        logger.warning("Failed to get dividends for %s: %s", symbol, e)
        return []


def get_portfolio_dividends(symbols: list[str]) -> dict:
    """Get dividend data for all portfolio symbols.

    Returns:
        Dict with per-symbol dividends and totals
    """
    all_dividends: dict[str, list[dict]] = {}
    total_annual = 0.0

    for symbol in symbols:
        divs = get_dividends(symbol, period="1y")
        all_dividends[symbol] = divs
        total_annual += sum(d["amount"] for d in divs)

    return {
        "dividends": all_dividends,
        "total_annual": round(total_annual, 4),
        "symbols_with_dividends": sum(1 for d in all_dividends.values() if d),
    }
