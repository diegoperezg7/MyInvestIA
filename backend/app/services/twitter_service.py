"""Twitter/X service — attempts to fetch via Nitter RSS instances.

Falls back gracefully to empty list if no Nitter instance is available.
This is a best-effort service; Nitter instances are frequently down.
"""

import logging
import time
import xml.etree.ElementTree as ET

import httpx

from app.services.cache import get_or_fetch

logger = logging.getLogger(__name__)

TWITTER_TTL = 300  # 5 minutes

# Nitter instances to try in order (frequently go up/down)
NITTER_INSTANCES = [
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
    "https://nitter.1d4.us",
]

# Finance-related Twitter accounts to follow
FINANCE_ACCOUNTS = [
    "markets",        # Bloomberg Markets
    "DeItaone",       # Walter Bloomberg (breaking news)
    "unusual_whales", # Unusual Whales
    "zaborsky_paul",  # Paul Zaborsky
]

USER_AGENT = "InvestIA-Dashboard/1.0 (financial news aggregator)"


def _parse_nitter_rss(xml_text: str, account: str) -> list[dict]:
    """Parse Nitter RSS XML into article dicts."""
    posts = []
    try:
        root = ET.fromstring(xml_text)
        for item in root.iter("item"):
            title_el = item.find("title")
            desc_el = item.find("description")
            link_el = item.find("link")
            pub_el = item.find("pubDate")

            text = title_el.text.strip() if title_el is not None and title_el.text else ""
            if not text:
                continue

            full_text = desc_el.text.strip() if desc_el is not None and desc_el.text else ""
            # Strip HTML
            if "<" in full_text:
                import re
                full_text = re.sub(r"<[^>]+>", "", full_text).strip()
            full_text = full_text[:500]

            url = link_el.text.strip() if link_el is not None and link_el.text else ""
            # Convert nitter URL to twitter URL
            for instance in NITTER_INSTANCES:
                if url.startswith(instance):
                    url = url.replace(instance, "https://x.com")
                    break

            dt = int(time.time())
            if pub_el is not None and pub_el.text:
                try:
                    from email.utils import parsedate_to_datetime
                    dt = int(parsedate_to_datetime(pub_el.text.strip()).timestamp())
                except Exception:
                    pass

            posts.append({
                "headline": text[:200],
                "summary": full_text if full_text != text else "",
                "source": f"X/@{account}",
                "url": url,
                "datetime": dt,
                "source_category": "social",
                "author": account,
            })
    except ET.ParseError as e:
        logger.debug("Nitter RSS parse error for @%s: %s", account, e)
    return posts


async def _fetch_account_nitter(account: str) -> list[dict]:
    """Try to fetch an account's RSS feed from available Nitter instances."""
    for instance in NITTER_INSTANCES:
        try:
            url = f"{instance}/{account}/rss"
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.get(
                    url,
                    headers={"User-Agent": USER_AGENT},
                    follow_redirects=True,
                )
                resp.raise_for_status()
                posts = _parse_nitter_rss(resp.text, account)
                if posts:
                    return posts
        except Exception:
            continue
    return []


async def get_twitter_posts(limit: int = 15) -> list[dict]:
    """Fetch tweets from finance accounts via Nitter. Degrades gracefully."""

    async def _fetch():
        import asyncio

        tasks = [_fetch_account_nitter(account) for account in FINANCE_ACCOUNTS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_posts: list[dict] = []
        for result in results:
            if isinstance(result, list):
                all_posts.extend(result)

        # Sort by datetime descending
        all_posts.sort(key=lambda p: p.get("datetime", 0), reverse=True)
        return all_posts[:limit]

    return await get_or_fetch("twitter:all", _fetch, TWITTER_TTL) or []
