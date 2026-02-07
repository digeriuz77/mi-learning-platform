-- Migration: Fix Practice Analytics Functions (v2)
-- Date: 2026-02-07
-- Description: Fixes SQL errors in practice analytics functions

-- ============================================
-- Fix: Get all users with practice analytics
-- Fix modules_completed count and GROUP BY issues
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
                'display_name', u2.display_name,
                'created_at', u.created_at,
                'role', COALESCE(u2.role, 'user'),
                'is_active', COALESCE(u2.is_active, true),
                'modules_completed', COALESCE(module_count.count, 0),
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
        LEFT JOIN (
            SELECT user_id, COUNT(*) as count
            FROM public.user_progress
            WHERE status = 'completed'
            GROUP BY user_id
        ) module_count ON u.id = module_count.user_id
        WHERE u.email ILIKE '%' || search_email || '%'
        ORDER BY u.created_at DESC
        LIMIT limit_count OFFSET offset_count;
    ELSE
        SELECT json_agg(
            json_build_object(
                'id', u.id,
                'email', u.email,
                'display_name', u2.display_name,
                'created_at', u.created_at,
                'role', COALESCE(u2.role, 'user'),
                'is_active', COALESCE(u2.is_active, true),
                'modules_completed', COALESCE(module_count.count, 0),
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
        LEFT JOIN (
            SELECT user_id, COUNT(*) as count
            FROM public.user_progress
            WHERE status = 'completed'
            GROUP BY user_id
        ) module_count ON u.id = module_count.user_id
        ORDER BY u.created_at DESC
        LIMIT limit_count OFFSET offset_count;
    END IF;

    RETURN COALESCE(result, '[]'::json);
END;
$$;

COMMENT ON FUNCTION get_all_users_with_practice_analytics IS 'Returns all users with their practice analytics for admin dashboard';

-- ============================================
-- Fix: Get practice leaderboard
-- Remove unnecessary GROUP BY
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
            'display_name', u2.display_name,
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
