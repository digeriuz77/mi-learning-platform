-- MI Learning Platform - Supabase Schema
-- Run this in Supabase SQL Editor to create required tables

-- =====================================================
-- user_profiles table
-- =====================================================
CREATE TABLE IF NOT EXISTS public.user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name VARCHAR(100),
    total_points INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    modules_completed INTEGER DEFAULT 0,
    change_talk_evoked INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_active_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id)
);

-- Enable RLS
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

-- Users can read their own profile
CREATE POLICY "Users can read own profile"
    ON public.user_profiles FOR SELECT
    USING (auth.uid() = user_id);

-- Users can update their own profile
CREATE POLICY "Users can update own profile"
    ON public.user_profiles FOR UPDATE
    USING (auth.uid() = user_id);

-- Service role can do everything
CREATE POLICY "Service role full access"
    ON public.user_profiles FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');

-- =====================================================
-- learning_modules table (should already exist)
-- =====================================================
-- This table was created by import_modules_http.py
-- It contains the 12 MI learning modules with dialogue_content

-- =====================================================
-- user_progress table
-- =====================================================
CREATE TABLE IF NOT EXISTS public.user_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    module_id UUID NOT NULL REFERENCES public.learning_modules(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'not_started',
    current_node_id VARCHAR(50),
    nodes_completed TEXT[] DEFAULT '{}',
    completion_score INTEGER DEFAULT 0,
    points_earned INTEGER DEFAULT 0,
    techniques_demonstrated JSONB DEFAULT '{}',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    UNIQUE(user_id, module_id)
);

-- Enable RLS
ALTER TABLE public.user_progress ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own progress"
    ON public.user_progress FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own progress"
    ON public.user_progress FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own progress"
    ON public.user_progress FOR UPDATE
    USING (auth.uid() = user_id);

-- =====================================================
-- dialogue_attempts table
-- =====================================================
CREATE TABLE IF NOT EXISTS public.dialogue_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    module_id UUID NOT NULL REFERENCES public.learning_modules(id) ON DELETE CASCADE,
    progress_id UUID NOT NULL REFERENCES public.user_progress(id) ON DELETE CASCADE,
    node_id VARCHAR(50) NOT NULL,
    choice_id VARCHAR(50) NOT NULL,
    choice_text TEXT NOT NULL,
    technique VARCHAR(100),
    is_correct_technique BOOLEAN DEFAULT FALSE,
    feedback_text TEXT,
    evoked_change_talk BOOLEAN DEFAULT FALSE,
    points_earned INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE public.dialogue_attempts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own attempts"
    ON public.dialogue_attempts FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own attempts"
    ON public.dialogue_attempts FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- =====================================================
-- Indexes for performance
-- =====================================================
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON public.user_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_progress_user_id ON public.user_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_user_progress_module_id ON public.user_progress(module_id);
CREATE INDEX IF NOT EXISTS idx_dialogue_attempts_user_id ON public.dialogue_attempts(user_id);
CREATE INDEX IF NOT EXISTS idx_dialogue_attempts_module_id ON public.dialogue_attempts(module_id);
