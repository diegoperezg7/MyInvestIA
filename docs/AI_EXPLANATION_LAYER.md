# AI Explanation Layer

## Objective

MyInvestIA uses AI as an explanation layer, not as a decision engine.

The AI should:

- summarize
- explain
- compare scenarios
- translate quant outputs into clear language

The AI should not:

- invent data
- hide uncertainty
- replace structured scoring
- act as an authority with unsupported recommendations

## Main components

Explanation service:

- `backend/app/services/ai_explanation_layer.py`

Schema:

- `backend/app/schemas/ai_explanation.py`

Main user-facing route:

- `GET /api/v1/chat/analyze/{symbol}`

## Data-first architecture

`/chat/analyze/{symbol}` now works like this:

1. compute structured asset scoring with `scoring_engine.py`
2. collect warnings and contradictory signals
3. derive confidence from quant confidence, component coverage and contradictions
4. ask the LLM only to explain the structured payload
5. fall back to a deterministic summary if no LLM is available

The LLM never sets the score itself.

## Output contract

The explanation route returns:

- `summary`
- `signal`
- `confidence`
- `confidence_label`
- `warnings`
- `contradictory_signals`
- `sources`
- `component_scores`
- `decision_support_only`

## Chat behavior

The streaming chat prompt in `backend/app/routers/chat.py` was also tightened.

The assistant is now instructed to:

- explain facts before giving options
- avoid invented data
- surface contradictory signals
- avoid hard imperative recommendations
- keep the output explicitly informational

## Briefing and recommendations

The current product surfaces for briefing and recommendations already route through `inbox_service.py`.

This phase enriches them with:

- `sources`
- `warnings`
- `contradictions`

That means the visible product layer can expose why an item exists and how solid the evidence is, without delegating that judgment to the LLM.

## Model usage

Priority:

1. structured analytics
2. Groq free models when available
3. Cerebras/OpenAI-compatible path as secondary fallback for explanation only
4. deterministic fallback if no LLM is available

## Test coverage

The AI explanation layer has comprehensive test coverage:

- `test_ai_explanation_layer.py` covers:
  - clipping functions
  - signal rating conversion
  - warning collection and deduplication
  - contradiction detection (technical/sentiment, fundamentals/macro, portfolio fit)
  - confidence calculation with quant confidence, components, contradictions and warnings
  - fallback summary generation with components, contradictions and warnings
  - end-to-end analysis with and without LLM

Run tests with:

```bash
cd backend && python -m pytest tests/test_ai_explanation_layer.py -v
```

## Current limitations

- generic streaming chat is still conversational and not yet fully tool-grounded turn by turn
- explanation summaries are constrained by the quality of the upstream structured payload
- the layer does not yet expose citation snippets per sentence

## Recommended next steps

1. add structured scenario comparison endpoints for portfolio what-if questions
2. expose source citations inline in frontend views
3. unify explanation payloads across prediction, research and chat surfaces
