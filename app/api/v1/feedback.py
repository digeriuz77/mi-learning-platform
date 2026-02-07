"""
Feedback API Routes - User feedback collection for MI Learning Platform

Stores user feedback after practice sessions in Supabase.
"""

import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from app.core.auth import get_current_user, AuthContext
from app.core.supabase import get_supabase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/feedback", tags=["Feedback"])


class FeedbackSubmission(BaseModel):
    """User feedback submission model"""

    session_id: str = Field(..., description="ID of the practice session")
    conversation_id: Optional[str] = Field(None, description="Optional conversation ID")
    persona_practiced: Optional[str] = Field(
        None, description="Name of persona practiced with"
    )
    helpfulness_score: int = Field(..., ge=0, le=10, description="Rating from 0-10")
    what_was_helpful: Optional[str] = Field(
        None, description="What the user found helpful"
    )
    improvement_suggestions: Optional[str] = Field(
        None, description="Suggestions for improvement"
    )
    user_email: Optional[str] = Field(None, description="Optional user email")


class FeedbackResponse(BaseModel):
    """Response after submitting feedback"""

    success: bool
    feedback_id: str
    message: str


@router.post("/submit", response_model=FeedbackResponse)
async def submit_feedback(
    feedback: FeedbackSubmission,
    auth: Optional[AuthContext] = Depends(get_current_user),
):
    """
    Submit user feedback after a practice session.

    Accessible by: All users (no authentication required)
    Stores feedback in Supabase user_feedback table.
    """
    try:
        # Validate score
        if not 0 <= feedback.helpfulness_score <= 10:
            raise HTTPException(
                status_code=400, detail="Helpfulness score must be between 0 and 10"
            )

        supabase = get_supabase()

        # Prepare data for insertion
        feedback_data = {
            "id": str(uuid.uuid4()),
            "session_id": feedback.session_id,
            "conversation_id": feedback.conversation_id,
            "persona_practiced": feedback.persona_practiced,
            "helpfulness_score": feedback.helpfulness_score,
            "what_was_helpful": feedback.what_was_helpful,
            "improvement_suggestions": feedback.improvement_suggestions,
            "user_email": feedback.user_email,
            "user_id": auth.user_id if auth else None,
            "created_at": datetime.utcnow().isoformat(),
        }

        # Store in Supabase
        result = supabase.table("user_feedback").insert(feedback_data).execute()

        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to store feedback")

        logger.info(f"Feedback submitted successfully: {feedback_data['id']}")

        return FeedbackResponse(
            success=True,
            feedback_id=feedback_data["id"],
            message="Thank you for your feedback!",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to submit feedback: {str(e)}"
        )


@router.get("/stats")
async def get_feedback_stats(auth: AuthContext = Depends(get_current_user)):
    """
    Get aggregate feedback statistics.

    Accessible by: Admin users only
    Returns average helpfulness score and total feedback count.
    """
    try:
        # Check admin role
        if not auth or auth.role not in ["admin", "moderator"]:
            raise HTTPException(status_code=403, detail="Admin access required")

        supabase = get_supabase()

        # Get all feedback
        result = supabase.table("user_feedback").select("*").execute()

        if not result.data:
            return {"total_feedback": 0, "average_score": 0.0, "score_distribution": {}}

        # Calculate stats
        scores = [
            f["helpfulness_score"] for f in result.data if "helpfulness_score" in f
        ]
        avg_score = sum(scores) / len(scores) if scores else 0.0

        # Score distribution
        distribution = {}
        for score in scores:
            distribution[score] = distribution.get(score, 0) + 1

        return {
            "total_feedback": len(result.data),
            "average_score": round(avg_score, 2),
            "score_distribution": distribution,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get feedback stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve feedback statistics: {str(e)}"
        )
