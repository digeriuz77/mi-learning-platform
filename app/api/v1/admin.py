"""
Admin API Endpoints for MI Learning Platform

Provides admin dashboard data and user management actions.
All endpoints require admin role authentication.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel

from app.core.supabase import get_supabase_admin
from app.core.auth import get_current_user, AuthContext

router = APIRouter()
logger = logging.getLogger(__name__)


async def require_admin(auth_context: AuthContext = Depends(get_current_user)) -> AuthContext:
    """Dependency that verifies the current user has admin role."""
    try:
        supabase_admin = get_supabase_admin()
        response = (
            supabase_admin.table("users")
            .select("role")
            .eq("id", auth_context.user_id)
            .maybe_single()
            .execute()
        )
        if not response.data or response.data.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking admin role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error verifying admin access",
        )
    return auth_context


@router.get("/stats")
async def get_dashboard_stats(admin: AuthContext = Depends(require_admin)):
    """Get dashboard statistics."""
    try:
        supabase = get_supabase_admin()

        # Total users
        users_resp = supabase.table("users").select("id", count="exact").execute()
        total_users = users_resp.count or 0

        # Modules completed
        completed_resp = (
            supabase.table("user_progress")
            .select("id", count="exact")
            .eq("status", "completed")
            .execute()
        )
        total_modules_completed = completed_resp.count or 0

        # Average progress (simplified)
        progress_resp = supabase.table("user_progress").select("nodes_completed").execute()
        avg_progress = 0.0
        if progress_resp.data:
            completions = []
            for row in progress_resp.data:
                nodes = row.get("nodes_completed")
                if nodes and isinstance(nodes, list):
                    completions.append(len(nodes))
                else:
                    completions.append(0)
            if completions:
                avg_progress = sum(completions) / len(completions) * 10  # rough percentage

        return {
            "total_users": total_users,
            "new_users_24h": 0,
            "total_modules_completed": total_modules_completed,
            "average_progress": round(avg_progress, 1),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading dashboard stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users")
async def get_users(
    search: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    admin: AuthContext = Depends(require_admin),
):
    """Get users list with pagination and optional search."""
    try:
        supabase = get_supabase_admin()

        query = supabase.table("users").select(
            "id, email, display_name, role, is_active, created_at"
        )

        if search:
            query = query.ilike("email", f"%{search}%")

        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        response = query.execute()

        users = []
        for user in response.data or []:
            users.append({
                "id": user.get("id"),
                "email": user.get("email"),
                "display_name": user.get("display_name"),
                "role": user.get("role", "user"),
                "is_active": user.get("is_active", True),
                "created_at": user.get("created_at"),
                "modules_completed": 0,
                "total_points": 0,
            })

        return users
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading users: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/modules/stats")
async def get_module_stats(admin: AuthContext = Depends(require_admin)):
    """Get module completion statistics."""
    try:
        supabase = get_supabase_admin()

        modules_resp = (
            supabase.table("learning_modules")
            .select("id, title, display_order")
            .eq("is_published", True)
            .order("display_order")
            .execute()
        )

        stats = []
        for module in modules_resp.data or []:
            module_id = module["id"]

            total_resp = (
                supabase.table("user_progress")
                .select("id", count="exact")
                .eq("module_id", module_id)
                .execute()
            )
            completed_resp = (
                supabase.table("user_progress")
                .select("id", count="exact")
                .eq("module_id", module_id)
                .eq("status", "completed")
                .execute()
            )
            in_progress_resp = (
                supabase.table("user_progress")
                .select("id", count="exact")
                .eq("module_id", module_id)
                .eq("status", "in_progress")
                .execute()
            )

            stats.append({
                "module_id": module_id,
                "module_title": module.get("title", "Unknown"),
                "total_enrolled": total_resp.count or 0,
                "completed_count": completed_resp.count or 0,
                "in_progress_count": in_progress_resp.count or 0,
            })

        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading module stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class AdminActionRequest(BaseModel):
    action: str
    target_user_id: str
    new_role: Optional[str] = None


@router.post("/action")
async def perform_admin_action(
    request: AdminActionRequest,
    admin: AuthContext = Depends(require_admin),
):
    """Perform an admin action on a user."""
    try:
        supabase = get_supabase_admin()
        action = request.action
        target_id = request.target_user_id

        if action == "promote_to_admin":
            supabase.table("users").update({"role": "admin"}).eq("id", target_id).execute()
            return {"message": "User promoted to admin"}

        elif action == "demote_from_admin":
            supabase.table("users").update({"role": "user"}).eq("id", target_id).execute()
            return {"message": "User demoted from admin"}

        elif action == "update_user_role":
            if request.new_role not in ("user", "admin", "moderator"):
                raise HTTPException(status_code=400, detail="Invalid role")
            supabase.table("users").update({"role": request.new_role}).eq("id", target_id).execute()
            return {"message": f"User role updated to {request.new_role}"}

        elif action == "ban_user":
            supabase.table("users").update({"is_active": False}).eq("id", target_id).execute()
            return {"message": "User banned"}

        elif action == "unban_user":
            supabase.table("users").update({"is_active": True}).eq("id", target_id).execute()
            return {"message": "User unbanned"}

        elif action == "delete_user":
            supabase.table("users").delete().eq("id", target_id).execute()
            return {"message": "User deleted"}

        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {action}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin action error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
