"""Common normalization, entity resolution, deduplication, and scoring for news/social items."""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.config import settings

SOURCE_RELIABILITY: dict[str, float] = {
    "finnhub": 0.88,
    "gdelt": 0.78,
    "newsapi": 0.62,
    "rss": 0.72,
    "reddit": 0.46,
    "stocktwits": 0.38,
    "twitter": 0.30,
}

SOURCE_RELIABILITY_OVERRIDES: dict[str, float] = {
    "Reuters": 0.95,
    "CNBC": 0.84,
    "Yahoo Finance": 0.78,
    "MarketWatch": 0.76,
    "Investing.com": 0.70,
    "Seeking Alpha": 0.64,
    "Motley Fool": 0.58,
    "StockTwits": 0.38,
}

POSITIVE_TERMS = {
    "beat",
    "beats",
    "bullish",
    "buyback",
    "breakout",
    "expands",
    "growth",
    "launch",
    "outperform",
    "partnership",
    "record",
    "rally",
    "rebound",
    "surge",
    "upgrade",
    "wins",
}

NEGATIVE_TERMS = {
    "bankruptcy",
    "bearish",
    "cut",
    "cuts",
    "decline",
    "default",
    "downgrade",
    "fraud",
    "investigation",
    "layoff",
    "lawsuit",
    "miss",
    "probe",
    "recall",
    "selloff",
    "slump",
    "warning",
}

RAW_TICKER_BLACKLIST = {
    "A",
    "AI",
    "ALL",
    "CPI",
    "CEO",
    "ETF",
    "ETFs",
    "FED",
    "FOMC",
    "GDP",
    "IPO",
    "SEC",
    "USA",
    "USD",
}

ENTITY_ALIASES: dict[str, set[str]] = {
    "AAPL": {"apple", "iphone", "cupertino"},
    "MSFT": {"microsoft", "windows", "azure"},
    "GOOGL": {"alphabet", "google", "youtube"},
    "AMZN": {"amazon", "aws", "prime day"},
    "NVDA": {"nvidia", "geforce", "cuda"},
    "META": {"meta", "facebook", "instagram", "whatsapp"},
    "TSLA": {"tesla", "elon musk", "model y"},
    "AMD": {"amd", "advanced micro devices", "ryzen"},
    "INTC": {"intel"},
    "PLTR": {"palantir"},
    "CRM": {"salesforce"},
    "NFLX": {"netflix"},
    "DIS": {"disney"},
    "JPM": {"jpmorgan", "jp morgan"},
    "BAC": {"bank of america"},
    "GS": {"goldman sachs"},
    "LLY": {"eli lilly"},
    "NVO": {"novo nordisk"},
    "UNH": {"unitedhealth"},
    "XOM": {"exxon", "exxon mobil"},
    "CVX": {"chevron"},
    "SPY": {"s&p 500", "spdr s&p 500", "spy etf", "sp500"},
    "QQQ": {"nasdaq 100", "invesco qqq"},
    "IWM": {"russell 2000"},
    "GLD": {"gold etf", "spdr gold"},
    "TLT": {"20 year treasury", "long bond etf"},
    "BTC": {"bitcoin", "btc"},
    "ETH": {"ethereum", "ether", "eth"},
    "SOL": {"solana", "sol"},
    "XRP": {"ripple", "xrp"},
    "DOGE": {"dogecoin", "doge"},
    "GOLD": {"spot gold", "gold futures"},
    "OIL": {"wti", "crude oil", "oil futures"},
}

THEME_KEYWORDS: dict[str, set[str]] = {
    "AI / semiconductors": {"ai", "chip", "chips", "gpu", "semiconductor", "data center"},
    "Earnings / guidance": {"earnings", "eps", "guidance", "quarter", "revenue", "forecast"},
    "Fed / rates": {"fed", "fomc", "rates", "yields", "powell", "inflation", "cpi"},
    "Macro slowdown": {"recession", "slowdown", "labor", "unemployment", "gdp"},
    "M&A / capital markets": {"merger", "acquisition", "deal", "stake", "ipo", "buyback"},
    "Crypto flows": {"bitcoin", "ethereum", "crypto", "etf", "solana", "on-chain"},
    "Energy / commodities": {"oil", "gold", "copper", "gas", "opec"},
}

RETRIEVAL_MODE_BY_PROVIDER = {
    "finnhub": "official_api",
    "gdelt": "public_api",
    "newsapi": "developer_api",
    "rss": "rss",
    "reddit": "oauth" if settings.reddit_client_id and settings.reddit_client_secret else "public_api",
    "stocktwits": "public_api",
    "twitter": "social_fallback",
}

_TICKER_PATTERN = re.compile(r"(?<![A-Z0-9])\$?([A-Z][A-Z0-9.\-]{0,9})(?![A-Za-z])")
_STRIP_TERMS = (
    "breaking:",
    "update:",
    "exclusive:",
    "live:",
)


def _clamp(value: float, floor: float, ceil: float) -> float:
    return max(floor, min(ceil, value))


def canonicalize_url(url: str) -> str:
    if not url:
        return ""
    parts = urlsplit(url)
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_")
        and key.lower() not in {"guccounter", "guce_referrer", "guce_referrer_sig", "mod", "cmpid"}
    ]
    netloc = parts.netloc.lower().removeprefix("www.")
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), netloc, path, urlencode(query), ""))


def _headline_key(headline: str) -> str:
    normalized = headline.lower().strip()
    for prefix in _STRIP_TERMS:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):].strip()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def _keyword_sentiment(text: str) -> float:
    lowered = text.lower()
    positive = sum(1 for term in POSITIVE_TERMS if term in lowered)
    negative = sum(1 for term in NEGATIVE_TERMS if term in lowered)
    total = positive + negative
    if total == 0:
        return 0.0
    return _clamp((positive - negative) / total * 0.6, -0.6, 0.6)


def _score_from_ai(article: dict) -> float:
    ai_analysis = article.get("ai_analysis") or {}
    sentiment = ai_analysis.get("sentiment")
    if sentiment == "positive":
        return 0.6
    if sentiment == "negative":
        return -0.6
    return 0.0


def _score_from_social_label(article: dict) -> float:
    label = str(article.get("sentiment_label") or "").lower()
    if label == "bullish":
        return 0.4
    if label == "bearish":
        return -0.4
    return 0.0


def get_source_reliability(article: dict) -> float:
    source_name = str(article.get("source") or "")
    if source_name in SOURCE_RELIABILITY_OVERRIDES:
        return SOURCE_RELIABILITY_OVERRIDES[source_name]
    provider = str(article.get("source_provider") or "")
    return SOURCE_RELIABILITY.get(provider, 0.55)


def get_retrieval_mode(article: dict) -> str:
    provider = str(article.get("source_provider") or "")
    return RETRIEVAL_MODE_BY_PROVIDER.get(provider, "unknown")


def resolve_ticker_mentions(article: dict) -> list[str]:
    mentions: set[str] = set()

    related = str(article.get("related") or "")
    if related:
        for token in re.split(r"[,\s]+", related.upper()):
            if token and token not in RAW_TICKER_BLACKLIST:
                mentions.add(token)

    for symbol in article.get("mentioned_symbols", []) or []:
        symbol_str = str(symbol).upper().strip()
        if symbol_str and symbol_str not in RAW_TICKER_BLACKLIST:
            mentions.add(symbol_str)

    body = " ".join(
        filter(
            None,
            [
                str(article.get("headline") or ""),
                str(article.get("summary") or ""),
            ],
        )
    )
    lowered = body.lower()

    for symbol, aliases in ENTITY_ALIASES.items():
        if any(alias in lowered for alias in aliases):
            mentions.add(symbol)

    for match in _TICKER_PATTERN.finditer(body):
        token = match.group(1).upper()
        if token in RAW_TICKER_BLACKLIST:
            continue
        if token in ENTITY_ALIASES or "$" in match.group(0):
            mentions.add(token)

    return sorted(mentions)[:10]


def compute_engagement(article: dict) -> float:
    provider = str(article.get("source_provider") or "")
    if provider == "reddit":
        upvotes = max(0, int(article.get("score") or 0))
        comments = max(0, int(article.get("num_comments") or 0))
        return _clamp((upvotes * 0.65 + comments * 0.35) / 500.0, 0.0, 1.0)
    if provider == "stocktwits":
        return 0.28 + (0.10 if article.get("sentiment_label") else 0.0)
    if provider == "twitter":
        return 0.22
    if article.get("source_category") == "blog":
        return 0.14
    return 0.08


def score_article(article: dict, *, now_ts: int | None = None) -> dict:
    working = dict(article)
    now_ts = now_ts or int(datetime.now(timezone.utc).timestamp())
    timestamp = int(working.get("datetime") or 0)
    age_hours = max(0.0, (now_ts - timestamp) / 3600) if timestamp else 72.0
    recency_weight = math.exp(-age_hours / 18.0)
    reliability = get_source_reliability(working)
    ticker_mentions = resolve_ticker_mentions(working)
    relevance = 0.20 + min(0.18 * len(ticker_mentions), 0.54)
    if working.get("related"):
        relevance += 0.14
    if working.get("mentioned_symbols"):
        relevance += 0.08
    relevance = _clamp(relevance, 0.0, 1.0)
    engagement = compute_engagement(working)

    headline_text = " ".join(
        [str(working.get("headline") or ""), str(working.get("summary") or "")]
    )
    lexicon_score = _keyword_sentiment(headline_text)
    ai_score = _score_from_ai(working)
    social_score = _score_from_social_label(working)

    if working.get("ai_analysis"):
        sentiment_score = ai_score * 0.7 + lexicon_score * 0.3
    elif social_score:
        sentiment_score = social_score * 0.65 + lexicon_score * 0.35
    else:
        sentiment_score = lexicon_score
    sentiment_score = round(_clamp(sentiment_score, -1.0, 1.0), 4)

    impact = ((working.get("ai_analysis") or {}).get("impact_score") or 5) / 10.0
    confidence = 0.12 + reliability * 0.42 + recency_weight * 0.14 + relevance * 0.12 + impact * 0.10 + engagement * 0.10
    if working.get("summary"):
        confidence += 0.06
    confidence = round(_clamp(confidence, 0.05, 0.99), 4)

    working["sentiment_score"] = sentiment_score
    working["confidence"] = confidence
    working["relevance_score"] = round(relevance, 4)
    working["ticker_mentions"] = ticker_mentions
    working["source_reliability"] = round(reliability, 4)
    working["engagement"] = round(engagement, 4)
    working["retrieval_mode"] = get_retrieval_mode(working)
    return working


def deduplicate_articles(articles: list[dict]) -> list[dict]:
    deduped: list[dict] = []
    next_group = 1
    for article in sorted(articles, key=lambda item: item.get("datetime", 0), reverse=True):
        candidate = dict(article)
        candidate_url = canonicalize_url(str(candidate.get("url") or ""))
        candidate_headline = _headline_key(str(candidate.get("headline") or ""))
        duplicate_of: dict | None = None

        for existing in deduped:
            existing_url = canonicalize_url(str(existing.get("url") or ""))
            existing_headline = _headline_key(str(existing.get("headline") or ""))
            same_url = bool(candidate_url and existing_url and candidate_url == existing_url)
            similarity = SequenceMatcher(None, candidate_headline, existing_headline).ratio()
            same_provider = candidate.get("source_provider") == existing.get("source_provider")
            if same_url or similarity >= 0.92 or (same_provider and similarity >= 0.85):
                duplicate_of = existing
                break

        if duplicate_of:
            merged_mentions = set(duplicate_of.get("ticker_mentions", [])) | set(candidate.get("ticker_mentions", []))
            duplicate_of["ticker_mentions"] = sorted(merged_mentions)[:10]
            duplicate_of["confidence"] = round(
                max(float(duplicate_of.get("confidence", 0.0)), float(candidate.get("confidence", 0.0))),
                4,
            )
            duplicate_of["engagement"] = round(
                max(float(duplicate_of.get("engagement", 0.0)), float(candidate.get("engagement", 0.0))),
                4,
            )
            continue

        candidate["duplicate_group"] = f"dup-{next_group:04d}"
        next_group += 1
        deduped.append(candidate)

    return deduped


def cluster_narratives(articles: list[dict], limit: int = 5) -> list[dict]:
    if not articles:
        return []

    buckets: dict[str, list[dict]] = defaultdict(list)
    for article in articles:
        lowered = " ".join(
            [str(article.get("headline") or ""), str(article.get("summary") or "")]
        ).lower()
        label = ""
        for theme, keywords in THEME_KEYWORDS.items():
            if any(keyword in lowered for keyword in keywords):
                label = theme
                break
        if not label:
            mentions = article.get("ticker_mentions") or []
            label = f"{mentions[0]} focus" if mentions else f"{article.get('source_category', 'news').title()} flow"
        buckets[label].append(article)

    clusters: list[dict] = []
    for label, items in buckets.items():
        symbol_counter = Counter(
            symbol
            for item in items
            for symbol in item.get("ticker_mentions", [])
        )
        avg_sentiment = sum(float(item.get("sentiment_score", 0.0)) for item in items) / len(items)
        clusters.append(
            {
                "label": label,
                "mentions": len(items),
                "avg_sentiment": round(avg_sentiment, 4),
                "symbols": [symbol for symbol, _ in symbol_counter.most_common(3)],
            }
        )

    clusters.sort(key=lambda cluster: (cluster["mentions"], abs(cluster["avg_sentiment"])), reverse=True)
    return clusters[:limit]


def build_source_health(articles: list[dict], sources_active: dict[str, bool]) -> dict[str, dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for article in articles:
        grouped[str(article.get("source_provider") or "unknown")].append(article)

    result: dict[str, dict] = {}
    for provider, active in sources_active.items():
        items = grouped.get(provider, [])
        avg_confidence = sum(float(item.get("confidence", 0.0)) for item in items) / len(items) if items else 0.0
        result[provider] = {
            "active": bool(active),
            "articles": len(items),
            "avg_confidence": round(avg_confidence, 4),
            "retrieval_mode": RETRIEVAL_MODE_BY_PROVIDER.get(provider, "unknown"),
            "status": "healthy" if active and items else "idle" if active else "offline",
        }
    return result


def build_source_breakdown(articles: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for article in articles:
        grouped[str(article.get("source_provider") or "unknown")].append(article)

    breakdown = []
    for provider, items in grouped.items():
        avg_sentiment = sum(float(item.get("sentiment_score", 0.0)) for item in items) / len(items)
        avg_confidence = sum(float(item.get("confidence", 0.0)) for item in items) / len(items)
        breakdown.append(
            {
                "provider": provider,
                "count": len(items),
                "avg_sentiment": round(avg_sentiment, 4),
                "avg_confidence": round(avg_confidence, 4),
                "retrieval_mode": RETRIEVAL_MODE_BY_PROVIDER.get(provider, "unknown"),
            }
        )

    breakdown.sort(key=lambda item: item["count"], reverse=True)
    return breakdown


def build_social_sentiment_from_articles(symbol: str, articles: list[dict]) -> dict:
    symbol_upper = symbol.upper()
    social_articles = [
        article
        for article in articles
        if article.get("source_category") == "social"
        and symbol_upper in set(article.get("ticker_mentions") or [])
    ]
    if not social_articles:
        return {
            "symbol": symbol_upper,
            "reddit": {"mentions": 0, "score": 0.0},
            "twitter": {"mentions": 0, "score": 0.0},
            "stocktwits": {"mentions": 0, "score": 0.0},
            "total_mentions": 0,
            "combined_score": 0.0,
            "buzz_level": "none",
            "sentiment_label": "neutral",
            "configured": False,
        }

    provider_groups: dict[str, list[dict]] = defaultdict(list)
    for article in social_articles:
        provider_groups[str(article.get("source_provider") or "unknown")].append(article)

    def summarize(provider: str) -> dict:
        items = provider_groups.get(provider, [])
        if not items:
            return {"mentions": 0, "score": 0.0}
        avg_score = sum(float(item.get("sentiment_score", 0.0)) for item in items) / len(items)
        return {"mentions": len(items), "score": round(avg_score, 4)}

    total_mentions = len(social_articles)
    weighted_sum = sum(
        float(item.get("sentiment_score", 0.0)) * max(float(item.get("confidence", 0.0)), 0.1)
        for item in social_articles
    )
    total_weight = sum(max(float(item.get("confidence", 0.0)), 0.1) for item in social_articles)
    combined_score = weighted_sum / total_weight if total_weight else 0.0

    if total_mentions >= 12:
        buzz_level = "viral"
    elif total_mentions >= 8:
        buzz_level = "high"
    elif total_mentions >= 4:
        buzz_level = "moderate"
    elif total_mentions >= 1:
        buzz_level = "low"
    else:
        buzz_level = "none"

    if combined_score >= 0.20:
        sentiment_label = "bullish"
    elif combined_score <= -0.20:
        sentiment_label = "bearish"
    else:
        sentiment_label = "neutral"

    return {
        "symbol": symbol_upper,
        "reddit": summarize("reddit"),
        "twitter": summarize("twitter"),
        "stocktwits": summarize("stocktwits"),
        "total_mentions": total_mentions,
        "combined_score": round(combined_score, 4),
        "buzz_level": buzz_level,
        "sentiment_label": sentiment_label,
        "configured": False,
    }

