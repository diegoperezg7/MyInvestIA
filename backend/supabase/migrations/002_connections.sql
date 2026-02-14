-- =============================================================================
-- MyInvestIA - External Connections Schema
-- Adds support for exchange, wallet, broker, and prediction market connections
-- =============================================================================

-- 1. CONNECTIONS TABLE
-- Stores external account connections (exchanges, wallets, brokers, prediction markets)
CREATE TABLE IF NOT EXISTS connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type TEXT NOT NULL CHECK (type IN ('exchange', 'wallet', 'broker', 'prediction')),
    provider TEXT NOT NULL,
    label TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'error', 'disconnected')),
    credentials_encrypted TEXT,
    wallet_address TEXT,
    chain TEXT,
    last_sync_at TIMESTAMPTZ,
    last_sync_status TEXT,
    last_sync_error TEXT,
    sync_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_connections_type ON connections(type);
CREATE INDEX IF NOT EXISTS idx_connections_provider ON connections(provider);
CREATE INDEX IF NOT EXISTS idx_connections_status ON connections(status);

COMMENT ON TABLE connections IS 'External account connections (exchanges, wallets, brokers)';

-- 2. SYNC HISTORY TABLE
-- Logs each synchronization attempt for auditing
CREATE TABLE IF NOT EXISTS sync_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_id UUID NOT NULL REFERENCES connections(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'success', 'partial', 'failed')),
    holdings_synced INTEGER DEFAULT 0,
    holdings_added INTEGER DEFAULT 0,
    holdings_updated INTEGER DEFAULT 0,
    holdings_removed INTEGER DEFAULT 0,
    error_message TEXT,
    details JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sync_history_connection ON sync_history(connection_id);
CREATE INDEX IF NOT EXISTS idx_sync_history_started ON sync_history(started_at DESC);

COMMENT ON TABLE sync_history IS 'Synchronization history for external connections';

-- 3. ALTER HOLDINGS TABLE
-- Add columns for tracking source of holdings (manual vs synced)

-- Add id column as new PK
ALTER TABLE holdings ADD COLUMN IF NOT EXISTS id UUID DEFAULT gen_random_uuid();

-- Add source tracking
ALTER TABLE holdings ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'manual';
ALTER TABLE holdings ADD COLUMN IF NOT EXISTS connection_id UUID REFERENCES connections(id) ON DELETE SET NULL;
ALTER TABLE holdings ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Drop old PK constraint and add new one
-- Note: symbol remains unique for manual holdings via partial index
ALTER TABLE holdings DROP CONSTRAINT IF EXISTS holdings_pkey;
ALTER TABLE holdings ADD PRIMARY KEY (id);

-- Update type check to include 'prediction'
ALTER TABLE holdings DROP CONSTRAINT IF EXISTS holdings_type_check;
ALTER TABLE holdings ADD CONSTRAINT holdings_type_check
    CHECK (type IN ('stock', 'etf', 'crypto', 'commodity', 'prediction'));

-- Partial unique indexes for backwards compatibility
CREATE UNIQUE INDEX IF NOT EXISTS idx_holdings_manual_symbol
    ON holdings(symbol) WHERE source = 'manual';

CREATE UNIQUE INDEX IF NOT EXISTS idx_holdings_synced_symbol
    ON holdings(symbol, connection_id) WHERE source != 'manual';

CREATE INDEX IF NOT EXISTS idx_holdings_source ON holdings(source);
CREATE INDEX IF NOT EXISTS idx_holdings_connection ON holdings(connection_id);

-- 4. ROW LEVEL SECURITY
ALTER TABLE connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE sync_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow full access to connections" ON connections
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow full access to sync_history" ON sync_history
    FOR ALL USING (true) WITH CHECK (true);
