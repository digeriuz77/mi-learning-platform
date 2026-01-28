"""
Progress API endpoints

Handles user progress tracking and statistics.
"""
from fastapi import APIRouter, HTTPException, Depends
from supabase import Client
from typing import List

from app.core.supabase import get_supabase
from app.api.v1.auth import get_current_user, get_user_profile
from app.models.progress import UserProgress, ProgressListResponse

router = APIRouter()


# =====================================================
# Endpoints
# =====================================================

@router.get("", response_model=ProgressListResponse)
async def get_user_stats(
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """
    Get user's overall statistics and all module progress.
"""
    # Get user profile
    profile = await get_user_profile(str(current_user.id), supabase)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Profile not found"
        )

    # Get all progress
    progress_response = supabase.table('user_progress') \
        .select('*, learning_modules(id, title, dialogue_content)') \
        .eq('user_id', str(current_user.id)) \
        .order('started_at', desc=True) \
        .execute()

    progress_list = []
    for p in progress_response.data:
        # Handle the joined data
        module_data = p.get('learning_modules')
        if module_data:
            module_title = module_data.get('title', 'Unknown Module')
            p.pop('learning_modules', None)
        else:
            # Fallback: fetch module separately
            module_resp = supabase.table('learning_modules').select('title').eq('id', p['module_id']).execute()
            module_title = module_resp.data[0].get('title', 'Unknown Module') if module_resp.data else 'Unknown Module'

        progress_list.append(UserProgress(
            id=str(p['id']),
            module_id=str(p['module_id']),
            module_title=module_title,
            status=p['status'],
            current_node_id=p['current_node_id'],
            nodes_completed=p.get('nodes_completed', []),
            points_earned=p.get('points_earned', 0),
            completion_score=p.get('completion_score', 0),
            techniques_demonstrated=p.get('techniques_demonstrated', {}),
            started_at=p['started_at'],
            completed_at=p.get('completed_at')
        ))

    return ProgressListResponse(
        progress=progress_list,
        total_points=profile.get('total_points', 0),
        level=profile.get('level', 1),
        modules_completed=profile.get('modules_completed', 0)
    )


@router.get("/modules", response_model=List[UserProgress])
async def get_all_progress(
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """
    Get all module progress for the current user.
"""
    progress_response = supabase.table('user_progress') \
        .select('*, learning_modules(id, title)') \
        .eq('user_id', str(current_user.id)) \
        .order('started_at', desc=True) \
        .execute()

    progress_list = []
    for p in progress_response.data:
        module_data = p.get('learning_modules')
        module_title = module_data.get('title', 'Unknown Module') if module_data else 'Unknown Module'
        p.pop('learning_modules', None)

        progress_list.append(UserProgress(
            id=str(p['id']),
            module_id=str(p['module_id']),
            module_title=module_title,
            status=p['status'],
            current_node_id=p['current_node_id'],
            nodes_completed=p.get('nodes_completed', []),
            points_earned=p.get('points_earned', 0),
            completion_score=p.get('completion_score', 0),
            techniques_demonstrated=p.get('techniques_demonstrated', {}),
            started_at=p['started_at'],
            completed_at=p.get('completed_at')
        ))

    return progress_list
