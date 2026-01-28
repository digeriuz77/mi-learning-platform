-- MI Learning Platform - Supabase Database Schema
-- Run this in Supabase SQL Editor to initialize the database

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- User Profiles Table
-- =====================================================
CREATE TABLE public.user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name VARCHAR(100),
    total_points INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    modules_completed INTEGER DEFAULT 0,
    change_talk_evoked INTEGER DEFAULT 0,
    reflections_offered INTEGER DEFAULT 0,
    technique_mastery JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_active_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id)
);

-- =====================================================
-- Learning Modules Table
-- =====================================================
CREATE TABLE public.learning_modules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    module_number INTEGER UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    learning_objective TEXT NOT NULL,
    technique_focus VARCHAR(100) NOT NULL,
    stage_of_change VARCHAR(50) NOT NULL,
    mi_process VARCHAR(50),
    description TEXT NOT NULL,
    dialogue_content JSONB NOT NULL,
    points INTEGER DEFAULT 500,
    display_order INTEGER DEFAULT 0,
    is_published BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- User Progress Table
-- =====================================================
CREATE TABLE public.user_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    module_id UUID NOT NULL REFERENCES public.learning_modules(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'not_started' CHECK (status IN ('not_started', 'in_progress', 'completed')),
    current_node_id VARCHAR(50) DEFAULT 'node_1',
    nodes_completed TEXT[] DEFAULT '{}',
    points_earned INTEGER DEFAULT 0,
    completion_score INTEGER DEFAULT 0,
    techniques_demonstrated JSONB DEFAULT '{}',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, module_id)
);

-- =====================================================
-- Dialogue Attempts Table
-- =====================================================
CREATE TABLE public.dialogue_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    module_id UUID NOT NULL REFERENCES public.learning_modules(id) ON DELETE CASCADE,
    progress_id UUID REFERENCES public.user_progress(id) ON DELETE CASCADE,
    node_id VARCHAR(50) NOT NULL,
    choice_id VARCHAR(50) NOT NULL,
    choice_text TEXT NOT NULL,
    technique VARCHAR(100) NOT NULL,
    is_correct_technique BOOLEAN NOT NULL,
    feedback_text TEXT NOT NULL,
    evoked_change_talk BOOLEAN DEFAULT FALSE,
    points_earned INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- Indexes for Performance
-- =====================================================
CREATE INDEX idx_user_profiles_points ON public.user_profiles(total_points DESC, level DESC);
CREATE INDEX idx_user_profiles_user_id ON public.user_profiles(user_id);
CREATE INDEX idx_learning_modules_published ON public.learning_modules(is_published, display_order);
CREATE INDEX idx_user_progress_user ON public.user_progress(user_id, status);
CREATE INDEX idx_user_progress_module ON public.user_progress(module_id, status);
CREATE INDEX idx_dialogue_attempts_user ON public.dialogue_attempts(user_id, created_at DESC);
CREATE INDEX idx_dialogue_attempts_progress ON public.dialogue_attempts(progress_id);

-- =====================================================
-- Row Level Security (RLS) Policies
-- =====================================================

-- Enable RLS
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dialogue_attempts ENABLE ROW LEVEL SECURITY;

-- User Profiles: Users can view and update own profile
CREATE POLICY "Users can view own profile"
    ON public.user_profiles
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own profile"
    ON public.user_profiles
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own profile"
    ON public.user_profiles
    FOR UPDATE
    USING (auth.uid() = user_id);

-- User Progress: Users can manage own progress
CREATE POLICY "Users can view own progress"
    ON public.user_progress
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own progress"
    ON public.user_progress
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own progress"
    ON public.user_progress
    FOR UPDATE
    USING (auth.uid() = user_id);

-- Dialogue Attempts: Users can manage own attempts
CREATE POLICY "Users can view own attempts"
    ON public.dialogue_attempts
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own attempts"
    ON public.dialogue_attempts
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Learning Modules: Public can read
ALTER TABLE public.learning_modules ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public can view modules"
    ON public.learning_modules
    FOR SELECT
    USING (is_published = TRUE);

-- =====================================================
-- Functions and Triggers
-- =====================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to user_profiles
CREATE TRIGGER update_user_profiles_updated_at
    BEFORE UPDATE ON public.user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply trigger to user_progress
CREATE TRIGGER update_user_progress_updated_at
    BEFORE UPDATE ON public.user_progress
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply trigger to learning_modules
CREATE TRIGGER update_learning_modules_updated_at
    BEFORE UPDATE ON public.learning_modules
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to create user profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.user_profiles (user_id, display_name)
    VALUES (NEW.id, NEW.raw_user_meta_data->>'display_name')
    ON CONFLICT (user_id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to create profile on user signup
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

-- =====================================================
-- Grant Permissions
-- =====================================================
GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;
GRANT ALL ON public.user_profiles TO authenticated, service_role;
GRANT ALL ON public.user_progress TO authenticated, service_role;
GRANT ALL ON public.dialogue_attempts TO authenticated, service_role;
GRANT SELECT ON public.learning_modules TO anon, authenticated, service_role;
