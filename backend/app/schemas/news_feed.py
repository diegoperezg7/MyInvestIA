"""Schemas for AI-analyzed news feed and enhanced sentiment."""

from enum import Enum

from pydantic import BaseModel


class NewsUrgency(str, Enum):
    breaking = "breaking"
    high = "high"
    normal = "normal"


class NewsSentiment(str, Enum):
    positive = "positive"
    negative = "negative"
    neutral = "neutral"


class SourceCategory(str, Enum):
    news = "news"
    social = "social"
    blog = "blog"


class ArticleAIAnalysis(BaseModel):
    impact_score: int  # 1-10
    affected_tickers: list[str]
    sentiment: NewsSentiment
    urgency: NewsUrgency
    brief_analysis: str


class AnalyzedArticle(BaseModel):
    id: str
    headline: str
    summary: str
    source: str
    source_provider: str  # "finnhub" | "newsapi" | "rss" | "reddit" | "stocktwits" | "twitter"
    source_category: SourceCategory = SourceCategory.news
    url: str
    datetime: int
    ai_analysis: ArticleAIAnalysis | None = None
    # Social-specific fields
    author: str | None = None
    score: int | None = None
    num_comments: int | None = None
    sentiment_label: str | None = None  # StockTwits: "Bullish" | "Bearish"
    sentiment_score: float = 0.0
    confidence: float = 0.0
    relevance_score: float = 0.0
    ticker_mentions: list[str] = []
    source_reliability: float = 0.0
    duplicate_group: str = ""
    engagement: float = 0.0
    retrieval_mode: str = "unknown"


class NewsFeedResponse(BaseModel):
    articles: list[AnalyzedArticle]
    total: int
    sources_active: dict[str, bool]
    category_counts: dict[str, int]
    generated_at: str
    top_narratives: list[dict] = []
    source_health: dict[str, dict] = {}


class EnhancedSentimentSource(BaseModel):
    source_name: str
    score: float
    weight: float
    details: dict


class EnhancedSentimentResponse(BaseModel):
    symbol: str
    unified_score: float
    unified_label: str
    sources: list[EnhancedSentimentSource]
    coverage_confidence: float = 0.0
    news_momentum: float = 0.0
    social_momentum: float = 0.0
    top_narratives: list[dict] = []
    source_breakdown: list[dict] = []
    cross_source_divergence: float = 0.0
    source_health: dict[str, dict] = {}
    total_data_points: int
    generated_at: str
