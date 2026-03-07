# Roadmap and Next Steps

## Vision

MyInvestIA is an AI-powered investment research platform that combines:
- Structured quantitative analysis
- Sentiment analysis with source tracking
- Explainable AI recommendations
- Decision logging and thesis tracking

## Current State (v1.0)

### Completed Features

1. **Sentiment Engine**
   - Per-item scoring
   - Multi-source aggregation
   - Time decay
   - Momentum detection
   - Optional FinBERT integration

2. **Alerting System**
   - Technical alerts (RSI, convergence)
   - Sentiment shift alerts
   - Portfolio concentration alerts
   - Macro-aware alerts
   - Structured evidence model

3. **AI Explanation Layer**
   - Data-first architecture
   - Confidence scoring
   - Contradiction detection
   - Source tracking

4. **Thesis System**
   - Thesis creation and tracking
   - Review workflow
   - Event history
   - Invalidation conditions

5. **Journal/Decision Log**
   - Decision recording
   - Outcome tracking
   - Reflection entries

## Roadmap

### Phase 1: Hardening (Q1 2026)

- [ ] Fix type errors in store.py (SupabaseStore return type)
- [ ] Add proper error boundaries in React
- [ ] Improve loading states across components
- [ ] Add empty states for all lists
- [ ] Complete SupabaseStore implementation for journal

### Phase 2: Data Persistence (Q1-Q2 2026)

- [ ] Complete SupabaseStore for all data types
- [ ] Add data migration scripts
- [ ] Implement backup/restore
- [ ] Add data export functionality

### Phase 3: Enhanced Analytics (Q2 2026)

- [ ] Add historical sentiment tracking
- [ ] Implement regime detection
- [ ] Add correlation matrix visualization
- [ ] Improve macro indicators

### Phase 4: Advanced Features (Q2-Q3 2026)

- [ ] Portfolio optimization suggestions
- [ ] Risk modeling (VaR, drawdown)
- [ ] Backtesting framework
- [ ] Strategy comparison

### Phase 5: Community & Enterprise (Q3 2026)

- [ ] Multi-tenant support improvements
- [ ] Team collaboration features
- [ ] Custom alert rules UI
- [ ] API for third-party integrations

## Known Limitations

1. **In-Memory Store**: Data is lost on restart (use Supabase for persistence)
2. **Single Provider**: Currently relies on free tier data providers
3. **Limited Backtesting**: No historical strategy testing
4. **No Paper Trading Integration**: Simulated trading exists but not connected to real execution

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Priority Order for V2

1. **Data Persistence**: Supabase integration
2. **Error Handling**: Graceful degradation
3. **Mobile UX**: Responsive improvements
4. **Advanced Analytics**: Regime detection, correlation
5. **Community Features**: Teams, sharing
