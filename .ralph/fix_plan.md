# Ralph Fix Plan

## High Priority
- [x] Set up basic project structure and build system
- [x] Define core data structures and types
- [x] Implement basic input/output handling (API endpoints)
- [x] Create test framework and initial tests
- [ ] Install dependencies and verify backend starts
- [ ] Install frontend dependencies and verify build

## Medium Priority
- [ ] Add error handling and validation
- [ ] Implement portfolio CRUD operations (manual asset entry)
- [ ] Implement watchlist CRUD operations
- [ ] Add market data service integration
- [ ] Implement technical analysis indicators (RSI, MACD, EMA, SMA, Bollinger)
- [ ] Add sentiment analysis service
- [ ] Create WebSocket support for real-time updates
- [ ] Add configuration management

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

## Notes
- Focus on MVP functionality first
- Ensure each feature is properly tested
- Update this file after each major milestone
- Backend runs on port 8000, frontend on port 3000
- Frontend proxies /api/* requests to backend via next.config.ts rewrites
