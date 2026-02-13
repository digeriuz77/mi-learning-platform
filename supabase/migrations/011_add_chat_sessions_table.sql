-- Migration: Add chat_sessions table for persistent session storage
-- Date: 2026-02-13
-- Description: Persists chat practice sessions to database instead of in-memory

-- ============================================
-- Table: chat_sessions
-- Stores chat practice sessions for persistence across restarts
-- ============================================
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT NOT NULL UNIQUE,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    persona_id TEXT NOT NULL,
    persona_data JSONB NOT NULL,
    history JSONB NOT NULL DEFAULT '[]',
    turn INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'
);

-- Enable RLS on chat_sessions
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;

-- RLS Policies for chat_sessions
-- Users can view their own sessions
CREATE POLICY "Users can view own chat sessions"
    ON chat_sessions FOR SELECT
    TO authenticated
    USING (user_id = auth.uid() OR user_id IS NULL);

-- Users can create their own sessions
CREATE POLICY "Users can create chat sessions"
    ON chat_sessions FOR INSERT
    TO authenticated
    WITH CHECK (user_id = auth.uid());

-- Users can update their own sessions
CREATE POLICY "Users can update own chat sessions"
    ON chat_sessions FOR UPDATE
    TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- Users can delete their own sessions
CREATE POLICY "Users can delete own chat sessions"
    ON chat_sessions FOR DELETE
    TO authenticated
    USING (user_id = auth.uid());

-- Admins can view all sessions
CREATE POLICY "Admins can view all chat sessions"
    ON chat_sessions FOR SELECT
    TO authenticated
    USING (auth.jwt()->>'role' IN ('admin', 'moderator'));

-- ============================================
-- Indexes for performance
-- ============================================
CREATE INDEX IF NOT EXISTS idx_chat_sessions_session_id ON chat_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_is_active ON chat_sessions(is_active);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_started_at ON chat_sessions(started_at);

-- ============================================
-- Function: Get or create chat session
-- Returns existing session or creates new one
-- ============================================
CREATE OR REPLACE FUNCTION get_or_create_chat_session(
    p_session_id TEXT,
    p_user_id UUID,
    p_persona_id TEXT,
    p_persona_data JSONB
)
RETURNS JSON
LANGUAGE plpgsql
AS $$
DECLARE
    v_session chat_sessions%ROWTYPE;
BEGIN
    -- Try to get existing session
    SELECT * INTO v_session
    FROM chat_sessions
    WHERE session_id = p_session_id;

    -- If not found, create new session
    IF v_session IS NULL THEN
        INSERT INTO chat_sessions (session_id, user_id, persona_id, persona_data, history, turn, is_active)
        VALUES (p_session_id, p_user_id, p_persona_id, p_persona_data, '[]', 0, TRUE)
        RETURNING * INTO v_session;
    END IF;

    RETURN json_build_object(
        'id', v_session.id,
        'session_id', v_session.session_id,
        'user_id', v_session.user_id,
        'persona_id', v_session.persona_id,
        'persona_data', v_session.persona_data,
        'history', v_session.history,
        'turn', v_session.turn,
        'is_active', v_session.is_active,
        'started_at', v_session.started_at
    );
END;
$$;

COMMENT ON FUNCTION get_or_create_chat_session IS 'Gets existing chat session or creates new one';
