from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "InvestIA"
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001", "http://localhost:3002"]

    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""

    # Telegram Bot
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Mistral AI
    mistral_api_key: str = ""

    # CoinGecko (optional - free tier works without key)
    coingecko_api_key: str = ""

    # NewsAPI.org (optional, free tier: 100 req/day)
    newsapi_key: str = ""

    # Market data providers (optional fallbacks)
    alphavantage_api_key: str = ""
    finnhub_api_key: str = ""
    twelvedata_api_key: str = ""

    # OpenClaw (self-hosted AI agent for alerts & Telegram)
    openclaw_url: str = "http://localhost:18789"
    openclaw_token: str = ""
    openclaw_enabled: bool = False

    # Display currency
    display_currency: str = "USD"

    # Redis
    redis_url: str = "redis://localhost:6379"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
