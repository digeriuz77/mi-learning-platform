"""
Shared helper functions used across multiple API modules.
"""
from supabase import Client


async def get_user_profile(user_id: str, supabase_admin: Client):
    """Get user profile from user_profiles table.

    Args:
        user_id: The user's UUID
        supabase_admin: Supabase admin client (bypasses RLS)

    Returns:
        dict or None: The user profile data, or None if not found
    """
    response = supabase_admin.table('user_profiles').select('*').eq('user_id', user_id).execute()
    if response.data:
        return response.data[0]
    return None
