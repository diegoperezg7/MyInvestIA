# MyInvestIA

AI-powered investment intelligence dashboard that aggregates real-time market data, technical analysis, sentiment intelligence, macroeconomic indicators, and portfolio tracking into a single explainable decision-support system.

> **This system does NOT execute trades or provide financial advice.** All outputs are informational. Users retain full control over their investment decisions.

![Python](https://img.shields.io/badge/Python-3.14-blue)
![Next.js](https://img.shields.io/badge/Next.js-15-black)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)
![Tailwind](https://img.shields.io/badge/Tailwind_CSS-4-38bdf8)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Features

### Market Intelligence
- **Real-time quotes** — stocks, ETFs, crypto, commodities via multi-provider chain (Yahoo Finance + optional AlphaVantage, Finnhub, TwelveData)
- **Batch data fetching** — single HTTP call for multiple symbols using `yf.download()`
- **Top movers** — gainers/losers with sparkline charts
- **Macro dashboard** — VIX, DXY, Treasury yields, gold, oil, copper with AI impact analysis
- **WebSocket streaming** — live price updates

### Technical Analysis
- RSI, MACD, EMA/SMA, Bollinger Bands
- Support/resistance levels and trend channels
- Overbought/oversold detection with reversal probability
- Signal summary per asset

### Sentiment Intelligence
- Multi-source analysis: financial news, social media (X, Reddit), headlines
- Bullish/bearish classification with -1 to +1 scoring
- Narrative extraction and sentiment momentum tracking
- Enhanced multi-source aggregation

### AI Chat & Reasoning
- Conversational asset analysis powered by Mistral AI
- Persona-based analysis (bullish, bearish, balanced analysts)
- AI-generated market briefings
- What-if scenario simulation
- Persistent AI memory for personalized context

### Portfolio & Trading
- Manual portfolio tracking with PnL calculation
- Import/export via CSV
- Dividend tracking
- Paper trading simulator with virtual accounts
- Transaction history and cost basis

### Alerts & Notifications
- AI-driven alerting with confidence scoring and reasoning
- Alert types: price anomalies, technical extremes, sentiment shifts, macro risk, multi-factor opportunities
- Delivery via Telegram Bot
- OpenClaw integration for advanced AI agent alerts

### Additional Modules
- **Screener** — custom filter rules and presets for market scanning
- **Recommendations** — AI-powered asset suggestions with reasoning
- **News feed** — aggregated from RSS + NewsAPI with per-article sentiment
- **Watchlists** — unlimited lists with price tracking and sparklines
- **Currency conversion** — multi-currency portfolio display

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  Frontend — Next.js 15 + Tailwind CSS 4 + Recharts      │
│  localhost:3000                                          │
│  ┌──────────┬──────────┬──────────┬──────────┐          │
│  │ Overview │ Analysis │ Portfolio│ Screener │ ...       │
│  └────┬─────┴────┬─────┴────┬─────┴────┬─────┘          │
│       │  Zustand stores  │  React hooks │                │
│       └────────┬─────────┴──────┬───────┘                │
│            fetchAPI (SWR cache, dedup)                    │
└────────────────┬─────────────────────────────────────────┘
                 │ /api/* proxy (next.config.ts rewrites)
┌────────────────▼─────────────────────────────────────────┐
│  Backend — FastAPI + Python 3.14                         │
│  localhost:8000                                          │
│  ┌──────────────────────────────────────────────┐        │
│  │ Routers: market, portfolio, watchlist, chat,  │        │
│  │ alerts, news, screener, paper-trading, ...    │        │
│  └──────────┬───────────────────────────────────┘        │
│  ┌──────────▼───────────────────────────────────┐        │
│  │ Services: provider_chain, ai_service,         │        │
│  │ sentiment, macro_intelligence, cache (SWR),   │        │
│  │ alert_scorer, recommendations, ...            │        │
│  └──────────┬───────────────────────────────────┘        │
│  ┌──────────▼───────────────────────────────────┐        │
│  │ Data Providers: yfinance │ AlphaVantage │     │        │
│  │ Finnhub │ TwelveData │ CoinGecko │ NewsAPI   │        │
│  └──────────────────────────────────────────────┘        │
└──────────┬────────────────────┬──────────────────────────┘
           │                    │
  ┌────────▼────────┐ ┌────────▼────────┐
  │  Supabase (PG)  │ │  Telegram Bot   │
  │  + AI Memory    │ │  + OpenClaw     │
  └─────────────────┘ └─────────────────┘
```

---

## Quick Start

### Prerequisites

- Python 3.12+ (tested on 3.14)
- Node.js 18+
- A [Supabase](https://supabase.com) project (free tier works)

### 1. Clone & configure

```bash
git clone https://github.com/diegoperezg7/MyInvestIA.git
cd MyInvestIA

# Backend environment
cp backend/.env.example backend/.env
# Edit backend/.env with your credentials (see Environment Variables below)
```

### 2. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API at http://localhost:8000 — Interactive docs at http://localhost:8000/docs

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard at http://localhost:3000

---

## Environment Variables

Create `backend/.env` from `backend/.env.example`:

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_KEY` | Yes | Supabase anon/public key |
| `MISTRAL_API_KEY` | Yes | Mistral AI key (chat, sentiment, reasoning) |
| `TELEGRAM_BOT_TOKEN` | No | Telegram Bot for alerts |
| `TELEGRAM_CHAT_ID` | No | Telegram chat to receive alerts |
| `NEWSAPI_KEY` | No | NewsAPI.org key (100 req/day free) |
| `ALPHAVANTAGE_API_KEY` | No | AlphaVantage fallback provider |
| `FINNHUB_API_KEY` | No | Finnhub fallback provider |
| `TWELVEDATA_API_KEY` | No | TwelveData fallback provider |
| `OPENCLAW_URL` | No | OpenClaw agent URL |
| `OPENCLAW_TOKEN` | No | OpenClaw auth token |
| `DISPLAY_CURRENCY` | No | Default display currency (default: USD) |
| `REDIS_URL` | No | Redis URL for caching |
| `DEBUG` | No | Enable debug logging |

> Yahoo Finance (primary market data provider) requires **no API key**.

---

## API Overview

All endpoints are under `/api/v1/`. Full interactive docs at `/docs` when the backend is running.

| Module | Endpoints | Description |
|--------|-----------|-------------|
| **Market** | `GET /market/`, `/market/quote/{symbol}`, `/market/movers`, `/market/macro`, `/market/history/{symbol}`, `/market/analysis/{symbol}` | Real-time quotes, movers, macro indicators, history, technical analysis |
| **Portfolio** | `GET/POST/PATCH/DELETE /portfolio/`, `/portfolio/export`, `/portfolio/dividends` | Holdings CRUD, CSV import/export, dividends |
| **Watchlists** | `GET/POST/DELETE /watchlists/`, `/watchlists/{id}/assets` | Watchlist management with live prices |
| **Chat** | `POST /chat/`, `GET /chat/analyze/{symbol}`, `/chat/briefing`, `/chat/recommendations` | AI chat, analysis, briefings, persona-based analysis |
| **Alerts** | `GET /alerts/`, `GET /alerts/scan/{symbol}`, `POST /alerts/scan-and-notify` | Alert engine with Telegram delivery |
| **News** | `GET /news/feed` | Aggregated news with sentiment |
| **Screener** | `POST /screener/scan`, `GET /screener/presets` | Market scanning with custom filters |
| **Paper Trading** | `POST /paper-trade/accounts`, `/accounts/{id}/trade` | Virtual trading simulator |
| **Notifications** | `POST /notifications/send`, `/notifications/test` | Telegram/email notifications |

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app & router registration
│   │   ├── config.py            # Settings (env vars)
│   │   ├── routers/             # API endpoint handlers (15 modules)
│   │   ├── schemas/             # Pydantic v2 data models
│   │   └── services/            # Business logic (30+ services)
│   │       ├── providers/       # Market data provider plugins
│   │       ├── cache.py         # In-memory TTL cache with stale-while-revalidate
│   │       ├── market_data.py   # Quotes, history, movers (batch fetch)
│   │       ├── ai_service.py    # Mistral AI integration
│   │       ├── macro_intelligence.py
│   │       ├── sentiment_service.py
│   │       ├── alert_scorer.py
│   │       └── ...
│   ├── tests/                   # pytest test suite
│   ├── supabase/                # Database migrations
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js app router (page, layout, globals)
│   │   ├── components/
│   │   │   ├── views/           # Page-level views (Overview, Analysis, Screener, ...)
│   │   │   ├── dashboard/       # Dashboard panels (18+ components)
│   │   │   ├── portfolio/       # Portfolio-specific components
│   │   │   ├── charts/          # Chart components
│   │   │   ├── screener/        # Screener UI
│   │   │   └── ui/              # Reusable UI primitives
│   │   ├── hooks/               # Custom React hooks
│   │   ├── stores/              # Zustand state management
│   │   ├── lib/api.ts           # API client with cache & request dedup
│   │   └── types/index.ts       # TypeScript type definitions
│   ├── next.config.ts           # API proxy rewrites
│   └── package.json
└── openclaw/                    # OpenClaw AI agent integration
```

---

## Performance

The system is optimized for fast dashboard loads:

- **Batch fetching** — `yf.download()` fetches 11+ symbols in a single HTTP call instead of N individual requests
- **Stale-while-revalidate cache** — returns cached data instantly while refreshing in the background (2x TTL grace window)
- **Tuned TTLs** — quotes: 120s, history: 600s, macro: 180s
- **Frontend caching** — 30s client-side cache with request deduplication
- **Reduced polling** — market: 60s, portfolio: 30s, watchlists: 60s
- **Lazy-loaded sections** — heavy components (recommendations, news) load after initial render

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, React 19, Tailwind CSS 4, Recharts, Zustand, TypeScript |
| Backend | Python 3.14, FastAPI, Pydantic v2, Uvicorn |
| Database | Supabase (PostgreSQL) with Row Level Security |
| AI | Mistral AI (chat, sentiment, reasoning, recommendations) |
| Market Data | Yahoo Finance (primary), AlphaVantage, Finnhub, TwelveData (fallbacks), CoinGecko (crypto) |
| Notifications | Telegram Bot API, OpenClaw |
| Testing | pytest, pytest-asyncio |

---

## Disclaimer

MyInvestIA is a decision-support tool for informational purposes only. It does not provide financial advice, and it does not execute trades. All AI-generated outputs include confidence scores and reasoning for transparency. Users are solely responsible for their investment decisions.

---

## License

MIT
