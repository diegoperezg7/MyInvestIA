"""Bloomberg market data provider.

Requires Bloomberg Terminal license and blpapi package.
pip install blpapi

Configuration:
- BLOOMBERG_HOST: Bloomberg server host (default: localhost)
- BLOOMBERG_PORT: Bloomberg server port (default: 8194)
"""

import logging
from datetime import datetime

from app.config import settings
from app.services.providers.base import MarketDataProvider

logger = logging.getLogger(__name__)

try:
    import blpapi

    BLOOMBERG_AVAILABLE = True
except ImportError:
    BLOOMBERG_AVAILABLE = False
    logger.warning("blpapi not installed. Bloomberg provider unavailable.")


class BloombergProvider(MarketDataProvider):
    """Bloomberg Terminal API provider for real-time and historical data."""

    def __init__(self, host: str = None, port: int = None):
        self._host = host or getattr(settings, "bloomberg_host", "localhost")
        self._port = port or getattr(settings, "bloomberg_port", 8194)
        self._session = None
        self._is_configured = False

        if BLOOMBERG_AVAILABLE and (settings.bloomberg_host or settings.bloomberg_port):
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

            request = self._session.getService(service).createRequest(
                "HistoricalDataRequest"
            )
            request.append("securities", symbol)
            request.append("fields", "PX_LAST")
            request.append("fields", "PX_OPEN")
            request.append("fields", "PX_HIGH")
            request.append("fields", "PX_LOW")
            request.append("fields", "PX_VOLUME")
            request.append("fields", "CHANGE_PCT")
            request.append("fields", "CLOSE")
            request.set("startDate", "20240101")
            request.set("endDate", "20241231")
            request.set("maxDataPoints", 1)

            self._session.sendRequest(request)

            for event in self._session.nextEvent():
                if event.eventType() == blpapi.Event.RESPONSE:
                    for msg in event:
                        if msg.hasElement("securityData"):
                            sec_data = msg.getElement("securityData")
                            if sec_data.numValues() > 0:
                                field_data = sec_data.getValueAsElement(0)
                                if field_data.hasElement("fieldData"):
                                    fd = field_data.getElement("fieldData")

                                    price = (
                                        fd.getElementAsFloat("PX_LAST")
                                        if fd.hasElement("PX_LAST")
                                        else 0
                                    )
                                    change_pct = (
                                        fd.getElementAsFloat("CHANGE_PCT")
                                        if fd.hasElement("CHANGE_PCT")
                                        else 0
                                    )
                                    volume = (
                                        fd.getElementAsInt("PX_VOLUME")
                                        if fd.hasElement("PX_VOLUME")
                                        else 0
                                    )

                                    return {
                                        "symbol": symbol,
                                        "name": symbol,
                                        "price": round(price, 2),
                                        "change_percent": round(change_pct, 2),
                                        "volume": volume,
                                        "previous_close": fd.getElementAsFloat("CLOSE")
                                        if fd.hasElement("CLOSE")
                                        else price,
                                    }
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
            "1d": ("-1D", "1D"),
            "5d": ("-5D", "1D"),
            "1mo": ("-1M", "1D"),
            "3mo": ("-3M", "1D"),
            "6mo": ("-6M", "1D"),
            "1y": ("-1Y", "1W"),
            "2y": ("-2Y", "1W"),
            "5y": ("-5Y", "1M"),
            "10y": ("-10Y", "1M"),
            "max": ("-50Y", "1M"),
        }

        period_str, interval_str = period_map.get(period, ("-1M", "1D"))

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
            request.set("startDate", period_str)
            request.set("endDate", "0D")
            request.set("periodicityAdjustment", "CALENDAR")
            request.set("periodicitySelection", interval_str)
            request.set("maxDataPoints", 500)

            self._session.sendRequest(request)

            results = []
            for event in self._session.nextEvent():
                if event.eventType() == blpapi.Event.RESPONSE:
                    for msg in event:
                        if msg.hasElement("securityData"):
                            sec_data = msg.getElement("securityData")
                            for i in range(sec_data.numValues()):
                                row = sec_data.getValueAsElement(i)
                                if row.hasElement("fieldData"):
                                    fd = row.getElement("fieldData")
                                    date = (
                                        fd.getElementAsDatetime("date")
                                        if fd.hasElement("date")
                                        else None
                                    )

                                    results.append(
                                        {
                                            "date": date.strftime("%Y-%m-%d")
                                            if date
                                            else "",
                                            "open": fd.getElementAsFloat("PX_OPEN")
                                            if fd.hasElement("PX_OPEN")
                                            else 0,
                                            "high": fd.getElementAsFloat("PX_HIGH")
                                            if fd.hasElement("PX_HIGH")
                                            else 0,
                                            "low": fd.getElementAsFloat("PX_LOW")
                                            if fd.hasElement("PX_LOW")
                                            else 0,
                                            "close": fd.getElementAsFloat("PX_LAST")
                                            if fd.hasElement("PX_LAST")
                                            else 0,
                                            "volume": fd.getElementAsInt("PX_VOLUME")
                                            if fd.hasElement("PX_VOLUME")
                                            else 0,
                                        }
                                    )
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
