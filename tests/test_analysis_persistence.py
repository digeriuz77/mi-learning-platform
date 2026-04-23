"""Tests for analysis persistence service."""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from app.services.analysis_persistence_service import (
    save_conversation_analysis,
    get_analysis_by_id,
    get_user_analyses,
    get_all_analyses,
)
from app.models.chat import ConversationAnalysis, MITechniqueUsed


@pytest.fixture
def sample_analysis():
    """Return a sample ConversationAnalysis object."""
    return ConversationAnalysis(
        overall_score=4.0,
        foundational_trust_safety=4.0,
        empathic_partnership_autonomy=3.5,
        empowerment_clarity=4.5,
        mi_spirit_score=4.0,
        partnership_demonstrated=True,
        acceptance_demonstrated=True,
        compassion_demonstrated=True,
        evocation_demonstrated=True,
        techniques_used=[
            MITechniqueUsed(
                technique="open_question",
                turn_number=1,
                example="Can you tell me more about that?",
                effectiveness="effective",
            )
        ],
        techniques_count={"open_question": 1},
        strengths=["Good rapport building"],
        areas_for_improvement=["More reflections"],
        client_movement="toward_change",
        change_talk_evoked=True,
        transcript_summary="Test summary",
        summary="Test summary",
        key_moments=[],
        suggestions_for_next_time=["Practice reflections"],
    )


@pytest.fixture
def sample_transcript():
    """Return a sample transcript."""
    return [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"},
    ]


class TestSaveConversationAnalysis:
    """Tests for save_conversation_analysis."""

    def test_save_success(self, sample_analysis, sample_transcript):
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{"id": "test-analysis-id-123"}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_result

        with patch("app.services.analysis_persistence_service.get_supabase_admin", return_value=mock_supabase):
            result = save_conversation_analysis(
                session_id="session-123",
                analysis=sample_analysis,
                transcript=sample_transcript,
                persona_id="persona-123",
                persona_name="Test Persona",
                user_id="user-123",
                total_turns=2,
            )

        assert result == "test-analysis-id-123"
        mock_supabase.table.assert_called_once_with("conversation_analyses")

    def test_save_no_data_returned(self, sample_analysis, sample_transcript):
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = []
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_result

        with patch("app.services.analysis_persistence_service.get_supabase_admin", return_value=mock_supabase):
            result = save_conversation_analysis(
                session_id="session-123",
                analysis=sample_analysis,
                transcript=sample_transcript,
            )

        assert result is None

    def test_save_database_error(self, sample_analysis, sample_transcript):
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.insert.return_value.execute.side_effect = Exception("DB connection failed")

        with patch("app.services.analysis_persistence_service.get_supabase_admin", return_value=mock_supabase):
            result = save_conversation_analysis(
                session_id="session-123",
                analysis=sample_analysis,
                transcript=sample_transcript,
            )

        assert result is None


class TestGetAnalysisById:
    """Tests for get_analysis_by_id."""

    def test_get_success(self):
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{"id": "analysis-123", "overall_score": 4.0}]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_result

        with patch("app.services.analysis_persistence_service.get_supabase", return_value=mock_supabase):
            result = get_analysis_by_id("analysis-123")

        assert result == {"id": "analysis-123", "overall_score": 4.0}

    def test_get_with_user_filter(self):
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{"id": "analysis-123", "user_id": "user-123"}]

        mock_query = MagicMock()
        mock_query.eq.return_value.execute.return_value = mock_result
        mock_supabase.table.return_value.select.return_value.eq.return_value = mock_query

        with patch("app.services.analysis_persistence_service.get_supabase", return_value=mock_supabase):
            result = get_analysis_by_id("analysis-123", user_id="user-123")

        assert result == {"id": "analysis-123", "user_id": "user-123"}
        mock_query.eq.assert_called_once_with("user_id", "user-123")

    def test_get_not_found(self):
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_result

        with patch("app.services.analysis_persistence_service.get_supabase", return_value=mock_supabase):
            result = get_analysis_by_id("nonexistent-id")

        assert result is None


class TestGetUserAnalyses:
    """Tests for get_user_analyses."""

    def test_get_user_analyses_success(self):
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [
            {"id": "analysis-1", "user_id": "user-123"},
            {"id": "analysis-2", "user_id": "user-123"},
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_result

        with patch("app.services.analysis_persistence_service.get_supabase", return_value=mock_supabase):
            result = get_user_analyses("user-123", limit=10)

        assert len(result) == 2
        assert result[0]["id"] == "analysis-1"

    def test_get_user_analyses_error(self):
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.side_effect = Exception("DB error")

        with patch("app.services.analysis_persistence_service.get_supabase", return_value=mock_supabase):
            result = get_user_analyses("user-123")

        assert result == []


class TestGetAllAnalyses:
    """Tests for get_all_analyses."""

    def test_get_all_analyses_success(self):
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [
            {"id": "analysis-1"},
            {"id": "analysis-2"},
        ]
        mock_supabase.table.return_value.select.return_value.order.return_value.limit.return_value.offset.return_value.execute.return_value = mock_result

        with patch("app.services.analysis_persistence_service.get_supabase", return_value=mock_supabase):
            result = get_all_analyses(limit=50, offset=0)

        assert len(result) == 2

    def test_get_all_analyses_error(self):
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.order.return_value.limit.return_value.offset.return_value.execute.side_effect = Exception("DB error")

        with patch("app.services.analysis_persistence_service.get_supabase", return_value=mock_supabase):
            result = get_all_analyses()

        assert result == []
