# Alerting

## Objective

MyInvestIA alerting focuses on structured, explainable alerts instead of generic notifications.

Each alert aims to answer:

- what changed
- why it matters
- what evidence supports it
- how confident the system is

## Main components

Rule engine:

- `backend/app/services/alert_scorer.py`

Delivery engine:

- `backend/app/services/alerts_engine.py`

Telegram delivery:

- `backend/app/services/telegram_service.py`

Schemas:

- `backend/app/schemas/alerting.py`

## Current alert families

### Asset-level alerts

- sharp price moves (configurable thresholds)
- RSI oversold / overbought (standard levels: 30/70, extreme: 20/80)
- multi-signal technical convergence (4+ signals aligned)
- technical breakout or breakdown confirmed by sentiment
- meaningful sentiment shift
- technical vs sentiment contradiction
- recent relevant filing (8-K, 10-Q, 10-K, S-1, etc.)

### Portfolio-level alerts

- excessive single-name concentration (>25%)
- excessive sector concentration (>40%)
- allocation drift versus equal-weight reference
- macro deterioration with concentrated exposure
- high-correlation cluster inside the portfolio

## Alert contract

Structured alerts now include:

- `title`
- `description`
- `reason`
- `reasoning`
- `evidence`
- `severity`
- `confidence`
- `suggested_action`
- `created_at`
- `sources`
- `warnings`

This contract is returned by:

- `GET /api/v1/alerts`
- `GET /api/v1/alerts/scan/{symbol}`
- `POST /api/v1/alerts/scan-and-notify`

## Evidence model

Each evidence item includes:

- `category`
- `summary`
- `value`
- `source`
- `timestamp`

This makes alert review and downstream summarization more traceable.

## Prioritization

Severity uses:

- `low`
- `medium`
- `high`
- `critical`

The engine sorts alerts by:

1. severity (critical > high > medium > low)
2. confidence (higher first)
3. title (alphabetically)

Telegram delivery thresholds remain configurable through `min_severity`.

## Notification behavior

Telegram/OpenClaw are preserved, but Telegram formatting now includes:

- clearer reason
- action
- confidence
- source list when available

This reduces low-information alert spam.

## Test coverage

The alert scorer has comprehensive test coverage:

- `test_alert_scorer.py` covers:
  - price move alerts (spikes and drops)
  - RSI alerts (oversold/overbought at multiple levels)
  - technical convergence alerts
  - contextual alerts (breakout/breakdown with sentiment)
  - sentiment shift alerts
  - contradictory signals alerts
  - filing alerts (form-based relevance)
  - portfolio concentration alerts
  - severity ordering and sorting
  - evidence and warning inclusion
  - graceful handling of missing data

Run tests with:

```bash
cd backend && python -m pytest tests/test_alert_scorer.py -v
```

## Design notes

- asset alerts are built from structured quote, technical, sentiment and filings context
- portfolio alerts are built from `portfolio_intelligence`
- macro-aware portfolio alerts only fire when macro deterioration and meaningful exposure coexist
- allocation drift currently uses equal-weight as a neutral reference, not a user-defined target

## Current limitations

- there is no user-defined target allocation model yet
- filing relevance is form-based and intentionally conservative
- anomaly detection is rule-based, not statistical anomaly modeling

## Recommended next steps

1. wire user-specific target allocations into alert generation
2. persist alert history and suppression windows to reduce repeat notifications
3. add sector- and factor-aware macro alert calibration
