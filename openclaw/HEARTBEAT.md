# MyInvestIA Heartbeat Monitoring Rules

Every 30 minutes during market hours (9:30 AM - 4:00 PM ET, Mon-Fri), check these conditions and alert the user if any trigger.

## Monitoring Rules

### 1. Portfolio P&L Check
- Fetch `GET http://host.docker.internal:8000/api/v1/portfolio/`
- If `daily_pnl_percent` < -3%, alert with MEDIUM severity
- If `daily_pnl_percent` < -5%, alert with HIGH severity
- If any single holding has `unrealized_pnl_percent` < -7%, alert on that symbol

### 2. Macro Environment Shift
- Fetch `GET http://host.docker.internal:8000/api/v1/market/macro`
- If VIX > 25, alert "Elevated volatility — review positions"
- If VIX > 30, alert HIGH "Extreme volatility — risk-off environment"
- If 10Y yield changes > 5% in a session, alert about rate impact

### 3. Price Alerts (Portfolio Holdings)
- For each holding in the portfolio, check the quote
- If any holding moves > 5% in a single day, alert
- If any holding moves > 8%, alert with HIGH severity

### 4. Technical Signal Changes
- Once per day (at market close), fetch signal summaries for portfolio holdings
- If a holding switches from bullish to bearish (or vice versa), alert
- Focus on multi-factor convergence signals (4+ indicators aligned)

## Silent Rules

Stay silent if:
- Markets are closed (weekends, holidays, after hours)
- All portfolio changes are within -2% to +2%
- VIX is between 12-20 (normal range)
- No technical signal changes detected

Only alert when something meaningful has changed. The user does not want noise.

## Daily Summary

At 4:30 PM ET (after market close), send a brief daily summary:
- Portfolio P&L for the day
- Biggest movers in holdings
- Any notable macro shifts
- Active alerts/signals
Keep it under 10 lines.
