from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "ORACLE"
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:3000"]

    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""

    # Telegram Bot
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Anthropic (Claude AI)
    anthropic_api_key: str = ""

    # CoinGecko (optional - free tier works without key)
    coingecko_api_key: str = ""

    # Redis
    redis_url: str = "redis://localhost:6379"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
