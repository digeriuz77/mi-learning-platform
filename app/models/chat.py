"""
Pydantic models for chat practice sessions
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class PersonaSummary(BaseModel):
    """Summary of a persona for listing"""

    id: str
    name: str
    title: str
    description: str
    avatar: str


class PersonaListResponse(BaseModel):
    """Response containing list of available personas"""

    personas: List[PersonaSummary]


class ChatStartRequest(BaseModel):
    """Request to start a new chat session"""

    persona_id: str = Field(..., description="ID of the persona to chat with")


class ChatStartResponse(BaseModel):
    """Response when starting a new chat session"""

    session_id: str
    persona_name: str
    persona_title: str
    persona_avatar: str
    opening_message: str
    max_turns: int = 20
    current_turn: int = 0


class ChatMessageRequest(BaseModel):
    """Request to send a message in a chat session"""

    session_id: str
    message: str = Field(..., min_length=1, max_length=2000)


class ChatMessageResponse(BaseModel):
    """Response from the persona"""

    response: str
    current_turn: int
    max_turns: int
    is_session_complete: bool = False
    session_summary: Optional[Dict[str, Any]] = None


class ChatEndRequest(BaseModel):
    """Request to end a chat session"""

    session_id: str


class MITechniqueUsed(BaseModel):
    """A single MI technique identified in conversation"""

    technique: str
    turn_number: int
    example: str
    effectiveness: str  # "effective", "partially_effective", "ineffective"


class ConversationAnalysis(BaseModel):
    """Comprehensive analysis of the practice conversation"""

    # Overall scores (1-5 scale)
    overall_score: float = Field(..., ge=1, le=5)

    # MAPS Framework Scores
    foundational_trust_safety: float = Field(..., ge=1, le=5)
    empathic_partnership_autonomy: float = Field(..., ge=1, le=5)
    empowerment_clarity: float = Field(..., ge=1, le=5)

    # MI Spirit Assessment
    mi_spirit_score: float = Field(..., ge=1, le=5)
    partnership_demonstrated: bool
    acceptance_demonstrated: bool
    compassion_demonstrated: bool
    evocation_demonstrated: bool

    # Technique Analysis
    techniques_used: List[MITechniqueUsed]
    techniques_count: Dict[str, int]  # {"open_question": 3, "reflection": 5, ...}

    # Patterns Observed
    strengths: List[str]
    areas_for_improvement: List[str]

    # Client Movement
    client_movement: str  # "toward_change", "stable", "away_from_change"
    change_talk_evoked: bool

    # Detailed Feedback
    transcript_summary: str  # Summary of what was discussed in the conversation
    summary: str
    key_moments: List[
        Dict[str, Any]
    ]  # [{"turn": 5, "moment": "description", "impact": "positive/negative"}]
    suggestions_for_next_time: List[str]


class ChatEndResponse(BaseModel):
    """Response when ending a chat session with full analysis"""

    session_id: str
    total_turns: int
    analysis: ConversationAnalysis
    transcript: List[Dict[str, str]]  # Full conversation history


class ChatSessionStatus(BaseModel):
    """Current status of a chat session"""

    session_id: str
    persona_id: str
    persona_name: str
    current_turn: int
    max_turns: int
    is_active: bool
    started_at: datetime
