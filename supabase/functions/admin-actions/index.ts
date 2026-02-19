import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"

interface AdminActionRequest {
    action: 'promote_to_admin' | 'demote_from_admin' | 'ban_user' | 'unban_user' | 'delete_user' | 'update_user_role' | 'reset_user_progress' | 'reset_all_progress'
    targetUserId?: string
    newRole?: string
}

serve(async (req: Request) => {
    // 1. Create a client for the user invoking the function
    const authHeader = req.headers.get('Authorization')
    if (!authHeader) {
        return new Response(JSON.stringify({ error: 'Missing authorization header' }), { status: 401 })
    }

    const supabaseClient = createClient(
        Deno.env.get('SUPABASE_URL') ?? '',
        Deno.env.get('SUPABASE_ANON_KEY') ?? '',
        { global: { headers: { Authorization: authHeader } } }
    )

    // 2. Get the current user and verify they are an admin
    const { data: { user: currentUser }, error: authError } = await supabaseClient.auth.getUser()

    if (authError || !currentUser) {
        return new Response(JSON.stringify({ error: 'Unauthorized: Invalid token' }), { status: 401 })
    }

    // Check if the caller is an admin
    const { data: profile, error: profileError } = await supabaseClient
        .from('user_profiles')
        .select('role')
        .eq('user_id', currentUser.id)
        .single()

    if (profileError || profile?.role !== 'admin') {
        return new Response(JSON.stringify({ error: 'Forbidden: Admin access required' }), { status: 403 })
    }

// 3. Parse the request body
    const { action, targetUserId, newRole }: AdminActionRequest = await req.json()

    // Actions that don't require targetUserId
    const noTargetRequired = ['reset_all_progress'];
    
    if (!action) {
        return new Response(JSON.stringify({ error: 'Missing action parameter' }), { status: 400 })
    }
    
    if (!noTargetRequired.includes(action) && !targetUserId) {
        return new Response(JSON.stringify({ error: 'Missing target user ID' }), { status: 400 })
    }

    // Prevent self-modification
    if (targetUserId && targetUserId === currentUser.id) {
        return new Response(JSON.stringify({ error: 'Cannot perform this action on yourself' }), { status: 400 })
    }

    try {
        // 4. Create the ADMIN client (Service Role) for privileged operations
        const supabaseAdmin = createClient(
            Deno.env.get('SUPABASE_URL') ?? '',
            Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
        )

// 5. Perform the requested action
    switch (action) {
        case 'promote_to_admin': {
            const { error: updateError } = await supabaseAdmin
                .from('user_profiles')
                .update({ role: 'admin', updated_at: new Date().toISOString() })
                .eq('user_id', targetUserId!)

            if (updateError) throw updateError
            return new Response(JSON.stringify({ message: 'User promoted to admin' }), { status: 200 })
        }

        case 'demote_from_admin': {
            // Ensure at least one admin remains
            const { count } = await supabaseAdmin
                .from('user_profiles')
                .select('user_id', { count: 'exact', head: true })
                .eq('role', 'admin')

            if (count <= 1) {
                return new Response(JSON.stringify({ error: 'Cannot demote the last admin' }), { status: 400 })
            }

            const { error: updateError } = await supabaseAdmin
                .from('user_profiles')
                .update({ role: 'user', updated_at: new Date().toISOString() })
                .eq('user_id', targetUserId!)

            if (updateError) throw updateError
            return new Response(JSON.stringify({ message: 'Admin demoted to user' }), { status: 200 })
        }

        case 'ban_user': {
            // Note: user_profiles doesn't have is_active column, skipping ban feature
            return new Response(JSON.stringify({ message: 'Ban feature not implemented for user_profiles table' }), { status: 200 })
        }

        case 'unban_user': {
            // Note: user_profiles doesn't have is_active column, skipping unban feature
            return new Response(JSON.stringify({ message: 'Unban feature not implemented for user_profiles table' }), { status: 200 })
        }

        case 'delete_user': {
            // Delete the user from auth.users (this will cascade to profiles due to FK)
            const { error: deleteError } = await supabaseAdmin.auth.admin.deleteUser(targetUserId!)
            if (deleteError) throw deleteError
            return new Response(JSON.stringify({ message: 'User deleted permanently' }), { status: 200 })
        }

        case 'update_user_role': {
            if (!newRole || !['user', 'admin', 'moderator'].includes(newRole)) {
                return new Response(JSON.stringify({ error: 'Invalid role' }), { status: 400 })
            }

            const { error: updateError } = await supabaseAdmin
                .from('user_profiles')
                .update({ role: newRole, updated_at: new Date().toISOString() })
                .eq('user_id', targetUserId!)

            if (updateError) throw updateError
            return new Response(JSON.stringify({ message: `User role updated to ${newRole}` }), { status: 200 })
        }

        case 'reset_user_progress': {
            const targetId = targetUserId
            if (!targetId) {
                return new Response(JSON.stringify({ error: 'Missing target user ID' }), { status: 400 })
            }

            // Delete user's progress records
            const { error: deleteProgressError } = await supabaseAdmin
                .from('user_progress')
                .delete()
                .eq('user_id', targetId)

            if (deleteProgressError) throw deleteProgressError

            // Delete user's dialogue attempts
            const { error: deleteAttemptsError } = await supabaseAdmin
                .from('dialogue_attempts')
                .delete()
                .eq('user_id', targetId)

            if (deleteAttemptsError) throw deleteAttemptsError

            // Reset user's profile stats (use user_id for lookup)
            const { error: resetProfileError } = await supabaseAdmin
                .from('user_profiles')
                .update({
                    total_points: 0,
                    level: 1,
                    modules_completed: 0,
                    change_talk_evoked: 0,
                    reflections_offered: 0,
                    technique_mastery: {},
                    updated_at: new Date().toISOString()
                })
                .eq('user_id', targetId)

            if (resetProfileError) throw resetProfileError

            return new Response(JSON.stringify({ message: 'User progress reset successfully' }), { status: 200 })
        }

        case 'reset_all_progress': {
            // Get all user IDs from user_profiles
            const { data: allUsers, error: usersError } = await supabaseAdmin
                .from('user_profiles')
                .select('user_id')

            if (usersError) throw usersError

            if (!allUsers || allUsers.length === 0) {
                return new Response(JSON.stringify({ message: 'No users to reset' }), { status: 200 })
            }

            const userIds = allUsers.map(u => u.user_id)

            // Delete all progress records
            const { error: deleteProgressError } = await supabaseAdmin
                .from('user_progress')
                .delete()
                .in('user_id', userIds)

            if (deleteProgressError) throw deleteProgressError

            // Delete all dialogue attempts
            const { error: deleteAttemptsError } = await supabaseAdmin
                .from('dialogue_attempts')
                .delete()
                .in('user_id', userIds)

            if (deleteAttemptsError) throw deleteAttemptsError

            // Reset all profiles
            const { error: resetProfilesError } = await supabaseAdmin
                .from('user_profiles')
                .update({
                    total_points: 0,
                    level: 1,
                    modules_completed: 0,
                    change_talk_evoked: 0,
                    reflections_offered: 0,
                    technique_mastery: {},
                    updated_at: new Date().toISOString()
                })

            if (resetProfilesError) throw resetProfilesError

            return new Response(JSON.stringify({ message: `Reset progress for ${userIds.length} users` }), { status: 200 })
        }

        default:
                return new Response(JSON.stringify({ error: 'Invalid action' }), { status: 400 })
        }
    } catch (error: any) {
        console.error('Admin action error:', error)
        return new Response(JSON.stringify({ error: error.message || 'Internal server error' }), { status: 500 })
    }
})

console.log('Admin actions Edge Function running')
