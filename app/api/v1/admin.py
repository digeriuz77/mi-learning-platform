"""
Admin API Endpoints for MI Learning Platform

Provides admin dashboard data and user management actions.
All endpoints require admin role authentication.
"""

import csv
import io
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.responses import StreamingResponse
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
        response = supabase_admin.table("users").select("role").eq("id", auth_context.user_id).maybe_single().execute()
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
        from datetime import datetime, timedelta, timezone

        # Total users
        users_resp = supabase.table("users").select("id", count="exact").execute()
        total_users = users_resp.count or 0

        # New users in last 24 hours
        since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        new_users_resp = supabase.table("users").select("id", count="exact").gte("created_at", since).execute()
        new_users_24h = new_users_resp.count or 0

        # Modules completed
        completed_resp = supabase.table("user_progress").select("id", count="exact").eq("status", "completed").execute()
        total_modules_completed = completed_resp.count or 0

        # Average progress - calculate properly based on nodes_visited vs total nodes per module
        progress_resp = (
            supabase.table("user_progress")
            .select("nodes_completed, nodes_visited, status, module_id, learning_modules(id, dialogue_content)")
            .execute()
        )
        avg_progress = 0.0
        if progress_resp.data:
            progress_values = []
            for row in progress_resp.data:
                if row.get("status") == "completed":
                    progress_values.append(100)
                else:
                    # Calculate progress based on nodes visited (use nodes_visited if available, else nodes_completed)
                    nodes_visited = row.get("nodes_visited", []) or []
                    nodes_completed = row.get("nodes_completed", []) or []
                    visited_count = len(nodes_visited) if nodes_visited else len(nodes_completed)

                    # Get total nodes from module
                    module_data = row.get("learning_modules")
                    if module_data:
                        dialogue_content = module_data.get("dialogue_content", {})
                        total_nodes = len(dialogue_content.get("nodes", []))
                        if total_nodes > 0:
                            progress_values.append((visited_count / total_nodes) * 100)
            if progress_values:
                avg_progress = sum(progress_values) / len(progress_values)

        return {
            "total_users": total_users,
            "new_users_24h": new_users_24h,
            "total_modules_completed": total_modules_completed,
            "average_progress": round(avg_progress, 1),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading dashboard stats: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred")


@router.get("/users")
async def get_users(
    search: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    admin: AuthContext = Depends(require_admin),
):
    """Get users list with pagination and optional search."""
    try:
        supabase = get_supabase_admin()

        query = supabase.table("users").select("id, email, display_name, role, is_active, created_at")

        if search:
            query = query.ilike("email", f"%{search}%")

        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        response = query.execute()

        # Fetch user profiles to get actual points and modules_completed
        user_ids = [u.get("id") for u in response.data or []]
        profiles_map = {}
        if user_ids:
            profiles_resp = (
                supabase.table("user_profiles")
                .select("user_id, total_points, modules_completed")
                .in_("user_id", user_ids)
                .execute()
            )
            profiles_map = {p["user_id"]: p for p in (profiles_resp.data or [])}

        users = []
        for user in response.data or []:
            profile = profiles_map.get(user.get("id"), {})
            users.append(
                {
                    "id": user.get("id"),
                    "email": user.get("email"),
                    "display_name": user.get("display_name"),
                    "role": user.get("role", "user"),
                    "is_active": user.get("is_active", True),
                    "created_at": user.get("created_at"),
                    # Admin dashboard fix: fetch actual values instead of hardcoded 0
                    "modules_completed": profile.get("modules_completed", 0),
                    "total_points": profile.get("total_points", 0),
                }
            )

        return users
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading users: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred")


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
                supabase.table("user_progress").select("id", count="exact").eq("module_id", module_id).execute()
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
        raise HTTPException(status_code=500, detail="An internal error occurred")


class AdminActionRequest(BaseModel):
    """Request to perform an admin action."""

    action: str
    target_user_id: Optional[str] = None
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
            # Clean up related data before deleting the user to avoid orphaned records
            supabase.table("conversation_analyses").delete().eq("user_id", target_id).execute()
            supabase.table("dialogue_attempts").delete().eq("user_id", target_id).execute()
            supabase.table("user_progress").delete().eq("user_id", target_id).execute()
            supabase.table("user_feedback").delete().eq("user_id", target_id).execute()
            supabase.table("user_profiles").delete().eq("user_id", target_id).execute()
            supabase.table("users").delete().eq("id", target_id).execute()
            return {"message": "User deleted"}

        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {action}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin action error: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred")


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
        result = supabase.rpc("get_practice_analytics", {"start_date": start_date, "end_date": end_date}).execute()

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
        raise HTTPException(status_code=500, detail="An internal error occurred")


@router.get("/practice/analyses")
async def get_practice_analyses(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    admin: AuthContext = Depends(require_admin),
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
        raise HTTPException(status_code=500, detail="An internal error occurred")


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
        raise HTTPException(status_code=500, detail="An internal error occurred")


@router.get("/feedback/recent")
async def get_recent_feedback(
    limit: int = Query(default=20, ge=1, le=500), admin: AuthContext = Depends(require_admin)
):
    """
    Get recent user feedback submissions.

    Returns the most recent feedback with comments.
    """
    try:
        supabase = get_supabase_admin()

        result = supabase.table("user_feedback").select("*").order("created_at", desc=True).limit(limit).execute()

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
        raise HTTPException(status_code=500, detail="An internal error occurred")


@router.get("/analytics/comprehensive")
async def get_comprehensive_analytics(admin: AuthContext = Depends(require_admin)):
    """
    Get comprehensive practice analytics.

    Returns aggregate statistics across all practice sessions.
    Note: Queries database directly instead of using RPC to avoid auth.uid() issues
    with service role key.
    """
    try:
        supabase = get_supabase_admin()

        # Query conversation_analyses table directly for aggregate stats
        result = (
            supabase.table("conversation_analyses")
            .select(
                "overall_score, foundational_trust_safety, empathic_partnership_autonomy, "
                "empowerment_clarity, mi_spirit_score, change_talk_evoked, total_turns, user_id"
            )
            .execute()
        )

        data = result.data or []

        if not data:
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

        # Calculate aggregates in Python
        total_sessions = len(data)
        unique_users = set(row.get("user_id") for row in data if row.get("user_id"))
        total_users = len(unique_users)

        avg_overall = (
            sum(row.get("overall_score", 0) or 0 for row in data) / total_sessions if total_sessions > 0 else 0
        )
        avg_trust = (
            sum(row.get("foundational_trust_safety", 0) or 0 for row in data) / total_sessions
            if total_sessions > 0
            else 0
        )
        avg_empathy = (
            sum(row.get("empathic_partnership_autonomy", 0) or 0 for row in data) / total_sessions
            if total_sessions > 0
            else 0
        )
        avg_empowerment = (
            sum(row.get("empowerment_clarity", 0) or 0 for row in data) / total_sessions if total_sessions > 0 else 0
        )
        avg_mi_spirit = (
            sum(row.get("mi_spirit_score", 0) or 0 for row in data) / total_sessions if total_sessions > 0 else 0
        )
        avg_turns = sum(row.get("total_turns", 0) or 0 for row in data) / total_sessions if total_sessions > 0 else 0

        change_talk_count = sum(1 for row in data if row.get("change_talk_evoked"))

        return {
            "total_sessions": total_sessions,
            "total_users": total_users,
            "avg_overall_score": round(avg_overall, 2),
            "avg_trust_safety": round(avg_trust, 2),
            "avg_empathy": round(avg_empathy, 2),
            "avg_empowerment": round(avg_empowerment, 2),
            "avg_mi_spirit": round(avg_mi_spirit, 2),
            "sessions_with_change_talk": change_talk_count,
            "avg_turns": round(avg_turns, 1),
        }

    except Exception as e:
        logger.error(f"Error loading comprehensive analytics: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred")


@router.get("/analytics/users")
async def get_users_with_analytics(
    search: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    admin: AuthContext = Depends(require_admin),
):
    """
    Get all users with their practice analytics.

    Returns users with practice session counts and average scores.
    Note: Queries database directly instead of using RPC to avoid auth.uid() issues
    with service role key.
    """
    try:
        supabase = get_supabase_admin()

        # Get users from auth.users (via public.users which mirrors it)
        query = supabase.table("users").select("id, email, display_name, role, is_active, created_at")

        if search:
            query = query.ilike("email", f"%{search}%")

        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        users_result = query.execute()

        users = users_result.data or []
        user_ids = [u.get("id") for u in users]

        # Get user profiles with practice analytics
        profiles_map = {}
        if user_ids:
            profiles_result = (
                supabase.table("user_profiles")
                .select(
                    "user_id, total_points, modules_completed, level, "
                    "practice_sessions_count, avg_overall_score, avg_trust_safety, "
                    "avg_empathy_partnership, avg_empowerment_clarity, avg_mi_spirit, last_practice_at"
                )
                .in_("user_id", user_ids)
                .execute()
            )

            for p in profiles_result.data or []:
                profiles_map[p.get("user_id")] = p

        # Combine user data with profile analytics
        result_users = []
        for user in users:
            profile = profiles_map.get(user.get("id"), {})
            result_users.append(
                {
                    "id": user.get("id"),
                    "email": user.get("email"),
                    "display_name": user.get("display_name"),
                    "created_at": user.get("created_at"),
                    "role": user.get("role", "user"),
                    "is_active": user.get("is_active", True),
                    "modules_completed": profile.get("modules_completed", 0),
                    "total_points": profile.get("total_points", 0),
                    "level": profile.get("level", 1),
                    "practice_sessions_count": profile.get("practice_sessions_count", 0),
                    "avg_overall_score": profile.get("avg_overall_score"),
                    "avg_trust_safety": profile.get("avg_trust_safety"),
                    "avg_empathy_partnership": profile.get("avg_empathy_partnership"),
                    "avg_empowerment_clarity": profile.get("avg_empowerment_clarity"),
                    "avg_mi_spirit": profile.get("avg_mi_spirit"),
                    "last_practice_at": profile.get("last_practice_at"),
                }
            )

        return {
            "users": result_users,
            "total": len(result_users),
            "limit": limit,
            "offset": offset,
        }

    except Exception as e:
        logger.error(f"Error loading users with analytics: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred")


@router.get("/analytics/leaderboard")
async def get_practice_analytics_leaderboard(
    limit: int = Query(default=20, ge=1, le=500), admin: AuthContext = Depends(require_admin)
):
    """
    Get practice leaderboard - top users by performance.

    Returns top users sorted by average overall score.
    Note: Queries database directly instead of using RPC to avoid auth.uid() issues
    with service role key.
    """
    try:
        supabase = get_supabase_admin()

        # Query user_profiles with practice sessions, joined with users for display_name
        profiles_result = (
            supabase.table("user_profiles")
            .select(
                "user_id, display_name, practice_sessions_count, avg_overall_score, "
                "avg_trust_safety, avg_empathy_partnership, avg_empowerment_clarity, avg_mi_spirit"
            )
            .gt("practice_sessions_count", 0)
            .order("avg_overall_score", desc=True)
            .limit(limit)
            .execute()
        )

        profiles = profiles_result.data or []

        # Get display names from users table for any missing names
        user_ids = [p.get("user_id") for p in profiles if p.get("user_id")]
        users_map = {}
        if user_ids:
            users_result = supabase.table("users").select("id, display_name").in_("id", user_ids).execute()
            for u in users_result.data or []:
                users_map[u.get("id")] = u.get("display_name")

        # Build leaderboard with display names
        leaderboard = []
        for p in profiles:
            leaderboard.append(
                {
                    "user_id": p.get("user_id"),
                    "display_name": p.get("display_name") or users_map.get(p.get("user_id"), "Anonymous"),
                    "practice_sessions_count": p.get("practice_sessions_count", 0),
                    "avg_overall_score": p.get("avg_overall_score"),
                    "avg_trust_safety": p.get("avg_trust_safety"),
                    "avg_empathy_partnership": p.get("avg_empathy_partnership"),
                    "avg_empowerment_clarity": p.get("avg_empowerment_clarity"),
                    "avg_mi_spirit": p.get("avg_mi_spirit"),
                }
            )

        return {"leaderboard": leaderboard, "total": len(leaderboard)}

    except Exception as e:
        logger.error(f"Error loading practice leaderboard: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred")


@router.get("/analytics/user/{user_id}")
async def get_user_detailed_analytics(user_id: str, admin: AuthContext = Depends(require_admin)):
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
        analytics_result = supabase.rpc("get_user_practice_analytics", {"p_user_id": user_id}).execute()

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
        raise HTTPException(status_code=500, detail="An internal error occurred")


# =====================================================
# P2-20: CSV Export Endpoints for HR Reporting
# =====================================================


@router.get("/export/users")
async def export_users_csv(admin: AuthContext = Depends(require_admin)):
    """
    Export user data as CSV for HR reporting.

    Returns a CSV file with user details, points, modules completed, and last active date.
    """
    try:
        supabase = get_supabase_admin()

        users_resp = (
            supabase.table("users")
            .select("id, email, display_name, role, is_active, created_at")
            .order("created_at", desc=True)
            .execute()
        )

        profiles_resp = (
            supabase.table("user_profiles")
            .select("user_id, total_points, level, modules_completed, last_active_at")
            .execute()
        )
        profiles_map = {p["user_id"]: p for p in (profiles_resp.data or [])}

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "User ID",
                "Email",
                "Display Name",
                "Role",
                "Is Active",
                "Total Points",
                "Level",
                "Modules Completed",
                "Created At",
                "Last Active",
            ]
        )

        for user in users_resp.data or []:
            profile = profiles_map.get(user.get("id"), {})
            writer.writerow(
                [
                    user.get("id", ""),
                    user.get("email", ""),
                    user.get("display_name", ""),
                    user.get("role", "user"),
                    user.get("is_active", True),
                    profile.get("total_points", 0),
                    profile.get("level", 1),
                    profile.get("modules_completed", 0),
                    user.get("created_at", ""),
                    profile.get("last_active_at", ""),
                ]
            )

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=users_export.csv"},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting users CSV: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred")


@router.get("/export/progress")
async def export_progress_csv(admin: AuthContext = Depends(require_admin)):
    """
    Export user progress data as CSV for HR reporting.

    Returns a CSV file with per-module progress for all users.
    """
    try:
        supabase = get_supabase_admin()

        progress_resp = (
            supabase.table("user_progress")
            .select("user_id, module_id, status, points_earned, completion_score, started_at, completed_at")
            .order("started_at", desc=True)
            .execute()
        )

        users_resp = supabase.table("users").select("id, email, display_name").execute()
        users_map = {u["id"]: u for u in (users_resp.data or [])}

        modules_resp = supabase.table("learning_modules").select("id, title").execute()
        modules_map = {m["id"]: m.get("title", "Unknown") for m in (modules_resp.data or [])}

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "User Email",
                "Display Name",
                "Module Title",
                "Status",
                "Points Earned",
                "Completed",
                "Started At",
                "Completed At",
            ]
        )

        for p in progress_resp.data or []:
            user = users_map.get(p.get("user_id"), {})
            writer.writerow(
                [
                    user.get("email", ""),
                    user.get("display_name", ""),
                    modules_map.get(p.get("module_id"), "Unknown"),
                    p.get("status", ""),
                    p.get("points_earned", 0),
                    "Yes" if p.get("status") == "completed" else "No",
                    p.get("started_at", ""),
                    p.get("completed_at", ""),
                ]
            )

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=progress_export.csv"},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting progress CSV: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred")


# =====================================================
# Practice History - Individual Session Records
# =====================================================


@router.get("/analytics/practice-history")
async def get_practice_history(
    search: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    admin: AuthContext = Depends(require_admin),
):
    """
    Get practice history - individual session records with user email.

    Returns all practice sessions with user details for tracking progress over time.
    """
    try:
        supabase = get_supabase_admin()

        # Get all conversation analyses with user info
        query = (
            supabase.table("conversation_analyses")
            .select(
                "id, session_id, user_id, persona_name, overall_score, "
                "foundational_trust_safety, empathic_partnership_autonomy, "
                "empowerment_clarity, mi_spirit_score, created_at"
            )
            .order("created_at", desc=True)
        )

        analyses_result = query.range(offset, offset + limit - 1).execute()
        analyses = analyses_result.data or []

        # Get user emails
        user_ids = list(set(a.get("user_id") for a in analyses if a.get("user_id")))
        users_map = {}
        if user_ids:
            users_result = supabase.table("users").select("id, email").in_("id", user_ids).execute()
            users_map = {u.get("id"): u.get("email") for u in (users_result.data or [])}

        # Build results
        results = []
        for a in analyses:
            results.append(
                {
                    "id": a.get("id"),
                    "email": users_map.get(a.get("user_id"), "Anonymous"),
                    "user_id": a.get("user_id"),
                    "session_id": a.get("session_id"),
                    "persona_name": a.get("persona_name", "Unknown"),
                    "overall_score": float(a.get("overall_score", 0)) if a.get("overall_score") else None,
                    "trust_safety": float(a.get("foundational_trust_safety", 0))
                    if a.get("foundational_trust_safety")
                    else None,
                    "empathy": float(a.get("empathic_partnership_autonomy", 0))
                    if a.get("empathic_partnership_autonomy")
                    else None,
                    "empowerment": float(a.get("empowerment_clarity", 0)) if a.get("empowerment_clarity") else None,
                    "mi_spirit": float(a.get("mi_spirit_score", 0)) if a.get("mi_spirit_score") else None,
                    "created_at": a.get("created_at"),
                }
            )

        # Filter by search if provided
        if search:
            results = [r for r in results if r["email"] and search.lower() in r["email"].lower()]

        return {
            "sessions": results,
            "total": len(results),
            "limit": limit,
            "offset": offset,
        }

    except Exception as e:
        logger.error(f"Error loading practice history: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred")


@router.get("/export/practice-history")
async def export_practice_history_csv(
    search: Optional[str] = None,
    admin: AuthContext = Depends(require_admin),
):
    """
    Export practice history as CSV for tracking user progress over time.
    """
    try:
        supabase = get_supabase_admin()

        # Get all conversation analyses
        analyses_result = (
            supabase.table("conversation_analyses")
            .select(
                "id, session_id, user_id, persona_name, overall_score, "
                "foundational_trust_safety, empathic_partnership_autonomy, "
                "empowerment_clarity, mi_spirit_score, created_at"
            )
            .order("created_at", desc=True)
            .execute()
        )

        analyses = analyses_result.data or []

        # Get user emails
        user_ids = list(set(a.get("user_id") for a in analyses if a.get("user_id")))
        users_map = {}
        if user_ids:
            users_result = supabase.table("users").select("id, email").in_("id", user_ids).execute()
            users_map = {u.get("id"): u.get("email") for u in (users_result.data or [])}

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "Email",
                "Date",
                "Time",
                "Persona",
                "Score",
                "Trust & Safety",
                "Empathy & Partnership",
                "Empowerment",
                "MI Spirit",
                "Session ID",
            ]
        )

        for a in analyses:
            created_at = a.get("created_at", "")
            date_part = created_at.split("T")[0] if created_at else ""
            time_part = created_at.split("T")[1].split(".")[0] if "T" in created_at else ""

            writer.writerow(
                [
                    users_map.get(a.get("user_id"), "Anonymous"),
                    date_part,
                    time_part,
                    a.get("persona_name", "Unknown"),
                    a.get("overall_score", ""),
                    a.get("foundational_trust_safety", ""),
                    a.get("empathic_partnership_autonomy", ""),
                    a.get("empowerment_clarity", ""),
                    a.get("mi_spirit_score", ""),
                    a.get("session_id", ""),
                ]
            )

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=practice_history_export.csv"},
        )

    except Exception as e:
        logger.error(f"Error exporting practice history CSV: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred")
