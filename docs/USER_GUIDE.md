# User Guide

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.10+
- (Optional) Supabase account for data persistence

### Installation

1. Clone the repository:
```bash
git clone https://github.com/your-org/myinvestia.git
cd myinvestia
```

2. Install backend dependencies:
```bash
cd backend
cp .env.example .env
# Configure your .env with API keys
pip install -e .
```

3. Install frontend dependencies:
```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

4. Start the backend:
```bash
cd backend
uvicorn app.main:app --reload
```

5. Open http://localhost:3000 in your browser

## Core Concepts

### 1. Sentiment Analysis

The sentiment engine aggregates news, social media, and AI analysis to produce a unified sentiment score for each asset.

**Key Metrics:**
- `unified_score`: -1 (bearish) to +1 (bullish)
- `coverage_confidence`: How reliable the score is (0-1)
- `news_momentum`: Recent trend in news sentiment
- `signal_to_noise`: Quality ratio of signal

**Usage:**
- Navigate to any asset detail
- View the sentiment card
- Check for warnings (low confidence, diverging sources)

### 2. Alerts

Alerts combine technical analysis, sentiment, and portfolio context to notify you of important changes.

**Alert Types:**
- Price spikes/drops
- RSI overbought/oversold
- Technical convergence (multiple signals aligned)
- Sentiment shifts
- Portfolio concentration
- Macro deterioration with exposure

**Usage:**
- Go to Portfolio → Alerts
- Click "Escanear" to scan your assets
- Click "Escanear y avisar" to send to Telegram

### 3. Thesis System

Theses track your investment ideas with conviction levels, catalysts, risks, and invalidation conditions.

**Creating a Thesis:**
1. From Inbox: Click "Crear tesis" on any item
2. From Portfolio: Click "Nueva tesis" in Theses tab

**Tracking:**
- Review theses regularly
- Update conviction as conditions change
- Mark as broken when invalidation triggers

### 4. Journal & Decision Log

Record your investment decisions, reflections, and lessons learned.

**Entry Types:**
- Decision: Buy/sell/hold with reasoning
- Reflection: Learning from the market
- Observation: Market notes without action
- Review: Post-analysis of past decisions

**Recording Outcomes:**
1. Create a decision entry
2. Later, record the outcome (success/failure/neutral)
3. Add notes on what went right/wrong

### 5. AI Assistant

The AI explains structured analysis without making up data.

**Features:**
- `/chat/analyze/{symbol}`: Get structured analysis
- Chat with context about your portfolio
- Persona analysis (Buffett style, etc.)

**Best Practices:**
- Use AI for explanation, not recommendations
- Always check sources and confidence levels
- Verify data with other sources

## Views Overview

### Home (Inicio)
Your dashboard with priorities, portfolio summary, and key metrics.

### Priorities (Prioridades)
AI-generated insights from news, sentiment, and alerts that need attention.

### Portfolio
- **Overview**: Holdings, allocation, performance
- **Watchlists**: Custom lists of assets to track
- **Theses**: Your investment ideas and tracking
- **Alerts**: Active alerts for your assets

### Research
- **Ideas**: AI-generated investment ideas
- **Screener**: Filter stocks by criteria
- **Factors**: Factor-based analysis
- **Signal**: Combined AI signal

### Markets
- **Today**: Daily market pulse
- **Macro**: Economic indicators
- **Calendar**: Upcoming earnings, economic events
- **Moves**: Top gainers/losers

### Assistant
- **Chat**: AI assistant with portfolio context
- **Alerts**: Active system alerts
- **Connections**: Broker/API connections

## Troubleshooting

### No data showing
1. Check API keys in .env
2. Verify network connectivity
3. Check browser console for errors

### Alerts not firing
1. Ensure assets are in portfolio/watchlist
2. Check severity thresholds
3. Verify Telegram bot is connected

### Thesis review stuck
1. Ensure symbol has price data
2. Check that invalidation condition is properly formatted (e.g., "180")

## API Reference

### Authentication
```
Authorization: Bearer <token>
```

### Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/market/quote/{symbol}` | Get quote data |
| `GET /api/v1/sentiment/{symbol}` | Get sentiment analysis |
| `GET /api/v1/alerts/` | Get active alerts |
| `POST /api/v1/alerts/scan-and-notify` | Scan and notify |
| `GET /api/v1/theses/` | List theses |
| `POST /api/v1/journal/` | Create journal entry |

## Support

- GitHub Issues: Report bugs and feature requests
- Documentation: See `/docs` folder
- Discord: Join the community
