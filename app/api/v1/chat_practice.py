"""
API routes for MI Chat Practice sessions.
Allows users to practice Motivational Interviewing with simulated client personas.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
import logging

from app.models.chat import (
    PersonaListResponse,
    PersonaSummary,
    ChatStartRequest,
    ChatStartResponse,
    ChatMessageRequest,
    ChatMessageResponse,
    ChatEndRequest,
    ChatEndResponse,
    ConversationAnalysis,
    MITechniqueUsed,
    ChatSessionStatus,
)
from app.services.personas import get_persona_list, get_persona
from app.services import chat_service
from app.services import conversation_analysis_service
from app.services.analysis_persistence_service import save_conversation_analysis
from app.core.auth import get_current_user, AuthContext

router = APIRouter(prefix="/chat-practice", tags=["Chat Practice"])
logger = logging.getLogger(__name__)


@router.get("/personas", response_model=PersonaListResponse)
async def list_personas():
    """
    Get list of available practice personas.

    Returns personas that users can practice MI techniques with.
    """
    personas = get_persona_list()
    return PersonaListResponse(personas=[PersonaSummary(**p) for p in personas])


@router.get("/personas/{persona_id}")
async def get_persona_details(persona_id: str):
    """
    Get detailed information about a specific persona.

    This provides the persona's background and context for practice.
    """
    persona = get_persona(persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail=f"Persona '{persona_id}' not found")

    # Return limited info (not the full system prompts)
    return {
        "id": persona["id"],
        "name": persona["name"],
        "age": persona["age"],
        "title": persona["title"],
        "description": persona["description"],
        "avatar": persona["avatar"],
        "stage_of_change": persona["stage_of_change"],
        "initial_mood": persona["initial_mood"],
    }


@router.post("/start", response_model=ChatStartResponse)
async def start_chat_session(
    request: ChatStartRequest, auth: Optional[AuthContext] = Depends(get_current_user)
):
    """
    Start a new chat practice session with a selected persona.

    The persona will send an opening message to begin the conversation.
    Sessions are limited to 20 turns, after which analysis is provided.
    """
    try:
        result = await chat_service.start_session(request.persona_id)
        return ChatStartResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to start session: {str(e)}"
        )


@router.post("/message", response_model=ChatMessageResponse)
async def send_message(
    request: ChatMessageRequest, auth: Optional[AuthContext] = Depends(get_current_user)
):
    """
    Send a message in an active chat practice session.

    The persona will respond based on:
    - Your MI technique usage
    - The conversation history
    - Their personality and stage of change

    After 20 turns, the session will automatically end and provide analysis.
    """
    try:
        result = await chat_service.send_message(request.session_id, request.message)
        return ChatMessageResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to process message: {str(e)}"
        )


@router.post("/end", response_model=ChatEndResponse)
async def end_chat_session(
    request: ChatEndRequest, auth: Optional[AuthContext] = Depends(get_current_user)
):
    """
    End a chat practice session and get comprehensive analysis.

    Analysis includes:
    - MAPS framework scores
    - MI Spirit assessment
    - Technique identification and counts
    - Strengths and areas for improvement
    - Specific suggestions for future practice
    """
    try:
        # Get session data
        session_data = chat_service.end_session(request.session_id)

        # Get the persona name for formatting
        persona = get_persona(session_data["persona_id"])
        persona_name = persona["name"] if persona else "Client"

        # Analyze the conversation
        analysis_result = await conversation_analysis_service.analyze_conversation(
            transcript=session_data["transcript"], persona_name=persona_name
        )

        # Build the response
        techniques_used = [
            MITechniqueUsed(**t) for t in analysis_result.get("techniques_used", [])
        ]

        analysis = ConversationAnalysis(
            overall_score=analysis_result.get("overall_score", 3.0),
            foundational_trust_safety=analysis_result.get(
                "foundational_trust_safety", 3.0
            ),
            empathic_partnership_autonomy=analysis_result.get(
                "empathic_partnership_autonomy", 3.0
            ),
            empowerment_clarity=analysis_result.get("empowerment_clarity", 3.0),
            mi_spirit_score=analysis_result.get("mi_spirit_score", 3.0),
            partnership_demonstrated=analysis_result.get(
                "partnership_demonstrated", False
            ),
            acceptance_demonstrated=analysis_result.get(
                "acceptance_demonstrated", False
            ),
            compassion_demonstrated=analysis_result.get(
                "compassion_demonstrated", False
            ),
            evocation_demonstrated=analysis_result.get("evocation_demonstrated", False),
            techniques_used=techniques_used,
            techniques_count=analysis_result.get("techniques_count", {}),
            strengths=analysis_result.get("strengths", []),
            areas_for_improvement=analysis_result.get("areas_for_improvement", []),
            client_movement=analysis_result.get("client_movement", "stable"),
            change_talk_evoked=analysis_result.get("change_talk_evoked", False),
            transcript_summary=analysis_result.get("transcript_summary", ""),
            summary=analysis_result.get("summary", ""),
            key_moments=analysis_result.get("key_moments", []),
            suggestions_for_next_time=analysis_result.get(
                "suggestions_for_next_time", []
            ),
        )

        # Format transcript for response
        transcript = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in session_data["transcript"]
        ]

        # Save analysis to database (async background operation)
        try:
            save_conversation_analysis(
                session_id=request.session_id,
                analysis=analysis,
                transcript=transcript,
                persona_id=session_data.get("persona_id"),
                persona_name=persona_name,
                user_id=auth.user_id if auth else None,
                total_turns=session_data["total_turns"],
            )
        except Exception as e:
            # Log error but don't fail the request
            logger.warning(f"Failed to save analysis to database: {e}")

        return ChatEndResponse(
            session_id=request.session_id,
            total_turns=session_data["total_turns"],
            analysis=analysis,
            transcript=transcript,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to end session: {str(e)}")


@router.get("/session/{session_id}", response_model=ChatSessionStatus)
async def get_session_status(
    session_id: str, auth: Optional[AuthContext] = Depends(get_current_user)
):
    """
    Get the current status of a chat practice session.
    """
    session = chat_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    return ChatSessionStatus(
        session_id=session["id"],
        persona_id=session["persona_id"],
        persona_name=session["persona"]["name"],
        current_turn=session["turn"],
        max_turns=chat_service.MAX_TURNS,
        is_active=session["is_active"],
        started_at=session["started_at"],
    )


@router.get("/session/{session_id}/transcript")
async def get_session_transcript(
    session_id: str, auth: Optional[AuthContext] = Depends(get_current_user)
):
    """
    Get the conversation transcript for a session.
    """
    transcript = chat_service.get_session_transcript(session_id)
    if not transcript:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    return {"transcript": transcript}


@router.post("/analyze")
async def analyze_transcript(
    request: dict, auth: Optional[AuthContext] = Depends(get_current_user)
):
    """
    Analyze a conversation transcript and return feedback.
    Used for demo sessions where no server-side session exists.
    """
    try:
        transcript = request.get("transcript", [])
        persona_name = request.get("persona_name", "Client")

        if not transcript:
            raise HTTPException(status_code=400, detail="Transcript is required")

        logger.info(
            f"[CHAT] Analyzing transcript for {persona_name}, {len(transcript)} messages"
        )

        analysis_result = await conversation_analysis_service.analyze_conversation(
            transcript=transcript, persona_name=persona_name
        )

        logger.info(f"[CHAT] Analysis complete for {persona_name}")

        techniques_used = [
            MITechniqueUsed(**t) for t in analysis_result.get("techniques_used", [])
        ]

        analysis = ConversationAnalysis(
            overall_score=analysis_result.get("overall_score", 3.0),
            foundational_trust_safety=analysis_result.get(
                "foundational_trust_safety", 3.0
            ),
            empathic_partnership_autonomy=analysis_result.get(
                "empathic_partnership_autonomy", 3.0
            ),
            empowerment_clarity=analysis_result.get("empowerment_clarity", 3.0),
            mi_spirit_score=analysis_result.get("mi_spirit_score", 3.0),
            partnership_demonstrated=analysis_result.get(
                "partnership_demonstrated", False
            ),
            acceptance_demonstrated=analysis_result.get(
                "acceptance_demonstrated", False
            ),
            compassion_demonstrated=analysis_result.get(
                "compassion_demonstrated", False
            ),
            evocation_demonstrated=analysis_result.get("evocation_demonstrated", False),
            techniques_used=techniques_used,
            techniques_count=analysis_result.get("techniques_count", {}),
            strengths=analysis_result.get("strengths", []),
            areas_for_improvement=analysis_result.get("areas_for_improvement", []),
            client_movement=analysis_result.get("client_movement", "stable"),
            change_talk_evoked=analysis_result.get("change_talk_evoked", False),
            transcript_summary=analysis_result.get("transcript_summary", ""),
            summary=analysis_result.get("summary", ""),
            key_moments=analysis_result.get("key_moments", []),
            suggestions_for_next_time=analysis_result.get(
                "suggestions_for_next_time", []
            ),
        )

        return {
            "session_id": "demo",
            "total_turns": len([m for m in transcript if m.get("role") == "user"]),
            "analysis": analysis.model_dump(),
            "transcript": transcript,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to analyze transcript: {str(e)}"
        )
