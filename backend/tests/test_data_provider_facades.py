from unittest.mock import AsyncMock, patch

import pytest

from app.services.market_data import market_data_service
from app.services.macro_intelligence import (
    get_all_macro_indicators,
    get_macro_indicator,
)
from app.services.news_aggregator import get_aggregated_news
from app.services.provider_chain import provider_chain
from app.services.sec_service import get_company_filings


@pytest.mark.asyncio
async def test_provider_chain_keeps_legacy_provider_alias():
    with patch(
        "app.services.provider_chain.market_provider_chain.get_quote",
        new_callable=AsyncMock,
        return_value={
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "price": 195.0,
            "source": "Yahoo Finance",
            "source_provider": "yfinance",
        },
    ):
        result = await provider_chain.get_quote("AAPL")

    assert result is not None
    assert result["provider"] == "Yahoo Finance"
    assert result["source_provider"] == "yfinance"


@pytest.mark.asyncio
async def test_market_data_service_routes_crypto_history_through_crypto_chain():
    with patch(
        "app.services.market_data.crypto_provider_chain.get_market_chart",
        new_callable=AsyncMock,
        return_value=[
            {
                "date": "2026-01-01T00:00:00+00:00",
                "price": 43000.0,
                "volume": 123.0,
                "market_cap": 999.0,
                "source_provider": "coingecko",
                "retrieval_mode": "public_api",
            }
        ],
    ) as mock_chart:
        result = await market_data_service.get_crypto_history("BTC", days=30)

    mock_chart.assert_awaited_once_with("BTC", days=30)
    assert result[0]["price"] == 43000.0
    assert result[0]["source_provider"] == "coingecko"


@pytest.mark.asyncio
async def test_macro_intelligence_delegates_to_provider_chain():
    indicators = [
        {"ticker": "^VIX", "name": "VIX (Volatility Index)", "value": 18.5},
        {"ticker": "DX-Y.NYB", "name": "US Dollar Index (DXY)", "value": 104.2},
    ]
    with patch(
        "app.services.macro_intelligence.macro_provider_chain.get_indicators",
        new_callable=AsyncMock,
        return_value=indicators,
    ):
        all_items = await get_all_macro_indicators()
        vix = await get_macro_indicator("^VIX")

    assert all_items == indicators
    assert vix == indicators[0]


@pytest.mark.asyncio
async def test_sec_service_uses_filings_provider_chain():
    payload = {
        "symbol": "MSFT",
        "company_name": "Microsoft Corp.",
        "cik": "0000789019",
        "source": "SEC EDGAR",
        "source_provider": "sec",
        "retrieval_mode": "official_api",
        "filings": [],
        "generated_at": "2026-03-06T00:00:00+00:00",
    }
    with patch(
        "app.services.sec_service.filings_provider_chain.get_filings",
        new_callable=AsyncMock,
        return_value=payload,
    ):
        result = await get_company_filings("MSFT")

    assert result == payload


@pytest.mark.asyncio
async def test_news_aggregator_reads_from_provider_aggregator():
    async def passthrough(_key, fetch_fn, _ttl):
        return await fetch_fn()

    with patch(
        "app.services.news_aggregator.get_or_fetch",
        new_callable=AsyncMock,
    ) as mock_cache, patch(
        "app.services.news_aggregator.news_provider_aggregator.fetch",
        new_callable=AsyncMock,
        return_value=[
            {
                "headline": "Markets rally on softer inflation print",
                "summary": "Stocks move higher.",
                "source": "Reuters",
                "source_provider": "rss",
                "source_category": "news",
                "url": "https://example.com/article",
                "datetime": 1700000000,
                "retrieval_mode": "rss",
            }
        ],
    ):
        mock_cache.side_effect = passthrough
        articles = await get_aggregated_news(limit=10)

    assert len(articles) == 1
    assert articles[0]["source_provider"] == "rss"
    assert "id" in articles[0]
