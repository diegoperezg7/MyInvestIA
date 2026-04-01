"""Reddit service with OAuth when configured and public JSON fallback otherwise."""

import logging
import time

import httpx

from app.config import settings
from app.services.cache import get_or_fetch

logger = logging.getLogger(__name__)

REDDIT_TTL = 300  # 5 minutes

SUBREDDITS = ["wallstreetbets", "stocks", "investing"]

USER_AGENT = "InvestIA-Dashboard/1.0 (financial news aggregator)"
_oauth_cache: dict[str, float | str] = {"token": "", "expires_at": 0.0}


def _oauth_available() -> bool:
    return bool(settings.reddit_client_id and settings.reddit_client_secret)


async def _get_oauth_token() -> str | None:
    if not _oauth_available():
        return None
    now = time.time()
    token = str(_oauth_cache.get("token") or "")
    expires_at = float(_oauth_cache.get("expires_at") or 0.0)
    if token and now < expires_at - 60:
        return token

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://www.reddit.com/api/v1/access_token",
                data={"grant_type": "client_credentials"},
                auth=(settings.reddit_client_id, settings.reddit_client_secret),
                headers={"User-Agent": settings.reddit_user_agent or USER_AGENT},
            )
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        logger.debug("Reddit OAuth token unavailable: %s", exc)
        return None

    access_token = str(payload.get("access_token") or "")
    expires_in = float(payload.get("expires_in") or 3600)
    if not access_token:
        return None
    _oauth_cache["token"] = access_token
    _oauth_cache["expires_at"] = now + expires_in
    return access_token


async def _fetch_subreddit(subreddit: str, limit: int = 15) -> list[dict]:
    """Fetch hot posts from a subreddit via OAuth when available, otherwise public JSON."""
    try:
        token = await _get_oauth_token()
        async with httpx.AsyncClient(timeout=10.0) as client:
            if token:
                url = f"https://oauth.reddit.com/r/{subreddit}/hot"
                resp = await client.get(
                    url,
                    params={"limit": limit, "raw_json": 1},
                    headers={
                        "Authorization": f"Bearer {token}",
                        "User-Agent": settings.reddit_user_agent or USER_AGENT,
                    },
                    follow_redirects=True,
                )
            else:
                url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}&raw_json=1"
                resp = await client.get(
                    url,
                    headers={"User-Agent": settings.reddit_user_agent or USER_AGENT},
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
