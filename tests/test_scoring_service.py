"""
Tests for the Scoring Service

Simplified scoring system (no bonuses):
- Excellent: 150 points
- Good: 100 points
- Acceptable: 50 points
- Poor: 0 points

Completion is binary: 100 if points_earned > 0, else 0.
"""

import pytest
from app.services.scoring_service import ScoringService


class TestScoringService:
    """Test suite for ScoringService"""

    # =====================================================
    # Technique Quality Classification Tests
    # =====================================================

    def test_get_technique_quality_excellent(self):
        """Test that excellent techniques are classified correctly"""
        choice = {"technique": "Complex reflection", "feedback": "Great use of complex reflection"}
        assert ScoringService.get_technique_quality(choice) == "excellent"

    def test_get_technique_quality_good(self):
        """Test that good techniques are classified correctly"""
        choice = {"technique": "Simple reflection", "feedback": "Good reflection"}
        assert ScoringService.get_technique_quality(choice) == "good"

    def test_get_technique_quality_acceptable(self):
        """Test that acceptable techniques are classified correctly"""
        choice = {"technique": "Affirmation", "feedback": "Nice affirmation"}
        assert ScoringService.get_technique_quality(choice) == "acceptable"

    def test_get_technique_quality_poor(self):
        """Test that poor techniques are classified correctly"""
        choice = {"technique": "Closed question", "feedback": "This is a closed question"}
        assert ScoringService.get_technique_quality(choice) == "poor"

    def test_get_technique_quality_inviting_interpretation_is_good(self):
        """Test that 'Inviting interpretation' is classified as good (not poor)"""
        # This was a bug - 'interpretation' was in NON_MI_KEYWORDS
        # but 'inviting interpretation' is good MI technique
        choice = {
            "technique": "Inviting interpretation (elicit phase)",
            "feedback": "Perfect - invites the patient interpretation",
        }
        assert ScoringService.get_technique_quality(choice) == "good"

    def test_get_technique_quality_directing_interpretation_is_poor(self):
        """Test that 'Directing interpretation' is classified as poor"""
        choice = {"technique": "Directing interpretation", "feedback": "This tells the patient what to think"}
        assert ScoringService.get_technique_quality(choice) == "poor"

    # =====================================================
    # Choice Points Tests (No Bonuses)
    # =====================================================

    def test_calculate_choice_points_excellent(self):
        """Test points for excellent technique"""
        points = ScoringService.calculate_choice_points(
            is_correct=True, is_first_attempt=True, evoked_change_talk=True, technique_quality="excellent"
        )
        assert points == 150

    def test_calculate_choice_points_good(self):
        """Test points for good technique"""
        points = ScoringService.calculate_choice_points(
            is_correct=True, is_first_attempt=True, evoked_change_talk=True, technique_quality="good"
        )
        assert points == 100

    def test_calculate_choice_points_acceptable(self):
        """Test points for acceptable technique"""
        points = ScoringService.calculate_choice_points(
            is_correct=True, is_first_attempt=True, evoked_change_talk=True, technique_quality="acceptable"
        )
        assert points == 50

    def test_calculate_choice_points_poor(self):
        """Test points for poor technique"""
        points = ScoringService.calculate_choice_points(
            is_correct=False, is_first_attempt=True, evoked_change_talk=True, technique_quality="poor"
        )
        assert points == 0

    def test_calculate_choice_points_no_bonuses(self):
        """Test that bonuses are not applied (simplified scoring)"""
        # First attempt, change talk - should NOT add bonuses
        points_first = ScoringService.calculate_choice_points(
            is_correct=True, is_first_attempt=True, evoked_change_talk=True, technique_quality="good"
        )
        points_retry = ScoringService.calculate_choice_points(
            is_correct=True, is_first_attempt=False, evoked_change_talk=False, technique_quality="good"
        )
        # Both should be same - no bonuses
        assert points_first == 100
        assert points_retry == 100

    # =====================================================
    # Level Calculation Tests
    # =====================================================

    def test_calculate_level_thresholds(self):
        """Test level calculation at various thresholds"""
        # Level 1: 0-499 points
        assert ScoringService.calculate_level(0) == 1
        assert ScoringService.calculate_level(499) == 1

        # Level 2: 500-1499 points
        assert ScoringService.calculate_level(500) == 2
        assert ScoringService.calculate_level(1499) == 2

        # Level 3: 1500-2999 points
        assert ScoringService.calculate_level(1500) == 3
        assert ScoringService.calculate_level(2999) == 3

        # Level 10: 30000+ points
        assert ScoringService.calculate_level(30000) == 10
        assert ScoringService.calculate_level(50000) == 10

    # =====================================================
    # Completion Score Tests (Binary)
    # =====================================================

    def test_calculate_completion_score_with_points(self):
        """Test completion score returns 100 when points earned"""
        score = ScoringService.calculate_completion_score(
            total_nodes=10,
            nodes_completed=5,
            correct_choices=5,
            nodes_visited=5,
            technique_quality_counts={"excellent": 3, "good": 2},
            points_earned=500,
            max_points_available=1000,
        )
        assert score == 100

    def test_calculate_completion_score_zero_points(self):
        """Test completion score returns 0 when no points earned"""
        score = ScoringService.calculate_completion_score(
            total_nodes=10,
            nodes_completed=5,
            correct_choices=5,
            nodes_visited=5,
            technique_quality_counts={},
            points_earned=0,
            max_points_available=1000,
        )
        assert score == 0

    def test_calculate_completion_score_any_points(self):
        """Test that any points earned means completion"""
        # Even with partial completion, if user earned points, they participated
        score = ScoringService.calculate_completion_score(
            total_nodes=10,
            nodes_completed=3,
            correct_choices=2,
            nodes_visited=3,
            technique_quality_counts={"good": 2, "acceptable": 1},
            points_earned=100,  # Just 100 points
            max_points_available=1500,
        )
        assert score == 100

    # =====================================================
    # Max Points Calculation Tests
    # =====================================================

    def test_calculate_max_points_for_choice_excellent(self):
        """Test max points calculation for an excellent choice"""
        choice = {
            "text": "You don't see your smoking as a problem right now.",
            "technique": "Complex reflection",
            "next_node_id": "node_2b",
        }
        points = ScoringService.calculate_max_points_for_choice(choice)
        assert points == 150  # Excellent = 150 (no bonuses)

    def test_calculate_max_points_for_choice_good(self):
        """Test max points calculation for a good choice"""
        choice = {
            "text": "Your daily activities show you're doing okay.",
            "technique": "Simple reflection",
            "next_node_id": "node_4b",
        }
        points = ScoringService.calculate_max_points_for_choice(choice)
        assert points == 100  # Good = 100

    def test_calculate_max_points_for_choice_acceptable(self):
        """Test max points calculation for an acceptable choice"""
        choice = {"text": "Some text", "technique": "Affirmation", "next_node_id": "node_x"}
        points = ScoringService.calculate_max_points_for_choice(choice)
        assert points == 50  # Acceptable = 50

    def test_calculate_max_points_for_choice_poor(self):
        """Test max points calculation for a poor/non-MI choice"""
        choice = {
            "text": "But are you sure your breathing is really okay?",
            "technique": "Closed question (non-MI)",
            "next_node_id": "node_3b",
        }
        points = ScoringService.calculate_max_points_for_choice(choice)
        assert points == 0  # Poor = 0

    def test_calculate_max_points_available_from_dialogue(self):
        """Test calculating max points from a dialogue structure"""
        dialogue_content = {
            "title": "Test Module",
            "start_node": "node_1",
            "nodes": [
                {
                    "id": "node_1",
                    "patient_statement": "Test statement",
                    "practitioner_choices": [
                        {"text": "A", "technique": "Complex reflection", "next_node_id": "node_2"},
                        {"text": "B", "technique": "Simple reflection", "next_node_id": "node_2"},
                    ],
                },
                {
                    "id": "node_2",
                    "patient_statement": "Test statement 2",
                    "practitioner_choices": [{"text": "C", "technique": "Complex reflection", "next_node_id": "end_1"}],
                },
                {"id": "end_1", "patient_statement": "End", "is_ending": True},
            ],
        }
        max_points = ScoringService.calculate_max_points_available(dialogue_content)
        # Should calculate based on optimal path: node_1(excellent=150) + node_2(excellent=150) = 300
        assert max_points == 300

    def test_calculate_max_points_available_empty_dialogue(self):
        """Test calculating max points from empty dialogue"""
        assert ScoringService.calculate_max_points_available({}) == 0

    # =====================================================
    # Next Level Threshold Tests
    # =====================================================

    def test_get_next_level_threshold(self):
        """Test getting next level threshold"""
        assert ScoringService.get_next_level_threshold(1) == 500
        assert ScoringService.get_next_level_threshold(2) == 1500
        assert ScoringService.get_next_level_threshold(9) == 30000
        assert ScoringService.get_next_level_threshold(10) == 0  # Max level
