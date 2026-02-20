"""
Progress and leaderboard models
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class UserProgress(BaseModel):
    """User progress for a module"""

    id: str
    module_id: str
    module_title: str
    status: str  # not_started, in_progress, completed
    current_node_id: str
    nodes_completed: List[str]
    points_earned: int
    completion_score: int
    techniques_demonstrated: dict
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_nodes: int = 0  # Total nodes in the module for progress calculation

    class Config:
        from_attributes = True


class ProgressListResponse(BaseModel):
    """List of user progress"""

    progress: List[UserProgress]
    total_points: int
    level: int
    modules_completed: int
    # Practice chat analytics
    practice_sessions_count: Optional[int] = 0
    avg_overall_score: Optional[float] = None
    avg_mi_spirit: Optional[float] = None
    last_practice_at: Optional[str] = None


class LeaderboardEntry(BaseModel):
    """Leaderboard entry"""

    rank: int
    display_name: str
    total_points: int
    level: int
    modules_completed: int


class LeaderboardResponse(BaseModel):
    """Leaderboard response"""

    entries: List[LeaderboardEntry]
    current_user: Optional[LeaderboardEntry] = None


class UserProfile(BaseModel):
    """User profile information"""

    id: str
    email: str
    display_name: Optional[str] = None
    total_points: int = 0
    level: int = 1
    modules_completed: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
