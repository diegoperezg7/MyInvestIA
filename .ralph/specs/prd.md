# AI Investment Intelligence Dashboard

## Codename
MyInvestIA

## Version
1.0.0

## Environment
Production

---

## 1. Project Overview

### Description
AI Investment Intelligence Dashboard (MyInvestIA) is an AI-powered investment intelligence system that aggregates real-time market data, technical indicators, sentiment analysis, macroeconomic context, and portfolio tracking into a single explainable decision-support dashboard.

The system does NOT execute trades. Its purpose is to assist the user in deciding when to buy, sell, wait, or monitor assets by providing structured, explainable, and personalized insights.

### Primary Goal
Provide actionable, explainable, and timely investment insights without performing trade execution.

### Secondary Goals
- Improve investor situational awareness
- Reduce emotional and impulsive decision-making
- Centralize dispersed financial information
- Act as a personal market intelligence copilot

---

## 2. Product Philosophy

### Core Principles
- Decision support, not trading automation
- Explainability over raw signals
- Multi-source confirmation before alerts
- User retains full control at all times
- No black-box recommendations

### Legal Positioning
- This system does NOT provide financial advice
- No trade execution or broker integration
- Clear financial disclaimers are required
- All outputs must be probabilistic, contextual, and explainable

---

## 3. Target Users

### User Profiles

#### Retail Investor
- Needs: Market overview, alerts, simple explanations
- Low to medium risk tolerance

#### Advanced Investor
- Needs: Technical indicators, macro context, scenario analysis
- Medium to high risk tolerance

#### Crypto & ETF Focused Investor
- Needs: Multi-asset watchlists, high-volatility alerts
- Fast-changing market conditions

---

## 4. Core Modules

### 4.1 Main Dashboard
Central real-time overview of markets, portfolio, and intelligence signals.

#### Widgets
- Total portfolio value
- Daily, weekly, and monthly PnL
- Asset allocation by class
- Top gainers and losers
- Market-wide sentiment index
- Macro risk indicators
- Active alerts summary

#### Refresh Mode
Near real-time updates using WebSockets or polling.

---

### 4.2 Portfolio Management (Read-only)

#### Description
Read-only portfolio tracking and performance analysis. No brokerage connections.

#### Features
- Manual asset entry
- Average buy price tracking
- Unrealized and realized PnL
- Exposure by asset, sector, and currency
- Risk concentration indicators

#### Explicit Non-Features
- No order execution
- No broker API connections

---

### 4.3 Watchlists

#### Description
User-defined lists of assets continuously monitored by AI agents.

#### Supported Asset Types
- Stocks
- ETFs
- Commodities (Silver, Gold, Oil, etc.)
- Cryptocurrencies

#### Capabilities
- Unlimited watchlists
- Priority tagging
- Custom price and indicator thresholds
- AI-driven interest and relevance ranking

---

### 4.4 Market Data Analysis

#### Price Monitoring
Continuous monitoring of price movements and anomalies.

##### Metrics
- Percentage change
- Volatility
- Drawdown
- Volume spikes

#### Historical Analysis
- Supported timeframes: 1D, 1W, 1M, 3M, 6M, 1Y, 5Y
- Pattern detection and trend recognition

---

### 4.5 Technical Analysis

#### Indicators
- RSI
- MACD
- EMA and SMA
- Bollinger Bands
- Support and resistance levels
- Trend channels

#### Outputs
- Overbought and oversold conditions
- Trend direction
- Reversal probability (non-deterministic)

---

### 4.6 Sentiment Intelligence

#### Sources
- Financial news
- Social media (X, Reddit)
- Market headlines
- Opinion and analysis articles

#### Analysis Outputs
- Bullish / Bearish classification
- Sentiment score ranging from -1 to +1
- Narrative extraction
- Sentiment momentum over time

---

### 4.7 Macro Intelligence

#### Tracked Factors
- Interest rates
- Inflation data
- USD strength (DXY)
- Central bank announcements
- Major geopolitical events

#### Impact Model
Each macro factor must be explained in qualitative and quantitative terms for its potential impact on assets.

---

### 4.8 Alerts Engine

#### Description
AI-driven alerting system with reasoning and contextual explanation.

#### Alert Types
- Price anomalies
- Technical extremes
- Sentiment shifts
- Macro risk changes
- Multi-factor opportunity detection

#### Delivery Channels
- Telegram
- Email

#### Alert Payload Structure
- What happened
- Why it matters
- Confidence level
- Suggested action: Buy, Sell, Wait, Monitor (non-binding)

---

### 4.9 Chat Interface

#### Description
Conversational interface connected to live data, portfolio, and AI memory.

#### Capabilities
- Ask about specific assets
- Explain alerts and signals
- Compare assets
- Simulate what-if scenarios
- Summarize portfolio risks and exposure

---

## 5. AI Architecture

### Role of AI
Continuous intelligence, reasoning, and synthesis layer.

### Operation Mode
- Event-driven (price changes, news events)
- Periodic monitoring (scheduled scans)

---

### AI Agents

#### Market Watcher Agent
- Detects price movements, volatility spikes, and anomalies

#### Technical Analysis Agent
- Computes indicators and technical signals

#### Sentiment Agent
- Analyzes sentiment and narrative shifts from multiple sources

#### Macro Agent
- Assesses macroeconomic context and systemic risks

#### Portfolio Agent
- Evaluates user exposure and portfolio risk

#### Decision Synthesizer Agent
- Fuses all signals into a coherent, explainable summary

---

### AI Models

- Primary LLM: Claude (reasoning, explanations, synthesis)
- Secondary LLM: Gemini (optional alternative for analysis)
- Embedding Model: Used for news clustering, similarity search, and memory retrieval

---

## 6. Personalization and AI Memory

### User Personalization
- User financial profile
- Risk tolerance
- Investment horizon
- Financial goals
- Communication preferences

### AI Memory
- Persistent memory stored in database
- Tracks past alerts, decisions, interactions
- Used to adapt explanations and alert aggressiveness
- No deterministic predictions or promises

---

## 7. External Repositories Usage

### Bloomberg Terminal Reference
Repository: https://github.com/feremabraz/bloomberg-terminal

Usage:
- UI and UX inspiration
- Financial data visualization patterns
- Terminal-style dashboard concepts

Integration Type:
Conceptual and architectural reference only

---

### AI Trading Agent Reference
Repository: https://github.com/danilobatson/ai-trading-agent-gemini

Usage:
- Agent-based reasoning patterns
- Market analysis logic
- Signal synthesis approaches

Integration Type:
Code and logic adaptation without trading execution

---

## 8. Automation and Orchestration

### RALPH
- Role: Autonomous development, refactoring, testing, and iteration
- Input: This PRD (Markdown specification)
- Output: Full codebase

### Auto-Claude
- Role: Multi-agent orchestration and workflow management
- Responsibilities:
  - Trigger agents
  - Chain analyses
  - Schedule monitoring
  - Generate alerts

---

## 9. Technology Stack

### Frontend
- Framework: Next.js
- Styling: Tailwind CSS
- Charts: Recharts or Chart.js

### Backend
- Language: Python
- Framework: FastAPI
- Realtime: WebSockets

### Database
- Supabase (PostgreSQL)
- Row Level Security enabled
- Realtime subscriptions
- Persistent AI memory storage

### Cache
- Redis (optional, for performance optimization)

### Notifications
- Telegram Bot API
- Email service (future-ready)

---

## 10. Monitoring and Performance

### System Monitoring
- Agent execution health
- Latency
- Data freshness

### AI Monitoring
- Hallucination detection
- Consistency validation
- Alert accuracy tracking

---

## 11. Future Extensions

- Backtesting engine
- Advanced user risk profiles
- Strategy comparison tools
- Mobile application
- Premium subscription tiers

---

## 12. Success Metrics

- Alert precision greater than 70%
- High daily active user engagement
- High explainability and clarity feedback
