-- MI Learning Platform PostgreSQL Schema for Supabase
-- This schema replaces Django models and provides clean progress tracking

-- Users table (extends Supabase auth.users)
CREATE TABLE IF NOT EXISTS app_user (
    id UUID REFERENCES auth.users(id) PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    first_name TEXT,
    last_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- MI Learning Modules (chapters)
CREATE TABLE IF NOT EXISTS mi_module (
    id SERIAL PRIMARY KEY,
    module_number INTEGER UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    learning_objective TEXT,
    technique_focus TEXT,
    stage_of_change TEXT,
    mi_process TEXT,
    difficulty TEXT DEFAULT 'beginner',
    points INTEGER DEFAULT 100,
    order_index INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Dialogue Trees for each module
CREATE TABLE IF NOT EXISTS dialogue_tree (
    id SERIAL PRIMARY KEY,
    module_id INTEGER REFERENCES mi_module(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    learning_objective TEXT,
    technique_focus TEXT,
    stage_of_change TEXT,
    mi_process TEXT,
    description TEXT,
    start_node_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Dialogue Nodes
CREATE TABLE IF NOT EXISTS dialogue_node (
    id SERIAL PRIMARY KEY,
    tree_id INTEGER REFERENCES dialogue_tree(id) ON DELETE CASCADE,
    node_id TEXT NOT NULL,
    patient_statement TEXT NOT NULL,
    patient_context TEXT,
    change_talk_present BOOLEAN DEFAULT FALSE,
    change_talk_type TEXT, -- D, A, R, N, C, T
    is_ending BOOLEAN DEFAULT FALSE,
    outcome TEXT,
    learning_summary TEXT,
    order_index INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Practitioner Choices
CREATE TABLE IF NOT EXISTS practitioner_choice (
    id SERIAL PRIMARY KEY,
    node_id INTEGER REFERENCES dialogue_node(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    technique TEXT NOT NULL,
    next_node_id TEXT,
    feedback TEXT,
    is_correct_technique BOOLEAN DEFAULT FALSE,
    is_mistake BOOLEAN DEFAULT FALSE,
    order_index INTEGER DEFAULT 0
);

-- User Progress Tracking
CREATE TABLE IF NOT EXISTS user_module_progress (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES app_user(id) ON DELETE CASCADE,
    module_id INTEGER REFERENCES mi_module(id) ON DELETE CASCADE,
    current_node_id TEXT DEFAULT 'start',
    nodes_completed TEXT[] DEFAULT '{}',
    techniques_demonstrated TEXT[] DEFAULT '{}',
    completion_status TEXT DEFAULT 'not_started', -- not_started, in_progress, completed_good, completed_moderate, completed_poor
    completion_score INTEGER DEFAULT 0,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(user_id, module_id)
);

-- User Attempts (for each choice)
CREATE TABLE IF NOT EXISTS user_attempt (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES app_user(id) ON DELETE CASCADE,
    node_id INTEGER REFERENCES dialogue_node(id) ON DELETE CASCADE,
    choice_id INTEGER REFERENCES practitioner_choice(id) ON DELETE CASCADE,
    is_correct BOOLEAN DEFAULT FALSE,
    points_earned INTEGER DEFAULT 0,
    attempted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User Overall Score
CREATE TABLE IF NOT EXISTS user_score (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES app_user(id) ON DELETE CASCADE UNIQUE,
    total_points INTEGER DEFAULT 0,
    modules_completed INTEGER DEFAULT 0,
    technique_mastery JSONB DEFAULT '{}',
    change_talk_evoked INTEGER DEFAULT 0,
    reflections_offered INTEGER DEFAULT 0,
    summaries_created INTEGER DEFAULT 0,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_module_progress_user_id ON user_module_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_user_module_progress_module_id ON user_module_progress(module_id);
CREATE INDEX IF NOT EXISTS idx_dialogue_node_tree_id ON dialogue_node(tree_id);
CREATE INDEX IF NOT EXISTS idx_practitioner_choice_node_id ON practitioner_choice(node_id);
CREATE INDEX IF NOT EXISTS idx_user_attempt_user_id ON user_attempt(user_id);

-- Row Level Security (RLS) policies
ALTER TABLE app_user ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_module_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_attempt ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_score ENABLE ROW LEVEL SECURITY;

-- Users can only see their own data
CREATE POLICY "Users can view own profile" ON app_user FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own profile" ON app_user FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Users can view own progress" ON user_module_progress FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own progress" ON user_module_progress FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own progress" ON user_module_progress FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can view own attempts" ON user_attempt FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own attempts" ON user_attempt FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can view own score" ON user_score FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can update own score" ON user_score FOR UPDATE USING (auth.uid() = user_id);

-- Public read access for modules and content
ALTER TABLE mi_module ENABLE ROW LEVEL SECURITY;
ALTER TABLE dialogue_tree ENABLE ROW LEVEL SECURITY;
ALTER TABLE dialogue_node ENABLE ROW LEVEL SECURITY;
ALTER TABLE practitioner_choice ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Everyone can view modules" ON mi_module FOR SELECT USING (is_active = TRUE);
CREATE POLICY "Everyone can view dialogue trees" ON dialogue_tree FOR SELECT USING (TRUE);
CREATE POLICY "Everyone can view dialogue nodes" ON dialogue_node FOR SELECT USING (TRUE);
CREATE POLICY "Everyone can view practitioner choices" ON practitioner_choice FOR SELECT USING (TRUE);

-- Functions to update user scores automatically
CREATE OR REPLACE FUNCTION update_user_score(user_uuid UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE user_score SET
        total_points = (
            SELECT COALESCE(SUM(points_earned), 0) 
            FROM user_attempt 
            WHERE user_id = user_uuid
        ),
        modules_completed = (
            SELECT COUNT(*) 
            FROM user_module_progress 
            WHERE user_id = user_uuid AND completion_status LIKE 'completed_%'
        ),
        last_updated = NOW()
    WHERE user_id = user_uuid;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update scores when attempts are made
CREATE OR REPLACE TRIGGER trigger_update_user_score
    AFTER INSERT OR UPDATE ON user_attempt
    FOR EACH ROW
    EXECUTE FUNCTION update_user_score(NEW.user_id);