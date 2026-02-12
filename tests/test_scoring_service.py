"""
Tests for the Scoring Service
"""
import pytest
from app.services.scoring_service import ScoringService


class TestScoringService:
    """Test suite for ScoringService"""

    def test_calculate_choice_points_correct_first_attempt_with_change_talk(self):
        """Test points calculation for correct answer on first attempt with change talk"""
        points = ScoringService.calculate_choice_points(
            is_correct=True,
            is_first_attempt=True,
            evoked_change_talk=True
        )
        expected = (ScoringService.CORRECT_TECHNIQUE_POINTS +
                   ScoringService.FIRST_ATTEMPT_BONUS +
                   ScoringService.CHANGE_TALK_BONUS)
        assert points == expected

    def test_calculate_choice_points_correct_first_attempt_no_change_talk(self):
        """Test points calculation for correct answer on first attempt without change talk"""
        points = ScoringService.calculate_choice_points(
            is_correct=True,
            is_first_attempt=True,
            evoked_change_talk=False
        )
        expected = (ScoringService.CORRECT_TECHNIQUE_POINTS +
                   ScoringService.FIRST_ATTEMPT_BONUS)
        assert points == expected

    def test_calculate_choice_points_correct_retry(self):
        """Test points calculation for correct answer on retry (not first attempt)"""
        points = ScoringService.calculate_choice_points(
            is_correct=True,
            is_first_attempt=False,
            evoked_change_talk=False
        )
        assert points == ScoringService.CORRECT_TECHNIQUE_POINTS

    def test_calculate_choice_points_incorrect(self):
        """Test points calculation for incorrect answer"""
        points = ScoringService.calculate_choice_points(
            is_correct=False,
            is_first_attempt=True,
            evoked_change_talk=True,
            technique_quality='poor'
        )
        assert points == 0

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

    def test_calculate_completion_score_perfect(self):
        """Test completion score calculation for perfect completion"""
        score = ScoringService.calculate_completion_score(
            total_nodes=10,
            nodes_completed=10,
            correct_choices=10
        )
        assert score == 100

    def test_calculate_completion_score_partial(self):
        """Test completion score calculation for partial completion"""
        # 50% progress, 80% accuracy on completed nodes
        # progress_score = (5/10) * 50 = 25
        # accuracy_score = (4/5) * 50 = 40
        # total = 65
        score = ScoringService.calculate_completion_score(
            total_nodes=10,
            nodes_completed=5,
            correct_choices=4
        )
        assert score == 65

    def test_calculate_completion_score_zero_nodes(self):
        """Test completion score calculation with zero nodes"""
        score = ScoringService.calculate_completion_score(
            total_nodes=0,
            nodes_completed=0,
            correct_choices=0
        )
        assert score == 0

    def test_calculate_completion_score_zero_completed(self):
        """Test completion score calculation with zero completed nodes"""
        score = ScoringService.calculate_completion_score(
            total_nodes=10,
            nodes_completed=0,
            correct_choices=0
        )
        assert score == 0

    def test_calculate_completion_score_with_max_points_perfect(self):
        """Test completion score calculation using points-based scoring for perfect score"""
        # User earned 1000 points, max available is 1000 → 100%
        score = ScoringService.calculate_completion_score(
            total_nodes=10,
            nodes_completed=10,
            correct_choices=10,
            points_earned=1000,
            max_points_available=1000
        )
        assert score == 100

    def test_calculate_completion_score_with_max_points_half(self):
        """Test completion score calculation using points-based scoring for half score"""
        # User earned 500 points, max available is 1000 → 50%
        score = ScoringService.calculate_completion_score(
            total_nodes=10,
            nodes_completed=10,
            correct_choices=10,
            points_earned=500,
            max_points_available=1000
        )
        assert score == 50

    def test_calculate_completion_score_with_max_points_gary_case(self):
        """Test Gary's case: 1000 points should show as 100% with 1000 max points"""
        # Gary earned 1000 points, max available is 1000 → 100%
        # This is the fix for the reported issue
        score = ScoringService.calculate_completion_score(
            total_nodes=13,  # Module 1 has 13 nodes
            nodes_completed=7,  # He visited ~7 nodes
            correct_choices=7,
            points_earned=1000,
            max_points_available=1000
        )
        assert score == 100

    def test_calculate_max_points_for_choice_excellent(self):
        """Test max points calculation for an excellent choice"""
        choice = {
            "text": "You don't see your smoking as a problem right now.",
            "technique": "Simple reflection (complete)",
            "next_node_id": "node_2b"
        }
        points = ScoringService.calculate_max_points_for_choice(choice)
        # Excellent + first attempt + change talk = 150 + 50 + 50 = 250
        assert points == 250

    def test_calculate_max_points_for_choice_good(self):
        """Test max points calculation for a good choice"""
        choice = {
            "text": "Your daily activities - walking your dog, your physical job - those are evidence to you that you're doing okay.",
            "technique": "Simple reflection (amplifying)",
            "next_node_id": "node_4b"
        }
        points = ScoringService.calculate_max_points_for_choice(choice)
        # Simple reflection (amplifying) contains "reflection" → excellent
        # Excellent + first attempt + change talk = 150 + 50 + 50 = 250
        assert points == 250

    def test_calculate_max_points_for_choice_acceptable(self):
        """Test max points calculation for an acceptable choice"""
        choice = {
            "text": "Some text",
            "technique": "Acceptable technique",
            "next_node_id": "node_x"
        }
        points = ScoringService.calculate_max_points_for_choice(choice)
        # Acceptable + first attempt + change talk = 50 + 50 + 50 = 150
        assert points == 150

    def test_calculate_max_points_for_choice_poor(self):
        """Test max points calculation for a poor/non-MI choice"""
        choice = {
            "text": "But are you sure your breathing is really okay?",
            "technique": "Questioning/challenging (non-MI)",
            "next_node_id": "node_3b"
        }
        points = ScoringService.calculate_max_points_for_choice(choice)
        # Poor choice = 0 points
        assert points == 0

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
                        {"text": "A", "technique": "Excellent choice", "next_node_id": "node_2"},
                        {"text": "B", "technique": "Good choice", "next_node_id": "node_2"}
                    ]
                },
                {
                    "id": "node_2",
                    "patient_statement": "Test statement 2",
                    "practitioner_choices": [
                        {"text": "C", "technique": "Excellent choice", "next_node_id": "end_1"}
                    ]
                },
                {
                    "id": "end_1",
                    "patient_statement": "End",
                    "is_ending": True
                }
            ]
        }
        max_points = ScoringService.calculate_max_points_available(dialogue_content)
        # Should calculate based on optimal path: node_1(excellent) + node_2(excellent) + end bonus
        assert max_points > 0
        assert isinstance(max_points, int)

    def test_calculate_max_points_available_empty_dialogue(self):
        """Test calculating max points from empty dialogue"""
        assert ScoringService.calculate_max_points_available({}) == 0
        assert ScoringService.calculate_max_points_available(None) == 0

    def test_calculate_completion_score_clamped_to_100(self):
        """Test that completion score is clamped to 100 even if points exceed max"""
        # User somehow earned more points than max (shouldn't happen normally)
        score = ScoringService.calculate_completion_score(
            total_nodes=10,
            nodes_completed=10,
            correct_choices=10,
            points_earned=1500,
            max_points_available=1000
        )
        assert score == 100

    def test_calculate_completion_score_backward_compatibility(self):
        """Test that old formula still works when max_points_available not provided"""
        # This ensures backward compatibility
        score = ScoringService.calculate_completion_score(
            total_nodes=10,
            nodes_completed=5,
            correct_choices=4
        )
        # Old formula: (5/10)*50 + (4/5)*50 = 25 + 40 = 65
        assert score == 65
