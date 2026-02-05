import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"

interface AdminActionRequest {
    action: 'promote_to_admin' | 'demote_from_admin' | 'ban_user' | 'unban_user' | 'delete_user' | 'update_user_role'
    targetUserId: string
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
        .from('profiles')
        .select('role')
        .eq('id', currentUser.id)
        .single()

    if (profileError || profile?.role !== 'admin') {
        return new Response(JSON.stringify({ error: 'Forbidden: Admin access required' }), { status: 403 })
    }

    // 3. Parse the request body
    const { action, targetUserId, newRole }: AdminActionRequest = await req.json()

    if (!action || !targetUserId) {
        return new Response(JSON.stringify({ error: 'Missing required parameters' }), { status: 400 })
    }

    // Prevent self-modification
    if (targetUserId === currentUser.id) {
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
                    .from('profiles')
                    .update({ role: 'admin', updated_at: new Date().toISOString() })
                    .eq('id', targetUserId)

                if (updateError) throw updateError
                return new Response(JSON.stringify({ message: 'User promoted to admin' }), { status: 200 })
            }

            case 'demote_from_admin': {
                // Ensure at least one admin remains
                const { count } = await supabaseAdmin
                    .from('profiles')
                    .select('id', { count: 'exact', head: true })
                    .eq('role', 'admin')

                if (count <= 1) {
                    return new Response(JSON.stringify({ error: 'Cannot demote the last admin' }), { status: 400 })
                }

                const { error: updateError } = await supabaseAdmin
                    .from('profiles')
                    .update({ role: 'user', updated_at: new Date().toISOString() })
                    .eq('id', targetUserId)

                if (updateError) throw updateError
                return new Response(JSON.stringify({ message: 'Admin demoted to user' }), { status: 200 })
            }

            case 'ban_user': {
                // Update the profile to mark as inactive
                const { error: updateError } = await supabaseAdmin
                    .from('profiles')
                    .update({ is_active: false, updated_at: new Date().toISOString() })
                    .eq('id', targetUserId)

                if (updateError) throw updateError
                return new Response(JSON.stringify({ message: 'User banned' }), { status: 200 })
            }

            case 'unban_user': {
                const { error: updateError } = await supabaseAdmin
                    .from('profiles')
                    .update({ is_active: true, updated_at: new Date().toISOString() })
                    .eq('id', targetUserId)

                if (updateError) throw updateError
                return new Response(JSON.stringify({ message: 'User unbanned' }), { status: 200 })
            }

            case 'delete_user': {
                // Delete the user from auth.users (this will cascade to profiles due to FK)
                const { error: deleteError } = await supabaseAdmin.auth.admin.deleteUser(targetUserId)
                if (deleteError) throw deleteError
                return new Response(JSON.stringify({ message: 'User deleted permanently' }), { status: 200 })
            }

            case 'update_user_role': {
                if (!newRole || !['user', 'admin', 'moderator'].includes(newRole)) {
                    return new Response(JSON.stringify({ error: 'Invalid role' }), { status: 400 })
                }

                const { error: updateError } = await supabaseAdmin
                    .from('profiles')
                    .update({ role: newRole, updated_at: new Date().toISOString() })
                    .eq('id', targetUserId)

                if (updateError) throw updateError
                return new Response(JSON.stringify({ message: `User role updated to ${newRole}` }), { status: 200 })
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
