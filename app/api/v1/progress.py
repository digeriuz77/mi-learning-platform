"""
Progress API endpoints

Handles user progress tracking and statistics.
"""
from fastapi import APIRouter, HTTPException, Depends
from supabase import Client
from typing import List

from app.core.supabase import get_supabase, get_supabase_admin
from app.core.auth import get_current_user, AuthContext
from app.models.progress import UserProgress, ProgressListResponse

router = APIRouter()


async def get_user_profile(user_id: str, supabase_admin: Client):
    """Get user profile from user_profiles table"""
    response = supabase_admin.table('user_profiles').select('*').eq('user_id', user_id).execute()
    if response.data:
        return response.data[0]
    return None


# =====================================================
# Endpoints
# =====================================================

@router.get("", response_model=ProgressListResponse)
async def get_user_stats(
    current_user: AuthContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """
    Get user's overall statistics and all module progress.
    """
    supabase_admin = get_supabase_admin()

    # Get user profile
    profile = await get_user_profile(current_user.user_id, supabase_admin)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Profile not found"
        )

    # Get all progress
    progress_response = supabase.table('user_progress') \
        .select('*, learning_modules(id, title, dialogue_content)') \
        .eq('user_id', current_user.user_id) \
        .order('started_at', desc=True) \
        .execute()

    progress_list = []
    for p in progress_response.data:
        # Handle the joined data
        module_data = p.get('learning_modules')
        if module_data:
            module_title = module_data.get('title', 'Unknown Module')
            p.pop('learning_modules', None)

            progress_list.append(UserProgress(
                id=str(p['id']),
                module_id=str(p['module_id']),
                module_title=module_title,
                status=p.get('status', 'not_started'),
                completion_score=p.get('completion_score', 0),
                points_earned=p.get('points_earned', 0),
                current_node_id=p.get('current_node_id'),
                nodes_completed=p.get('nodes_completed', []),
                techniques_demonstrated=p.get('techniques_demonstrated', {}),
                started_at=p.get('started_at'),
                completed_at=p.get('completed_at')
            ))

    return ProgressListResponse(
        total_points=profile.get('total_points', 0),
        level=profile.get('level', 1),
        modules_completed=profile.get('modules_completed', 0),
        progress=progress_list
    )


@router.get("/{module_id}", response_model=UserProgress)
async def get_module_progress(
    module_id: str,
    current_user: AuthContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """
    Get progress for a specific module.
    """
    response = supabase.table('user_progress') \
        .select('*, learning_modules(id, title, dialogue_content)') \
        .eq('user_id', current_user.user_id) \
        .eq('module_id', module_id) \
        .execute()

    if not response.data:
        raise HTTPException(
            status_code=404,
            detail="Progress not found for this module"
        )

    p = response.data[0]
    module_data = p.get('learning_modules')
    module_title = module_data.get('title', 'Unknown Module') if module_data else 'Unknown Module'

    return UserProgress(
        id=str(p['id']),
        module_id=str(p['module_id']),
        module_title=module_title,
        status=p.get('status', 'not_started'),
        completion_score=p.get('completion_score', 0),
        points_earned=p.get('points_earned', 0),
        current_node_id=p.get('current_node_id'),
        nodes_completed=p.get('nodes_completed', []),
        techniques_demonstrated=p.get('techniques_demonstrated', {}),
        started_at=p.get('started_at'),
        completed_at=p.get('completed_at')
    )
