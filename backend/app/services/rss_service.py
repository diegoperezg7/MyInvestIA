"""RSS feed aggregator for financial news.

Fetches from free RSS feeds: Reuters Business, CNBC, MarketWatch, Investing.com.
Uses stdlib xml.etree.ElementTree for parsing.
"""

import hashlib
import logging
import time
import xml.etree.ElementTree as ET

import httpx

from app.services.cache import get_or_fetch

logger = logging.getLogger(__name__)

RSS_TTL = 300  # 5 minutes

RSS_FEEDS = [
    {
        "name": "Reuters Business",
        "url": "https://feeds.reuters.com/reuters/businessNews",
        "source": "Reuters",
    },
    {
        "name": "CNBC Top News",
        "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
        "source": "CNBC",
    },
    {
        "name": "MarketWatch",
        "url": "https://feeds.marketwatch.com/marketwatch/topstories/",
        "source": "MarketWatch",
    },
    {
        "name": "Investing.com",
        "url": "https://www.investing.com/rss/news.rss",
        "source": "Investing.com",
    },
]


def _parse_rss(xml_text: str, source: str) -> list[dict]:
    """Parse RSS XML into article dicts."""
    articles = []
    try:
        root = ET.fromstring(xml_text)
        for item in root.iter("item"):
            title_el = item.find("title")
            desc_el = item.find("description")
            link_el = item.find("link")
            pub_el = item.find("pubDate")

            headline = title_el.text.strip() if title_el is not None and title_el.text else ""
            if not headline:
                continue

            summary = desc_el.text.strip() if desc_el is not None and desc_el.text else ""
            # Strip HTML tags from summary
            if "<" in summary:
                import re
                summary = re.sub(r"<[^>]+>", "", summary).strip()
            summary = summary[:500]

            url = link_el.text.strip() if link_el is not None and link_el.text else ""

            # Parse pubDate to unix timestamp
            dt = 0
            if pub_el is not None and pub_el.text:
                try:
                    from email.utils import parsedate_to_datetime
                    dt = int(parsedate_to_datetime(pub_el.text.strip()).timestamp())
                except Exception:
                    dt = int(time.time())

            articles.append({
                "headline": headline,
                "summary": summary,
                "source": source,
                "url": url,
                "datetime": dt,
            })
    except ET.ParseError as e:
        logger.warning("RSS parse error for %s: %s", source, e)
    return articles


async def _fetch_single_feed(feed: dict) -> list[dict]:
    """Fetch and parse a single RSS feed."""
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                feed["url"],
                headers={"User-Agent": "InvestIA/1.0"},
                follow_redirects=True,
            )
            resp.raise_for_status()
            return _parse_rss(resp.text, feed["source"])
    except Exception as e:
        logger.debug("RSS feed %s unavailable: %s", feed["name"], e)
        return []


async def get_rss_news(limit: int = 20) -> list[dict]:
    """Aggregate news from all RSS feeds, deduplicated by headline."""

    async def _fetch():
        import asyncio

        tasks = [_fetch_single_feed(feed) for feed in RSS_FEEDS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        seen: set[str] = set()
        all_articles: list[dict] = []
        for result in results:
            if isinstance(result, list):
                for article in result:
                    # Deduplicate by headline hash
                    key = hashlib.md5(article["headline"].lower().encode()).hexdigest()
                    if key not in seen:
                        seen.add(key)
                        all_articles.append(article)

        # Sort by datetime descending
        all_articles.sort(key=lambda a: a.get("datetime", 0), reverse=True)
        return all_articles[:limit]

    return await get_or_fetch("rss:all", _fetch, RSS_TTL) or []
