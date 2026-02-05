-- ============================================
-- ADMIN ROLE MIGRATION (v3)
-- Compatible with existing Supabase schema
-- ============================================

-- 1. Add role column to users table (if not exists)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'users' AND column_name = 'role'
    ) THEN
        ALTER TABLE public.users ADD COLUMN role text DEFAULT 'user' CHECK (role IN ('user', 'admin', 'moderator'));
        RAISE NOTICE 'Added role column to users table';
    ELSE
        RAISE NOTICE 'Role column already exists in users table';
    END IF;
END $$;

-- 2. Add is_active column for banning users
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'users' AND column_name = 'is_active'
    ) THEN
        ALTER TABLE public.users ADD COLUMN is_active boolean DEFAULT true;
        RAISE NOTICE 'Added is_active column to users table';
    ELSE
        RAISE NOTICE 'is_active column already exists in users table';
    END IF;
END $$;

-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Function to check if user is admin
CREATE OR REPLACE FUNCTION public.is_admin(user_id uuid)
RETURNS boolean AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM public.users
        WHERE id = user_id AND role = 'admin'
    );
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION public.is_admin IS 'Checks if a user has admin role';

-- ============================================
-- ADMIN DASHBOARD RPC FUNCTIONS
-- ============================================

-- 1. Get dashboard statistics
CREATE OR REPLACE FUNCTION get_dashboard_stats()
RETURNS json
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    total_users int;
    new_users_24h int;
    total_modules_completed int;
    avg_progress decimal;
BEGIN
    -- Verify admin access
    IF NOT public.is_admin(auth.uid()) THEN
        RAISE EXCEPTION 'Access denied: Admin access required';
    END IF;

    -- Get total user count
    SELECT COUNT(*) INTO total_users FROM auth.users;

    -- Get new users in last 24 hours
    SELECT COUNT(*) INTO new_users_24h
    FROM auth.users
    WHERE created_at > (now() - interval '24 hours');

    -- Get total modules completed
    SELECT COUNT(*) INTO total_modules_completed
    FROM public.user_progress
    WHERE status = 'completed';

    -- Calculate average progress
    SELECT COALESCE(AVG(
        CASE
            WHEN array_length(nodes_completed, 1) IS NOT NULL
            THEN (array_length(nodes_completed, 1)::decimal / 
                  (SELECT COUNT(*) FROM learning_modules WHERE is_published = true)) * 100
            ELSE 0
        END
    ), 0) INTO avg_progress
    FROM public.user_progress;

    RETURN json_build_object(
        'total_users', total_users,
        'new_users_24h', new_users_24h,
        'total_modules_completed', total_modules_completed,
        'average_progress', avg_progress
    );
END;
$$;

COMMENT ON FUNCTION get_dashboard_stats IS 'Returns dashboard statistics for admins';

-- ============================================

-- 2. Get all users with progress
CREATE OR REPLACE FUNCTION get_all_users_with_progress(
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
                'role', COALESCE(u.role, 'user'),
                'is_active', COALESCE(u.is_active, true),
                'modules_completed', COALESCE(up.modules_completed, 0),
                'total_points', COALESCE(ups.total_points, 0),
                'level', COALESCE(ups.level, 1)
            )::json
        ) INTO result
        FROM auth.users u
        LEFT JOIN public.users u2 ON u.id = u2.id
        LEFT JOIN public.user_progress up ON u.id = up.user_id AND up.status = 'completed'
        LEFT JOIN public.user_profiles ups ON u.id = ups.user_id
        WHERE u.email ILIKE '%' || search_email || '%'
        GROUP BY u.id, u.email, u.display_name, u.created_at, u.role, u.is_active, up.modules_completed, ups.total_points, ups.level
        ORDER BY u.created_at DESC
        LIMIT limit_count OFFSET offset_count;
    ELSE
        SELECT json_agg(
            json_build_object(
                'id', u.id,
                'email', u.email,
                'display_name', u.display_name,
                'created_at', u.created_at,
                'role', COALESCE(u.role, 'user'),
                'is_active', COALESCE(u.is_active, true),
                'modules_completed', COALESCE(up.modules_completed, 0),
                'total_points', COALESCE(ups.total_points, 0),
                'level', COALESCE(ups.level, 1)
            )::json
        ) INTO result
        FROM auth.users u
        LEFT JOIN public.users u2 ON u.id = u2.id
        LEFT JOIN public.user_progress up ON u.id = up.user_id AND up.status = 'completed'
        LEFT JOIN public.user_profiles ups ON u.id = ups.user_id
        GROUP BY u.id, u.email, u.display_name, u.created_at, u.role, u.is_active, up.modules_completed, ups.total_points, ups.level
        ORDER BY u.created_at DESC
        LIMIT limit_count OFFSET offset_count;
    END IF;

    RETURN COALESCE(result, '[]'::json);
END;
$$;

COMMENT ON FUNCTION get_all_users_with_progress IS 'Returns list of users with their progress';

-- ============================================

-- 3. Get module statistics
CREATE OR REPLACE FUNCTION get_module_stats()
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

    SELECT json_agg(
        json_build_object(
            'module_id', m.id,
            'module_title', m.title,
            'total_enrolled', (
                SELECT COUNT(*) FROM public.user_progress up
                WHERE up.module_id = m.id
            ),
            'completed_count', (
                SELECT COUNT(*) FROM public.user_progress up
                WHERE up.module_id = m.id AND up.status = 'completed'
            ),
            'in_progress_count', (
                SELECT COUNT(*) FROM public.user_progress up
                WHERE up.module_id = m.id AND up.status = 'in_progress'
            )
        )::json
    ) INTO result
    FROM public.learning_modules m
    WHERE m.is_published = true
    ORDER BY m.display_order;

    RETURN COALESCE(result, '[]'::json);
END;
$$;

COMMENT ON FUNCTION get_module_stats IS 'Returns module-wise completion statistics';

-- ============================================

-- 4. Get user progress details
CREATE OR REPLACE FUNCTION get_user_progress_details(target_user_id uuid)
RETURNS json
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    user_info json;
    progress_info json;
BEGIN
    -- Verify admin access
    IF NOT public.is_admin(auth.uid()) THEN
        RAISE EXCEPTION 'Access denied: Admin access required';
    END IF;

    -- Get user information
    SELECT json_build_object(
        'id', u.id,
        'email', u.email,
        'display_name', u.display_name,
        'created_at', u.created_at,
        'role', COALESCE(u2.role, 'user'),
        'is_active', COALESCE(u2.is_active, true)
    ) INTO user_info
    FROM auth.users u
    LEFT JOIN public.users u2 ON u.id = u2.id
    WHERE u.id = target_user_id;

    -- Get user's progress
    SELECT json_agg(
        json_build_object(
            'module_id', up.module_id,
            'module_title', m.title,
            'status', up.status,
            'current_node', up.current_node_id,
            'nodes_completed', up.nodes_completed,
            'points_earned', up.points_earned,
            'started_at', up.started_at,
            'completed_at', up.completed_at
        )::json
    ) INTO progress_info
    FROM public.user_progress up
    JOIN public.learning_modules m ON up.module_id = m.id
    WHERE up.user_id = target_user_id;

    RETURN json_build_object(
        'user', COALESCE(user_info, '{}'::json),
        'progress', COALESCE(progress_info, '[]'::json)
    );
END;
$$;

COMMENT ON FUNCTION get_user_progress_details IS 'Returns detailed progress for a specific user';
