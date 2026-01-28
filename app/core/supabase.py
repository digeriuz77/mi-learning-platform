"""
Supabase client for database and authentication operations
"""
from supabase import create_client, Client
from app.config import settings

_supabase_client: Client = None
_supabase_admin_client: Client = None


def get_supabase() -> Client:
    """
    Get a Supabase client with anon key permissions.

    Used for client-side operations like user sign up and sign in.

    Returns:
        Client: Initialized Supabase client
    """
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _supabase_client


def get_supabase_admin() -> Client:
    """
    Get a Supabase client with service role key permissions.

    Used for administrative operations that bypass RLS policies.

    Returns:
        Client: Initialized Supabase admin client
    """
    global _supabase_admin_client
    if _supabase_admin_client is None:
        _supabase_admin_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )
    return _supabase_admin_client
