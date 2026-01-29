"""
Leaderboard API endpoints

Handles leaderboard rankings and user rankings.
"""
from fastapi import APIRouter, Depends
from supabase import Client
from typing import Optional

from app.core.supabase import get_supabase, get_supabase_admin
from app.core.auth import get_current_user, AuthContext
from app.models.progress import LeaderboardResponse, LeaderboardEntry

router = APIRouter()


@router.get("", response_model=LeaderboardResponse)
async def get_leaderboard(
    limit: int = 50,
    current_user: AuthContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """
    Get the leaderboard with top users by points.
    Includes the current user's rank if not in top list.
    """
    supabase_admin = get_supabase_admin()

    # Get top users
    response = supabase_admin.table('user_profiles') \
        .select('*') \
        .order('total_points', desc=True) \
        .order('created_at', desc=False) \
        .limit(limit) \
        .execute()

    entries = []
    current_user_entry = None

    for i, profile in enumerate(response.data, start=1):
        entry = LeaderboardEntry(
            rank=i,
            display_name=profile.get('display_name') or f"User {profile['user_id'][:8]}",
            total_points=profile.get('total_points', 0),
            level=profile.get('level', 1),
            modules_completed=profile.get('modules_completed', 0)
        )

        # Check if this is the current user
        if profile['user_id'] == current_user.user_id:
            current_user_entry = entry

        entries.append(entry)

    # If current user not in top list, get their rank
    if not current_user_entry:
        user_profile_response = supabase_admin.table('user_profiles') \
            .select('*') \
            .eq('user_id', current_user.user_id) \
            .execute()

        if user_profile_response.data:
            # Get user's rank by counting users with more points
            user_points = user_profile_response.data[0].get('total_points', 0)
            rank_response = supabase_admin.table('user_profiles') \
                .select('id') \
                .gt('total_points', user_points) \
                .execute()

            user_rank = len(rank_response.data) + 1

            current_user_entry = LeaderboardEntry(
                rank=user_rank,
                display_name=user_profile_response.data[0].get('display_name') or f"You",
                total_points=user_points,
                level=user_profile_response.data[0].get('level', 1),
                modules_completed=user_profile_response.data[0].get('modules_completed', 0)
            )

    return LeaderboardResponse(
        entries=entries,
        current_user=current_user_entry
    )
