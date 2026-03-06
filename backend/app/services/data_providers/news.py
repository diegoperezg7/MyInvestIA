"""News and social feed provider aggregation."""

from __future__ import annotations

import logging

from app.config import settings
from app.services.data_providers.base import NewsProvider
from app.services.data_providers.chain import AggregatingProviderChain, parse_provider_order
from app.services.data_providers.normalization import normalize_news_article
from app.services.gdelt_service import get_gdelt_news
from app.services.news_service import news_service
from app.services.newsapi_service import newsapi_service
from app.services.reddit_service import get_reddit_posts
from app.services.rss_service import get_rss_news
from app.services.stocktwits_service import get_trending as get_stocktwits_trending
from app.services.twitter_service import get_twitter_posts

logger = logging.getLogger(__name__)


class CallableNewsProvider(NewsProvider):
    def __init__(
        self,
        *,
        provider_id: str,
        display_name: str,
        retrieval_mode: str,
        note: str,
        default_category: str,
        is_core: bool,
        is_free: bool,
        configured_check,
        fetcher,
    ):
        self.provider_id = provider_id
        self.display_name = display_name
        self.retrieval_mode = retrieval_mode
        self.note = note
        self.default_category = default_category
        self.is_core = is_core
        self.is_free = is_free
        self._configured_check = configured_check
        self._fetcher = fetcher
        self.capabilities = ("news",)

    @property
    def is_configured(self) -> bool:
        return bool(self._configured_check())

    async def fetch(self, limit: int = 15) -> list[dict]:
        raw_items = await self._fetcher(limit)
        normalized = []
        for item in raw_items:
            article = normalize_news_article(
                item,
                provider_id=self.provider_id,
                retrieval_mode=self.retrieval_mode,
                default_category=self.default_category,
            )
            if article:
                normalized.append(article)
        return normalized


def _build_news_providers() -> list[NewsProvider]:
    return [
        CallableNewsProvider(
            provider_id="finnhub",
            display_name="Finnhub",
            retrieval_mode="developer_api",
            note="Optional market news feed",
            default_category="news",
            is_core=False,
            is_free=True,
            configured_check=lambda: news_service.is_configured,
            fetcher=lambda limit: news_service.get_market_news(limit=limit),
        ),
        CallableNewsProvider(
            provider_id="gdelt",
            display_name="GDELT",
            retrieval_mode="public_api",
            note="Free broad news coverage",
            default_category="news",
            is_core=True,
            is_free=True,
            configured_check=lambda: True,
            fetcher=lambda limit: get_gdelt_news(limit=limit),
        ),
        CallableNewsProvider(
            provider_id="rss",
            display_name="RSS",
            retrieval_mode="rss",
            note="Free curated RSS feed bundle",
            default_category="news",
            is_core=True,
            is_free=True,
            configured_check=lambda: True,
            fetcher=lambda limit: get_rss_news(limit=limit),
        ),
        CallableNewsProvider(
            provider_id="newsapi",
            display_name="NewsAPI",
            retrieval_mode="developer_api",
            note="Optional fallback with free daily quota",
            default_category="news",
            is_core=False,
            is_free=True,
            configured_check=lambda: settings.news_mixed_mode and newsapi_service.is_configured,
            fetcher=lambda limit: newsapi_service.get_business_news(limit=limit),
        ),
        CallableNewsProvider(
            provider_id="reddit",
            display_name="Reddit",
            retrieval_mode="oauth" if settings.reddit_client_id and settings.reddit_client_secret else "public_api",
            note="Free social/news signal feed",
            default_category="social",
            is_core=True,
            is_free=True,
            configured_check=lambda: settings.news_mixed_mode or bool(settings.reddit_client_id and settings.reddit_client_secret),
            fetcher=lambda limit: get_reddit_posts(limit=limit),
        ),
        CallableNewsProvider(
            provider_id="stocktwits",
            display_name="StockTwits",
            retrieval_mode="public_api",
            note="Optional social sentiment feed",
            default_category="social",
            is_core=False,
            is_free=True,
            configured_check=lambda: settings.news_mixed_mode,
            fetcher=lambda limit: get_stocktwits_trending(limit=limit),
        ),
        CallableNewsProvider(
            provider_id="twitter",
            display_name="Twitter/X",
            retrieval_mode="social_fallback",
            note="Optional social fallback feed",
            default_category="social",
            is_core=False,
            is_free=True,
            configured_check=lambda: settings.news_mixed_mode,
            fetcher=lambda limit: get_twitter_posts(limit=limit),
        ),
    ]


class NewsProviderAggregator(AggregatingProviderChain):
    def __init__(self):
        super().__init__(
            "news",
            _build_news_providers(),
            parse_provider_order(settings.news_provider_order),
        )

    async def fetch(self, limit: int = 15) -> list[dict]:
        items: list[dict] = []
        for _provider_id, result in await self.gather("fetch", limit):
            if isinstance(result, list):
                items.extend(result)
        items.sort(key=lambda article: article.get("datetime", 0), reverse=True)
        return items

    def source_status(self) -> dict[str, bool]:
        return {
            provider["id"]: bool(provider["enabled"])
            for provider in self.providers
        }


news_provider_aggregator = NewsProviderAggregator()
