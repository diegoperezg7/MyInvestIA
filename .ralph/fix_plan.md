# Ralph Fix Plan

## High Priority - Infrastructure
- [x] Set up basic project structure and build system
- [x] Define core data structures and types
- [x] Implement basic input/output handling (API endpoints)
- [x] Create test framework and initial tests
- [x] Install dependencies and verify backend starts (Python 3.13 + pip)
- [x] Install frontend dependencies and verify build (npm)

## High Priority - API Integrations (CRITICAL)
- [x] Integrate yfinance for stock/ETF market data (prices, historical data, indicators)
- [x] Integrate CoinGecko API for cryptocurrency data (prices, market cap, volume)
- [ ] Integrate Anthropic Claude API for AI reasoning, chat interface, and signal synthesis
- [ ] Integrate Telegram Bot API for alert/notification delivery
- [ ] Connect Supabase as primary database (replace in-memory store with PostgreSQL)
- [x] Add pip dependencies: yfinance, numpy

## Medium Priority - Core Features
- [x] Add error handling and validation
- [x] Implement portfolio CRUD operations (manual asset entry)
- [x] Implement watchlist CRUD operations
- [x] Add configuration management
- [x] Implement market data service (use yfinance + CoinGecko to fetch real prices)
- [x] Implement technical analysis indicators (RSI, MACD, EMA, SMA, Bollinger Bands) using real market data
- [ ] Add sentiment analysis service (use Claude API to analyze news/social sentiment)
- [ ] Create WebSocket support for real-time price updates
- [ ] Build frontend dashboard components (charts, portfolio view, watchlist view)
- [ ] Connect frontend to real backend API data

## Medium Priority - AI Features
- [ ] Build AI Decision Synthesizer - fuses technical + sentiment + macro signals via Claude
- [ ] Implement chat interface backend (Claude-powered conversational Q&A about portfolio/market)
- [ ] Add AI memory/context system in Supabase for personalized insights
- [ ] Create alert scoring system (multi-factor: price + technical + sentiment + macro)

## Low Priority - Advanced Features
- [ ] Implement macro intelligence module (interest rates, inflation, DXY, central bank events)
- [ ] Build alerts engine with multi-factor detection and Telegram delivery
- [ ] Add chat interface frontend (conversational UI)
- [ ] Email notification delivery
- [ ] Performance optimization (Redis caching)
- [ ] Advanced error recovery

## Completed
- [x] Project initialization
- [x] Backend FastAPI structure (routers, schemas, config)
- [x] Frontend Next.js structure (layout, pages, types, API lib)
- [x] Core data models (Asset, Portfolio, Watchlist, Alert, Sentiment, Macro)
- [x] API routes (health, portfolio, watchlists, market, alerts)
- [x] Test framework with pytest + httpx async client
- [x] Health check endpoint test
- [x] Updated .gitignore, README, AGENT.md
- [x] Portfolio CRUD: InMemoryStore + router (GET/POST/PATCH/DELETE)
- [x] Watchlist CRUD: InMemoryStore + router (full CRUD + asset management)
- [x] Comprehensive portfolio tests (14 test cases)
- [x] Comprehensive watchlist tests (16 test cases)
- [x] Global exception handler in main.py
- [x] Typed response models for market and alerts stubs (MarketOverview, AlertList)
- [x] pyproject.toml with pytest async config
- [x] Request validation with Pydantic Field constraints
- [x] Config updated with Telegram, Anthropic, Supabase settings
- [x] .env.example with all required API keys documented
- [x] Market data service: yfinance (stocks/ETFs) + CoinGecko (crypto) with quotes, history, top movers
- [x] Technical analysis service: RSI, MACD, EMA, SMA, Bollinger Bands with signal assessment
- [x] Market router: /quote/{symbol}, /history/{symbol}, /analysis/{symbol} endpoints
- [x] Portfolio router: live price integration via market data service
- [x] Market and technical analysis response schemas (AssetQuote, HistoricalData, TechnicalAnalysis)
- [x] Test suite: 59 tests passing (market, portfolio, watchlist, technical analysis, health)

## API Configuration
- **Market Data**: yfinance (stocks/ETFs) + CoinGecko (crypto) - both free, no API key needed
- **AI Engine**: Anthropic Claude API - requires ANTHROPIC_API_KEY in .env
- **Notifications**: Telegram Bot API - requires TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID in .env
- **Database**: Supabase PostgreSQL - requires SUPABASE_URL + SUPABASE_KEY in .env
- **Config file**: backend/.env (copy from backend/.env.example)

## Notes
- Focus on MVP functionality first
- Ensure each feature is properly tested
- Update this file after each major milestone
- Backend runs on port 8000, frontend on port 3000
- Frontend proxies /api/* requests to backend via next.config.ts rewrites
- Python 3.13 venv at backend/.venv (Python 3.14 incompatible with pydantic-core)
- Run backend: cd backend && source .venv/bin/activate && uvicorn app.main:app --reload
- Run tests: cd backend && source .venv/bin/activate && pytest tests/ -v
- Run frontend: cd frontend && npm run dev
