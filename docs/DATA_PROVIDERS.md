# Data Providers

## Objective

MyInvestIA now uses a normalized provider layer in `backend/app/services/data_providers/` to separate external data access from business logic.

This layer standardizes:

- provider interfaces
- fallback priority
- normalization rules
- source metadata
- error handling
- provider configuration

## Domains

### Market data

File: `backend/app/services/data_providers/market.py`

Default order:

- `yfinance`
- `alphavantage`
- `finnhub`
- `twelvedata`
- `bloomberg`

Notes:

- Yahoo Finance is the primary free provider.
- Bloomberg stays optional and isolated.
- Batch quote support is used when available.

### Crypto data

File: `backend/app/services/data_providers/crypto.py`

Default order:

- `coingecko`
- `yfinance`

Notes:

- CoinGecko is the primary free crypto provider.
- Yahoo Finance acts as a fallback using `SYMBOL-USD`.
- Market chart responses are normalized for downstream RL and chart consumers.

### Macro data

File: `backend/app/services/data_providers/macro.py`

Default order:

- `fred`
- `yfinance`

Notes:

- FRED is used first for official/public macro series.
- Yahoo Finance remains the fallback for market-derived proxies such as VIX, DXY, rates, and commodity proxies.
- Macro providers merge on ticker, keeping the first successful source per indicator.

### Fundamentals

File: `backend/app/services/data_providers/fundamentals.py`

Default order:

- `yfinance`

Notes:

- Current normalized fundamentals provider is Yahoo Finance.
- Peer comparison and growth metrics remain inside the normalized provider implementation.

### Filings

File: `backend/app/services/data_providers/filings.py`

Default order:

- `sec`

Notes:

- Uses SEC EDGAR / `data.sec.gov`
- Includes normalized filing URLs, accession numbers, filing dates, and filing forms

### News and social

File: `backend/app/services/data_providers/news.py`

Default order:

- `gdelt`
- `rss`
- `finnhub`
- `reddit`
- `stocktwits`
- `newsapi`
- `twitter`

Notes:

- This domain aggregates rather than first-success fallback, because multiple concurrent sources are desirable.
- Free/no-key sources are prioritized in the default ordering.
- Optional API-key sources remain non-core.

## Provider chains

### Fallback chain

Used by:

- market
- crypto
- fundamentals
- filings

Behavior:

- orders providers by configured priority
- skips disabled/unconfigured providers
- tries providers in sequence
- returns the first valid normalized payload
- logs provider failures without breaking the caller

### Aggregating chain

Used by:

- news

Behavior:

- fetches from all active providers
- tolerates per-provider errors
- returns flattened normalized items
- lets downstream logic deduplicate, cluster narratives, and score sentiment

## Normalization rules

Implemented in `backend/app/services/data_providers/normalization.py`.

### Symbols

- uppercased
- stripped
- mapped consistently for crypto and commodities

### Timestamps

- converted to UTC ISO strings where applicable
- unix timestamps normalized for feed-like payloads

### Quote payload

Normalized fields include:

- `symbol`
- `name`
- `price`
- `change_percent`
- `volume`
- `previous_close`
- `market_cap`
- `currency`
- `source`
- `source_provider`
- `retrieval_mode`
- `as_of`

### History payload

Normalized fields include:

- `date`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `source_provider`
- `retrieval_mode`

### Macro payload

Normalized fields include:

- `name`
- `ticker`
- `value`
- `change_percent`
- `previous_close`
- `trend`
- `impact_description`
- `category`
- `source`
- `source_provider`
- `retrieval_mode`
- `as_of`

### Fundamentals and filings payloads

Both domains are normalized to include source metadata and normalized timestamps so downstream services do not need provider-specific branching.

## Error-handling model

- provider exceptions are logged and isolated
- chains continue to the next provider when possible
- empty lists and `None` are used as safe fallbacks
- compatibility services keep historical public method names

## Configuration

Relevant settings in `backend/app/config.py`:

- `MARKET_PROVIDER_ORDER`
- `CRYPTO_PROVIDER_ORDER`
- `MACRO_PROVIDER_ORDER`
- `FUNDAMENTALS_PROVIDER_ORDER`
- `FILINGS_PROVIDER_ORDER`
- `NEWS_PROVIDER_ORDER`
- `COINGECKO_API_KEY`
- `FRED_API_KEY`
- `SEC_USER_AGENT`
- optional fallback keys such as `FINNHUB_API_KEY`, `ALPHAVANTAGE_API_KEY`, `TWELVEDATA_API_KEY`, `NEWSAPI_KEY`

Example free-first operation:

```env
MARKET_PROVIDER_ORDER=yfinance,alphavantage,finnhub,twelvedata,bloomberg
CRYPTO_PROVIDER_ORDER=coingecko,yfinance
MACRO_PROVIDER_ORDER=fred,yfinance
FUNDAMENTALS_PROVIDER_ORDER=yfinance
FILINGS_PROVIDER_ORDER=sec
NEWS_PROVIDER_ORDER=gdelt,rss,finnhub,reddit,stocktwits,newsapi,twitter
```

## Compatibility layer mapping

Legacy service entrypoints now delegate to the provider layer:

- `market_data_service` -> market + crypto provider chains
- `provider_chain` -> market provider chain compatibility facade
- `get_all_macro_indicators` -> macro provider chain
- `get_fundamentals` -> fundamentals provider chain
- `get_company_filings` -> filings provider chain
- `get_ai_analyzed_feed` -> news provider aggregator + AI enrichment

## Pending extensions

- Add optional ccxt-based crypto execution-independent market reads where useful.
- Add optional public fundamentals/filings enrichers when they improve quality without creating vendor lock-in.
- Add explicit contract tests for normalized payloads and provider-order parsing.
