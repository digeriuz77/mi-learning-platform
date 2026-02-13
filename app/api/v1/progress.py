"""
Progress API endpoints

Handles user progress tracking and statistics.
"""
from fastapi import APIRouter, HTTPException, Depends
from supabase import Client
from typing import List

from app.core.supabase import get_supabase, get_supabase_admin
from app.core.auth import get_current_user, AuthContext
from app.core.helpers import get_user_profile
from app.models.progress import UserProgress, ProgressListResponse

router = APIRouter()


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
    # Use admin client to bypass RLS for user_progress operations
    # We've already validated the user through get_current_user
    supabase_admin = get_supabase_admin()

    # Get user profile
    profile = await get_user_profile(current_user.user_id, supabase_admin)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Profile not found"
        )

    # Get all progress - use admin client to bypass RLS
    progress_response = supabase_admin.table('user_progress') \
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
            dialogue_content = module_data.get('dialogue_content', {})
            total_nodes = len(dialogue_content.get('nodes', []))
            p.pop('learning_modules', None)
            
            # Calculate progress percentage for in-progress modules
            # Use nodes_visited if available, otherwise fall back to nodes_completed
            nodes_visited = p.get('nodes_visited', []) or []
            nodes_completed = p.get('nodes_completed', []) or []
            visited_count = len(nodes_visited) if nodes_visited else len(nodes_completed)
            progress_percentage = int((visited_count / total_nodes) * 100) if total_nodes > 0 else 0
            
            # For completed modules, use completion_score as the percentage
            # For in-progress, use calculated progress_percentage
            status = p.get('status', 'not_started')
            completion_score = p.get('completion_score', 0)
            
            # If in progress, show progress percentage; if completed, show completion score
            display_score = completion_score if status == 'completed' else progress_percentage
            progress_list.append(UserProgress(
                id=str(p['id']),
                module_id=str(p['module_id']),
                module_title=module_title,
                status=status,
                completion_score=display_score,
                points_earned=p.get('points_earned', 0),
                current_node_id=p.get('current_node_id'),
                nodes_completed=nodes_completed,
                techniques_demonstrated=p.get('techniques_demonstrated', {}),
                started_at=p.get('started_at'),
                completed_at=p.get('completed_at'),
                total_nodes=total_nodes
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
    # Use admin client to bypass RLS for user_progress operations
    # We've already validated the user through get_current_user
    supabase_admin = get_supabase_admin()
    
    response = supabase_admin.table('user_progress') \
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
    dialogue_content = module_data.get('dialogue_content', {}) if module_data else {}
    total_nodes = len(dialogue_content.get('nodes', []))
    
    # Calculate progress percentage for in-progress modules
    # Use nodes_visited if available, otherwise fall back to nodes_completed
    nodes_visited = p.get('nodes_visited', []) or []
    nodes_completed = p.get('nodes_completed', []) or []
    visited_count = len(nodes_visited) if nodes_visited else len(nodes_completed)
    progress_percentage = int((visited_count / total_nodes) * 100) if total_nodes > 0 else 0
    
    # For completed modules, use completion_score; for in-progress, use progress percentage
    status = p.get('status', 'not_started')
    completion_score = p.get('completion_score', 0)
    display_score = completion_score if status == 'completed' else progress_percentage
    return UserProgress(
        id=str(p['id']),
        module_id=str(p['module_id']),
        module_title=module_title,
        status=status,
        completion_score=display_score,
        points_earned=p.get('points_earned', 0),
        current_node_id=p.get('current_node_id'),
        nodes_completed=nodes_completed,
        techniques_demonstrated=p.get('techniques_demonstrated', {}),
        started_at=p.get('started_at'),
        completed_at=p.get('completed_at'),
        total_nodes=total_nodes
    )
