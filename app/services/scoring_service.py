"""
Scoring Service for calculating points and levels

Implements the MI Learning Platform gamification logic:
- Correct technique: 100 points
- First attempt bonus: +50 points
- Change talk evoked: +50 points
- Module completion: +200 points
"""
from typing import Dict, Any


class ScoringService:
    """Service for calculating points and levels"""

    # Point values
    CORRECT_TECHNIQUE_POINTS = 100
    FIRST_ATTEMPT_BONUS = 50
    CHANGE_TALK_BONUS = 50
    MODULE_COMPLETION_BONUS = 200

    # Level thresholds
    LEVEL_THRESHOLDS = [
        0,      # Level 1
        500,    # Level 2
        1500,   # Level 3
        3000,   # Level 4
        5000,   # Level 5
        8000,   # Level 6
        12000,  # Level 7
        17000,  # Level 8
        23000,  # Level 9
        30000,  # Level 10
    ]

    @staticmethod
    def calculate_choice_points(
        is_correct: bool,
        is_first_attempt: bool,
        evoked_change_talk: bool
    ) -> int:
        """
        Calculate points earned for a dialogue choice.

        Args:
            is_correct: Whether the technique was correct
            is_first_attempt: Whether this is the first attempt at this node
            evoked_change_talk: Whether the choice evoked change talk

        Returns:
            int: Points earned
        """
        points = 0
        if is_correct:
            points += ScoringService.CORRECT_TECHNIQUE_POINTS
            if is_first_attempt:
                points += ScoringService.FIRST_ATTEMPT_BONUS
            if evoked_change_talk:
                points += ScoringService.CHANGE_TALK_BONUS
        return points

    @staticmethod
    def calculate_level(total_points: int) -> int:
        """
        Calculate user level based on total points.

        Args:
            total_points: User's total points

        Returns:
            int: User's level (1-10)
        """
        level = 1
        for i, threshold in enumerate(ScoringService.LEVEL_THRESHOLDS):
            if i == 0:
                continue  # Skip first threshold (0 points = level 1)
            if total_points >= threshold:
                level = i + 1
            else:
                break
        return min(level, 10)  # Cap at level 10

    @staticmethod
    def calculate_completion_score(
        total_nodes: int,
        nodes_completed: int,
        correct_choices: int
    ) -> int:
        """
        Calculate module completion score (0-100).

        Args:
            total_nodes: Total nodes in module
            nodes_completed: Number of nodes completed
            correct_choices: Number of correct technique choices

        Returns:
            int: Completion score (0-100)
        """
        if total_nodes == 0:
            return 0

        progress_score = (nodes_completed / total_nodes) * 50
        accuracy_score = (correct_choices / nodes_completed) * 50 if nodes_completed > 0 else 0
        return int(progress_score + accuracy_score)

    @staticmethod
    def get_next_level_threshold(current_level: int) -> int:
        """
        Get the points needed for the next level.

        Args:
            current_level: Current user level

        Returns:
            int: Points needed for next level, or 0 if at max level
        """
        if current_level - 1 < len(ScoringService.LEVEL_THRESHOLDS):
            return ScoringService.LEVEL_THRESHOLDS[current_level - 1]
        return 0
