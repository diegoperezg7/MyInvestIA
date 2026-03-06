# Free Mode Operation

## Goal

MyInvestIA should remain usable without paid APIs as the architectural baseline.

This mode is designed for:

- local-first development
- personal use
- low-cost deployments
- graceful degradation when optional providers are unavailable

## Core free stack

### Market

- Yahoo Finance via `yfinance`

### Crypto

- CoinGecko public API
- Yahoo Finance fallback for `SYMBOL-USD`

### Macro

- FRED
- Yahoo Finance fallback for market proxy series

### Fundamentals

- Yahoo Finance

### Filings

- SEC EDGAR / `data.sec.gov`

### News

- GDELT
- RSS feed bundle
- Reddit public JSON fallback
- StockTwits public API
- best-effort Twitter/X via Nitter-based fallback

## Optional providers that stay non-core

These can improve coverage, but free mode must not depend on them:

- Finnhub
- Alpha Vantage
- Twelve Data
- NewsAPI
- Bloomberg

## Recommended `.env` for free mode

```env
DEBUG=false

MARKET_PROVIDER_ORDER=yfinance,alphavantage,finnhub,twelvedata,bloomberg
CRYPTO_PROVIDER_ORDER=coingecko,yfinance
MACRO_PROVIDER_ORDER=fred,yfinance
FUNDAMENTALS_PROVIDER_ORDER=yfinance
FILINGS_PROVIDER_ORDER=sec
NEWS_PROVIDER_ORDER=gdelt,rss,finnhub,reddit,stocktwits,newsapi,twitter

NEWS_MIXED_MODE=true
SEC_USER_AGENT=InvestIA/1.0 contact: support@example.com
WORLDBANK_COUNTRY=WLD
REDIS_URL=redis://localhost:6379
```

You can leave these empty in free mode:

- `ALPHAVANTAGE_API_KEY`
- `FINNHUB_API_KEY`
- `TWELVEDATA_API_KEY`
- `NEWSAPI_KEY`
- `BLOOMBERG_*`
- `COINGECKO_API_KEY`
- `FRED_API_KEY`

`COINGECKO_API_KEY` and `FRED_API_KEY` are optional enhancements, not hard requirements for the baseline architecture.

## Expected behavior in free mode

### Quotes and history

- Stocks and ETFs resolve through Yahoo Finance first.
- Crypto resolves through CoinGecko first and Yahoo Finance second.
- Commodity aliases are translated to futures tickers and resolved through the market chain.

### Macro

- Official/public FRED series are preferred when available.
- Yahoo Finance fills market-derived indicators when official series are missing or unsuitable.

### Filings

- SEC company map and submissions are cached and normalized.
- If a ticker is unknown to SEC, the service returns an empty but valid filings payload.

### News

- GDELT and RSS provide the baseline feed.
- Social feeds enrich the feed when reachable.
- Optional keyed providers expand coverage but do not own the core workflow.

## Free-mode limitations

- Yahoo Finance can be rate-limited or structurally inconsistent for some metadata.
- CoinGecko public endpoints can throttle under heavier usage.
- Reddit, StockTwits, and Nitter-based sources are inherently less stable than official APIs.
- Fundamentals coverage quality is acceptable for personal intelligence, but not a substitute for licensed institutional datasets.

## Operational guidance

1. Keep Redis enabled when possible to smooth out free-provider rate limits.
2. Set a valid `SEC_USER_AGENT`; SEC endpoints should not be called anonymously.
3. Treat optional paid providers as coverage enhancers, not dependencies.
4. Prefer adding open/public providers before introducing paid vendor lock-in.

## Exit criteria for future phases

Free mode should still work after future refactors. Any new provider integration must satisfy at least one of these conditions:

- it is free/public and improves reliability or coverage
- it is optional and isolated behind configuration
- it does not replace the free-first baseline as the default core path
