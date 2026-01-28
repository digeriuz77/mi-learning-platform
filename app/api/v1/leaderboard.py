"""
Leaderboard API endpoints

Handles leaderboard rankings and user rankings.
"""
from fastapi import APIRouter, Depends
from supabase import Client
from typing import Optional

from app.core.supabase import get_supabase
from app.api.v1.auth import get_current_user, get_user_profile
from app.models.progress import LeaderboardResponse, LeaderboardEntry

router = APIRouter()


@router.get("", response_model=LeaderboardResponse)
async def get_leaderboard(
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """
    Get the leaderboard with top users by points.
    Includes the current user's rank if not in top list.
    """
    # Get top users
    response = supabase.table('user_profiles') \
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
        if profile['user_id'] == str(current_user.id):
            current_user_entry = entry

        entries.append(entry)

    # If current user not in top list, get their rank
    if not current_user_entry:
        user_profile = await get_user_profile(str(current_user.id), supabase)
        if user_profile:
            # Get user's rank
            rank_response = supabase.table('user_profiles') \
                .select('id') \
                .gt('total_points', user_profile.get('total_points', 0)) \
                .execute()

            rank = len(rank_response.data) + 1

            current_user_entry = LeaderboardEntry(
                rank=rank,
                display_name=user_profile.get('display_name') or f"User {user_profile['user_id'][:8]}",
                total_points=user_profile.get('total_points', 0),
                level=user_profile.get('level', 1),
                modules_completed=user_profile.get('modules_completed', 0)
            )

    return LeaderboardResponse(
        entries=entries,
        current_user=current_user_entry
    )


@router.get("/me")
async def get_my_rank(
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """
    Get the current user's rank on the leaderboard.
    """
    user_profile = await get_user_profile(str(current_user.id), supabase)
    if not user_profile:
        return {"rank": None, "message": "Profile not found"}

    # Count users with more points
    rank_response = supabase.table('user_profiles') \
        .select('id') \
        .gt('total_points', user_profile.get('total_points', 0)) \
        .execute()

    rank = len(rank_response.data) + 1

    return {
        "rank": rank,
        "total_points": user_profile.get('total_points', 0),
        "level": user_profile.get('level', 1),
        "modules_completed": user_profile.get('modules_completed', 0)
    }
