-- Migration: Add User Feedback and Conversation Analysis Tables
-- Date: 2026-02-07
-- Description: Creates tables for storing user feedback and conversation analysis scores

-- ============================================
-- Table: user_feedback
-- Stores user feedback after practice sessions
-- ============================================
CREATE TABLE IF NOT EXISTS user_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT NOT NULL,
    conversation_id TEXT,
    persona_practiced TEXT,
    helpfulness_score INTEGER CHECK (helpfulness_score >= 0 AND helpfulness_score <= 10),
    what_was_helpful TEXT,
    improvement_suggestions TEXT,
    user_email TEXT,
    user_id UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- Enable RLS on user_feedback
ALTER TABLE user_feedback ENABLE ROW LEVEL SECURITY;

-- RLS Policies for user_feedback
CREATE POLICY "Users can view their own feedback"
    ON user_feedback FOR SELECT
    TO authenticated
    USING (user_id = auth.uid() OR auth.jwt()->>'role' IN ('admin', 'moderator'));

CREATE POLICY "Users can submit feedback"
    ON user_feedback FOR INSERT
    TO authenticated
    WITH CHECK (user_id = auth.uid() OR user_id IS NULL);

CREATE POLICY "Users can submit feedback anonymously"
    ON user_feedback FOR INSERT
    TO anon
    WITH CHECK (user_id IS NULL);

CREATE POLICY "Admins can view all feedback"
    ON user_feedback FOR SELECT
    TO authenticated
    USING (auth.jwt()->>'role' IN ('admin', 'moderator'));

-- ============================================
-- Table: conversation_analyses
-- Stores detailed conversation analysis results and scores
-- ============================================
CREATE TABLE IF NOT EXISTS conversation_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT NOT NULL,
    conversation_id TEXT,
    user_id UUID REFERENCES auth.users(id),
    persona_id TEXT,
    persona_name TEXT,
    
    -- Overall scores (1-5 scale)
    overall_score NUMERIC(3,2) CHECK (overall_score >= 1 AND overall_score <= 5),
    
    -- MAPS Framework Scores
    foundational_trust_safety NUMERIC(3,2) CHECK (foundational_trust_safety >= 1 AND foundational_trust_safety <= 5),
    empathic_partnership_autonomy NUMERIC(3,2) CHECK (empathic_partnership_autonomy >= 1 AND empathic_partnership_autonomy <= 5),
    empowerment_clarity NUMERIC(3,2) CHECK (empowerment_clarity >= 1 AND empowerment_clarity <= 5),
    
    -- MI Spirit Assessment
    mi_spirit_score NUMERIC(3,2) CHECK (mi_spirit_score >= 1 AND mi_spirit_score <= 5),
    partnership_demonstrated BOOLEAN DEFAULT FALSE,
    acceptance_demonstrated BOOLEAN DEFAULT FALSE,
    compassion_demonstrated BOOLEAN DEFAULT FALSE,
    evocation_demonstrated BOOLEAN DEFAULT FALSE,
    
    -- Technique counts stored as JSON
    techniques_count JSONB DEFAULT '{}',
    
    -- Technique details stored as JSON array
    techniques_used JSONB DEFAULT '[]',
    
    -- Patterns Observed
    strengths JSONB DEFAULT '[]',
    areas_for_improvement JSONB DEFAULT '[]',
    
    -- Client Movement
    client_movement TEXT CHECK (client_movement IN ('toward_change', 'stable', 'away_from_change')),
    change_talk_evoked BOOLEAN DEFAULT FALSE,
    
    -- Detailed Feedback
    transcript_summary TEXT,
    summary TEXT,
    key_moments JSONB DEFAULT '[]',
    suggestions_for_next_time JSONB DEFAULT '[]',
    
    -- Full transcript stored as JSON
    transcript JSONB DEFAULT '[]',
    
    -- Metadata
    total_turns INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- Enable RLS on conversation_analyses
ALTER TABLE conversation_analyses ENABLE ROW LEVEL SECURITY;

-- RLS Policies for conversation_analyses
CREATE POLICY "Users can view their own analyses"
    ON conversation_analyses FOR SELECT
    TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "Admins can view all analyses"
    ON conversation_analyses FOR SELECT
    TO authenticated
    USING (auth.jwt()->>'role' IN ('admin', 'moderator'));

CREATE POLICY "Users can create their own analyses"
    ON conversation_analyses FOR INSERT
    TO authenticated
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Admins can create analyses for any user"
    ON conversation_analyses FOR INSERT
    TO authenticated
    WITH CHECK (auth.jwt()->>'role' IN ('admin', 'moderator'));

-- ============================================
-- Indexes for performance
-- ============================================
CREATE INDEX IF NOT EXISTS idx_user_feedback_user_id ON user_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_user_feedback_session_id ON user_feedback(session_id);
CREATE INDEX IF NOT EXISTS idx_user_feedback_created_at ON user_feedback(created_at);

CREATE INDEX IF NOT EXISTS idx_conversation_analyses_user_id ON conversation_analyses(user_id);
CREATE INDEX IF NOT EXISTS idx_conversation_analyses_session_id ON conversation_analyses(session_id);
CREATE INDEX IF NOT EXISTS idx_conversation_analyses_persona_id ON conversation_analyses(persona_id);
CREATE INDEX IF NOT EXISTS idx_conversation_analyses_created_at ON conversation_analyses(created_at);

-- ============================================
-- Function: Get practice analytics
-- Returns aggregated practice statistics for admin dashboard
-- ============================================
CREATE OR REPLACE FUNCTION get_practice_analytics(
    start_date DATE DEFAULT NULL,
    end_date DATE DEFAULT NULL
)
RETURNS TABLE (
    total_sessions BIGINT,
    total_users BIGINT,
    avg_overall_score NUMERIC,
    avg_trust_safety NUMERIC,
    avg_empathy NUMERIC,
    avg_empowerment NUMERIC,
    avg_mi_spirit NUMERIC,
    sessions_with_change_talk BIGINT,
    avg_turns NUMERIC
) 
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::BIGINT as total_sessions,
        COUNT(DISTINCT user_id)::BIGINT as total_users,
        ROUND(AVG(overall_score), 2) as avg_overall_score,
        ROUND(AVG(foundational_trust_safety), 2) as avg_trust_safety,
        ROUND(AVG(empathic_partnership_autonomy), 2) as avg_empathy,
        ROUND(AVG(empowerment_clarity), 2) as avg_empowerment,
        ROUND(AVG(mi_spirit_score), 2) as avg_mi_spirit,
        COUNT(*) FILTER (WHERE change_talk_evoked = TRUE)::BIGINT as sessions_with_change_talk,
        ROUND(AVG(total_turns), 1) as avg_turns
    FROM conversation_analyses
    WHERE 
        (start_date IS NULL OR created_at >= start_date)
        AND (end_date IS NULL OR created_at <= end_date);
END;
$$;

-- ============================================
-- Function: Get feedback stats
-- Returns aggregated feedback statistics
-- ============================================
CREATE OR REPLACE FUNCTION get_feedback_stats()
RETURNS TABLE (
    total_feedback BIGINT,
    average_score NUMERIC,
    score_10_count BIGINT,
    score_8_9_count BIGINT,
    score_5_7_count BIGINT,
    score_0_4_count BIGINT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::BIGINT as total_feedback,
        ROUND(AVG(helpfulness_score), 2) as average_score,
        COUNT(*) FILTER (WHERE helpfulness_score = 10)::BIGINT as score_10_count,
        COUNT(*) FILTER (WHERE helpfulness_score BETWEEN 8 AND 9)::BIGINT as score_8_9_count,
        COUNT(*) FILTER (WHERE helpfulness_score BETWEEN 5 AND 7)::BIGINT as score_5_7_count,
        COUNT(*) FILTER (WHERE helpfulness_score BETWEEN 0 AND 4)::BIGINT as score_0_4_count
    FROM user_feedback;
END;
$$;
