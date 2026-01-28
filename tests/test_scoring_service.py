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
            evoked_change_talk=True
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
