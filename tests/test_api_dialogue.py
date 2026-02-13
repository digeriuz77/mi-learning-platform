"""
Tests for Dialogue API endpoints
"""

import pytest
from fastapi import status
from unittest.mock import Mock, patch, AsyncMock


class TestDialogueAPI:
    """Test suite for Dialogue API"""

    @patch("app.api.v1.dialogue.get_supabase_admin")
    @patch("app.api.v1.dialogue.get_supabase")
    @patch("app.api.v1.dialogue.get_current_user")
    def test_submit_choice_success(
        self, mock_get_current_user, mock_get_supabase, mock_get_supabase_admin, client, sample_user
    ):
        """Test successful choice submission"""
        mock_get_current_user.return_value = sample_user

        mock_supabase = Mock()
        mock_supabase_admin = Mock()
        mock_get_supabase.return_value = mock_supabase
        mock_get_supabase_admin.return_value = mock_supabase_admin

        module_id = "test-module-id"
        progress_id = "test-progress-id"

        sample_module = {
            "id": module_id,
            "module_number": 1,
            "title": "Test Module",
            "dialogue_content": {
                "start_node": "node_1",
                "nodes": [
                    {
                        "id": "node_1",
                        "is_ending": False,
                        "practitioner_choices": [
                            {
                                "id": "choice_0",
                                "technique": "reflection",
                                "feedback": "Good reflection!",
                                "next_node_id": "node_2",
                            }
                        ],
                    },
                    {"id": "node_2", "is_ending": True, "practitioner_choices": []},
                ],
            },
            "max_points_available": 600,
        }

        sample_progress = {
            "id": progress_id,
            "user_id": sample_user.user_id,
            "module_id": module_id,
            "status": "in_progress",
            "current_node_id": "node_1",
            "nodes_completed": [],
            "nodes_visited": [],
            "points_earned": 0,
            "technique_quality_counts": {"excellent": 0, "good": 0, "acceptable": 0, "poor": 0},
        }

        sample_profile = {"user_id": sample_user.user_id, "total_points": 0, "level": 1, "modules_completed": 0}

        def table_side_effect(table_name):
            mock_table = Mock()

            if table_name == "learning_modules":
                mock_table.select.return_value.eq.return_value.execute.return_value = Mock(data=[sample_module])
            elif table_name == "user_progress":
                mock_table.select.return_value.eq.return_value.execute.return_value = Mock(data=[sample_progress])
            elif table_name == "dialogue_attempts":
                mock_table.insert.return_value.execute.return_value = Mock(data=[{"id": "attempt-id"}])
                mock_table.select.return_value.eq.return_value.execute.return_value = Mock(data=[])
            elif table_name == "user_profiles":
                mock_table.select.return_value.eq.return_value.execute.return_value = Mock(data=[sample_profile])
                mock_table.update.return_value.eq.return_value.execute.return_value = Mock(data=[sample_profile])

            return mock_table

        mock_supabase.table.side_effect = table_side_effect
        mock_supabase_admin.table.side_effect = table_side_effect

        response = client.post(
            "/api/v1/dialogue/submit",
            json={
                "module_id": module_id,
                "node_id": "node_1",
                "choice_id": "choice_0",
                "choice_text": "I hear you're feeling conflicted about making a change.",
                "technique": "reflection",
            },
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "is_correct" in data
        assert "points_earned" in data
        assert "next_node_id" in data

    @patch("app.api.v1.dialogue.get_supabase")
    @patch("app.api.v1.dialogue.get_current_user")
    def test_submit_choice_module_not_started(self, mock_get_current_user, mock_get_supabase, client, sample_user):
        """Test submitting choice when module not started"""
        mock_get_current_user.return_value = sample_user

        mock_supabase = Mock()
        mock_get_supabase.return_value = mock_supabase

        mock_table = Mock()
        mock_table.select.return_value.eq.return_value.execute.return_value = Mock(data=[])
        mock_supabase.table.return_value = mock_table

        response = client.post(
            "/api/v1/dialogue/submit",
            json={
                "module_id": "test-module-id",
                "node_id": "node_1",
                "choice_id": "choice_0",
                "choice_text": "Test choice",
                "technique": "reflection",
            },
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Module not started" in response.json()["detail"]

    @patch("app.api.v1.dialogue.get_supabase_admin")
    @patch("app.api.v1.dialogue.get_supabase")
    @patch("app.api.v1.dialogue.get_current_user")
    def test_submit_choice_wrong_node(
        self, mock_get_current_user, mock_get_supabase, mock_get_supabase_admin, client, sample_user
    ):
        """Test submitting choice for wrong node"""
        mock_get_current_user.return_value = sample_user

        mock_supabase = Mock()
        mock_supabase_admin = Mock()
        mock_get_supabase.return_value = mock_supabase
        mock_get_supabase_admin.return_value = mock_supabase_admin

        module_id = "test-module-id"

        sample_module = {
            "id": module_id,
            "dialogue_content": {
                "start_node": "node_1",
                "nodes": [{"id": "node_1", "is_ending": False, "practitioner_choices": []}],
            },
            "max_points_available": 600,
        }

        sample_progress = {
            "id": "progress-id",
            "user_id": sample_user.user_id,
            "module_id": module_id,
            "status": "in_progress",
            "current_node_id": "node_1",
            "nodes_completed": [],
            "nodes_visited": [],
            "points_earned": 0,
            "technique_quality_counts": {"excellent": 0, "good": 0, "acceptable": 0, "poor": 0},
        }

        def table_side_effect(table_name):
            mock_table = Mock()
            if table_name == "learning_modules":
                mock_table.select.return_value.eq.return_value.execute.return_value = Mock(data=[sample_module])
            elif table_name == "user_progress":
                mock_table.select.return_value.eq.return_value.execute.return_value = Mock(data=[sample_progress])
            return mock_table

        mock_supabase.table.side_effect = table_side_effect
        mock_supabase_admin.table.side_effect = table_side_effect

        response = client.post(
            "/api/v1/dialogue/submit",
            json={
                "module_id": module_id,
                "node_id": "node_wrong",  # Wrong node
                "choice_id": "choice_0",
                "choice_text": "Test choice",
                "technique": "reflection",
            },
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "does not match your current node" in response.json()["detail"]

    @patch("app.api.v1.dialogue.get_supabase_admin")
    @patch("app.api.v1.dialogue.get_supabase")
    @patch("app.api.v1.dialogue.get_current_user")
    def test_submit_choice_invalid_choice(
        self, mock_get_current_user, mock_get_supabase, mock_get_supabase_admin, client, sample_user
    ):
        """Test submitting invalid choice ID"""
        mock_get_current_user.return_value = sample_user

        mock_supabase = Mock()
        mock_supabase_admin = Mock()
        mock_get_supabase.return_value = mock_supabase
        mock_get_supabase_admin.return_value = mock_supabase_admin

        module_id = "test-module-id"

        sample_module = {
            "id": module_id,
            "dialogue_content": {
                "start_node": "node_1",
                "nodes": [
                    {
                        "id": "node_1",
                        "is_ending": False,
                        "practitioner_choices": [
                            {"id": "choice_0", "technique": "reflection", "feedback": "Good", "next_node_id": "node_2"}
                        ],
                    }
                ],
            },
            "max_points_available": 600,
        }

        sample_progress = {
            "id": "progress-id",
            "user_id": sample_user.user_id,
            "module_id": module_id,
            "status": "in_progress",
            "current_node_id": "node_1",
            "nodes_completed": [],
            "nodes_visited": [],
            "points_earned": 0,
            "technique_quality_counts": {"excellent": 0, "good": 0, "acceptable": 0, "poor": 0},
        }

        def table_side_effect(table_name):
            mock_table = Mock()
            if table_name == "learning_modules":
                mock_table.select.return_value.eq.return_value.execute.return_value = Mock(data=[sample_module])
            elif table_name == "user_progress":
                mock_table.select.return_value.eq.return_value.execute.return_value = Mock(data=[sample_progress])
            return mock_table

        mock_supabase.table.side_effect = table_side_effect
        mock_supabase_admin.table.side_effect = table_side_effect

        response = client.post(
            "/api/v1/dialogue/submit",
            json={
                "module_id": module_id,
                "node_id": "node_1",
                "choice_id": "choice_invalid",  # Invalid choice
                "choice_text": "Test choice",
                "technique": "reflection",
            },
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid choice" in response.json()["detail"]

    @patch("app.api.v1.dialogue.get_supabase")
    @patch("app.api.v1.dialogue.get_current_user")
    def test_submit_choice_unauthenticated(self, mock_get_current_user, mock_get_supabase, client):
        """Test submitting choice without authentication"""
        mock_get_current_user.side_effect = Exception("Not authenticated")

        response = client.post(
            "/api/v1/dialogue/submit",
            json={
                "module_id": "test-module-id",
                "node_id": "node_1",
                "choice_id": "choice_0",
                "choice_text": "Test choice",
                "technique": "reflection",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
