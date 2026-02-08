# Ralph Fix Plan

## High Priority
- [x] Set up basic project structure and build system
- [x] Define core data structures and types
- [x] Implement basic input/output handling (API endpoints)
- [x] Create test framework and initial tests
- [ ] Install dependencies and verify backend starts
- [ ] Install frontend dependencies and verify build

## Medium Priority
- [x] Add error handling and validation
- [x] Implement portfolio CRUD operations (manual asset entry)
- [x] Implement watchlist CRUD operations
- [ ] Add market data service integration
- [ ] Implement technical analysis indicators (RSI, MACD, EMA, SMA, Bollinger)
- [ ] Add sentiment analysis service
- [ ] Create WebSocket support for real-time updates
- [x] Add configuration management

## Low Priority
- [ ] Implement macro intelligence module
- [ ] Build alerts engine with multi-factor detection
- [ ] Add chat interface with AI integration
- [ ] Telegram/Email notification delivery
- [ ] Performance optimization
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

## Notes
- Focus on MVP functionality first
- Ensure each feature is properly tested
- Update this file after each major milestone
- Backend runs on port 8000, frontend on port 3000
- Frontend proxies /api/* requests to backend via next.config.ts rewrites
- Sandbox environment blocks pip install, venv creation, and pytest execution
- Dependencies must be installed manually: `cd backend && pip install -r requirements.txt`
- Tests can be run with: `cd backend && python -m pytest tests/ -v`
