"""
Learning Modules API endpoints

Handles listing modules, getting module details, and starting a module.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from supabase import Client
from typing import List
import logging

from app.core.supabase import get_supabase, get_supabase_admin
from app.core.auth import get_current_user, AuthContext
from app.models.modules import ModuleResponse, ModuleListResponse
from app.services.scoring_service import ScoringService

router = APIRouter()
logger = logging.getLogger(__name__)


# =====================================================
# Helper Functions
# =====================================================


async def get_user_module_progress(
    user_id: str, module_id: str, supabase: Client
) -> dict:
    """Get user progress for a specific module"""
    response = (
        supabase.table("user_progress")
        .select("*")
        .eq("user_id", user_id)
        .eq("module_id", module_id)
        .execute()
    )
    if response.data:
        return response.data[0]
    return None


async def get_all_user_progress(user_id: str, supabase: Client) -> List[dict]:
    """Get all progress for a user"""
    response = (
        supabase.table("user_progress").select("*").eq("user_id", user_id).execute()
    )
    return response.data


# =====================================================
# Endpoints
# =====================================================


@router.get("", response_model=ModuleListResponse)
async def list_modules(
    current_user: AuthContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    """
    List all published learning modules with user progress.
    """
    # Get all modules
    modules_response = (
        supabase.table("learning_modules")
        .select("*")
        .eq("is_published", True)
        .order("display_order")
        .execute()
    )

    # Get all user progress
    user_progress = await get_all_user_progress(current_user.user_id, supabase)
    progress_map = {p["module_id"]: p for p in user_progress}

    modules = []
    for module in modules_response.data:
        module_data = {**module, "id": str(module["id"])}

        # Add user progress if exists
        if module["id"] in progress_map:
            progress = progress_map[module["id"]]
            module_data["user_status"] = progress["status"]
            module_data["user_score"] = progress.get("completion_score", 0)
            module_data["user_points_earned"] = progress.get("points_earned", 0)

        modules.append(ModuleResponse(**module_data))

    return ModuleListResponse(modules=modules, total=len(modules))


@router.get("/{module_id}", response_model=ModuleResponse)
async def get_module(
    module_id: str,
    current_user: AuthContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    """
    Get details of a specific module.
    """
    response = (
        supabase.table("learning_modules").select("*").eq("id", module_id).execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Module not found"
        )

    module = response.data[0]
    module_data = {**module, "id": str(module["id"])}

    # Add user progress if exists
    progress = await get_user_module_progress(current_user.user_id, module_id, supabase)
    if progress:
        module_data["user_status"] = progress["status"]
        module_data["user_score"] = progress.get("completion_score", 0)
        module_data["user_points_earned"] = progress.get("points_earned", 0)

    return ModuleResponse(**module_data)


@router.post("/{module_id}/start", status_code=status.HTTP_201_CREATED)
async def start_module(
    module_id: str,
    current_user: AuthContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    """
    Start a learning module. Creates a new progress record.
    """
    logger.info(f"[MODULES] User {current_user.user_id} starting module {module_id}")

    # Check if module exists
    logger.debug(f"[MODULES] Checking if module {module_id} exists")
    module_response = (
        supabase.table("learning_modules").select("*").eq("id", module_id).execute()
    )
    if not module_response.data:
        logger.warning(f"[MODULES] Module {module_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Module not found"
        )

    logger.debug(f"[MODULES] Module {module_id} found, checking existing progress")

    # Check if already started
    existing_progress = await get_user_module_progress(
        current_user.user_id, module_id, supabase
    )
    if existing_progress:
        logger.debug(
            f"[MODULES] Found existing progress: {existing_progress.get('id')}"
        )
        if existing_progress["status"] == "completed":
            # Return information about completed module with option to restart
            return {
                "message": "Module already completed",
                "progress_id": str(existing_progress["id"]),
                "current_node_id": existing_progress["current_node_id"],
                "status": "completed",
                "completion_score": existing_progress.get("completion_score", 0),
                "points_earned": existing_progress.get("points_earned", 0),
                "can_restart": True
            }
        logger.info(
            f"[MODULES] Returning existing progress for user {current_user.user_id}"
        )
        return {
            "message": "Module already in progress",
            "progress_id": str(existing_progress["id"]),
            "current_node_id": existing_progress["current_node_id"],
            "status": "in_progress",
            "nodes_completed": existing_progress.get("nodes_completed", []),
        }

    # Get dialogue content to find start node
    module = module_response.data[0]
    dialogue_content = module.get("dialogue_content", {})
    start_node = dialogue_content.get("start_node", "node_1")
    logger.info(
        f"[MODULES] Creating new progress for module {module_id}, start_node: {start_node}"
    )

    # Create progress record
    try:
        progress_response = (
            supabase.table("user_progress")
            .insert(
                {
                    "user_id": current_user.user_id,
                    "module_id": module_id,
                    "status": "in_progress",
                    "current_node_id": start_node,
                }
            )
            .execute()
        )
        logger.info(
            f"[MODULES] Progress created: {progress_response.data[0].get('id')}"
        )
    except Exception as e:
        logger.error(f"[MODULES] Failed to insert progress: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create progress: {str(e)}",
        )

    progress = progress_response.data[0]

    return {
        "message": "Module started",
        "progress_id": str(progress["id"]),
        "current_node_id": progress["current_node_id"],
    }

    # Create progress record
    progress_response = (
        supabase.table("user_progress")
        .insert(
            {
                "user_id": current_user.user_id,
                "module_id": module_id,
                "status": "in_progress",
                "current_node_id": start_node,
            }
        )
        .execute()
    )

    progress = progress_response.data[0]

    return {
        "message": "Module started",
        "progress_id": str(progress["id"]),
        "current_node_id": progress["current_node_id"],
    }


@router.post("/{module_id}/restart")
async def restart_module(
    module_id: str,
    current_user: AuthContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    """
    Restart a module by resetting progress.
    """
    # Check if module exists
    module_response = (
        supabase.table("learning_modules").select("*").eq("id", module_id).execute()
    )
    if not module_response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Module not found"
        )

    # Get dialogue content to find start node
    module = module_response.data[0]
    dialogue_content = module.get("dialogue_content", {})
    start_node = dialogue_content.get("start_node", "node_1")

    # Check for existing progress
    existing_progress = await get_user_module_progress(
        current_user.user_id, module_id, supabase
    )

    if existing_progress:
        # Get the points that were earned in this module to deduct from user profile
        old_points = existing_progress.get("points_earned", 0)
        was_completed = existing_progress.get("status") == "completed"
        
        # Reset existing progress using authenticated client
        try:
            update_response = (
                supabase.table("user_progress")
                .update(
                    {
                        "status": "in_progress",
                        "current_node_id": start_node,
                        "nodes_completed": [],
                        "points_earned": 0,
                        "completion_score": 0,
                        "techniques_demonstrated": {},
                        "completed_at": None,
                    }
                )
                .eq("id", existing_progress["id"])
                .execute()
            )
            logger.info(f"[MODULES] Progress reset successfully for module {module_id}")
            
            # Deduct points from user profile if module was previously completed
            if old_points > 0:
                try:
                    supabase_admin = get_supabase_admin()
                    profile_response = supabase_admin.table("user_profiles").select("*").eq("user_id", current_user.user_id).execute()
                    if profile_response.data:
                        profile = profile_response.data[0]
                        new_total = max(0, profile.get("total_points", 0) - old_points)
                        new_modules_completed = profile.get("modules_completed", 0)
                        if was_completed and new_modules_completed > 0:
                            new_modules_completed -= 1
                        
                        supabase_admin.table("user_profiles").update({
                            "total_points": new_total,
                            "modules_completed": new_modules_completed,
                            "level": ScoringService.calculate_level(new_total)
                        }).eq("user_id", current_user.user_id).execute()
                        logger.info(f"[MODULES] Deducted {old_points} points from user profile on restart")
                except Exception as e:
                    logger.warning(f"[MODULES] Failed to deduct points from profile: {e}")
                    # Don't fail the restart if profile update fails
            
        except Exception as e:
            logger.error(f"[MODULES] Failed to reset progress: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to reset progress: {str(e)}",
            )

        return {
            "message": "Module restarted",
            "progress_id": str(existing_progress["id"]),
            "current_node_id": start_node,
            "points_deducted": old_points,
        }
    else:
        # Create new progress
        progress_response = (
            supabase.table("user_progress")
            .insert(
                {
                    "user_id": current_user.user_id,
                    "module_id": module_id,
                    "status": "in_progress",
                    "current_node_id": start_node,
                }
            )
            .execute()
        )

        progress = progress_response.data[0]

        return {
            "message": "Module started",
            "progress_id": str(progress["id"]),
            "current_node_id": start_node,
        }
