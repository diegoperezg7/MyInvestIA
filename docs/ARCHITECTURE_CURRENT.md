# Current Architecture

## High-Level Runtime

MyInvestIA is currently a monorepo with a browser-facing Next.js frontend and a FastAPI backend behind Caddy. Redis is present for infrastructure completeness, but a significant amount of application caching still happens in Python in-memory structures.

Current runtime flow:

1. Browser loads the Next.js app
2. Caddy routes:
   - `/api/*` and `/health` to FastAPI
   - app shell and static assets to Next.js
3. FastAPI routes requests into router modules
4. Routers delegate to service modules
5. Services call:
   - market/news/social providers
   - AI providers
   - persistence store
   - Telegram / OpenClaw integrations

## Frontend Architecture

### Entry Points

- App Router entry: `frontend/src/app`
- Main shell: `frontend/src/components/Dashboard.tsx`
- Providers:
  - `AuthProvider`
  - `ThemeProvider`
  - `ViewProvider`

### Navigation Model

The frontend is no longer organized as a simple page-per-feature dashboard. It has moved to a shell model with sections and tabs:

- `home`
- `priorities`
- `portfolio`
- `research`
- `markets`
- `assistant`
- `settings`

This is a positive move because it better matches the product surface. However, the frontend still carries a legacy mapping layer (`LEGACY_VIEW_TO_SHELL`) to preserve old view aliases.

### Data Access Pattern

- Base URL resolution lives in `frontend/src/lib/api-base.ts`
- Fetch helpers live in `frontend/src/lib/api.ts`
- Auth token handling lives in `frontend/src/lib/auth.ts`
- Real-time and streaming flows use:
  - `EventSource`
  - polling intervals
  - SSE token streaming

### Frontend Strengths

- Good top-level shell abstraction
- Typed tab and section model
- Centralized API helpers
- Feature-specific views and hooks

### Frontend Weaknesses

- Some large components now own too much state and too many responsibilities
- Lint configuration is not committed, so quality gates are weak
- Auth and storage naming still carry older Oracle / darc3 coupling
- Some screens eagerly combine many concerns instead of composing smaller feature panels

## Backend Architecture

### Entry Point

- App bootstrap: `backend/app/main.py`
- Router registration happens explicitly in one place

### Main Backend Domains

- Core market intelligence
  - `market.py`
  - `market_data.py`
  - provider chain
  - technical analysis
  - fundamentals, volatility, sector heatmap, economic calendar
- Portfolio and watchlists
  - `portfolio.py`
  - `watchlist.py`
  - dividend, currency, portfolio risk services
- Alerts and notifications
  - `alerts.py`
  - `notifications.py`
  - `alert_scorer.py`
  - `alerts_engine.py`
  - Telegram and OpenClaw services
- AI and workflow
  - `chat.py`
  - `inbox.py`
  - `theses.py`
  - `research.py`
  - `inbox_service.py`
  - `research_service.py`
  - `thesis_service.py`
- External account connections
  - `connections.py`
  - exchange / wallet / broker / prediction integrations
- Experimental or lab modules
  - paper trading
  - RL trading
  - agent orchestrator

### Persistence Layer

The backend uses a global singleton store selected at import time:

- `InMemoryStore` if Supabase is not configured
- `SupabaseStore` if Supabase configuration is present

This keeps the code simple but creates hidden runtime behavior changes. The same API can behave as:

- fully ephemeral
- partially persistent
- persistent with silent in-memory fallback for some workflow features

That ambiguity is one of the largest architectural risks in the current codebase.

### AI Layer

There are two active AI integration paths:

- `groq_service`
  - used by chat and several live or latency-sensitive flows
- `ai_service`
  - Cerebras / OpenAI-compatible path
  - still used by legacy recommendations, briefing, some sentiment and news analysis

This is workable short term, but it means the AI strategy is not yet consolidated.

### Data Provider Layer

Market and news data is assembled from multiple providers:

- Yahoo Finance via provider chain
- optional AlphaVantage, Finnhub, TwelveData, Bloomberg
- CoinGecko for crypto
- Finnhub, NewsAPI, GDELT, RSS, Reddit, StockTwits, Twitter for news and social flows
- Moralis for wallet tracking
- CCXT for exchange integrations

This breadth is valuable, but it also increases:

- request fan-out
- retry complexity
- rate-limit exposure
- debugging cost

## Infrastructure In Repo

### Reverse Proxy

- `Caddyfile` handles local and production-style routing
- Next.js runs with `output: "standalone"`

### Containers

- backend
- frontend
- redis
- caddy

There is also a separate `openclaw/` compose file for the optional Telegram / agent integration.

## Cross-Cutting Concerns

### Caching

- Python in-memory stale-while-revalidate cache in `backend/app/services/cache.py`
- frontend request cache and deduplication in `frontend/src/lib/api.ts`

This is efficient for a single-node deployment. It is not enough by itself for safe horizontal scale.

### Background Work

Background tasks currently rely on in-process `asyncio.create_task(...)` patterns:

- movers warmup
- stale cache refresh
- personal bot scheduler

This is lightweight but fragile when processes restart, scale out, or crash mid-task.

### Auth

- AIdentity primary path
- Supabase fallback path
- browser cookie plus token parsing in frontend
- backend role / tenant resolution in dependencies

This is powerful, but operationally complex.

## Current Architectural Tensions

1. Feature breadth is ahead of platform hardening.
2. Product naming and runtime naming are not aligned.
3. Legacy and new workflow paths coexist without a clear deprecation boundary.
4. Persistence behavior is convenient but ambiguous.
5. Public and semi-public integration endpoints need stronger perimeter assumptions.

## Recommended Near-Term Architecture Direction

- Keep the monorepo for now
- Stabilize contracts before extracting anything
- Consolidate around one AI orchestration model
- Make persistence modes explicit instead of silently falling back
- Separate production-grade domains from lab-grade modules at both navigation and service levels

