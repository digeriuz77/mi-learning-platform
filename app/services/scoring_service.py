"""
Scoring Service for calculating points and levels

Implements the MI Learning Platform gamification logic:
- Correct technique: 100 points
- First attempt bonus: +50 points
- Change talk evoked: +50 points
- Module completion: +200 points
"""
from typing import Dict, Any, Optional


class ScoringService:
    """Service for calculating points and levels"""

    # Point values
    CORRECT_TECHNIQUE_POINTS = 100
    FIRST_ATTEMPT_BONUS = 50
    CHANGE_TALK_BONUS = 50
    MODULE_COMPLETION_BONUS = 200

    # Quality-based point values
    EXCELLENT_POINTS = 150  # Best MI technique
    GOOD_POINTS = 100       # Solid MI technique
    ACCEPTABLE_POINTS = 50  # Basic MI technique
    POOR_POINTS = 0         # Non-MI technique

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
        evoked_change_talk: bool,
        technique_quality: str = 'good'
    ) -> int:
        """
        Calculate points earned for a dialogue choice.

        Args:
            is_correct: Whether the technique was correct (deprecated, use technique_quality)
            is_first_attempt: Whether this is the first attempt at this node
            evoked_change_talk: Whether the choice evoked change talk
            technique_quality: Quality of technique ('excellent', 'good', 'acceptable', 'poor')

        Returns:
            int: Points earned
        """
        # Base points based on technique quality
        quality_points = {
            'excellent': ScoringService.EXCELLENT_POINTS,
            'good': ScoringService.GOOD_POINTS,
            'acceptable': ScoringService.ACCEPTABLE_POINTS,
            'poor': ScoringService.POOR_POINTS
        }
        
        points = quality_points.get(technique_quality, ScoringService.GOOD_POINTS)
        
        # First attempt bonus only for good or excellent techniques
        if is_first_attempt and technique_quality in ['excellent', 'good']:
            points += ScoringService.FIRST_ATTEMPT_BONUS
        
        # Change talk bonus for any non-poor technique
        if evoked_change_talk and technique_quality != 'poor':
            points += ScoringService.CHANGE_TALK_BONUS
            
        return points

    @staticmethod
    def calculate_choice_points_legacy(
        is_correct: bool,
        is_first_attempt: bool,
        evoked_change_talk: bool
    ) -> int:
        """
        Legacy method for backward compatibility.
        Calculate points earned for a dialogue choice.
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
        
        nodes = dialogue_content.get('nodes', [])
        if not nodes:
            return 0
        
        # Build a node lookup map
        node_map = {node['id']: node for node in nodes}
        
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
            if node.get('is_ending', False):
                # Add completion bonus for ending
                return ScoringService.MODULE_COMPLETION_BONUS
            
            # Find the best path through choices
            best_path_points = 0
            choices = node.get('practitioner_choices', [])
            
            for choice in choices:
                next_node_id = choice.get('next_node_id')
                # Calculate max points for this choice path
                path_points = ScoringService.calculate_max_points_for_choice(choice)
                next_points = get_max_points_for_path(next_node_id, visited | {node_id})
                total_path = path_points + next_points
                best_path_points = max(best_path_points, total_path)
            
            return best_path_points
        
        # Start from the start node
        start_node_id = dialogue_content.get('start_node', 'node_1')
        
        # Get the best path and add starting node's first choice points
        start_node = node_map.get(start_node_id)
        if not start_node:
            return 0
        
        # Calculate the optimal first choice points
        best_first_choice_points = 0
        for choice in start_node.get('practitioner_choices', []):
            choice_points = ScoringService.calculate_max_points_for_choice(choice)
            best_first_choice_points = max(best_first_choice_points, choice_points)
        
        # Get remaining path points (excluding the starting node's choice since we counted it)
        remaining_points = get_max_points_for_path(start_node_id) - best_first_choice_points
        
        return best_first_choice_points + remaining_points

    @staticmethod
    def calculate_max_points_for_choice(choice: dict) -> int:
        """
        Calculate the maximum points achievable for a single choice.
        
        Args:
            choice: The choice dictionary
            
        Returns:
            int: Maximum points for this choice
        """
        technique = choice.get('technique', '').lower()
        
        # Determine quality from technique string
        if 'excellent' in technique or ('reflection' in technique and 'partial' not in technique and 'incomplete' not in technique):
            # Excellent choices are best responses
            base_points = ScoringService.EXCELLENT_POINTS
        elif 'good' in technique or 'simple reflection' in technique:
            base_points = ScoringService.GOOD_POINTS
        elif 'acceptable' in technique:
            base_points = ScoringService.ACCEPTABLE_POINTS
        else:
            # Poor/non-MI choices get 0
            base_points = ScoringService.POOR_POINTS
        
        # Add bonuses for best case scenario
        max_points = base_points
        
        # First attempt bonus (best case: first attempt)
        if base_points > 0:
            max_points += ScoringService.FIRST_ATTEMPT_BONUS
        
        # Change talk bonus (best case: evoked change talk)
        if base_points > 0:
            max_points += ScoringService.CHANGE_TALK_BONUS
        
        return max_points

    @staticmethod
    def calculate_completion_score(
        total_nodes: int,
        nodes_completed: int,
        correct_choices: int,
        nodes_visited: int = None,
        technique_quality_counts: dict = None,
        points_earned: int = 0,
        max_points_available: int = None
    ) -> int:
        """
        Calculate module completion score (0-100).

        Uses points-based scoring when max_points_available is provided,
        falling back to the old formula for backward compatibility.

        Args:
            total_nodes: Total nodes in module
            nodes_completed: Number of nodes completed (correct on first attempt)
            correct_choices: Number of correct technique choices (deprecated, use technique_quality_counts)
            nodes_visited: Number of nodes visited (all nodes reached)
            technique_quality_counts: Dict with counts of 'excellent', 'good', 'acceptable', 'poor' choices
            points_earned: Total points earned in the module
            max_points_available: Maximum points available in the module (calculated from dialogue)

        Returns:
            int: Completion score (0-100)
        """
        # Use points-based scoring if max_points_available is provided
        if max_points_available is not None and max_points_available > 0:
            score = int((points_earned / max_points_available) * 100)
            return min(max(score, 0), 100)  # Clamp between 0 and 100
        
        # Fall back to old formula for backward compatibility
        if total_nodes == 0:
            return 0

        # Use nodes_visited for progress if available, otherwise fall back to nodes_completed
        visited = nodes_visited if nodes_visited is not None else nodes_completed
        
        # Progress score: how far through the module (0-50 points)
        progress_score = (visited / total_nodes) * 50

        # Accuracy score: based on technique quality (0-50 points)
        if technique_quality_counts and visited > 0:
            # Weight technique quality: excellent=1.0, good=0.8, acceptable=0.5, poor=0
            quality_weights = {
                'excellent': 1.0,
                'good': 0.8,
                'acceptable': 0.5,
                'poor': 0.0
            }
            
            weighted_score = 0.0
            for quality, count in technique_quality_counts.items():
                weight = quality_weights.get(quality, 0.5)
                weighted_score += count * weight
            
            # Normalize to 0-50 scale
            accuracy_score = (weighted_score / visited) * 50
        elif visited > 0:
            # Fallback: use correct_choices ratio
            accuracy_score = (correct_choices / visited) * 50
        else:
            accuracy_score = 0

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
