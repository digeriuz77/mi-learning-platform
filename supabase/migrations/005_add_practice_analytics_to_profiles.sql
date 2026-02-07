-- Migration: Add Practice Analytics to User Profiles
-- Date: 2026-02-07
-- Description: Adds practice session analytics columns to user_profiles table

-- ============================================
-- Add practice analytics columns to user_profiles
-- ============================================
DO $$
BEGIN
    -- Add practice_sessions_count
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user_profiles' AND column_name = 'practice_sessions_count'
    ) THEN
        ALTER TABLE public.user_profiles ADD COLUMN practice_sessions_count INTEGER DEFAULT 0;
        RAISE NOTICE 'Added practice_sessions_count column';
    END IF;

    -- Add avg_overall_score
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user_profiles' AND column_name = 'avg_overall_score'
    ) THEN
        ALTER TABLE public.user_profiles ADD COLUMN avg_overall_score NUMERIC(3,2);
        RAISE NOTICE 'Added avg_overall_score column';
    END IF;

    -- Add avg_trust_safety
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user_profiles' AND column_name = 'avg_trust_safety'
    ) THEN
        ALTER TABLE public.user_profiles ADD COLUMN avg_trust_safety NUMERIC(3,2);
        RAISE NOTICE 'Added avg_trust_safety column';
    END IF;

    -- Add avg_empathy_partnership
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user_profiles' AND column_name = 'avg_empathy_partnership'
    ) THEN
        ALTER TABLE public.user_profiles ADD COLUMN avg_empathy_partnership NUMERIC(3,2);
        RAISE NOTICE 'Added avg_empathy_partnership column';
    END IF;

    -- Add avg_empowerment_clarity
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user_profiles' AND column_name = 'avg_empowerment_clarity'
    ) THEN
        ALTER TABLE public.user_profiles ADD COLUMN avg_empowerment_clarity NUMERIC(3,2);
        RAISE NOTICE 'Added avg_empowerment_clarity column';
    END IF;

    -- Add avg_mi_spirit
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user_profiles' AND column_name = 'avg_mi_spirit'
    ) THEN
        ALTER TABLE public.user_profiles ADD COLUMN avg_mi_spirit NUMERIC(3,2);
        RAISE NOTICE 'Added avg_mi_spirit column';
    END IF;

    -- Add last_practice_at
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user_profiles' AND column_name = 'last_practice_at'
    ) THEN
        ALTER TABLE public.user_profiles ADD COLUMN last_practice_at TIMESTAMPTZ;
        RAISE NOTICE 'Added last_practice_at column';
    END IF;
END $$;

-- ============================================
-- Function: Update user practice analytics
-- Called automatically when new analysis is saved
-- ============================================
CREATE OR REPLACE FUNCTION update_user_practice_analytics(
    p_user_id UUID,
    p_overall_score NUMERIC,
    p_trust_safety NUMERIC,
    p_empathy_partnership NUMERIC,
    p_empowerment_clarity NUMERIC,
    p_mi_spirit NUMERIC
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_current_count INTEGER;
    v_new_count INTEGER;
BEGIN
    -- Get current practice session count
    SELECT practice_sessions_count INTO v_current_count
    FROM public.user_profiles
    WHERE user_id = p_user_id;

    -- If no profile exists, create one
    IF v_current_count IS NULL THEN
        INSERT INTO public.user_profiles (user_id, practice_sessions_count)
        VALUES (p_user_id, 1);
        v_current_count := 0;
    END IF;

    v_new_count := v_current_count + 1;

    -- Update the profile with new averages
    UPDATE public.user_profiles
    SET 
        practice_sessions_count = v_new_count,
        -- Calculate running average: new_avg = (old_avg * old_count + new_value) / new_count
        avg_overall_score = COALESCE(
            ((COALESCE(avg_overall_score, 0) * v_current_count) + p_overall_score) / v_new_count,
            p_overall_score
        ),
        avg_trust_safety = COALESCE(
            ((COALESCE(avg_trust_safety, 0) * v_current_count) + p_trust_safety) / v_new_count,
            p_trust_safety
        ),
        avg_empathy_partnership = COALESCE(
            ((COALESCE(avg_empathy_partnership, 0) * v_current_count) + p_empathy_partnership) / v_new_count,
            p_empathy_partnership
        ),
        avg_empowerment_clarity = COALESCE(
            ((COALESCE(avg_empowerment_clarity, 0) * v_current_count) + p_empowerment_clarity) / v_new_count,
            p_empowerment_clarity
        ),
        avg_mi_spirit = COALESCE(
            ((COALESCE(avg_mi_spirit, 0) * v_current_count) + p_mi_spirit) / v_new_count,
            p_mi_spirit
        ),
        last_practice_at = NOW()
    WHERE user_id = p_user_id;
END;
$$;

COMMENT ON FUNCTION update_user_practice_analytics IS 'Updates user practice analytics with new session scores';

-- ============================================
-- Function: Get user practice analytics
-- Returns practice statistics for a specific user
-- ============================================
CREATE OR REPLACE FUNCTION get_user_practice_analytics(p_user_id UUID)
RETURNS json
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    result json;
BEGIN
    SELECT json_build_object(
        'user_id', user_id,
        'practice_sessions_count', COALESCE(practice_sessions_count, 0),
        'avg_overall_score', avg_overall_score,
        'avg_trust_safety', avg_trust_safety,
        'avg_empathy_partnership', avg_empathy_partnership,
        'avg_empowerment_clarity', avg_empowerment_clarity,
        'avg_mi_spirit', avg_mi_spirit,
        'last_practice_at', last_practice_at
    ) INTO result
    FROM public.user_profiles
    WHERE user_id = p_user_id;

    RETURN COALESCE(result, '{}'::json);
END;
$$;

COMMENT ON FUNCTION get_user_practice_analytics IS 'Returns practice analytics for a specific user';

-- ============================================
-- Function: Get all users with practice analytics (Admin)
-- Returns all users with their practice statistics
-- ============================================
CREATE OR REPLACE FUNCTION get_all_users_with_practice_analytics(
    search_email text DEFAULT null,
    limit_count int DEFAULT 50,
    offset_count int DEFAULT 0
)
RETURNS json
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    result json;
BEGIN
    -- Verify admin access
    IF NOT public.is_admin(auth.uid()) THEN
        RAISE EXCEPTION 'Access denied: Admin access required';
    END IF;

    IF search_email IS NOT NULL THEN
        SELECT json_agg(
            json_build_object(
                'id', u.id,
                'email', u.email,
                'display_name', u.display_name,
                'created_at', u.created_at,
                'role', COALESCE(u2.role, 'user'),
                'is_active', COALESCE(u2.is_active, true),
                'modules_completed', COALESCE(up.modules_completed, 0),
                'total_points', COALESCE(ups.total_points, 0),
                'level', COALESCE(ups.level, 1),
                'practice_sessions_count', COALESCE(ups.practice_sessions_count, 0),
                'avg_overall_score', ups.avg_overall_score,
                'avg_trust_safety', ups.avg_trust_safety,
                'avg_empathy_partnership', ups.avg_empathy_partnership,
                'avg_empowerment_clarity', ups.avg_empowerment_clarity,
                'avg_mi_spirit', ups.avg_mi_spirit,
                'last_practice_at', ups.last_practice_at
            )::json
        ) INTO result
        FROM auth.users u
        LEFT JOIN public.users u2 ON u.id = u2.id
        LEFT JOIN public.user_progress up ON u.id = up.user_id AND up.status = 'completed'
        LEFT JOIN public.user_profiles ups ON u.id = ups.user_id
        WHERE u.email ILIKE '%' || search_email || '%'
        GROUP BY u.id, u.email, u.display_name, u.created_at, u2.role, u2.is_active, 
                 up.modules_completed, ups.total_points, ups.level,
                 ups.practice_sessions_count, ups.avg_overall_score, ups.avg_trust_safety,
                 ups.avg_empathy_partnership, ups.avg_empowerment_clarity, ups.avg_mi_spirit,
                 ups.last_practice_at
        ORDER BY u.created_at DESC
        LIMIT limit_count OFFSET offset_count;
    ELSE
        SELECT json_agg(
            json_build_object(
                'id', u.id,
                'email', u.email,
                'display_name', u.display_name,
                'created_at', u.created_at,
                'role', COALESCE(u2.role, 'user'),
                'is_active', COALESCE(u2.is_active, true),
                'modules_completed', COALESCE(up.modules_completed, 0),
                'total_points', COALESCE(ups.total_points, 0),
                'level', COALESCE(ups.level, 1),
                'practice_sessions_count', COALESCE(ups.practice_sessions_count, 0),
                'avg_overall_score', ups.avg_overall_score,
                'avg_trust_safety', ups.avg_trust_safety,
                'avg_empathy_partnership', ups.avg_empathy_partnership,
                'avg_empowerment_clarity', ups.avg_empowerment_clarity,
                'avg_mi_spirit', ups.avg_mi_spirit,
                'last_practice_at', ups.last_practice_at
            )::json
        ) INTO result
        FROM auth.users u
        LEFT JOIN public.users u2 ON u.id = u2.id
        LEFT JOIN public.user_progress up ON u.id = up.user_id AND up.status = 'completed'
        LEFT JOIN public.user_profiles ups ON u.id = ups.user_id
        GROUP BY u.id, u.email, u.display_name, u.created_at, u2.role, u2.is_active, 
                 up.modules_completed, ups.total_points, ups.level,
                 ups.practice_sessions_count, ups.avg_overall_score, ups.avg_trust_safety,
                 ups.avg_empathy_partnership, ups.avg_empowerment_clarity, ups.avg_mi_spirit,
                 ups.last_practice_at
        ORDER BY u.created_at DESC
        LIMIT limit_count OFFSET offset_count;
    END IF;

    RETURN COALESCE(result, '[]'::json);
END;
$$;

COMMENT ON FUNCTION get_all_users_with_practice_analytics IS 'Returns all users with their practice analytics for admin dashboard';

-- ============================================
-- Function: Get practice leaderboard
-- Returns top users by practice performance
-- ============================================
CREATE OR REPLACE FUNCTION get_practice_leaderboard(limit_count int DEFAULT 20)
RETURNS json
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    result json;
BEGIN
    SELECT json_agg(
        json_build_object(
            'user_id', ups.user_id,
            'display_name', u.display_name,
            'practice_sessions_count', COALESCE(ups.practice_sessions_count, 0),
            'avg_overall_score', ups.avg_overall_score,
            'avg_trust_safety', ups.avg_trust_safety,
            'avg_empathy_partnership', ups.avg_empathy_partnership,
            'avg_empowerment_clarity', ups.avg_empowerment_clarity,
            'avg_mi_spirit', ups.avg_mi_spirit
        )::json
    ) INTO result
    FROM public.user_profiles ups
    JOIN auth.users u ON ups.user_id = u.id
    WHERE ups.practice_sessions_count > 0
    ORDER BY ups.avg_overall_score DESC NULLS LAST
    LIMIT limit_count;

    RETURN COALESCE(result, '[]'::json);
END;
$$;

COMMENT ON FUNCTION get_practice_leaderboard IS 'Returns top users by practice performance scores';

-- ============================================
-- Function: Get comprehensive practice analytics
-- Returns aggregate analytics for admin dashboard
-- ============================================
CREATE OR REPLACE FUNCTION get_comprehensive_practice_analytics()
RETURNS json
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_total_sessions BIGINT;
    v_total_users BIGINT;
    v_avg_overall_score NUMERIC;
    v_avg_trust_safety NUMERIC;
    v_avg_empathy NUMERIC;
    v_avg_empowerment NUMERIC;
    v_avg_mi_spirit NUMERIC;
    v_sessions_with_change_talk BIGINT;
    v_avg_turns NUMERIC;
BEGIN
    -- Verify admin access
    IF NOT public.is_admin(auth.uid()) THEN
        RAISE EXCEPTION 'Access denied: Admin access required';
    END IF;

    -- Get aggregate stats from conversation_analyses
    SELECT 
        COUNT(*)::BIGINT,
        COUNT(DISTINCT user_id)::BIGINT,
        ROUND(AVG(overall_score), 2),
        ROUND(AVG(foundational_trust_safety), 2),
        ROUND(AVG(empathic_partnership_autonomy), 2),
        ROUND(AVG(empowerment_clarity), 2),
        ROUND(AVG(mi_spirit_score), 2),
        COUNT(*) FILTER (WHERE change_talk_evoked = TRUE)::BIGINT,
        ROUND(AVG(total_turns), 1)
    INTO 
        v_total_sessions,
        v_total_users,
        v_avg_overall_score,
        v_avg_trust_safety,
        v_avg_empathy,
        v_avg_empowerment,
        v_avg_mi_spirit,
        v_sessions_with_change_talk,
        v_avg_turns
    FROM public.conversation_analyses;

    RETURN json_build_object(
        'total_sessions', COALESCE(v_total_sessions, 0),
        'total_users', COALESCE(v_total_users, 0),
        'avg_overall_score', v_avg_overall_score,
        'avg_trust_safety', v_avg_trust_safety,
        'avg_empathy', v_avg_empathy,
        'avg_empowerment', v_avg_empowerment,
        'avg_mi_spirit', v_avg_mi_spirit,
        'sessions_with_change_talk', COALESCE(v_sessions_with_change_talk, 0),
        'avg_turns', v_avg_turns
    );
END;
$$;

COMMENT ON FUNCTION get_comprehensive_practice_analytics IS 'Returns comprehensive practice analytics for admin dashboard';

-- ============================================
-- Create trigger to automatically update user analytics
-- when new analysis is inserted
-- ============================================
CREATE OR REPLACE FUNCTION trigger_update_user_analytics()
RETURNS TRIGGER AS $$
BEGIN
    -- Only update if user_id is not null
    IF NEW.user_id IS NOT NULL THEN
        PERFORM update_user_practice_analytics(
            NEW.user_id,
            NEW.overall_score,
            NEW.foundational_trust_safety,
            NEW.empathic_partnership_autonomy,
            NEW.empowerment_clarity,
            NEW.mi_spirit_score
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create the trigger
DROP TRIGGER IF EXISTS update_user_analytics_on_analysis ON public.conversation_analyses;

CREATE TRIGGER update_user_analytics_on_analysis
    AFTER INSERT ON public.conversation_analyses
    FOR EACH ROW
    EXECUTE FUNCTION trigger_update_user_analytics();

COMMENT ON TRIGGER update_user_analytics_on_analysis ON public.conversation_analyses IS 'Automatically updates user practice analytics when new analysis is saved';
