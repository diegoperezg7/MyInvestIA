from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "ORACLE"
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:3000"]
    supabase_url: str = ""
    supabase_key: str = ""
    redis_url: str = "redis://localhost:6379"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
