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


async def require_admin(
    auth_context: AuthContext = Depends(get_current_user),
) -> AuthContext:
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
        progress_resp = (
            supabase.table("user_progress").select("nodes_completed").execute()
        )
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
                avg_progress = (
                    sum(completions) / len(completions) * 10
                )  # rough percentage

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
            users.append(
                {
                    "id": user.get("id"),
                    "email": user.get("email"),
                    "display_name": user.get("display_name"),
                    "role": user.get("role", "user"),
                    "is_active": user.get("is_active", True),
                    "created_at": user.get("created_at"),
                    "modules_completed": 0,
                    "total_points": 0,
                }
            )

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

            stats.append(
                {
                    "module_id": module_id,
                    "module_title": module.get("title", "Unknown"),
                    "total_enrolled": total_resp.count or 0,
                    "completed_count": completed_resp.count or 0,
                    "in_progress_count": in_progress_resp.count or 0,
                }
            )

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
            supabase.table("users").update({"role": "admin"}).eq(
                "id", target_id
            ).execute()
            return {"message": "User promoted to admin"}

        elif action == "demote_from_admin":
            supabase.table("users").update({"role": "user"}).eq(
                "id", target_id
            ).execute()
            return {"message": "User demoted from admin"}

        elif action == "update_user_role":
            if request.new_role not in ("user", "admin", "moderator"):
                raise HTTPException(status_code=400, detail="Invalid role")
            supabase.table("users").update({"role": request.new_role}).eq(
                "id", target_id
            ).execute()
            return {"message": f"User role updated to {request.new_role}"}

        elif action == "ban_user":
            supabase.table("users").update({"is_active": False}).eq(
                "id", target_id
            ).execute()
            return {"message": "User banned"}

        elif action == "unban_user":
            supabase.table("users").update({"is_active": True}).eq(
                "id", target_id
            ).execute()
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


@router.get("/practice/stats")
async def get_practice_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    admin: AuthContext = Depends(require_admin),
):
    """
    Get practice session analytics and MI adherence scores.

    Returns aggregated statistics from conversation analyses including:
    - Total practice sessions
    - Average MI adherence scores
    - Sessions with change talk evoked
    - Average conversation length
    """
    try:
        supabase = get_supabase_admin()

        # Call the database function for analytics
        result = supabase.rpc(
            "get_practice_analytics", {"start_date": start_date, "end_date": end_date}
        ).execute()

        if result.data and len(result.data) > 0:
            return result.data[0]

        # Return empty stats if no data
        return {
            "total_sessions": 0,
            "total_users": 0,
            "avg_overall_score": 0.0,
            "avg_trust_safety": 0.0,
            "avg_empathy": 0.0,
            "avg_empowerment": 0.0,
            "avg_mi_spirit": 0.0,
            "sessions_with_change_talk": 0,
            "avg_turns": 0.0,
        }

    except Exception as e:
        logger.error(f"Error loading practice stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/practice/analyses")
async def get_practice_analyses(
    limit: int = 50, offset: int = 0, admin: AuthContext = Depends(require_admin)
):
    """
    Get detailed practice analyses for review.

    Returns a list of conversation analyses with scores and summaries.
    """
    try:
        supabase = get_supabase_admin()

        result = (
            supabase.table("conversation_analyses")
            .select("id, session_id, user_id, persona_name, overall_score, created_at")
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        analyses = []
        for analysis in result.data or []:
            analyses.append(
                {
                    "id": analysis.get("id"),
                    "session_id": analysis.get("session_id"),
                    "user_id": analysis.get("user_id"),
                    "persona_name": analysis.get("persona_name", "Unknown"),
                    "overall_score": float(analysis.get("overall_score", 0)),
                    "created_at": analysis.get("created_at"),
                }
            )

        return {
            "analyses": analyses,
            "total": len(analyses),
            "limit": limit,
            "offset": offset,
        }

    except Exception as e:
        logger.error(f"Error loading practice analyses: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feedback/stats")
async def get_admin_feedback_stats(admin: AuthContext = Depends(require_admin)):
    """
    Get user feedback statistics.

    Returns aggregated feedback data including average score and distribution.
    """
    try:
        supabase = get_supabase_admin()

        # Call the database function for feedback stats
        result = supabase.rpc("get_feedback_stats").execute()

        if result.data and len(result.data) > 0:
            return result.data[0]

        # Return empty stats if no data
        return {
            "total_feedback": 0,
            "average_score": 0.0,
            "score_10_count": 0,
            "score_8_9_count": 0,
            "score_5_7_count": 0,
            "score_0_4_count": 0,
        }

    except Exception as e:
        logger.error(f"Error loading feedback stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feedback/recent")
async def get_recent_feedback(
    limit: int = 20, admin: AuthContext = Depends(require_admin)
):
    """
    Get recent user feedback submissions.

    Returns the most recent feedback with comments.
    """
    try:
        supabase = get_supabase_admin()

        result = (
            supabase.table("user_feedback")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        feedback_items = []
        for feedback in result.data or []:
            feedback_items.append(
                {
                    "id": feedback.get("id"),
                    "session_id": feedback.get("session_id"),
                    "persona_practiced": feedback.get("persona_practiced"),
                    "helpfulness_score": feedback.get("helpfulness_score"),
                    "what_was_helpful": feedback.get("what_was_helpful"),
                    "improvement_suggestions": feedback.get("improvement_suggestions"),
                    "created_at": feedback.get("created_at"),
                }
            )

        return {"feedback": feedback_items, "total": len(feedback_items)}

    except Exception as e:
        logger.error(f"Error loading recent feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/comprehensive")
async def get_comprehensive_analytics(admin: AuthContext = Depends(require_admin)):
    """
    Get comprehensive practice analytics.

    Returns aggregate statistics across all practice sessions.
    """
    try:
        supabase = get_supabase_admin()

        # Call the database function for comprehensive analytics
        result = supabase.rpc("get_comprehensive_practice_analytics").execute()

        if result.data:
            return result.data

        return {
            "total_sessions": 0,
            "total_users": 0,
            "avg_overall_score": 0.0,
            "avg_trust_safety": 0.0,
            "avg_empathy": 0.0,
            "avg_empowerment": 0.0,
            "avg_mi_spirit": 0.0,
            "sessions_with_change_talk": 0,
            "avg_turns": 0.0,
        }

    except Exception as e:
        logger.error(f"Error loading comprehensive analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/users")
async def get_users_with_analytics(
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    admin: AuthContext = Depends(require_admin),
):
    """
    Get all users with their practice analytics.

    Returns users with practice session counts and average scores.
    """
    try:
        supabase = get_supabase_admin()

        # Call the database function for users with analytics
        result = supabase.rpc(
            "get_all_users_with_practice_analytics",
            {"search_email": search, "limit_count": limit, "offset_count": offset},
        ).execute()

        if result.data:
            return {
                "users": result.data,
                "total": len(result.data),
                "limit": limit,
                "offset": offset,
            }

        return {"users": [], "total": 0, "limit": limit, "offset": offset}

    except Exception as e:
        logger.error(f"Error loading users with analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/leaderboard")
async def get_practice_analytics_leaderboard(
    limit: int = 20, admin: AuthContext = Depends(require_admin)
):
    """
    Get practice leaderboard - top users by performance.

    Returns top users sorted by average overall score.
    """
    try:
        supabase = get_supabase_admin()

        # Call the database function for leaderboard
        result = supabase.rpc(
            "get_practice_leaderboard", {"limit_count": limit}
        ).execute()

        if result.data:
            return {"leaderboard": result.data, "total": len(result.data)}

        return {"leaderboard": [], "total": 0}

    except Exception as e:
        logger.error(f"Error loading practice leaderboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/user/{user_id}")
async def get_user_detailed_analytics(
    user_id: str, admin: AuthContext = Depends(require_admin)
):
    """
    Get detailed analytics for a specific user.

    Returns user profile with practice analytics and recent analyses.
    """
    try:
        supabase = get_supabase_admin()

        # Get user basic info
        user_result = (
            supabase.table("users")
            .select("id, email, display_name, created_at, role, is_active")
            .eq("id", user_id)
            .single()
            .execute()
        )

        if not user_result.data:
            raise HTTPException(status_code=404, detail="User not found")

        user = user_result.data

        # Get user analytics
        analytics_result = supabase.rpc(
            "get_user_practice_analytics", {"p_user_id": user_id}
        ).execute()

        # Get recent analyses for this user
        analyses_result = (
            supabase.table("conversation_analyses")
            .select("id, session_id, persona_name, overall_score, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )

        return {
            "user": {
                "id": user.get("id"),
                "email": user.get("email"),
                "display_name": user.get("display_name"),
                "created_at": user.get("created_at"),
                "role": user.get("role", "user"),
                "is_active": user.get("is_active", True),
            },
            "analytics": analytics_result.data if analytics_result.data else {},
            "recent_analyses": analyses_result.data if analyses_result.data else [],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading user analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
