from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "InvestIA"
    debug: bool = False
    cors_origins: list[str] = [
        "https://myinvestia.darc3.com",
        "https://portal.darc3.com",
    ]

    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""

    # Telegram Bot
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Cerebras AI
    cerebras_api_key: str = ""

    # Groq AI (free, fast inference)
    groq_api_key: str = ""

    # CoinGecko (optional - free tier works without key)
    coingecko_api_key: str = ""

    # NewsAPI.org (optional, free tier: 100 req/day)
    newsapi_key: str = ""
    news_mixed_mode: bool = True
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "InvestIA/1.0"

    # Market data providers (optional fallbacks)
    alphavantage_api_key: str = ""
    finnhub_api_key: str = ""
    twelvedata_api_key: str = ""
    bloomberg_enabled: bool = False
    bloomberg_host: str = ""
    bloomberg_port: int = 8194
    market_provider_order: str = "yfinance,alphavantage,finnhub,twelvedata,bloomberg"
    crypto_provider_order: str = "coingecko,yfinance"
    macro_provider_order: str = "fred,yfinance"
    fundamentals_provider_order: str = "yfinance"
    filings_provider_order: str = "sec"
    news_provider_order: str = "gdelt,rss,finnhub,reddit,stocktwits,newsapi,twitter"

    # Official/public data sources
    fred_api_key: str = ""
    bls_api_key: str = ""
    sec_user_agent: str = "InvestIA/1.0 contact: support@example.com"
    worldbank_country: str = "WLD"

    # Multi-tenancy
    enable_multitenant: bool = False
    default_tenant_id: str = "default"

    # OpenClaw (self-hosted AI agent for alerts & Telegram)
    openclaw_url: str = "http://localhost:18789"
    openclaw_token: str = ""
    openclaw_enabled: bool = False

    # Connections / Encryption
    encryption_master_key: str = ""
    moralis_api_key: str = ""
    etoro_api_key: str = ""
    etoro_api_secret: str = ""
    polymarket_api_key: str = ""

    # Auth / JWT
    jwt_secret: str = ""
    supabase_service_key: str = ""
    aidentity_url: str = "https://aidentity.darc3.com/api/v1"
    aidentity_secret: str = ""

    # Display currency
    display_currency: str = "USD"

    # Redis
    redis_url: str = "redis://localhost:6379"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
