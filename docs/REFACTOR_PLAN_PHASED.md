# Phased Refactor Plan

This plan is intentionally incremental. The goal is to reduce risk while preserving the current feature surface.

## Rules For The Refactor

- No large rewrite before the baseline is stable
- Prefer contract alignment before structural moves
- Preserve working product flows while removing ambiguity
- Make persistence and security behavior explicit
- Land changes in small, verifiable batches

## Phase 0: Baseline Stabilization

Goal: make the repository reliably testable, buildable, and understandable before deeper refactors.

Scope:
- fix backend local environment portability
- commit a non-interactive frontend lint setup
- align README and env documentation with actual runtime
- document active routes, providers, and persistence modes
- create a lightweight validation checklist for local work and CI

Exit criteria:
- backend tests can be invoked from the current repo path
- frontend lint does not prompt interactively
- docs reflect current AI, auth, and API reality

## Phase 1: Contract And Naming Alignment

Goal: reduce cognitive load and remove obvious drift.

Scope:
- standardize product naming across:
  - package names
  - health payloads
  - local storage keys
  - user-facing labels
- define the canonical env contract
- define the canonical API inventory
- mark legacy aliases explicitly in code and docs

Exit criteria:
- one product naming vocabulary
- one env variable reference
- one route inventory checked against code

## Phase 2: Backend Domain Consolidation

Goal: clarify ownership boundaries without changing the deployment model.

Scope:
- group backend services by domain:
  - market
  - workflow
  - portfolio
  - integrations
  - AI
- separate legacy AI flows from active flows
- isolate lab modules from core portfolio intelligence
- reduce cross-service imports where routers call into multiple unrelated service families

Exit criteria:
- each router has a narrow service dependency surface
- legacy recommendation / briefing paths have a defined deprecation path
- core domains have clearer boundaries

## Phase 3: Persistence And Auth Hardening

Goal: remove ambiguous runtime behavior and harden identity flows.

Scope:
- make store mode explicit at startup
- remove silent in-memory fallback for features that must persist
- add or finish workflow-oriented Supabase tables if they are intended to be durable
- harden auth cookie and token strategy
- review and protect OpenClaw endpoints according to deployment intent

Exit criteria:
- workflow data persistence is deterministic
- auth behavior is documented and environment-aware
- public integration endpoints have an explicit security posture

## Phase 4: Frontend Modularization

Goal: reduce component complexity and improve maintainability.

Scope:
- split large views:
  - settings
  - chat-related surfaces
  - complex dashboard panels
- centralize repeated fetch / polling patterns
- reduce ad hoc local state where reducer-based state fits better
- keep the section / tab shell, but remove obsolete compatibility paths once safe

Exit criteria:
- largest views are decomposed into focused subcomponents
- repeated polling and SSE behavior is centralized
- legacy shell mapping is reduced or retired

## Phase 5: Scalability And Observability

Goal: prepare the system for higher traffic and more reliable operations.

Scope:
- move critical cache or job semantics out of process-local memory where needed
- introduce request tracing and provider failure visibility
- add explicit provider timeouts, retry policies, and circuit-breaking rules
- review single-worker assumptions and background scheduler ownership

Exit criteria:
- provider failures are observable
- background jobs have clear ownership
- horizontal-scaling blockers are documented or reduced

## Phase 6: Feature Hardening And Productization

Goal: convert broad capability into a cleaner, more trustworthy product surface.

Scope:
- create a provider maturity matrix
- hide or re-label low-maturity integrations
- add tests around:
  - auth
  - persistence
  - workflow assembly
  - provider fallback behavior
- separate experimental lab tooling from standard investor workflows in the UI

Exit criteria:
- user-facing modules have a clear maturity level
- core flows are covered by regression tests
- experimental features no longer blur the primary product path

## Safe Quick Wins Before Any Deep Refactor

- fix README and env drift
- fix backend venv portability
- add repo lint configuration
- rename remaining Oracle-specific identifiers where impact is local and obvious
- add explicit warnings when persistence falls back to memory
- document which connection providers are truly production-ready

## Recommended Execution Order

1. Phase 0
2. Phase 1
3. Phase 3
4. Phase 2
5. Phase 4
6. Phase 5
7. Phase 6

Reasoning:
- tooling and contracts must stabilize before structural consolidation
- persistence and security ambiguity is more dangerous than imperfect folder layout
- frontend cleanup is easier after backend contracts stop shifting

