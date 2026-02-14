"""Reddit service — fetch top posts from finance subreddits via public JSON API.

Fetches from r/wallstreetbets, r/stocks, r/investing.
No API key needed; uses descriptive User-Agent to avoid 429.
Filters out stickied posts and posts with score < 10.
"""

import logging
import time

import httpx

from app.services.cache import get_or_fetch

logger = logging.getLogger(__name__)

REDDIT_TTL = 300  # 5 minutes

SUBREDDITS = ["wallstreetbets", "stocks", "investing"]

USER_AGENT = "InvestIA-Dashboard/1.0 (financial news aggregator)"


async def _fetch_subreddit(subreddit: str, limit: int = 15) -> list[dict]:
    """Fetch hot posts from a subreddit via public JSON API."""
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}&raw_json=1"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                url,
                headers={"User-Agent": USER_AGENT},
                follow_redirects=True,
            )
            resp.raise_for_status()
            data = resp.json()

        posts = []
        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            # Skip stickied and low-score posts
            if post.get("stickied"):
                continue
            if (post.get("score") or 0) < 10:
                continue

            title = post.get("title", "").strip()
            if not title:
                continue

            selftext = (post.get("selftext") or "")[:500]
            permalink = post.get("permalink", "")
            post_url = f"https://www.reddit.com{permalink}" if permalink else ""

            posts.append({
                "headline": title,
                "summary": selftext,
                "source": f"r/{subreddit}",
                "url": post_url,
                "datetime": int(post.get("created_utc", time.time())),
                "source_category": "social",
                "author": post.get("author", ""),
                "score": post.get("score", 0),
                "num_comments": post.get("num_comments", 0),
            })
        return posts
    except Exception as e:
        logger.debug("Reddit r/%s unavailable: %s", subreddit, e)
        return []


async def get_reddit_posts(limit: int = 20) -> list[dict]:
    """Aggregate hot posts from all finance subreddits."""

    async def _fetch():
        import asyncio

        tasks = [_fetch_subreddit(sub) for sub in SUBREDDITS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_posts: list[dict] = []
        for result in results:
            if isinstance(result, list):
                all_posts.extend(result)

        # Sort by score descending
        all_posts.sort(key=lambda p: p.get("score", 0), reverse=True)
        return all_posts[:limit]

    return await get_or_fetch("reddit:all", _fetch, REDDIT_TTL) or []
