"""
Tests for Modules API endpoints
"""
import pytest
from fastapi import status
from unittest.mock import Mock, patch


class TestModulesAPI:
    """Test suite for Modules API"""

    @patch('app.api.v1.modules.get_supabase')
    @patch('app.api.v1.modules.get_current_user')
    def test_list_modules(self, mock_get_current_user, mock_get_supabase, client, mock_supabase_client, sample_user, sample_module):
        """Test listing all modules"""
        mock_get_supabase.return_value = mock_supabase_client
        mock_get_current_user.return_value = sample_user
        
        # Mock modules response
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = Mock(
            data=[sample_module]
        )
        
        # Mock progress response
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
            data=[]
        )
        
        response = client.get("/api/v1/modules", headers={"Authorization": "Bearer test-token"})
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "modules" in data
        assert "total" in data

    @patch('app.api.v1.modules.get_supabase')
    @patch('app.api.v1.modules.get_current_user')
    def test_get_module_detail(self, mock_get_current_user, mock_get_supabase, client, mock_supabase_client, sample_user, sample_module):
        """Test getting a specific module"""
        mock_get_supabase.return_value = mock_supabase_client
        mock_get_current_user.return_value = sample_user
        
        # Mock module response
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
            data=[sample_module]
        )
        
        # Mock progress response
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = Mock(
            data=[]
        )
        
        response = client.get(f"/api/v1/modules/{sample_module['id']}", headers={"Authorization": "Bearer test-token"})
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == sample_module["id"]
        assert data["title"] == sample_module["title"]

    @patch('app.api.v1.modules.get_supabase')
    @patch('app.api.v1.modules.get_current_user')
    def test_get_module_not_found(self, mock_get_current_user, mock_get_supabase, client, mock_supabase_client, sample_user):
        """Test getting a non-existent module returns 404"""
        mock_get_supabase.return_value = mock_supabase_client
        mock_get_current_user.return_value = sample_user
        
        # Mock empty response
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
            data=[]
        )
        
        response = client.get("/api/v1/modules/non-existent-id", headers={"Authorization": "Bearer test-token"})
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch('app.api.v1.modules.get_supabase')
    @patch('app.api.v1.modules.get_current_user')
    def test_start_module(self, mock_get_current_user, mock_get_supabase, client, mock_supabase_client, sample_user, sample_module, sample_progress):
        """Test starting a new module"""
        mock_get_supabase.return_value = mock_supabase_client
        mock_get_current_user.return_value = sample_user
        
        # Mock module exists
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.side_effect = [
            Mock(data=[sample_module]),  # First call - check module exists
            Mock(data=[]),  # Second call - check existing progress
        ]
        
        # Mock insert progress
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = Mock(
            data=[sample_progress]
        )
        
        response = client.post(f"/api/v1/modules/{sample_module['id']}/start", headers={"Authorization": "Bearer test-token"})
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "progress_id" in data
        assert "current_node_id" in data

    @patch('app.api.v1.modules.get_supabase')
    @patch('app.api.v1.modules.get_current_user')
    def test_start_module_already_in_progress(self, mock_get_current_user, mock_get_supabase, client, mock_supabase_client, sample_user, sample_module, sample_progress):
        """Test starting a module that's already in progress"""
        mock_get_supabase.return_value = mock_supabase_client
        mock_get_current_user.return_value = sample_user
        
        # Mock module exists and progress exists
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.side_effect = [
            Mock(data=[sample_module]),  # Check module exists
            Mock(data=[sample_progress]),  # Check existing progress
        ]
        
        response = client.post(f"/api/v1/modules/{sample_module['id']}/start", headers={"Authorization": "Bearer test-token"})
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Module already in progress"

    @patch('app.api.v1.modules.get_supabase')
    @patch('app.api.v1.modules.get_current_user')
    def test_restart_module(self, mock_get_current_user, mock_get_supabase, client, mock_supabase_client, sample_user, sample_module, sample_progress):
        """Test restarting a module"""
        mock_get_supabase.return_value = mock_supabase_client
        mock_get_current_user.return_value = sample_user
        
        # Mock module exists and progress exists
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.side_effect = [
            Mock(data=[sample_module]),  # Check module exists
            Mock(data=[sample_progress]),  # Check existing progress
        ]
        
        # Mock update progress
        mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value = Mock(
            data=[{**sample_progress, "status": "in_progress", "nodes_completed": [], "points_earned": 0}]
        )
        
        response = client.post(f"/api/v1/modules/{sample_module['id']}/restart", headers={"Authorization": "Bearer test-token"})
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Module restarted"

    @patch('app.api.v1.modules.get_supabase')
    @patch('app.api.v1.modules.get_current_user')
    def test_start_nonexistent_module(self, mock_get_current_user, mock_get_supabase, client, mock_supabase_client, sample_user):
        """Test starting a non-existent module returns 404"""
        mock_get_supabase.return_value = mock_supabase_client
        mock_get_current_user.return_value = sample_user
        
        # Mock module not found
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
            data=[]
        )
        
        response = client.post("/api/v1/modules/non-existent-id/start", headers={"Authorization": "Bearer test-token"})
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
