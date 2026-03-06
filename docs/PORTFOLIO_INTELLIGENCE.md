# Portfolio Intelligence

## Objective

MyInvestIA now exposes a structured portfolio intelligence layer focused on analysis, risk context and informative suggestions.

It is explicitly non-executive:

- it does not place orders
- it does not auto-rebalance
- it does not present outputs as financial advice

## Entry points

Service:

- `backend/app/services/portfolio_intelligence.py`

API:

- `GET /api/v1/portfolio/intelligence`

Optional query params:

- `candidate_symbol`
- `candidate_type`
- `candidate_weight`

Schema:

- `backend/app/schemas/portfolio_intelligence.py`

## What it computes

### Allocation and concentration

- current allocation by asset
- concentration by asset
- concentration by sector
- concentration by currency
- HHI-style concentration score
- exposure alerts when weights breach simple thresholds

### Risk and portfolio metrics

- annualized return
- annualized volatility
- Sharpe ratio
- Sortino ratio
- max drawdown
- beta vs `SPY`
- historical VaR 95%
- historical CVaR 95%
- rolling 21d and 63d returns
- rolling 21d and 63d volatility
- contribution to risk

### Diversification diagnostics

- correlation matrix
- average pairwise correlation
- list of high-correlation pairs

### Informative strategy snapshots

- `equal_weight`
- `inverse_volatility`
- `mean_variance`
- `risk_parity`

These are comparison views, not execution plans.

### Candidate impact simulation

When `candidate_symbol` is provided, the service simulates the effect of adding a small position to the current portfolio and returns:

- correlation to the existing portfolio
- volatility delta
- Sharpe delta
- max drawdown delta
- sector exposure before/after
- plain-language notes

## Data flow

1. load current holdings
2. fetch quote, 1Y history and fundamentals context for each holding
3. normalize metadata such as sector and currency
4. align return series across holdings
5. compute portfolio-level risk, concentration and correlation outputs
6. generate strategy comparison snapshots
7. optionally simulate candidate impact

## Formula notes

- returns are derived from aligned close-price histories
- annualization assumes `252` trading days
- Sharpe and Sortino use a configurable annual risk-free rate, default `0.02`
- VaR and CVaR are historical, non-parametric estimates
- beta is computed versus aligned benchmark returns
- contribution to risk is derived from portfolio weights and the annualized covariance matrix

## Current defaults and safeguards

- candidate weight is clamped to a conservative range inside the service
- if histories cannot be aligned, the response degrades gracefully and emits warnings
- missing sectors or currencies fall back to deterministic placeholders instead of failing
- suggestions are heuristic and intentionally phrased as review prompts, not instructions

## Current limitations

- the benchmark is currently fixed to `SPY`
- history depth and quality depend on free market-data availability
- mean-variance and risk-parity allocations are lightweight in-house heuristics, not full optimizers
- optional optimizers such as PyPortfolioOpt or Riskfolio-Lib are not integrated yet to avoid premature dependency and operational complexity
- covariance and correlation are sample-statistics based and should be treated as approximate

## Recommended next steps

1. expose benchmark selection and risk-free configuration at the API layer
2. add optional optimizer adapters behind a clean interface
3. persist portfolio analytics snapshots for trend comparison
4. extend factor-aware attribution and scenario stress testing
