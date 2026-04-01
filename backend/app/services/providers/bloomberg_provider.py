"""Bloomberg market data provider.

Requires Bloomberg Terminal license and blpapi package.
Install separately in licensed environments:
pip install blpapi

Configuration:
- BLOOMBERG_ENABLED: enable the provider explicitly
- BLOOMBERG_HOST: Bloomberg server host (default: localhost)
- BLOOMBERG_PORT: Bloomberg server port (default: 8194)
"""

import logging
from datetime import datetime, timedelta

from app.config import settings
from app.services.providers.base import MarketDataProvider

logger = logging.getLogger(__name__)

try:
    import blpapi

    BLOOMBERG_AVAILABLE = True
except ImportError:
    BLOOMBERG_AVAILABLE = False
    if getattr(settings, "bloomberg_enabled", False):
        logger.warning("blpapi not installed. Bloomberg provider unavailable.")


class BloombergProvider(MarketDataProvider):
    """Bloomberg Terminal API provider for real-time and historical data."""

    def __init__(self, host: str | None = None, port: int | None = None):
        self._host = host or getattr(settings, "bloomberg_host", "") or "localhost"
        self._port = port or getattr(settings, "bloomberg_port", 8194)
        self._session = None
        self._is_configured = False

        if (
            getattr(settings, "bloomberg_enabled", False)
            and BLOOMBERG_AVAILABLE
            and self._host
            and self._port
        ):
            self._is_configured = True

    @property
    def name(self) -> str:
        return "Bloomberg"

    @property
    def is_configured(self) -> bool:
        return self._is_configured and BLOOMBERG_AVAILABLE

    def _start_session(self):
        """Start Bloomberg session if not already running."""
        if self._session is None and self.is_configured:
            try:
                session_options = blpapi.SessionOptions()
                session_options.setServerHost(self._host)
                session_options.setServerPort(self._port)
                self._session = blpapi.Session(session_options)
                self._session.start()
                logger.info(
                    "Bloomberg session started at %s:%s", self._host, self._port
                )
            except Exception as e:
                logger.error("Failed to start Bloomberg session: %s", e)
                self._session = None

    async def get_quote(self, symbol: str) -> dict | None:
        """Get current quote from Bloomberg."""
        if not self.is_configured:
            return None

        self._start_session()
        if self._session is None:
            return None

        try:
            service = "//blp/refdata"
            if not self._session.openService(service):
                logger.warning("Failed to open Bloomberg refdata service")
                return None

            request = self._session.getService(service).createRequest("ReferenceDataRequest")
            request.append("securities", symbol)
            request.append("fields", "PX_LAST")
            request.append("fields", "PX_OPEN")
            request.append("fields", "PX_HIGH")
            request.append("fields", "PX_LOW")
            request.append("fields", "PX_VOLUME")
            request.append("fields", "CHG_PCT_1D")
            request.append("fields", "PREV_CLOSE_VALUE")

            self._session.sendRequest(request)

            while True:
                event = self._session.nextEvent(500)
                for msg in event:
                    if not msg.hasElement("securityData"):
                        continue
                    sec_data = msg.getElement("securityData")
                    if not sec_data.hasElement("fieldData"):
                        continue
                    fd = sec_data.getElement("fieldData")
                    price = fd.getElementAsFloat("PX_LAST") if fd.hasElement("PX_LAST") else 0
                    change_pct = (
                        fd.getElementAsFloat("CHG_PCT_1D")
                        if fd.hasElement("CHG_PCT_1D")
                        else 0
                    )
                    volume = fd.getElementAsInteger("PX_VOLUME") if fd.hasElement("PX_VOLUME") else 0
                    previous_close = (
                        fd.getElementAsFloat("PREV_CLOSE_VALUE")
                        if fd.hasElement("PREV_CLOSE_VALUE")
                        else price
                    )
                    if price:
                        return {
                            "symbol": symbol,
                            "name": symbol,
                            "price": round(price, 2),
                            "change_percent": round(change_pct, 2),
                            "volume": int(volume),
                            "previous_close": round(previous_close, 2),
                        }
                if event.eventType() == blpapi.Event.RESPONSE:
                    break
            return None
        except Exception as e:
            logger.warning("Bloomberg quote failed for %s: %s", symbol, e)
            return None

    async def get_history(
        self, symbol: str, period: str = "1mo", interval: str = "1d"
    ) -> list[dict]:
        """Get historical OHLCV data from Bloomberg."""
        if not self.is_configured:
            return []

        period_map = {
            "1d": (timedelta(days=1), "DAILY"),
            "5d": (timedelta(days=5), "DAILY"),
            "1mo": (timedelta(days=30), "DAILY"),
            "3mo": (timedelta(days=90), "DAILY"),
            "6mo": (timedelta(days=180), "DAILY"),
            "1y": (timedelta(days=365), "WEEKLY"),
            "2y": (timedelta(days=730), "WEEKLY"),
            "5y": (timedelta(days=1825), "MONTHLY"),
            "10y": (timedelta(days=3650), "MONTHLY"),
            "max": (timedelta(days=3650 * 5), "MONTHLY"),
        }

        lookback, periodicity = period_map.get(period, (timedelta(days=30), "DAILY"))
        end_date = datetime.utcnow().strftime("%Y%m%d")
        start_date = (datetime.utcnow() - lookback).strftime("%Y%m%d")

        self._start_session()
        if self._session is None:
            return []

        try:
            service = "//blp/refdata"
            if not self._session.openService(service):
                return []

            request = self._session.getService(service).createRequest(
                "HistoricalDataRequest"
            )
            request.append("securities", symbol)
            request.append("fields", "PX_OPEN")
            request.append("fields", "PX_HIGH")
            request.append("fields", "PX_LOW")
            request.append("fields", "PX_LAST")
            request.append("fields", "PX_VOLUME")
            request.set("startDate", start_date)
            request.set("endDate", end_date)
            request.set("periodicityAdjustment", "CALENDAR")
            request.set("periodicitySelection", periodicity)
            request.set("maxDataPoints", 500)

            self._session.sendRequest(request)

            results = []
            while True:
                event = self._session.nextEvent(500)
                for msg in event:
                    if not msg.hasElement("securityData"):
                        continue
                    sec_data = msg.getElement("securityData")
                    if not sec_data.hasElement("fieldData"):
                        continue
                    field_data = sec_data.getElement("fieldData")
                    for i in range(field_data.numValues()):
                        fd = field_data.getValueAsElement(i)
                        date = fd.getElementAsDatetime("date") if fd.hasElement("date") else None
                        results.append(
                            {
                                "date": date.strftime("%Y-%m-%d") if date else "",
                                "open": fd.getElementAsFloat("PX_OPEN") if fd.hasElement("PX_OPEN") else 0,
                                "high": fd.getElementAsFloat("PX_HIGH") if fd.hasElement("PX_HIGH") else 0,
                                "low": fd.getElementAsFloat("PX_LOW") if fd.hasElement("PX_LOW") else 0,
                                "close": fd.getElementAsFloat("PX_LAST") if fd.hasElement("PX_LAST") else 0,
                                "volume": int(fd.getElementAsInteger("PX_VOLUME")) if fd.hasElement("PX_VOLUME") else 0,
                            }
                        )
                if event.eventType() == blpapi.Event.RESPONSE:
                    break
            return results
        except Exception as e:
            logger.warning("Bloomberg history failed for %s: %s", symbol, e)
            return []

    async def close(self) -> None:
        """Close Bloomberg session."""
        if self._session:
            try:
                self._session.stop()
            except Exception:
                pass
            self._session = None
