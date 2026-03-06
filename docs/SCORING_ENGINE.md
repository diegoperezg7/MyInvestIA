# Scoring Engine

## Objective

MyInvestIA now includes an explainable asset scoring engine centered on structured data and deterministic calculations.

The scoring engine is informational:

- it does not execute trades
- it does not delegate the decision to an LLM
- it produces traceable sub-scores and a weighted total score

## Entry point

Service:

- `backend/app/services/scoring_engine.py`

API:

- `GET /api/v1/market/score/{symbol}`

Optional query params:

- `asset_type`

Schema:

- `backend/app/schemas/scoring.py`

## Score structure

Each asset score is composed of:

- `fundamentals_score`
- `technical_score`
- `sentiment_score`
- `macro_score`
- `portfolio_fit_score`
- `total_score`

Each score component returns:

- numeric value
- human explanation
- structured inputs used
- warnings
- timestamp
- sources
- applied weight

The response also includes:

- `quote`
- `weights`
- `quant_overlay`
- `portfolio_context`
- `decision_support_only`
- `disclaimer`

## Scale

Scores are normalized to a 0-100 range:

- `0-24`: negative / very weak setup
- `25-39`: cautious
- `40-59`: neutral / mixed
- `60-74`: positive
- `75-100`: strong positive

## Weight configuration

Defined in:

- `backend/app/config.py`
- `backend/.env.example`

Current defaults:

```env
SCORE_WEIGHT_FUNDAMENTALS=0.25
SCORE_WEIGHT_TECHNICAL=0.25
SCORE_WEIGHT_SENTIMENT=0.15
SCORE_WEIGHT_MACRO=0.15
SCORE_WEIGHT_PORTFOLIO_FIT=0.20
```

Weights are normalized internally, so misconfigured totals do not break scoring.

## Component logic

### Fundamentals score

Uses:

- ROE
- profit margins
- debt to equity
- current ratio
- forward/trailing PE
- price to book
- revenue growth
- earnings growth

Intent:

- reward profitability, balance-sheet quality, and growth
- penalize stretched valuation and weak financial structure

### Technical score

Uses:

- existing technical indicators from `technical_analysis.py`
- quant factor bundle from `quant_scoring.py`
- trend
- momentum
- volume confirmation
- mean reversion
- support/resistance
- candlestick context

Intent:

- preserve the existing quant engine
- surface it in a more interpretable, 0-100 explainable score

### Sentiment score

Uses:

- `enhanced_sentiment_service`
- unified sentiment score
- coverage confidence
- source count

Intent:

- avoid raw headline counts as the primary driver
- weight sentiment only when coverage is credible

### Macro score

Uses:

- macro summary regime
- VIX level
- DXY change
- 10Y vs 13W spread

Intent:

- reflect whether the current macro regime is supportive or hostile for risk assets

### Portfolio fit score

Uses:

- current portfolio context when available
- candidate-to-portfolio correlation
- estimated volatility delta
- estimated Sharpe delta
- current concentration in the same asset

Intent:

- measure fit inside the user portfolio, not just standalone attractiveness
- reward diversification benefit
- penalize overlap and concentration

If no portfolio is available, the component stays neutral and returns an explicit warning.

## Data flow

1. load quote, 1Y history, fundamentals, enhanced sentiment and macro indicators in parallel
2. compute deterministic sub-scores
3. optionally simulate portfolio fit using the current user holdings
4. normalize weights and compute `total_score`
5. return component-level warnings, inputs and sources

## Source traceability

The engine preserves source references per component whenever the upstream payload exposes them.

Examples:

- fundamentals: `Yahoo Finance`
- macro: `FRED`
- sentiment: aggregated source names from enhanced sentiment inputs
- portfolio fit: `portfolio_intelligence`
- technicals: internal deterministic services (`technical_analysis`, `quant_scoring`)

## Output contract

High-level response shape:

```json
{
  "symbol": "AAPL",
  "fundamentals_score": {
    "value": 72.4,
    "explanation": "...",
    "inputs_used": {},
    "warnings": [],
    "sources": ["Yahoo Finance"],
    "weight_applied": 0.25
  },
  "total_score": {
    "value": 63.1,
    "inputs_used": {
      "rating": "positive"
    }
  },
  "decision_support_only": true
}
```

`quant_overlay` preserves the existing factor-based quant view so the new contract remains additive rather than replacing the prior engine.

## Design decisions

### Data first

The engine computes scores from structured inputs. An LLM may explain results elsewhere in the product, but it is not the scoring authority.

### Compatibility

The new scoring engine is additive. It does not remove the existing quant engine, signal summary, or prediction services.

### Traceability

Every component emits the data it used, warnings, and source references.

## Current limitations

- Fundamentals coverage quality depends heavily on Yahoo Finance.
- Macro scoring is still a generic risk-asset lens, not a sector-specific macro model.
- Portfolio fit is strongest when the user already has a populated portfolio and enough history for candidate simulation.
- Scores are current-state snapshots; they are not yet versioned or historized for drift analysis.

## Recommended next steps

1. Migrate research rankings to use the same explainable component contract.
2. Add sector-sensitive macro mappings so defensive, rate-sensitive, and commodity assets get tailored macro scoring.
3. Persist historical score snapshots for drift and validation monitoring.
