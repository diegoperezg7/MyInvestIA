-- =============================================================================
-- InvestIA (ORACLE) - Initial Database Schema
-- Run this in the Supabase SQL Editor
-- =============================================================================

-- 1. HOLDINGS TABLE
-- Stores portfolio assets with average cost basis
CREATE TABLE IF NOT EXISTS holdings (
    symbol TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('stock', 'etf', 'crypto', 'commodity')),
    quantity REAL NOT NULL CHECK (quantity >= 0),
    avg_buy_price REAL NOT NULL CHECK (avg_buy_price >= 0),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE holdings IS 'Portfolio holdings with cost basis tracking';

-- 2. WATCHLISTS TABLE
-- User-defined lists for monitoring assets
CREATE TABLE IF NOT EXISTS watchlists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE watchlists IS 'User-defined asset monitoring lists';

-- 3. WATCHLIST ASSETS TABLE
-- Assets assigned to watchlists (many-to-many)
CREATE TABLE IF NOT EXISTS watchlist_assets (
    watchlist_id UUID REFERENCES watchlists(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('stock', 'etf', 'crypto', 'commodity')),
    PRIMARY KEY (watchlist_id, symbol)
);

COMMENT ON TABLE watchlist_assets IS 'Assets within watchlists (cascading delete)';

-- 4. AI MEMORY TABLE
-- Persistent AI context: past alerts, user preferences, interactions
CREATE TABLE IF NOT EXISTS ai_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_memory_category ON ai_memory(category);
CREATE INDEX IF NOT EXISTS idx_ai_memory_created_at ON ai_memory(created_at DESC);

COMMENT ON TABLE ai_memory IS 'AI memory for personalized insights and context';

-- =============================================================================
-- ROW LEVEL SECURITY (RLS)
-- Using anon key = public access (single-user app)
-- Enable RLS but allow full access via anon key for now
-- =============================================================================

ALTER TABLE holdings ENABLE ROW LEVEL SECURITY;
ALTER TABLE watchlists ENABLE ROW LEVEL SECURITY;
ALTER TABLE watchlist_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_memory ENABLE ROW LEVEL SECURITY;

-- Holdings policies
CREATE POLICY "Allow full access to holdings" ON holdings
    FOR ALL USING (true) WITH CHECK (true);

-- Watchlists policies
CREATE POLICY "Allow full access to watchlists" ON watchlists
    FOR ALL USING (true) WITH CHECK (true);

-- Watchlist assets policies
CREATE POLICY "Allow full access to watchlist_assets" ON watchlist_assets
    FOR ALL USING (true) WITH CHECK (true);

-- AI memory policies
CREATE POLICY "Allow full access to ai_memory" ON ai_memory
    FOR ALL USING (true) WITH CHECK (true);

-- =============================================================================
-- SEED DATA (optional starter watchlist)
-- =============================================================================

-- Create a default watchlist with popular assets
INSERT INTO watchlists (name) VALUES ('Top Tech & Crypto')
ON CONFLICT DO NOTHING;

-- Insert some starter assets into the default watchlist
DO $$
DECLARE
    wl_id UUID;
BEGIN
    SELECT id INTO wl_id FROM watchlists WHERE name = 'Top Tech & Crypto' LIMIT 1;
    IF wl_id IS NOT NULL THEN
        INSERT INTO watchlist_assets (watchlist_id, symbol, name, type) VALUES
            (wl_id, 'AAPL', 'Apple Inc.', 'stock'),
            (wl_id, 'MSFT', 'Microsoft Corp.', 'stock'),
            (wl_id, 'NVDA', 'NVIDIA Corp.', 'stock'),
            (wl_id, 'GOOGL', 'Alphabet Inc.', 'stock'),
            (wl_id, 'BTC', 'Bitcoin', 'crypto'),
            (wl_id, 'ETH', 'Ethereum', 'crypto'),
            (wl_id, 'SPY', 'SPDR S&P 500 ETF', 'etf'),
            (wl_id, 'QQQ', 'Invesco QQQ Trust', 'etf'),
            (wl_id, 'GLD', 'SPDR Gold Shares', 'commodity')
        ON CONFLICT DO NOTHING;
    END IF;
END $$;
