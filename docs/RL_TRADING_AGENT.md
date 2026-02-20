# RL Trading Agent API

## Overview

The RL Trading Agent is an automated trading system that uses Reinforcement Learning (PPO) to generate trading signals. It integrates with MyInvestIA and supports paper trading, shadow mode, and live trading.

## Features

- **Multiple Indicators**: RSI, MACD, Bollinger Bands, Stochastic, ADX, CCI, Williams %R
- **Risk Management**: Stop loss, take profit, max position size
- **Trading Modes**: Paper (simulation), Shadow (signals only), Live (real trading)
- **Scheduler**: Automated trading at regular intervals
- **Exchange Integration**: Binance, Coinbase, Kraken, KuCoin (via CCXT)

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Configure your API keys in .env (for live trading)
```

## Quick Start

### 1. Initialize the Agent

```bash
curl -X POST "http://localhost:8000/api/v1/rl-agent/init" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTC/USD",
    "mode": "paper",
    "initial_balance": 10000,
    "max_position_pct": 0.1,
    "stop_loss_pct": 0.05,
    "take_profit_pct": 0.10
  }'
```

### 2. Get Current Status

```bash
curl "http://localhost:8000/api/v1/rl-agent/status"
```

Response:
```json
{
  "model_loaded": false,
  "mode": "paper",
  "symbol": "BTC/USD",
  "position": 0,
  "entry_price": 0,
  "max_position_pct": 0.1,
  "stop_loss_pct": 0.05,
  "take_profit_pct": 0.10,
  "total_trades": 0
}
```

### 3. Get Trading Signal

```bash
curl -X POST "http://localhost:8000/api/v1/rl-agent/signal" \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      {"Close": 45000, "Open": 44800, "High": 45200, "Low": 44500, "Volume": 1000000},
      ...
    ],
    "current_price": 45100
  }'
```

Response:
```json
{
  "action": "buy",
  "confidence": 0.75,
  "reason": "Momentum: 0.52%, RSI: 42.3",
  "momentum": 0.0052,
  "rsi": 42.3,
  "volume_ratio": 1.2,
  "position": 0
}
```

### 4. Execute Trade

```bash
curl -X POST "http://localhost:8000/api/v1/rl-agent/trade" \
  -H "Content-Type: application/json" \
  -d '{
    "data": [...],
    "current_price": 45100
  }'
```

### 5. Get Performance

```bash
curl "http://localhost:8000/api/v1/rl-agent/performance"
```

Response:
```json
{
  "total_trades": 15,
  "buy_trades": 8,
  "sell_trades": 7,
  "winning_trades": 9,
  "losing_trades": 6,
  "win_rate": 0.6,
  "total_pnl": 1250.50,
  "initial_balance": 10000,
  "current_estimate": 11250.50
}
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/rl-agent/init` | Initialize the agent |
| GET | `/api/v1/rl-agent/status` | Get agent status |
| POST | `/api/v1/rl-agent/signal` | Get trading signal |
| POST | `/api/v1/rl-agent/trade` | Execute trade |
| GET | `/api/v1/rl-agent/performance` | Get performance metrics |
| GET | `/api/v1/rl-agent/trades` | Get trade history |
| POST | `/api/v1/rl-agent/mode` | Change mode (paper/shadow/live) |
| POST | `/api/v1/rl-agent/close-position` | Force close position |

## Trading Modes

### Paper Trading
- Fully simulated trading
- No real money involved
- Good for testing strategies

### Shadow Mode
- Generates signals but doesn't execute
- Useful for monitoring and backtesting

### Live Trading
- Real trading on exchange
- Requires API keys
- Requires approval for high-confidence trades (≥80%)

## Risk Management

- **Max Position**: 10% of portfolio per trade
- **Stop Loss**: 5% automatic exit
- **Take Profit**: 10% automatic exit
- **Min Confidence**: 50% for paper, 80% for live

## Scheduler

The scheduler runs automatically at configurable intervals:

```json
{
  "scheduler_enabled": true,
  "scheduler_interval_minutes": 30
}
```

## Configuration

Environment variables can be configured in `.env`:

```env
SYMBOL=BTC/USD
MODE=paper
INITIAL_BALANCE=10000
MAX_POSITION_PCT=0.1
STOP_LOSS_PCT=0.05
TAKE_PROFIT_PCT=0.10

# For live trading
BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret
```

## Frontend Dashboard

The React component `RLAgentDashboard` provides:
- Real-time status display
- Current signal visualization
- Trade history
- Performance metrics
- Mode controls

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      MyInvestIA Backend                     │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Router     │  │   Service    │  │    Agent     │    │
│  │ rl_trading.py│→ │rl_trading_  │→ │  agent.py    │    │
│  │              │  │  service.py  │  │              │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                 │          │
│                           ┌──────────────────────┼────────┐│
│                           │   indicators.py       │        ││
│                           │   scheduler.py      │        ││
│                           │   exchange_client.py│        ││
│                           └──────────────────────┼────────┘│
└─────────────────────────────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
    ┌──────────┐   ┌──────────┐   ┌──────────┐
    │  CCXT    │   │  Yahoo   │   │   MySQL  │
    │ Exchange │   │  Finance │   │ Database │
    └──────────┘   └──────────┘   └──────────┘
```

## Performance Results

Based on training with TensorTrade:

| Strategy | PnL |
|----------|-----|
| Random Actions | -46.82% |
| Buy & Hold | -31.81% |
| **PPO Agent** | **-0.71%** |

The agent outperformed Buy & Hold by +31%!

## Next Steps for Production

1. Train agent with more iterations (100+)
2. Test in paper mode for extended period
3. Switch to testnet exchange
4. Configure API keys
5. Start with small capital
6. Monitor and adjust parameters

## Troubleshooting

### Agent not initialized
```bash
# Initialize first
curl -X POST "http://localhost:8000/api/v1/rl-agent/init"
```

### No signal generated
- Ensure sufficient data is provided (≥20 candles)
- Check data format

### Connection errors
- Check API keys are configured
- Verify testnet/live mode settings
