"""
Analysis Persistence Service

Handles saving conversation analysis results to Supabase database
and retrieving them for reporting and analytics.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.core.supabase import get_supabase
from app.models.chat import ConversationAnalysis

logger = logging.getLogger(__name__)


def save_conversation_analysis(
    session_id: str,
    analysis: ConversationAnalysis,
    transcript: List[Dict[str, str]],
    persona_id: Optional[str] = None,
    persona_name: Optional[str] = None,
    user_id: Optional[str] = None,
    total_turns: int = 0,
) -> Optional[str]:
    """
    Save a conversation analysis to the database.

    Args:
        session_id: The session identifier
        analysis: The ConversationAnalysis object
        transcript: The full conversation transcript
        persona_id: ID of the persona used
        persona_name: Name of the persona
        user_id: ID of the user (if authenticated)
        total_turns: Number of turns in the conversation

    Returns:
        The ID of the saved analysis, or None if failed
    """
    try:
        supabase = get_supabase()

        # Prepare data for insertion
        analysis_data = {
            "session_id": session_id,
            "user_id": user_id,
            "persona_id": persona_id,
            "persona_name": persona_name,
            # Scores
            "overall_score": analysis.overall_score,
            "foundational_trust_safety": analysis.foundational_trust_safety,
            "empathic_partnership_autonomy": analysis.empathic_partnership_autonomy,
            "empowerment_clarity": analysis.empowerment_clarity,
            "mi_spirit_score": analysis.mi_spirit_score,
            # MI Spirit
            "partnership_demonstrated": analysis.partnership_demonstrated,
            "acceptance_demonstrated": analysis.acceptance_demonstrated,
            "compassion_demonstrated": analysis.compassion_demonstrated,
            "evocation_demonstrated": analysis.evocation_demonstrated,
            # Techniques
            "techniques_count": analysis.techniques_count,
            "techniques_used": [
                {
                    "technique": t.technique,
                    "turn_number": t.turn_number,
                    "example": t.example,
                    "effectiveness": t.effectiveness,
                }
                for t in analysis.techniques_used
            ],
            # Patterns
            "strengths": analysis.strengths,
            "areas_for_improvement": analysis.areas_for_improvement,
            # Client Movement
            "client_movement": analysis.client_movement,
            "change_talk_evoked": analysis.change_talk_evoked,
            # Summaries
            "transcript_summary": analysis.transcript_summary,
            "summary": analysis.summary,
            "key_moments": analysis.key_moments,
            "suggestions_for_next_time": analysis.suggestions_for_next_time,
            # Transcript
            "transcript": transcript,
            "total_turns": total_turns,
            "created_at": datetime.utcnow().isoformat(),
        }

        # Insert into database
        result = supabase.table("conversation_analyses").insert(analysis_data).execute()

        if result.data and len(result.data) > 0:
            analysis_id = result.data[0]["id"]
            logger.info(f"Analysis saved successfully: {analysis_id}")
            return analysis_id
        else:
            logger.error("Failed to save analysis: No data returned")
            return None

    except Exception as e:
        logger.error(f"Failed to save conversation analysis: {e}", exc_info=True)
        return None


def get_analysis_by_id(
    analysis_id: str, user_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Retrieve a specific analysis by ID.

    Args:
        analysis_id: The analysis ID
        user_id: Optional user ID for access control

    Returns:
        The analysis data or None if not found
    """
    try:
        supabase = get_supabase()

        query = (
            supabase.table("conversation_analyses").select("*").eq("id", analysis_id)
        )

        if user_id:
            query = query.eq("user_id", user_id)

        result = query.execute()

        if result.data and len(result.data) > 0:
            return result.data[0]
        return None

    except Exception as e:
        logger.error(f"Failed to retrieve analysis: {e}", exc_info=True)
        return None


def get_user_analyses(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get all analyses for a specific user.

    Args:
        user_id: The user ID
        limit: Maximum number of results

    Returns:
        List of analysis records
    """
    try:
        supabase = get_supabase()

        result = (
            supabase.table("conversation_analyses")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        return result.data or []

    except Exception as e:
        logger.error(f"Failed to retrieve user analyses: {e}", exc_info=True)
        return []


def get_all_analyses(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Get all analyses (admin only).

    Args:
        limit: Maximum number of results
        offset: Pagination offset

    Returns:
        List of analysis records
    """
    try:
        supabase = get_supabase()

        result = (
            supabase.table("conversation_analyses")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .offset(offset)
            .execute()
        )

        return result.data or []

    except Exception as e:
        logger.error(f"Failed to retrieve analyses: {e}", exc_info=True)
        return []
