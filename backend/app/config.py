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
    groq_api_key: str = "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"

    # CoinGecko (optional - free tier works without key)
    coingecko_api_key: str = ""

    # NewsAPI.org (optional, free tier: 100 req/day)
    newsapi_key: str = ""

    # Market data providers (optional fallbacks)
    alphavantage_api_key: str = ""
    finnhub_api_key: str = ""
    twelvedata_api_key: str = ""
    bloomberg_host: str = ""
    bloomberg_port: int = 8194

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
    aidentity_secret: str = ""

    # Display currency
    display_currency: str = "USD"

    # Redis
    redis_url: str = "redis://localhost:6379"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
