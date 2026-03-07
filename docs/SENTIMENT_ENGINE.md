# Sentiment Engine

## Objective

MyInvestIA treats sentiment as a structured signal layer, not as a generic prompt.

The system prioritizes:

- per-item scoring
- source traceability
- temporal aggregation
- time decay
- momentum detection
- basic deduplication
- signal-vs-noise separation

The LLM is no longer the primary sentiment classifier.

## Main components

Core engine:

- `backend/app/services/sentiment_engine.py`

Compatibility service:

- `backend/app/services/enhanced_sentiment_service.py`

Deterministic single-asset sentiment:

- `backend/app/services/sentiment_service.py`

Normalization and scoring helpers:

- `backend/app/services/news_intelligence.py`

## Data flow

1. aggregate normalized articles and social items from the news provider layer
2. score each item with the existing normalization pipeline
3. deduplicate similar headlines
4. compute per-item effective weight using:
   - confidence
   - relevance
   - source reliability
   - source category
   - time decay
5. split news/blog flow from social flow
6. blend structured news, social pulse and optional AI narrative overlay into a unified score

## Unified output

`get_enhanced_sentiment(symbol)` returns, among other fields:

- `unified_score`
- `unified_label`
- `sources`
- `coverage_confidence`
- `news_momentum`
- `social_momentum`
- `recent_shift`
- `signal_to_noise`
- `noise_ratio`
- `temporal_aggregation`
- `items`
- `top_narratives`
- `source_breakdown`
- `divergences`
- `warnings`

## Time handling

The engine applies exponential time decay.

Config:

- `SENTIMENT_DECAY_HALF_LIFE_HOURS`

Default:

```env
SENTIMENT_DECAY_HALF_LIFE_HOURS=18
```

This makes fresh items matter more without fully discarding the recent multi-day context.

## Noise handling

The engine computes:

- `signal_to_noise`
- `noise_ratio`

These values are derived from item confidence, sentiment magnitude and effective weight.

If the engine detects thin coverage, single-source concentration or cross-source conflict, it emits warnings.

## Optional FinBERT

There is now an optional FinBERT adapter in `sentiment_engine.py`.

Config:

```env
SENTIMENT_FINBERT_ENABLED=false
```

Behavior:

- disabled by default
- never required for core operation
- used only as an optional base text classifier
- falls back to heuristic scoring when unavailable

This keeps the core free-first and operational without heavyweight ML dependencies.

## LLM role

The LLM is limited to explanation.

In `sentiment_service.py`:

- deterministic components compute the score and label
- the LLM may add a narrative overlay
- the LLM does not decide the final numeric score

## Test coverage

The sentiment engine has comprehensive test coverage:

- `test_sentiment_engine.py` covers:
  - aggregation functions (`_window_summary`)
  - time decay calculations
  - deduplication logic
  - scoring and weighting
  - momentum detection
  - cross-source divergence detection
  - warning generation for low confidence scenarios

Run tests with:

```bash
cd backend && python -m pytest tests/test_sentiment_engine.py -v
```

## Current limitations

- FinBERT is optional but not bundled as a mandatory runtime dependency
- temporal windows are practical heuristics, not a full event-study framework
- sentiment still depends on source coverage quality from upstream news/social feeds

## Recommended next steps

1. persist historical sentiment snapshots for drift and regime-change analysis
2. add stronger entity resolution for ambiguous tickers and multi-company headlines
3. add sector-aware and asset-class-aware sentiment calibration
