# Current State Audit

Date: 2026-03-06
Scope: repository-only audit and preparation pass. No external services, containers, or host-level configuration were modified.

Backup created before edits:
- Backup branch: `codex/backup/pre-audit-myinvestia-20260306-2326`
- Local snapshot: `artifacts/backups/pre-audit-myinvestia-20260306-2326`

## Executive Summary

MyInvestIA is a feature-rich monorepo with a clear product direction: investment intelligence, portfolio tracking, alerts, news, workflow-driven recommendations, and AI-assisted research. The repository already has meaningful modular separation between frontend views, FastAPI routers, schemas, and backend services.

The main issue is not lack of capability; it is architectural drift. The codebase is currently in a transition state where legacy paths and newer workflow-oriented paths coexist. Naming, documentation, and runtime assumptions have not fully caught up with that transition. This increases delivery risk, onboarding cost, and the chance of silent regressions.

## Snapshot Of The Repo

- Frontend: Next.js 15, React 19, TypeScript, Tailwind CSS 4
- Backend: FastAPI, Pydantic v2, Python-based service layer
- Infra in repo: Caddy, Redis, Docker Compose, optional OpenClaw side integration
- Persistence: `InMemoryStore` by default, `SupabaseStore` when configured
- Current footprint observed in code:
  - 23 backend routers
  - 61 top-level backend services
  - 12 backend schemas
  - 19 backend test files
  - 24 frontend view components
  - 9 frontend hooks

## What Is Working Well

- Backend is organized around routers plus services, which is a reasonable boundary for future extraction.
- Frontend has moved toward a section-and-tab shell model instead of a flat page list. That is a better foundation for a complex product.
- There is meaningful domain coverage already implemented:
  - market data
  - portfolio
  - watchlists
  - alerts
  - chat
  - news
  - research
  - inbox / theses workflow
  - external account connections
  - notifications / Telegram bot
- The repo includes tests instead of being a code-only prototype.
- Frontend production build succeeds.
- Backend source and tests pass syntax compilation via `python3 -m compileall`.
- React Doctor result is strong for the current frontend baseline: `96/100`.

## What Is Wrong Or Risky

### P0 Baseline And Tooling Stability

- The working tree was already heavily modified before this audit started. That means the repository is a moving target and changes must remain tightly scoped.
- Backend test execution is not portable in the current repo state:
  - `backend/.venv/bin/pytest` points to an old absolute interpreter path: `/Users/darce/ai-investment-dashboard/backend/.venv/bin/python3`
  - this blocks normal local test execution from the current repository path
- Frontend linting is not CI-friendly yet:
  - `npm run lint` opens interactive ESLint setup instead of running a deterministic check
- Direct `tsc --noEmit` is also not fully clean as a standalone check because `tsconfig.json` includes `.next/types/**`; without a generated `.next` tree the command fails even though `next build` succeeds afterward

### P1 Architecture Drift

- README and code diverged materially:
  - README still references Mistral in multiple sections
  - runtime code uses both `groq_service` and `ai_service` (Cerebras/OpenAI-compatible path)
  - newer modules such as inbox, theses, research, and connections were missing or under-described
- Product naming is inconsistent:
  - repo is `MyInvestIA`
  - backend health response still reports `oracle-api`
  - frontend package name is still `oracle-dashboard`
  - several frontend stores and keys still use `oracle-*`
- There are visible legacy-to-new-architecture compatibility layers:
  - `LEGACY_VIEW_TO_SHELL` in the frontend shell state
  - legacy briefing / recommendation services still feed the new inbox assembly
  - both `ai_service` and `groq_service` remain active in different flows

### P1 Persistence And Data Integrity Risk

- Store selection is implicit and broad:
  - if `SUPABASE_URL` and `SUPABASE_KEY` exist, the app switches to `SupabaseStore`
  - this decision is made globally in `backend/app/services/store.py`
- `SupabaseStore` contains workflow fallbacks for inbox, theses, alert rules, research screens, and snapshots using in-memory structures when Supabase operations fail
- This is convenient for continuity, but risky for correctness because persistence failures can silently degrade into partial in-memory behavior
- Multi-tenancy exists in settings and some store methods, but is still only partially realized operationally

### P1 Security And Auth Risk

- Auth is more complex than it looks:
  - AIdentity first
  - Supabase JWT fallback
  - optional automatic Supabase user creation
- Frontend auth cookies are coupled to a hardcoded domain in `frontend/src/lib/auth.ts`:
  - `.darc3.com`
- Access token is intentionally JS-readable, which simplifies SSO but increases browser-side exposure compared with fully HttpOnly token handling
- OpenClaw router is intentionally unauthenticated and exposes:
  - wake
  - send-alert
  - callback
  - public quote
  - public macro
- That may be acceptable in a private environment, but it is a clear hardening target before wider deployment

### P1 Scalability Risk

- Current runtime favors a single-node, low-worker deployment model:
  - in-memory cache
  - background `asyncio.create_task(...)` refreshes
  - in-memory fallback storage
  - startup warmup task
- `docker-compose.yml` pins backend to one worker, which likely avoids cache and memory consistency issues rather than solving them
- News, research, and sentiment pipelines fan out to many external providers. This is useful, but without stronger rate-limit management and observability it will become fragile under load

### P2 Maintainability Risk

- Some frontend components are already too large:
  - `SettingsView` flagged by React Doctor at 642 lines
  - `ChatPanel` and other screens hold many `useState` values and related transitions
- Some provider claims exceed implementation maturity:
  - several broker providers are listed even though the descriptions themselves say "no public API"
  - wallet support is EVM-focused and explicitly marks some flows as coming soon
- Empty top-level directories `app/` and `src/` look residual and add noise
- The repo mixes real production concerns with lab features (RL trading, paper trading, OpenClaw, quant research) inside the same service and navigation surface

## What Seems Extra Or Duplicated

- Dual AI service paths:
  - `groq_service` for active chat and some live flows
  - `ai_service` for batch analysis, legacy recommendations, briefing, and some sentiment/news flows
- Dual workflow generation:
  - older recommendation / briefing services
  - newer inbox-centric workflow assembly
- Dual naming vocabulary:
  - MyInvestIA
  - InvestIA
  - Oracle / oracle-dashboard / oracle-* local storage keys
- Top-level empty directories:
  - `app/`
  - `src/`

## What Is Missing

- Deterministic backend developer environment from the repo root
- Non-interactive frontend lint configuration committed to the repository
- A single documented source of truth for:
  - active AI providers
  - active routes
  - persistence behavior
  - security assumptions
- Better observability around provider failures, retries, fallback activation, and background tasks
- Clear maturity boundaries between production features and experimental lab features

## Fragile Pieces

- Auth bridge between AIdentity and Supabase user identity
- Silent persistence fallback paths in `SupabaseStore`
- OpenClaw public endpoints if exposed beyond a trusted perimeter
- Large cross-provider aggregation flows:
  - news
  - enhanced sentiment
  - research ranking
  - inbox assembly
- Frontend shell migration layer from legacy views to new sections/tabs

## Pieces To Touch First

1. Tooling baseline: backend venv portability, frontend lint configuration, stable local validation commands
2. Naming and contract drift: README, env contracts, API inventory, package and app naming cleanup
3. Persistence semantics: remove or strictly surface silent in-memory fallbacks for persisted workflow objects
4. Auth and security hardening: cookie strategy, OpenClaw exposure, secret handling assumptions
5. Frontend modularization: break down large screens and centralize repeated state flows

## Validation Performed

- `python3 -m compileall backend/app backend/tests`
  - Result: success
- `./node_modules/.bin/next build` in `frontend/`
  - Result: success
- `npx -y react-doctor@latest . --verbose --diff` in `frontend/`
  - Result: `96/100`
  - Main warnings:
    - repeated `setState` in a single `useEffect`
    - large multi-state components
    - index keys in lists
    - `recharts` weight on an eagerly loaded panel
- `npm run lint` in `frontend/`
  - Result: blocked by interactive ESLint setup prompt
- `./.venv/bin/pytest -q` in `backend/`
  - Result: failed because the local venv wrapper references an old absolute path
- `./node_modules/.bin/tsc --noEmit` in `frontend/`
  - Result: fails before build because `.next/types/**` is part of `tsconfig.json` includes

## Safe Fixes Applied In This Phase

- Added the audit, architecture, and phased refactor documents under `docs/`
- Updated `README.md` to align obvious documentation drift with the current AI providers and API surface

