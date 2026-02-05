-- ============================================
-- EMAIL PRIVACY & RLS POLICIES (v3)
-- Note: Signup trigger is already created in migration 001
-- This migration only adds RLS policies
-- ============================================

-- 1. Users table - protect email visibility

DO $$
BEGIN
    -- Create new policy if not exists: Users can only view their own record
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'users' AND policyname = 'Users can view own user record'
    ) THEN
        CREATE POLICY "Users can view own user record" ON public.users
            FOR SELECT
            USING (auth.uid() = id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'users' AND policyname = 'Users can update own user record'
    ) THEN
        CREATE POLICY "Users can update own user record" ON public.users
            FOR UPDATE
            USING (auth.uid() = id)
            WITH CHECK (auth.uid() = id);
    END IF;

    RAISE NOTICE 'Updated users table policies';
END $$;

-- ============================================

-- 2. user_profiles table - protect user data

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'user_profiles' AND policyname = 'Users can view own profile'
    ) THEN
        CREATE POLICY "Users can view own profile" ON public.user_profiles
            FOR SELECT
            USING (auth.uid() = user_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'user_profiles' AND policyname = 'Users can update own profile'
    ) THEN
        CREATE POLICY "Users can update own profile" ON public.user_profiles
            FOR UPDATE
            USING (auth.uid() = user_id)
            WITH CHECK (auth.uid() = user_id);
    END IF;

    RAISE NOTICE 'Updated user_profiles table policies';
END $$;

-- ============================================

-- 3. user_progress table - protect user progress

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'user_progress' AND policyname = 'Users can view own progress'
    ) THEN
        CREATE POLICY "Users can view own progress" ON public.user_progress
            FOR SELECT
            USING (auth.uid() = user_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'user_progress' AND policyname = 'Users can insert own progress'
    ) THEN
        CREATE POLICY "Users can insert own progress" ON public.user_progress
            FOR INSERT
            WITH CHECK (auth.uid() = user_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'user_progress' AND policyname = 'Users can update own progress'
    ) THEN
        CREATE POLICY "Users can update own progress" ON public.user_progress
            FOR UPDATE
            USING (auth.uid() = user_id)
            WITH CHECK (auth.uid() = user_id);
    END IF;

    RAISE NOTICE 'Updated user_progress table policies';
END $$;

-- ============================================

-- 4. learning_modules table - public read access

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'learning_modules' AND policyname = 'Public modules are viewable by everyone'
    ) THEN
        CREATE POLICY "Public modules are viewable by everyone" ON public.learning_modules
            FOR SELECT
            USING (is_published = true);
    END IF;

    RAISE NOTICE 'Updated learning_modules table policies';
END $$;

-- ============================================

-- 5. user_score table - protect scores

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = 'user_score'
        AND rowsecurity = true
    ) THEN
        ALTER TABLE public.user_score ENABLE ROW LEVEL SECURITY;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'user_score' AND policyname = 'Users can view own score'
    ) THEN
        CREATE POLICY "Users can view own score" ON public.user_score
            FOR SELECT
            USING (user_id = auth.uid());
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'user_score' AND policyname = 'Users can update own score'
    ) THEN
        CREATE POLICY "Users can update own score" ON public.user_score
            FOR UPDATE
            USING (user_id = auth.uid())
            WITH CHECK (user_id = auth.uid());
    END IF;

    RAISE NOTICE 'Enabled RLS on user_score table';
END $$;

-- ============================================

-- 6. dialogue_attempts table - protect attempt data

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'dialogue_attempts' AND policyname = 'Users can view own attempts'
    ) THEN
        CREATE POLICY "Users can view own attempts" ON public.dialogue_attempts
            FOR SELECT
            USING (auth.uid() = user_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'dialogue_attempts' AND policyname = 'Users can insert own attempts'
    ) THEN
        CREATE POLICY "Users can insert own attempts" ON public.dialogue_attempts
            FOR INSERT
            WITH CHECK (auth.uid() = user_id);
    END IF;

    RAISE NOTICE 'Updated dialogue_attempts table policies';
END $$;

-- ============================================
-- NOTE: Signup trigger already created in migration 001
-- No need to recreate handle_new_user() function
-- ============================================
