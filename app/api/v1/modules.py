"""
Learning Modules API endpoints

Handles listing modules, getting module details, and starting a module.
"""
from fastapi import APIRouter, HTTPException, Depends, status
from supabase import Client
from typing import List

from app.core.supabase import get_supabase
from app.api.v1.auth import get_current_user
from app.models.modules import ModuleResponse, ModuleListResponse

router = APIRouter()


# =====================================================
# Helper Functions
# =====================================================

async def get_user_module_progress(
    user_id: str,
    module_id: str,
    supabase: Client
) -> dict:
    """Get user progress for a specific module"""
    response = supabase.table('user_progress').select('*').eq('user_id', user_id).eq('module_id', module_id).execute()
    if response.data:
        return response.data[0]
    return None


async def get_all_user_progress(
    user_id: str,
    supabase: Client
) -> List[dict]:
    """Get all progress for a user"""
    response = supabase.table('user_progress').select('*').eq('user_id', user_id).execute()
    return response.data


# =====================================================
# Endpoints
# =====================================================

@router.get("", response_model=ModuleListResponse)
async def list_modules(
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """
    List all published learning modules with user progress.
    """
    # Get all modules
    modules_response = supabase.table('learning_modules').select('*').eq('is_published', True).order('display_order').execute()

    # Get all user progress
    user_progress = await get_all_user_progress(str(current_user.id), supabase)
    progress_map = {p['module_id']: p for p in user_progress}

    modules = []
    for module in modules_response.data:
        module_data = {
            **module,
            'id': str(module['id'])
        }

        # Add user progress if exists
        if module['id'] in progress_map:
            progress = progress_map[module['id']]
            module_data['user_status'] = progress['status']
            module_data['user_score'] = progress.get('completion_score', 0)
            module_data['user_points_earned'] = progress.get('points_earned', 0)

        modules.append(ModuleResponse(**module_data))

    return ModuleListResponse(modules=modules, total=len(modules))


@router.get("/{module_id}", response_model=ModuleResponse)
async def get_module(
    module_id: str,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """
    Get details of a specific module.
    """
    response = supabase.table('learning_modules').select('*').eq('id', module_id).execute()

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module not found"
        )

    module = response.data[0]
    module_data = {
        **module,
        'id': str(module['id'])
    }

    # Add user progress if exists
    progress = await get_user_module_progress(str(current_user.id), module_id, supabase)
    if progress:
        module_data['user_status'] = progress['status']
        module_data['user_score'] = progress.get('completion_score', 0)
        module_data['user_points_earned'] = progress.get('points_earned', 0)

    return ModuleResponse(**module_data)


@router.post("/{module_id}/start", status_code=status.HTTP_201_CREATED)
async def start_module(
    module_id: str,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """
    Start a learning module. Creates a new progress record.
    """
    # Check if module exists
    module_response = supabase.table('learning_modules').select('*').eq('id', module_id).execute()
    if not module_response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module not found"
        )

    # Check if already started
    existing_progress = await get_user_module_progress(str(current_user.id), module_id, supabase)
    if existing_progress:
        if existing_progress['status'] == 'completed':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Module already completed. Start a new attempt?"
            )
        return {
            "message": "Module already in progress",
            "progress_id": str(existing_progress['id']),
            "current_node_id": existing_progress['current_node_id']
        }

    # Get dialogue content to find start node
    module = module_response.data[0]
    dialogue_content = module.get('dialogue_content', {})
    start_node = dialogue_content.get('start_node', 'node_1')

    # Create progress record
    progress_response = supabase.table('user_progress').insert({
        'user_id': str(current_user.id),
        'module_id': module_id,
        'status': 'in_progress',
        'current_node_id': start_node
    }).execute()

    progress = progress_response.data[0]

    return {
        "message": "Module started",
        "progress_id": str(progress['id']),
        "current_node_id": progress['current_node_id']
    }


@router.post("/{module_id}/restart")
async def restart_module(
    module_id: str,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """
    Restart a module by resetting progress.
    """
    # Check if module exists
    module_response = supabase.table('learning_modules').select('*').eq('id', module_id).execute()
    if not module_response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module not found"
        )

    # Get dialogue content to find start node
    module = module_response.data[0]
    dialogue_content = module.get('dialogue_content', {})
    start_node = dialogue_content.get('start_node', 'node_1')

    # Check for existing progress
    existing_progress = await get_user_module_progress(str(current_user.id), module_id, supabase)

    if existing_progress:
        # Reset existing progress
        supabase.table('user_progress').update({
            'status': 'in_progress',
            'current_node_id': start_node,
            'nodes_completed': [],
            'points_earned': 0,
            'completion_score': 0,
            'techniques_demonstrated': {},
            'completed_at': None
        }).eq('id', existing_progress['id']).execute()

        return {
            "message": "Module restarted",
            "progress_id": str(existing_progress['id']),
            "current_node_id": start_node
        }
    else:
        # Create new progress
        progress_response = supabase.table('user_progress').insert({
            'user_id': str(current_user.id),
            'module_id': module_id,
            'status': 'in_progress',
            'current_node_id': start_node
        }).execute()

        progress = progress_response.data[0]

        return {
            "message": "Module started",
            "progress_id": str(progress['id']),
            "current_node_id": start_node
        }
