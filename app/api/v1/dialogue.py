"""
Dialogue API endpoints

Handles dialogue node retrieval and choice submission.
"""
from fastapi import APIRouter, HTTPException, Depends, status
from supabase import Client
from typing import Optional

from app.core.supabase import get_supabase, get_supabase_admin
from app.core.auth import get_current_user, AuthContext
from app.api.v1.modules import get_user_module_progress
from app.services.scoring_service import ScoringService
from app.models.modules import NodeResponse, ChoiceSubmit, ChoiceFeedback
from app.models.progress import UserProgress

router = APIRouter()


# =====================================================
# Helper Functions
# =====================================================

async def get_user_profile(user_id: str, supabase_admin: Client):
    """Get user profile from user_profiles table"""
    response = supabase_admin.table('user_profiles').select('*').eq('user_id', user_id).execute()
    if response.data:
        return response.data[0]
    return None


async def get_module_by_id(module_id: str, supabase: Client) -> dict:
    """Get module by ID"""
    response = supabase.table('learning_modules').select('*').eq('id', module_id).execute()
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module not found"
        )
    return response.data[0]


def find_dialogue_node(dialogue_content: dict, node_id: str) -> Optional[dict]:
    """Find a node in the dialogue tree"""
    nodes = dialogue_content.get('nodes', [])
    for node in nodes:
        if node.get('id') == node_id:
            return node
    return None


def get_node_number(dialogue_content: dict, node_id: str) -> int:
    """Get the sequential number of a node"""
    nodes = dialogue_content.get('nodes', [])
    for i, node in enumerate(nodes):
        if node.get('id') == node_id:
            return i + 1
    return 0


def is_correct_technique(choice: dict) -> bool:
    """Determine if a choice uses the correct MI technique"""
    technique = choice.get('technique', '').lower()
    # Non-MI techniques
    non_mi_keywords = ['non-mi', 'righting reflex', 'educating', 'lecturing',
                       'defending', 'challenging', 'questioning']
    return not any(keyword in technique for keyword in non_mi_keywords)


def evokes_change_talk(node: dict, choice: dict) -> bool:
    """Determine if a choice evokes change talk (simplified heuristic)"""
    feedback = choice.get('feedback', '').lower()
    return 'change talk' in feedback or 'evoked' in feedback


# =====================================================
# Endpoints
# =====================================================

@router.get("/module/{module_id}/node/{node_id}", response_model=NodeResponse)
async def get_dialogue_node(
    module_id: str,
    node_id: str,
    current_user: AuthContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """
    Get a dialogue node for a module.

    Returns the patient statement and available practitioner choices.
    """
    # Get module
    module = await get_module_by_id(module_id, supabase)

    # Check user progress
    progress = await get_user_module_progress(current_user.user_id, module_id, supabase)
    if not progress:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Module not started. Call /modules/{id}/start first"
        )

    # Find the node
    dialogue_content = module.get('dialogue_content', {})
    node = find_dialogue_node(dialogue_content, node_id)

    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node {node_id} not found"
        )

    # Check if user can retry this node (has attempted before)
    nodes_completed = progress.get('nodes_completed', [])
    can_retry = node_id in nodes_completed

    total_nodes = len(dialogue_content.get('nodes', []))
    current_node_number = get_node_number(dialogue_content, node_id)

    return NodeResponse(
        node=node,
        module_id=module_id,
        progress_id=str(progress['id']),
        current_node_number=current_node_number,
        total_nodes=total_nodes,
        can_retry=can_retry
    )


@router.post("/submit", response_model=ChoiceFeedback)
async def submit_choice(
    choice_data: ChoiceSubmit,
    current_user: AuthContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """
    Submit a dialogue choice and get feedback.

    Processes the user's choice, awards points, and returns the next node.
    """
    supabase_admin = get_supabase_admin()

    # Get module and progress
    module = await get_module_by_id(choice_data.module_id, supabase)
    progress = await get_user_module_progress(current_user.user_id, choice_data.module_id, supabase)

    if not progress:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Module not started"
        )

    # Find the current node
    dialogue_content = module.get('dialogue_content', {})
    node = find_dialogue_node(dialogue_content, choice_data.node_id)

    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node {choice_data.node_id} not found"
        )

    # Find the selected choice by ID (more reliable than text matching)
    choices = node.get('practitioner_choices', [])
    selected_choice = None

    for i, choice in enumerate(choices):
        choice_id = f"choice_{i}"
        if choice_id == choice_data.choice_id:
            selected_choice = choice
            break

    if not selected_choice:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid choice"
        )

    # Determine if correct and if evokes change talk
    is_correct = is_correct_technique(selected_choice)
    evoked_ct = evokes_change_talk(node, selected_choice)

    # Determine if first attempt
    nodes_completed = progress.get('nodes_completed', [])
    is_first_attempt = choice_data.node_id not in nodes_completed

    # Calculate points
    points_earned = ScoringService.calculate_choice_points(
        is_correct=is_correct,
        is_first_attempt=is_first_attempt,
        evoked_change_talk=evoked_ct
    )

    # Record attempt
    supabase.table('dialogue_attempts').insert({
        'user_id': current_user.user_id,
        'module_id': choice_data.module_id,
        'progress_id': progress['id'],
        'node_id': choice_data.node_id,
        'choice_id': choice_data.choice_id,
        'choice_text': choice_data.choice_text,
        'technique': choice_data.technique,
        'is_correct_technique': is_correct,
        'feedback_text': selected_choice.get('feedback', ''),
        'evoked_change_talk': evoked_ct,
        'points_earned': points_earned
    }).execute()

    # Update progress
    new_nodes_completed = list(nodes_completed)
    if is_first_attempt and is_correct:
        new_nodes_completed.append(choice_data.node_id)

    next_node_id = selected_choice.get('next_node_id')

    # Check if module is complete (no next node or reached end)
    is_module_complete = (
        not next_node_id or
        next_node_id.startswith('node_end') or
        next_node_id == 'end'
    )

    status = progress['status']
    completion_score = progress.get('completion_score', 0)

    if is_module_complete:
        status = 'completed'
        total_nodes = len(dialogue_content.get('nodes', []))
        correct_attempts = len(new_nodes_completed)
        completion_score = ScoringService.calculate_completion_score(
            total_nodes=total_nodes,
            nodes_completed=len(new_nodes_completed),
            correct_choices=correct_attempts
        )

        # Add completion bonus
        points_earned += ScoringService.MODULE_COMPLETION_BONUS

    # Update progress record
    update_data = {
        'current_node_id': next_node_id if not is_module_complete else choice_data.node_id,
        'nodes_completed': new_nodes_completed,
        'points_earned': progress.get('points_earned', 0) + points_earned,
    }

    if is_module_complete:
        update_data.update({
            'status': 'completed',
            'completion_score': completion_score,
            'completed_at': 'now()'
        })

    supabase.table('user_progress').update(update_data).eq('id', progress['id']).execute()

    # Update user profile
    profile = await get_user_profile(current_user.user_id, supabase_admin)
    if profile:
        new_total_points = profile.get('total_points', 0) + points_earned
        new_level = ScoringService.calculate_level(new_total_points)

        modules_completed = profile.get('modules_completed', 0)
        change_talk_evoked = profile.get('change_talk_evoked', 0) + (1 if evoked_ct else 0)

        supabase_admin.table('user_profiles').update({
            'total_points': new_total_points,
            'level': new_level,
            'modules_completed': modules_completed + (1 if is_module_complete else 0),
            'change_talk_evoked': change_talk_evoked,
            'last_active_at': 'now()'
        }).eq('user_id', current_user.user_id).execute()

        return ChoiceFeedback(
            is_correct=is_correct,
            feedback_text=selected_choice.get('feedback', ''),
            points_earned=points_earned,
            evoked_change_talk=evoked_ct,
            next_node_id=next_node_id if not is_module_complete else None,
            is_module_complete=is_module_complete,
            completion_score=completion_score if is_module_complete else None,
            total_points=new_total_points,
            level=new_level
        )

    # Fallback if no profile (shouldn't happen)
    return ChoiceFeedback(
        is_correct=is_correct,
        feedback_text=selected_choice.get('feedback', ''),
        points_earned=points_earned,
        evoked_change_talk=evoked_ct,
        next_node_id=next_node_id,
        is_module_complete=is_module_complete
    )
