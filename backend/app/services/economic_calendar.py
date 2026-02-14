"""Economic calendar service using Finnhub API."""

import logging
from datetime import datetime, timedelta

import httpx

from app.config import settings
from app.services import cache

logger = logging.getLogger(__name__)

CALENDAR_TTL = 3600  # 1 hour
FINNHUB_BASE = "https://finnhub.io/api/v1"


async def fetch_economic_calendar(start_date: str = "", end_date: str = "") -> dict:
    """Fetch economic events and earnings from Finnhub."""
    today = datetime.now()

    if not start_date:
        start_date = today.strftime("%Y-%m-%d")
    if not end_date:
        end_date = (today + timedelta(days=7)).strftime("%Y-%m-%d")

    cache_key = f"economic_calendar:{start_date}:{end_date}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    events = await _fetch_economic_events(start_date, end_date)
    earnings = await _fetch_earnings(start_date, end_date)

    result = {
        "events": events,
        "earnings": earnings,
        "date_range": {"start": start_date, "end": end_date},
    }

    cache.set(cache_key, result, CALENDAR_TTL)
    return result


async def _fetch_economic_events(start: str, end: str) -> list[dict]:
    """Fetch economic events from Finnhub."""
    if not settings.finnhub_api_key:
        return _get_sample_events()

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{FINNHUB_BASE}/calendar/economic",
                params={"from": start, "to": end, "token": settings.finnhub_api_key},
            )
            resp.raise_for_status()
            data = resp.json()

        events = []
        for item in (data.get("economicCalendar", []) or []):
            impact = "low"
            event_name = item.get("event", "").lower()
            if any(k in event_name for k in ["gdp", "cpi", "interest rate", "nonfarm", "fomc", "fed"]):
                impact = "high"
            elif any(k in event_name for k in ["pmi", "employment", "retail", "housing", "confidence"]):
                impact = "medium"

            events.append({
                "date": item.get("date", ""),
                "time": item.get("time", ""),
                "event": item.get("event", ""),
                "country": item.get("country", ""),
                "impact": impact,
                "forecast": item.get("estimate"),
                "previous": item.get("prev"),
                "actual": item.get("actual"),
            })

        return events[:50]
    except Exception as e:
        logger.error("Failed to fetch economic events: %s", e)
        return _get_sample_events()


async def _fetch_earnings(start: str, end: str) -> list[dict]:
    """Fetch earnings calendar from Finnhub."""
    if not settings.finnhub_api_key:
        return _get_sample_earnings()

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{FINNHUB_BASE}/calendar/earnings",
                params={"from": start, "to": end, "token": settings.finnhub_api_key},
            )
            resp.raise_for_status()
            data = resp.json()

        earnings = []
        for item in (data.get("earningsCalendar", []) or []):
            earnings.append({
                "symbol": item.get("symbol", ""),
                "name": item.get("symbol", ""),
                "date": item.get("date", ""),
                "eps_estimate": item.get("epsEstimate"),
                "eps_actual": item.get("epsActual"),
                "revenue_estimate": item.get("revenueEstimate"),
                "revenue_actual": item.get("revenueActual"),
            })

        return earnings[:30]
    except Exception as e:
        logger.error("Failed to fetch earnings: %s", e)
        return _get_sample_earnings()


def _get_sample_events() -> list[dict]:
    """Return sample economic events when API is unavailable."""
    today = datetime.now()
    base = today.strftime("%Y-%m-%d")
    return [
        {"date": base, "time": "08:30", "event": "US Initial Jobless Claims", "country": "US", "impact": "medium", "forecast": 215, "previous": 213, "actual": None},
        {"date": base, "time": "10:00", "event": "US ISM Manufacturing PMI", "country": "US", "impact": "high", "forecast": 49.5, "previous": 49.2, "actual": None},
        {"date": base, "time": "14:00", "event": "FOMC Meeting Minutes", "country": "US", "impact": "high", "forecast": None, "previous": None, "actual": None},
        {"date": base, "time": "08:30", "event": "US CPI (MoM)", "country": "US", "impact": "high", "forecast": 0.3, "previous": 0.4, "actual": None},
        {"date": base, "time": "07:00", "event": "EU GDP (QoQ)", "country": "EU", "impact": "high", "forecast": 0.2, "previous": 0.3, "actual": None},
        {"date": base, "time": "09:30", "event": "UK Retail Sales", "country": "UK", "impact": "medium", "forecast": -0.3, "previous": 0.3, "actual": None},
    ]


def _get_sample_earnings() -> list[dict]:
    """Return sample earnings when API is unavailable."""
    today = datetime.now()
    base = today.strftime("%Y-%m-%d")
    return [
        {"symbol": "AAPL", "name": "Apple Inc.", "date": base, "eps_estimate": 2.35, "eps_actual": None, "revenue_estimate": 124e9, "revenue_actual": None},
        {"symbol": "MSFT", "name": "Microsoft Corp.", "date": base, "eps_estimate": 3.10, "eps_actual": None, "revenue_estimate": 68e9, "revenue_actual": None},
        {"symbol": "GOOGL", "name": "Alphabet Inc.", "date": base, "eps_estimate": 1.85, "eps_actual": None, "revenue_estimate": 86e9, "revenue_actual": None},
    ]
