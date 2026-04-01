"""
Environment configuration for RL Trading Agent.
"""

import os
from typing import Optional
from pydantic import BaseModel


class RLAgentConfig(BaseModel):
    """Configuration for RL Trading Agent."""

    # Agent settings
    symbol: str = "BTC/USD"
    mode: str = "paper"  # paper, shadow, live

    # Risk management
    initial_balance: float = 10000
    max_position_pct: float = 0.1  # Max 10% of portfolio per trade
    stop_loss_pct: float = 0.05  # 5% stop loss
    take_profit_pct: float = 0.10  # 10% take profit

    # Trading settings
    min_confidence: float = 0.5  # Minimum confidence to trade
    max_daily_trades: int = 5  # Max trades per day

    # Scheduler settings
    scheduler_enabled: bool = False
    scheduler_interval_minutes: int = 30

    # Exchange settings
    exchange: str = "binance"
    testnet: bool = True

    # Model settings
    model_checkpoint: Optional[str] = None
    use_rl_model: bool = False  # Use ML model vs heuristics

    # Indicators to use
    indicators: list = None

    def __init__(self, **data):
        if data.get("indicators") is None:
            data["indicators"] = ["rsi", "macd", "bb", "stoch"]
        super().__init__(**data)


class DatabaseConfig(BaseModel):
    """Database configuration."""

    host: str = os.environ.get("DB_HOST", "localhost")
    port: int = int(os.environ.get("DB_PORT", "5432"))
    name: str = os.environ.get("DB_NAME", "myinvestia")
    user: str = os.environ.get("DB_USER", "postgres")
    password: str = os.environ.get("DB_PASSWORD", "")


class RedisConfig(BaseModel):
    """Redis configuration."""

    host: str = os.environ.get("REDIS_HOST", "localhost")
    port: int = int(os.environ.get("REDIS_PORT", "6379"))
    password: Optional[str] = os.environ.get("REDIS_PASSWORD", None)


class ExchangeConfig(BaseModel):
    """Exchange API configuration."""

    binance_api_key: Optional[str] = os.environ.get("BINANCE_API_KEY", None)
    binance_api_secret: Optional[str] = os.environ.get("BINANCE_API_SECRET", None)
    coinbase_api_key: Optional[str] = os.environ.get("COINBASE_API_KEY", None)
    coinbase_api_secret: Optional[str] = os.environ.get("COINBASE_API_SECRET", None)
    kraken_api_key: Optional[str] = os.environ.get("KRAKEN_API_KEY", None)
    kraken_api_secret: Optional[str] = os.environ.get("KRAKEN_API_SECRET", None)


class AppConfig(BaseModel):
    """Main application configuration."""

    # App settings
    debug: bool = os.environ.get("DEBUG", "false").lower() == "true"
    environment: str = os.environ.get(
        "ENVIRONMENT", "development"
    )  # development, staging, production

    # RL Agent
    rl_agent: RLAgentConfig = RLAgentConfig()

    # Database
    database: DatabaseConfig = DatabaseConfig()

    # Redis
    redis: RedisConfig = RedisConfig()

    # Exchanges
    exchanges: ExchangeConfig = ExchangeConfig()

    # Paths
    models_path: str = os.environ.get(
        "MODELS_PATH", "./models"
    )
    logs_path: str = os.environ.get(
        "LOGS_PATH", "./logs"
    )

    # CORS
    cors_origins: list = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global config instance
config = AppConfig()


def get_config() -> AppConfig:
    """Get the global configuration instance."""
    return config


def update_rl_agent_config(**kwargs):
    """Update RL agent configuration."""
    for key, value in kwargs.items():
        if hasattr(config.rl_agent, key):
            setattr(config.rl_agent, key, value)


# Example .env file content
ENV_EXAMPLE = """
# RL Trading Agent Configuration
SYMBOL=BTC/USD
MODE=paper
INITIAL_BALANCE=10000
MAX_POSITION_PCT=0.1
STOP_LOSS_PCT=0.05
TAKE_PROFIT_PCT=0.10

# Scheduler
SCHEDULER_ENABLED=false
SCHEDULER_INTERVAL_MINUTES=30

# Exchange API Keys (for live trading)
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret
# COINBASE_API_KEY=your_api_key
# COINBASE_API_SECRET=your_api_secret
# KRAKEN_API_KEY=your_api_key
# KRAKEN_API_SECRET=your_api_secret

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=myinvestia
DB_USER=postgres
DB_PASSWORD=your_password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Paths
MODELS_PATH=./models
LOGS_PATH=./logs

# App
DEBUG=false
ENVIRONMENT=development
"""


# Save example .env
def save_example_env(path: str = ".env.example"):
    """Save example .env file."""
    with open(path, "w") as f:
        f.write(ENV_EXAMPLE)
