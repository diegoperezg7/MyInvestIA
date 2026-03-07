# Journal and Decision Log

## Objective

MyInvestIA provides a journal system to record investment decisions, reflections, and learning. The journal is designed to:

- Record decisions with context and reasoning
- Track the evolution of investment thesis over time
- Document lessons learned
- Enable post-mortem analysis of trades

## Integration with Thesis System

The journal is designed to work alongside the existing thesis system:

- **Decisions** can be created from thesis reviews
- **Observations** can be linked to specific symbols or thesis
- **Reflections** capture learning moments
- **Reviews** document post-analysis of past decisions

## Journal Entry Types

| Type | Description |
|------|-------------|
| `decision` | Investment decision (buy/sell/hold) with reasoning |
| `reflection` | Learning or insight from market observation |
| `lesson` | Specific lesson learned from a trade or thesis |
| `observation` | Market observation without immediate action |
| `review` | Post-analysis of a past decision or thesis |

## API Endpoints

### List Journal Entries

```
GET /api/v1/journal/?limit=50&entry_type=decision
```

Parameters:
- `limit`: Max entries to return (default: 50, max: 200)
- `entry_type`: Filter by type (optional)

### Get Journal Entry

```
GET /api/v1/journal/{entry_id}
```

### Create Journal Entry

```
POST /api/v1/journal/
```

```json
{
  "entry_type": "decision",
  "title": "Buy AAPL on breakout",
  "content": "RSI turning up, earnings beat, technical breakout above 180",
  "symbol": "AAPL",
  "tags": ["buy", "bull", "medium"],
  "thesis_id": "optional-thesis-id"
}
```

### Update Journal Entry

```
PATCH /api/v1/journal/{entry_id}
```

### Delete Journal Entry

```
DELETE /api/v1/journal/{entry_id}
```

### Record Outcome

```
POST /api/v1/journal/{entry_id}/outcome?result=success&notes=Price hit target
```

Result values: `success`, `failure`, `neutral`

### Create Decision from Thesis

```
POST /api/v1/journal/decision-from-thesis/{thesis_id}?decision=buy&reason=Breaking out
```

### Get Journal Statistics

```
GET /api/v1/journal/stats
```

Returns:
- Total entries
- Total decisions
- Entries by type
- Top symbols by journal activity

## Data Model

### Journal Entry

```python
{
    "id": "uuid",
    "entry_type": "decision|reflection|lesson|observation|review",
    "title": "string",
    "content": "string",
    "symbol": "string|null",
    "thesis_id": "string|null",
    "tags": ["string"],
    "mood": "string|null",
    "outcome": {
        "decision": "buy|sell|hold",
        "thesis_id": "string",
        "price_at_decision": "float|null",
        "conviction_at_decision": "float",
        "result": "success|failure|neutral",
        "notes": "string",
        "recorded_at": "iso_timestamp"
    },
    "created_at": "iso_timestamp",
    "updated_at": "iso_timestamp"
}
```

## Usage Patterns

### Recording a Decision

1. Review a thesis
2. Create a decision entry with:
   - The decision type (buy/sell/hold)
   - Reasoning
   - Current price (auto-captured if available)
   - Conviction level from thesis

### Post-Mortem Analysis

1. Find the original decision entry
2. Use `/outcome` endpoint to record:
   - Result (success/failure/neutral)
   - Notes on what happened
   - Lessons learned

### Daily Reflection

1. Create a `reflection` entry
2. Document market observations
3. Link to symbols if relevant

## Current Limitations

- Journal entries are stored in-memory (lost on restart unless Supabase is configured)
- No rich text formatting for content
- No export functionality yet

## Future Enhancements

1. Add export to CSV/JSON
2. Add search functionality
3. Add tagging and filtering
4. Add reminders for thesis review
5. Add correlation analysis between decisions and outcomes
