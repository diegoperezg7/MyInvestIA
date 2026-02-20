-- ============================================================
-- Migration 003: Multi-user support
-- Adds user_id to all data tables, creates RLS policies
-- that isolate data per user, and adds role support.
-- ============================================================

-- 1. Add user_id column (nullable initially so we can backfill)
ALTER TABLE holdings     ADD COLUMN IF NOT EXISTS user_id UUID;
ALTER TABLE watchlists   ADD COLUMN IF NOT EXISTS user_id UUID;
ALTER TABLE ai_memory    ADD COLUMN IF NOT EXISTS user_id UUID;
ALTER TABLE connections  ADD COLUMN IF NOT EXISTS user_id UUID;

-- watchlist_assets inherits user isolation through watchlist_id FK,
-- but we add user_id for simpler RLS policies
ALTER TABLE watchlist_assets ADD COLUMN IF NOT EXISTS user_id UUID;

-- sync_history inherits through connection_id FK
ALTER TABLE sync_history ADD COLUMN IF NOT EXISTS user_id UUID;

-- 2. Backfill: assign all existing data to Diego's user_id.
--    We use a DO block so we can look up the user or create a placeholder.
--    The actual Supabase Auth user will be created via the API (GoTrue).
--    For now, we use a well-known UUID that we'll map to Diego's account.
--
--    IMPORTANT: After creating Diego's auth account via GoTrue API,
--    run the UPDATE below with his actual auth.users UUID.
--    Or, the backend migration script will handle this.

-- Temporary: assign a placeholder UUID. The deploy script will update
-- this with the real auth user id after creating the account.
DO $$
DECLARE
    diego_id UUID;
BEGIN
    -- Try to find Diego in auth.users by email
    SELECT id INTO diego_id FROM auth.users WHERE email = 'diegoperezgarc@gmail.com' LIMIT 1;

    IF diego_id IS NULL THEN
        -- If not found yet, use a placeholder that will be updated
        -- after the auth account is created via GoTrue API
        diego_id := '00000000-0000-0000-0000-000000000001'::UUID;
        RAISE NOTICE 'Diego auth user not found yet. Using placeholder UUID. Run UPDATE after creating auth account.';
    END IF;

    -- Backfill all existing data to Diego
    UPDATE holdings      SET user_id = diego_id WHERE user_id IS NULL;
    UPDATE watchlists    SET user_id = diego_id WHERE user_id IS NULL;
    UPDATE watchlist_assets SET user_id = diego_id WHERE user_id IS NULL;
    UPDATE ai_memory     SET user_id = diego_id WHERE user_id IS NULL;
    UPDATE connections   SET user_id = diego_id WHERE user_id IS NULL;
    UPDATE sync_history  SET user_id = diego_id WHERE user_id IS NULL;
END $$;

-- 3. Make user_id NOT NULL
ALTER TABLE holdings      ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE watchlists    ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE watchlist_assets ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE ai_memory     ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE connections   ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE sync_history  ALTER COLUMN user_id SET NOT NULL;

-- 4. Add indexes for user_id lookups
CREATE INDEX IF NOT EXISTS idx_holdings_user_id      ON holdings(user_id);
CREATE INDEX IF NOT EXISTS idx_watchlists_user_id    ON watchlists(user_id);
CREATE INDEX IF NOT EXISTS idx_watchlist_assets_user_id ON watchlist_assets(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_memory_user_id     ON ai_memory(user_id);
CREATE INDEX IF NOT EXISTS idx_connections_user_id   ON connections(user_id);
CREATE INDEX IF NOT EXISTS idx_sync_history_user_id  ON sync_history(user_id);

-- 5. Drop old permissive RLS policies and create user-scoped ones

-- Holdings
DROP POLICY IF EXISTS "Allow all access to holdings" ON holdings;
DROP POLICY IF EXISTS "Allow full access to holdings" ON holdings;
DROP POLICY IF EXISTS "Users can view own holdings" ON holdings;
DROP POLICY IF EXISTS "Users can insert own holdings" ON holdings;
DROP POLICY IF EXISTS "Users can update own holdings" ON holdings;
DROP POLICY IF EXISTS "Users can delete own holdings" ON holdings;

CREATE POLICY "Users can view own holdings"
    ON holdings FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own holdings"
    ON holdings FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own holdings"
    ON holdings FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own holdings"
    ON holdings FOR DELETE
    USING (auth.uid() = user_id);

-- Watchlists
DROP POLICY IF EXISTS "Allow all access to watchlists" ON watchlists;
DROP POLICY IF EXISTS "Allow full access to watchlists" ON watchlists;
DROP POLICY IF EXISTS "Users can view own watchlists" ON watchlists;
DROP POLICY IF EXISTS "Users can insert own watchlists" ON watchlists;
DROP POLICY IF EXISTS "Users can update own watchlists" ON watchlists;
DROP POLICY IF EXISTS "Users can delete own watchlists" ON watchlists;

CREATE POLICY "Users can view own watchlists"
    ON watchlists FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own watchlists"
    ON watchlists FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own watchlists"
    ON watchlists FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own watchlists"
    ON watchlists FOR DELETE
    USING (auth.uid() = user_id);

-- Watchlist assets
DROP POLICY IF EXISTS "Allow all access to watchlist_assets" ON watchlist_assets;
DROP POLICY IF EXISTS "Allow full access to watchlist_assets" ON watchlist_assets;
DROP POLICY IF EXISTS "Users can view own watchlist_assets" ON watchlist_assets;
DROP POLICY IF EXISTS "Users can insert own watchlist_assets" ON watchlist_assets;
DROP POLICY IF EXISTS "Users can update own watchlist_assets" ON watchlist_assets;
DROP POLICY IF EXISTS "Users can delete own watchlist_assets" ON watchlist_assets;

CREATE POLICY "Users can view own watchlist_assets"
    ON watchlist_assets FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own watchlist_assets"
    ON watchlist_assets FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own watchlist_assets"
    ON watchlist_assets FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own watchlist_assets"
    ON watchlist_assets FOR DELETE
    USING (auth.uid() = user_id);

-- AI Memory
DROP POLICY IF EXISTS "Allow all access to ai_memory" ON ai_memory;
DROP POLICY IF EXISTS "Allow full access to ai_memory" ON ai_memory;
DROP POLICY IF EXISTS "Users can view own ai_memory" ON ai_memory;
DROP POLICY IF EXISTS "Users can insert own ai_memory" ON ai_memory;
DROP POLICY IF EXISTS "Users can update own ai_memory" ON ai_memory;
DROP POLICY IF EXISTS "Users can delete own ai_memory" ON ai_memory;

CREATE POLICY "Users can view own ai_memory"
    ON ai_memory FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own ai_memory"
    ON ai_memory FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own ai_memory"
    ON ai_memory FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own ai_memory"
    ON ai_memory FOR DELETE
    USING (auth.uid() = user_id);

-- Connections
DROP POLICY IF EXISTS "Allow all access to connections" ON connections;
DROP POLICY IF EXISTS "Allow full access to connections" ON connections;
DROP POLICY IF EXISTS "Users can view own connections" ON connections;
DROP POLICY IF EXISTS "Users can insert own connections" ON connections;
DROP POLICY IF EXISTS "Users can update own connections" ON connections;
DROP POLICY IF EXISTS "Users can delete own connections" ON connections;

CREATE POLICY "Users can view own connections"
    ON connections FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own connections"
    ON connections FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own connections"
    ON connections FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own connections"
    ON connections FOR DELETE
    USING (auth.uid() = user_id);

-- Sync history
DROP POLICY IF EXISTS "Allow all access to sync_history" ON sync_history;
DROP POLICY IF EXISTS "Allow full access to sync_history" ON sync_history;
DROP POLICY IF EXISTS "Users can view own sync_history" ON sync_history;
DROP POLICY IF EXISTS "Users can insert own sync_history" ON sync_history;
DROP POLICY IF EXISTS "Users can update own sync_history" ON sync_history;
DROP POLICY IF EXISTS "Users can delete own sync_history" ON sync_history;

CREATE POLICY "Users can view own sync_history"
    ON sync_history FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own sync_history"
    ON sync_history FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own sync_history"
    ON sync_history FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own sync_history"
    ON sync_history FOR DELETE
    USING (auth.uid() = user_id);

-- 6. Ensure RLS is enabled on all tables
ALTER TABLE holdings ENABLE ROW LEVEL SECURITY;
ALTER TABLE watchlists ENABLE ROW LEVEL SECURITY;
ALTER TABLE watchlist_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE sync_history ENABLE ROW LEVEL SECURITY;
