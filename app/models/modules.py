"""
Module and dialogue models for request/response validation
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class PractitionerChoice(BaseModel):
    """A choice available to the practitioner"""
    text: str
    technique: str
    next_node_id: Optional[str] = None
    feedback: str = ""

    class Config:
        extra = "allow"  # Allow extra fields from JSON


class DialogueNode(BaseModel):
    """A single node in the dialogue tree"""
    id: str
    patient_statement: Optional[str] = None
    patient_context: Optional[str] = None
    practitioner_choices: Optional[List[PractitionerChoice]] = None
    is_ending: Optional[bool] = False
    outcome: Optional[str] = None
    learning_summary: Optional[str] = None

    class Config:
        extra = "allow"  # Allow extra fields from JSON


class ModuleResponse(BaseModel):
    """Learning module response"""
    id: str
    module_number: int
    title: str
    slug: str
    learning_objective: str
    technique_focus: str
    stage_of_change: str
    description: str
    points: int = 500
    dialogue_content: Dict[str, Any]

    # User progress (optional)
    user_status: Optional[str] = None
    user_score: Optional[int] = None
    user_points_earned: Optional[int] = None

    class Config:
        from_attributes = True


class ModuleListResponse(BaseModel):
    """List of modules response"""
    modules: List[ModuleResponse]
    total: int


class NodeResponse(BaseModel):
    """Dialogue node response"""
    node: Dict[str, Any]  # Raw node data from database
    module_id: str
    progress_id: str
    current_node_number: int
    total_nodes: int
    can_retry: bool = False


class ChoiceSubmit(BaseModel):
    """Submit a dialogue choice"""
    module_id: str
    node_id: str
    choice_id: str
    choice_text: str
    technique: str


class ChoiceFeedback(BaseModel):
    """Feedback for a submitted choice"""
    is_correct: bool
    feedback_text: str
    points_earned: int
    evoked_change_talk: bool
    next_node_id: Optional[str] = None
    is_module_complete: bool = False
    completion_score: Optional[int] = None
    total_points: Optional[int] = None
    level: Optional[int] = None
