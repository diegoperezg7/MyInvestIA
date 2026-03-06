"""Shared data provider layer for free-first, normalized provider access."""

from app.services.data_providers.crypto import (
    CRYPTO_ID_MAP,
    crypto_provider_chain,
)
from app.services.data_providers.filings import filings_provider_chain
from app.services.data_providers.fundamentals import fundamentals_provider_chain
from app.services.data_providers.market import (
    COMMODITY_FUTURES_MAP,
    market_provider_chain,
)
from app.services.data_providers.macro import macro_provider_chain
from app.services.data_providers.news import news_provider_aggregator

__all__ = [
    "COMMODITY_FUTURES_MAP",
    "CRYPTO_ID_MAP",
    "crypto_provider_chain",
    "filings_provider_chain",
    "fundamentals_provider_chain",
    "macro_provider_chain",
    "market_provider_chain",
    "news_provider_aggregator",
]
