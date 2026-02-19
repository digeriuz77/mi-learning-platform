"""
Dialogue API endpoints

Handles dialogue node retrieval and choice submission.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, status
from supabase import Client
from typing import Optional

from app.core.supabase import get_supabase, get_supabase_admin
from app.core.auth import get_current_user, AuthContext
from app.core.helpers import get_user_profile
from app.api.v1.modules import get_user_module_progress
from app.services.scoring_service import ScoringService
from app.models.modules import NodeResponse, ChoiceSubmit, ChoiceFeedback
from app.models.progress import UserProgress

router = APIRouter()


async def get_module_by_id(module_id: str, supabase: Client) -> dict:
    """Get module by ID"""
    response = supabase.table("learning_modules").select("*").eq("id", module_id).execute()
    if not response.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    return response.data[0]


def find_dialogue_node(dialogue_content: dict, node_id: str) -> Optional[dict]:
    """Find a node in the dialogue tree"""
    nodes = dialogue_content.get("nodes", [])
    for node in nodes:
        if node.get("id") == node_id:
            return node
    return None


def get_node_number(dialogue_content: dict, node_id: str) -> int:
    """Get the sequential number of a node"""
    nodes = dialogue_content.get("nodes", [])
    for i, node in enumerate(nodes):
        if node.get("id") == node_id:
            return i + 1
    return 0


def get_technique_quality(choice: dict) -> str:
    """
    Determine the quality of a technique choice.

    Delegates to ScoringService.get_technique_quality() which is the single
    source of truth for technique quality classification.

    Returns:
        'excellent', 'good', 'acceptable', or 'poor'
    """
    return ScoringService.get_technique_quality(choice)


def is_correct_technique(choice: dict) -> bool:
    """Determine if a choice uses an acceptable or better MI technique"""
    quality = get_technique_quality(choice)
    return quality in ["excellent", "good", "acceptable"]


def evokes_change_talk(node: dict, choice: dict) -> bool:
    """Determine if a choice evokes change talk (simplified heuristic)"""
    feedback = choice.get("feedback", "").lower()
    technique = choice.get("technique", "").lower()

    # Check feedback for change talk indicators
    if any(
        kw in feedback for kw in ["change talk", "evoked", "sustain talk", "explores ambivalence", "deeper sharing"]
    ):
        return True

    # Check technique for change-talk evoking patterns
    if any(kw in technique for kw in ["open question", "reflection", "explor"]):
        return True

    return False


# =====================================================
# Endpoints
# =====================================================


@router.get("/module/{module_id}/node/{node_id}", response_model=NodeResponse)
async def get_dialogue_node(
    module_id: str,
    node_id: str,
    current_user: AuthContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    """
    Get a dialogue node for a module.

    Returns the patient statement and available practitioner choices.
    """
    # Get module
    module = await get_module_by_id(module_id, supabase)

    # Check user progress - use admin client to bypass RLS
    supabase_admin = get_supabase_admin()
    progress = await get_user_module_progress(current_user.user_id, module_id, supabase_admin)
    if not progress:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Module not started. Call /modules/{id}/start first"
        )

    # Find the node
    dialogue_content = module.get("dialogue_content", {})
    node = find_dialogue_node(dialogue_content, node_id)

    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Node {node_id} not found")

    # Check if user can retry this node (has attempted before)
    nodes_completed = progress.get("nodes_completed", [])
    can_retry = node_id in nodes_completed

    total_nodes = len(dialogue_content.get("nodes", []))
    current_node_number = get_node_number(dialogue_content, node_id)

    # P3-7: Track when user entered this node for time-on-task analytics
    supabase_admin.table("user_progress").update({"node_started_at": datetime.now(timezone.utc).isoformat()}).eq(
        "id", progress["id"]
    ).execute()

    return NodeResponse(
        node=node,
        module_id=module_id,
        progress_id=str(progress["id"]),
        current_node_number=current_node_number,
        total_nodes=total_nodes,
        can_retry=can_retry,
    )


@router.post("/submit", response_model=ChoiceFeedback)
async def submit_choice(
    choice_data: ChoiceSubmit,
    current_user: AuthContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    """
    Submit a dialogue choice and get feedback.

    Processes the user's choice, awards points, and returns the next node.
    """
    # Use admin client to bypass RLS for user_progress operations
    # We've already validated the user through get_current_user
    supabase_admin = get_supabase_admin()

    # Get module and progress
    module = await get_module_by_id(choice_data.module_id, supabase)
    progress = await get_user_module_progress(current_user.user_id, choice_data.module_id, supabase_admin)

    if not progress:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Module not started")

    # Validate that the submitted node matches the user's current position
    if choice_data.node_id != progress.get("current_node_id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Choice submission does not match your current node. Please refresh and try again.",
        )

    # Find the current node
    dialogue_content = module.get("dialogue_content", {})
    node = find_dialogue_node(dialogue_content, choice_data.node_id)

    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Node {choice_data.node_id} not found")

    # Find the selected choice by ID (more reliable than text matching)
    choices = node.get("practitioner_choices", [])
    selected_choice = None

    for i, choice in enumerate(choices):
        choice_id = f"choice_{i}"
        if choice_id == choice_data.choice_id:
            selected_choice = choice
            break

    if not selected_choice:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid choice")

    # Determine technique quality and if evokes change talk
    technique_quality = get_technique_quality(selected_choice)
    is_correct = technique_quality != "poor"  # Correct if not poor
    evoked_ct = evokes_change_talk(node, selected_choice)

    # Get existing tracking lists
    nodes_completed = progress.get("nodes_completed", [])
    nodes_visited = progress.get("nodes_visited", [])  # Track all visited nodes
    technique_quality_counts = progress.get("technique_quality_counts", {})  # Track quality distribution

    # Track if this is the first attempt (for bonus points)
    is_first_attempt = choice_data.node_id not in nodes_completed

    # Calculate points using quality-based scoring
    points_earned = ScoringService.calculate_choice_points(
        is_correct=is_correct,
        is_first_attempt=is_first_attempt,
        evoked_change_talk=evoked_ct,
        technique_quality=technique_quality,
    )
    # Preserve the per-choice points before completion logic may reassign points_earned
    current_choice_points = points_earned

    # Record attempt - use admin client to bypass RLS
    node_entered_at = progress.get("node_started_at") or datetime.now(timezone.utc)
    time_spent = 0
    if isinstance(node_entered_at, str):
        from datetime import datetime as dt

        entered = dt.fromisoformat(node_entered_at.replace("Z", "+00:00"))
        time_spent = int((datetime.now(timezone.utc) - entered).total_seconds())

    supabase_admin.table("dialogue_attempts").insert(
        {
            "user_id": current_user.user_id,
            "module_id": choice_data.module_id,
            "progress_id": progress["id"],
            "node_id": choice_data.node_id,
            "choice_id": choice_data.choice_id,
            "choice_text": choice_data.choice_text,
            "technique": choice_data.technique,
            "is_correct_technique": is_correct,
            "feedback_text": selected_choice.get("feedback", ""),
            "evoked_change_talk": evoked_ct,
            "points_earned": points_earned,
            "node_entered_at": node_entered_at.isoformat()
            if hasattr(node_entered_at, "isoformat")
            else node_entered_at,
            "time_spent_seconds": time_spent,
        }
    ).execute()

    # Update progress - track both completed and visited
    new_nodes_completed = list(nodes_completed)
    new_nodes_visited = list(nodes_visited) if nodes_visited else []
    new_technique_quality_counts = (
        dict(technique_quality_counts)
        if technique_quality_counts
        else {"excellent": 0, "good": 0, "acceptable": 0, "poor": 0}
    )

    # Add to completed if first attempt and correct technique
    if is_first_attempt and is_correct:
        new_nodes_completed.append(choice_data.node_id)

    # Track all visited nodes (for progress calculation)
    if choice_data.node_id not in new_nodes_visited:
        new_nodes_visited.append(choice_data.node_id)

    # Track technique quality (for accuracy calculation)
    new_technique_quality_counts[technique_quality] = new_technique_quality_counts.get(technique_quality, 0) + 1

    next_node_id = selected_choice.get("next_node_id")

    total_nodes = len(dialogue_content.get("nodes", []))

    # Calculate progress percentage (how far through the module)
    visited_count = len(new_nodes_visited)
    progress_percentage = int((visited_count / total_nodes) * 100) if total_nodes > 0 else 0

    # Check if module is complete - check if next node is an ending node or no next node
    is_module_complete = False
    if next_node_id:
        # Check if the next node is an ending node
        next_node = find_dialogue_node(dialogue_content, next_node_id)
        if next_node and next_node.get("is_ending", False):
            is_module_complete = True
        elif next_node_id.startswith("node_end") or next_node_id == "end":
            is_module_complete = True
    else:
        # No next node means we've reached the end
        is_module_complete = True

    progress_status = progress["status"]
    completion_score = progress.get("completion_score", 0)

    if is_module_complete:
        progress_status = "completed"

        # Get max_points_available from module
        max_points_available = module.get("max_points_available")

        # Calculate completion score based on points earned vs max available
        # Note: Completion bonus is NOT added to points_earned for scoring
        total_points_earned = progress.get("points_earned", 0) + points_earned

        completion_score = ScoringService.calculate_completion_score(
            total_nodes=total_nodes,
            nodes_completed=len(new_nodes_completed),
            correct_choices=len(new_nodes_completed),  # Backward compatible
            nodes_visited=visited_count,
            technique_quality_counts=new_technique_quality_counts,
            points_earned=total_points_earned,
            max_points_available=max_points_available,
        )

        # P1-10: Fixed double-counting. total_points_earned already includes current
        # choice points + previous points. Use it directly instead of adding again.
        points_earned = total_points_earned

    # Update progress record
    if is_module_complete:
        # When module is complete, points_earned is already the total (previous + current)
        new_points_earned = points_earned
    else:
        # Normal case: add current choice points to existing progress points
        new_points_earned = progress.get("points_earned", 0) + points_earned

    update_data = {
        "current_node_id": next_node_id if not is_module_complete else choice_data.node_id,
        "nodes_completed": new_nodes_completed,
        "nodes_visited": new_nodes_visited,
        "technique_quality_counts": new_technique_quality_counts,
        "points_earned": new_points_earned,
    }

    if is_module_complete:
        update_data.update({"status": "completed", "completion_score": completion_score, "completed_at": "now()"})

    # Update progress record - use admin client to bypass RLS
    supabase_admin.table("user_progress").update(update_data).eq("id", progress["id"]).execute()

    # Update user profile
    # Only add the current choice's points to the profile total.
    # On completion, `points_earned` was reassigned to the full module total
    # (previous + current), but previous points were already added in earlier
    # submissions.  Use the original per-choice points for the profile update.
    profile = await get_user_profile(current_user.user_id, supabase_admin)
    if profile:
        new_total_points = profile.get("total_points", 0) + current_choice_points
        new_level = ScoringService.calculate_level(new_total_points)

        modules_completed = profile.get("modules_completed", 0)
        change_talk_evoked = profile.get("change_talk_evoked", 0) + (1 if evoked_ct else 0)

        supabase_admin.table("user_profiles").update(
            {
                "total_points": new_total_points,
                "level": new_level,
                "modules_completed": modules_completed + (1 if is_module_complete else 0),
                "change_talk_evoked": change_talk_evoked,
                "last_active_at": "now()",
            }
        ).eq("user_id", current_user.user_id).execute()

        return ChoiceFeedback(
            is_correct=is_correct,
            feedback_text=selected_choice.get("feedback", ""),
            points_earned=points_earned,
            evoked_change_talk=evoked_ct,
            next_node_id=next_node_id if not is_module_complete else None,
            is_module_complete=is_module_complete,
            completion_score=completion_score if is_module_complete else None,
            total_points=new_total_points,
            level=new_level,
            technique_quality=technique_quality,
            progress_percentage=progress_percentage,
            max_points_available=max_points_available,
        )

    # Fallback if no profile (shouldn't happen)
    return ChoiceFeedback(
        is_correct=is_correct,
        feedback_text=selected_choice.get("feedback", ""),
        points_earned=points_earned,
        evoked_change_talk=evoked_ct,
        next_node_id=next_node_id,
        is_module_complete=is_module_complete,
        technique_quality=technique_quality,
        progress_percentage=progress_percentage,
        max_points_available=module.get("max_points_available") if module else None,
    )
