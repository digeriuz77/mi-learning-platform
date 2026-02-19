"""
Scoring Service for calculating points and levels

Implements the MI Learning Platform gamification logic:
- Excellent technique: 150 points
- Good technique: 100 points
- Acceptable technique: 50 points
- Poor/Non-MI technique: 0 points

NO bonuses - simple and clear scoring.
Module completion is binary: COMPLETE or NOT COMPLETE.
"""

from typing import Dict, Any, Optional


def _get_scoring_constants():
    """Load scoring constants from settings or use defaults."""
    try:
        from app.config import settings

        return {
            "EXCELLENT_POINTS": getattr(settings, "SCORING_EXCELLENT_POINTS", 150),
            "GOOD_POINTS": getattr(settings, "SCORING_GOOD_POINTS", 100),
            "ACCEPTABLE_POINTS": getattr(settings, "SCORING_ACCEPTABLE_POINTS", 50),
            "POOR_POINTS": getattr(settings, "SCORING_POOR_POINTS", 0),
        }
    except Exception:
        return {
            "EXCELLENT_POINTS": 150,
            "GOOD_POINTS": 100,
            "ACCEPTABLE_POINTS": 50,
            "POOR_POINTS": 0,
        }


class ScoringService:
    """Service for calculating points and levels"""

    # Load configurable constants
    _constants = _get_scoring_constants()

    # Point values (from configurable constants) - NO BONUSES
    EXCELLENT_POINTS = _constants["EXCELLENT_POINTS"]  # Best MI technique
    GOOD_POINTS = _constants["GOOD_POINTS"]  # Solid MI technique
    ACCEPTABLE_POINTS = _constants["ACCEPTABLE_POINTS"]  # Basic MI technique
    POOR_POINTS = _constants["POOR_POINTS"]  # Non-MI technique

    # Keyword lists for technique quality classification
    NON_MI_KEYWORDS = [
        "non-mi",
        "righting reflex",
        "educating",
        "lecturing",
        "defending",
        "challenging",
        "interpretation",
        "closed question",
        "non-impartial",
        "colluding",
        "cheerleading",
        "false reassurance",
        "dismissive",
        "premature",
        "goal-focused",
    ]
    EXCELLENT_KEYWORDS = [
        "complex reflection",
        "reflection + open",
        "reflection + affirmation",
        "affirmation + reflection",
        "summary",
        "double-sided reflection",
    ]
    GOOD_KEYWORDS = ["reflection", "open question", "empathic", "affirmation +"]
    ACCEPTABLE_KEYWORDS = ["affirmation", "boundary", "acknowledgment", "validat", "apology"]

    @staticmethod
    def get_technique_quality(choice: dict) -> str:
        """
        Determine the quality of a technique choice.

        This is the single source of truth for technique quality classification,
        used by both actual scoring and max_points_available calculation.

        Args:
            choice: Dictionary with 'technique' and 'feedback' keys

        Returns:
            'excellent': Best MI technique (complex reflection, affirmation + reflection)
            'good': Solid MI technique (simple reflection, open question)
            'acceptable': Basic MI technique (affirmation, boundary setting)
            'poor': Non-MI technique (closed question, interpretation)
        """
        technique = choice.get("technique", "").lower()
        feedback = choice.get("feedback", "").lower()

        # Non-MI techniques (poor quality)
        if any(keyword in technique for keyword in ScoringService.NON_MI_KEYWORDS):
            return "poor"

        # Check feedback for quality indicators
        if any(
            kw in feedback for kw in ["miss", "stops the flow", "surface level", "risk breaking", "does not dig deeper"]
        ):
            return "acceptable"

        # Excellent techniques - complex combinations
        if any(keyword in technique for keyword in ScoringService.EXCELLENT_KEYWORDS):
            return "excellent"

        # Good techniques - core MI skills
        if any(keyword in technique for keyword in ScoringService.GOOD_KEYWORDS):
            # But check if feedback suggests it's only acceptable
            if "but" in feedback or "however" in feedback or "miss" in feedback:
                return "acceptable"
            return "good"

        # Acceptable techniques - basic skills
        if any(keyword in technique for keyword in ScoringService.ACCEPTABLE_KEYWORDS):
            return "acceptable"

        # Default to good if it doesn't match non-MI patterns
        return "good"

    # Level thresholds
    LEVEL_THRESHOLDS = [
        0,  # Level 1
        500,  # Level 2
        1500,  # Level 3
        3000,  # Level 4
        5000,  # Level 5
        8000,  # Level 6
        12000,  # Level 7
        17000,  # Level 8
        23000,  # Level 9
        30000,  # Level 10
    ]

    @staticmethod
    def calculate_choice_points(
        is_correct: bool, is_first_attempt: bool, evoked_change_talk: bool, technique_quality: str = "good"
    ) -> int:
        """
        Calculate points earned for a dialogue choice.

        Args:
            is_correct: Whether the technique was correct (deprecated, use technique_quality)
            is_first_attempt: Whether this is the first attempt at this node (unused - no bonuses)
            evoked_change_talk: Whether the choice evoked change talk (unused - no bonuses)
            technique_quality: Quality of technique ('excellent', 'good', 'acceptable', 'poor')

        Returns:
            int: Points earned (based solely on technique quality)
        """
        # Simple points based on technique quality - NO BONUSES
        quality_points = {
            "excellent": ScoringService.EXCELLENT_POINTS,
            "good": ScoringService.GOOD_POINTS,
            "acceptable": ScoringService.ACCEPTABLE_POINTS,
            "poor": ScoringService.POOR_POINTS,
        }

        return quality_points.get(technique_quality, ScoringService.GOOD_POINTS)

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
    def calculate_max_points_available(dialogue_content: dict) -> int:
        """
        Calculate the maximum points available for a module based on its dialogue structure.
        This finds the optimal path through the dialogue and sums the maximum possible
        points for each node on that path.

        Args:
            dialogue_content: The module's dialogue JSON content

        Returns:
            int: Maximum points achievable in the module
        """
        if not dialogue_content:
            return 0

        nodes = dialogue_content.get("nodes", [])
        if not nodes:
            return 0

        # Build a node lookup map
        node_map = {node["id"]: node for node in nodes}

        # Calculate max points for each ending node path
        def get_max_points_for_path(node_id: str, visited: set = None) -> int:
            if visited is None:
                visited = set()

            if node_id in visited:
                return 0  # Prevent infinite loops

            if node_id not in node_map:
                return 0

            node = node_map[node_id]

            # Check if this is an ending node
            if node.get("is_ending", False):
                # No completion bonus - module is complete or not
                return 0

            # Find the best path through choices
            best_path_points = 0
            choices = node.get("practitioner_choices", [])

            for choice in choices:
                next_node_id = choice.get("next_node_id")
                # Calculate max points for this choice path
                path_points = ScoringService.calculate_max_points_for_choice(choice)
                next_points = get_max_points_for_path(next_node_id, visited | {node_id})
                total_path = path_points + next_points
                best_path_points = max(best_path_points, total_path)

            return best_path_points

        # Start from the start node
        start_node_id = dialogue_content.get("start_node", "node_1")

        # Get the max points for the optimal path from start node
        return get_max_points_for_path(start_node_id)

    @staticmethod
    def calculate_max_points_for_choice(choice: dict) -> int:
        """
        Calculate the maximum points achievable for a single choice.

        Uses the unified get_technique_quality() method to ensure consistency
        between max_points_available calculation and actual scoring.

        Args:
            choice: The choice dictionary

        Returns:
            int: Points for this choice (based solely on technique quality)
        """
        quality = ScoringService.get_technique_quality(choice)

        quality_points = {
            "excellent": ScoringService.EXCELLENT_POINTS,
            "good": ScoringService.GOOD_POINTS,
            "acceptable": ScoringService.ACCEPTABLE_POINTS,
            "poor": ScoringService.POOR_POINTS,
        }

        return quality_points.get(quality, ScoringService.GOOD_POINTS)

    @staticmethod
    def calculate_completion_score(
        total_nodes: int,
        nodes_completed: int,
        correct_choices: int,
        nodes_visited: int = None,
        technique_quality_counts: dict = None,
        points_earned: int = 0,
        max_points_available: int = None,
    ) -> int:
        """
        Calculate module completion score.

        Returns 100 if module is complete (reached ending), 0 otherwise.
        The actual points earned vs max points available should be shown separately.

        Args:
            total_nodes: Total nodes in module
            nodes_completed: Number of nodes completed
            correct_choices: Number of correct technique choices (unused)
            nodes_visited: Number of nodes visited
            technique_quality_counts: Dict with counts of technique qualities (unused)
            points_earned: Total points earned (unused for binary completion)
            max_points_available: Max points available (unused for binary completion)

        Returns:
            int: 100 if complete, 0 if not complete
        """
        # Binary completion: if we visited all nodes and reached an ending
        # A module is complete when the user has made choices through to an ending
        # This is indicated by nodes_completed > 0 and all nodes visited
        if nodes_visited and total_nodes and nodes_visited >= total_nodes:
            return 100

        # Alternative: if nodes_completed matches or exceeds expected, module is done
        if nodes_completed and total_nodes and nodes_completed >= total_nodes:
            return 100

        return 0

    @staticmethod
    def get_next_level_threshold(current_level: int) -> int:
        """
        Get the points needed for the next level.

        Args:
            current_level: Current user level

        Returns:
            int: Points needed for next level, or 0 if at max level
        """
        # P1-14: Fixed - was returning LEVEL_THRESHOLDS[current_level - 1] which is the
        # *current* level's threshold. Should return the *next* level's threshold.
        if current_level < len(ScoringService.LEVEL_THRESHOLDS):
            return ScoringService.LEVEL_THRESHOLDS[current_level]
        return 0
