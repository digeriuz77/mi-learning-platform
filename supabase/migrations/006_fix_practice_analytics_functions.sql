-- Migration: Fix Practice Analytics Functions (v3)
-- Date: 2026-02-07
-- Description: Fixes SQL to use correct table references based on actual schema

-- ============================================
-- Fix: Get all users with practice analytics
-- Use correct table aliases: u=auth.users, u2=public.users, ups=user_profiles
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
    IF search_email IS NOT NULL THEN
        SELECT json_agg(
            json_build_object(
                'id', u.id,
                'email', u.email,
                'display_name', COALESCE(u2.display_name, ups.display_name),
                'created_at', u.created_at,
                'role', COALESCE(u2.role, 'user'),
                'is_active', COALESCE(u2.is_active, true),
                'modules_completed', COALESCE(ups.modules_completed, 0),
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
        LEFT JOIN public.user_profiles ups ON u.id = ups.user_id
        WHERE u.email ILIKE '%' || search_email || '%'
        ORDER BY u.created_at DESC
        LIMIT limit_count OFFSET offset_count;
    ELSE
        SELECT json_agg(
            json_build_object(
                'id', u.id,
                'email', u.email,
                'display_name', COALESCE(u2.display_name, ups.display_name),
                'created_at', u.created_at,
                'role', COALESCE(u2.role, 'user'),
                'is_active', COALESCE(u2.is_active, true),
                'modules_completed', COALESCE(ups.modules_completed, 0),
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
        LEFT JOIN public.user_profiles ups ON u.id = ups.user_id
        ORDER BY u.created_at DESC
        LIMIT limit_count OFFSET offset_count;
    END IF;

    RETURN COALESCE(result, '[]'::json);
END;
$$;

COMMENT ON FUNCTION get_all_users_with_practice_analytics IS 'Returns all users with their practice analytics for admin dashboard';

-- ============================================
-- Fix: Get practice leaderboard
-- Use correct table references
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
            'display_name', COALESCE(u2.display_name, ups.display_name),
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
    LEFT JOIN public.users u2 ON u.id = u2.id
    WHERE ups.practice_sessions_count > 0
    ORDER BY ups.avg_overall_score DESC NULLS LAST
    LIMIT limit_count;

    RETURN COALESCE(result, '[]'::json);
END;
$$;

COMMENT ON FUNCTION get_practice_leaderboard IS 'Returns top users by practice performance scores';

-- ============================================
-- Fix: Get comprehensive practice analytics
-- This one was already correct
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
