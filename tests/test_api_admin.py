"""
Tests for Admin API endpoints
"""

import pytest
from fastapi import status
from unittest.mock import Mock, patch


class TestAdminAPI:
    """Test suite for Admin API"""

    @patch("app.api.v1.admin.get_supabase_admin")
    def test_get_stats_success(self, mock_get_supabase_admin, client, admin_user):
        """Test getting dashboard stats as admin"""
        mock_supabase = Mock()
        mock_get_supabase_admin.return_value = mock_supabase

        mock_supabase.table.return_value.select.return_value.execute.return_value = Mock(
            count=10, data=[{"id": "user1"}]
        )
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
            count=5, data=[{"id": "progress1"}]
        )

        response = client.get("/api/v1/admin/stats", headers={"Authorization": "Bearer test-admin-token"})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_users" in data

    @patch("app.api.v1.admin.get_supabase_admin")
    def test_get_stats_unauthorized(self, mock_get_supabase_admin, client):
        """Test getting dashboard stats without admin role"""
        mock_supabase = Mock()
        mock_get_supabase_admin.return_value = mock_supabase

        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = Mock(
            data={"role": "user"}
        )

        response = client.get("/api/v1/admin/stats", headers={"Authorization": "Bearer test-user-token"})

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("app.api.v1.admin.get_supabase_admin")
    def test_get_users_list(self, mock_get_supabase_admin, client, admin_user):
        """Test listing users as admin"""
        mock_supabase = Mock()
        mock_get_supabase_admin.return_value = mock_supabase

        mock_supabase.table.return_value.select.return_value.execute.return_value = Mock(
            data=[
                {"id": "user1", "email": "user1@test.com", "role": "user", "is_active": True},
                {"id": "user2", "email": "user2@test.com", "role": "admin", "is_active": True},
            ]
        )

        response = client.get("/api/v1/admin/users", headers={"Authorization": "Bearer test-admin-token"})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "users" in data

    @patch("app.api.v1.admin.get_supabase_admin")
    def test_promote_user_to_admin(self, mock_get_supabase_admin, client, admin_user):
        """Test promoting a user to admin"""
        mock_supabase = Mock()
        mock_get_supabase_admin.return_value = mock_supabase

        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = Mock(
            data={"role": "user"}
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = Mock(
            data=[{"id": "user1", "role": "admin"}]
        )

        response = client.post(
            "/api/v1/admin/action",
            json={"action": "promote", "user_id": "user1", "new_role": "admin"},
            headers={"Authorization": "Bearer test-admin-token"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "User promoted to admin"

    @patch("app.api.v1.admin.get_supabase_admin")
    def test_ban_user(self, mock_get_supabase_admin, client, admin_user):
        """Test banning a user"""
        mock_supabase = Mock()
        mock_get_supabase_admin.return_value = mock_supabase

        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = Mock(
            data=[{"id": "user1", "is_active": False}]
        )

        response = client.post(
            "/api/v1/admin/action",
            json={"action": "ban", "user_id": "user1"},
            headers={"Authorization": "Bearer test-admin-token"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "User banned"

    @patch("app.api.v1.admin.get_supabase_admin")
    def test_delete_user(self, mock_get_supabase_admin, client, admin_user):
        """Test deleting a user"""
        mock_supabase = Mock()
        mock_get_supabase_admin.return_value = mock_supabase

        mock_table = Mock()
        mock_table.delete.return_value.eq.return_value.execute.return_value = Mock(data=[{"id": "user1"}])

        def table_side_effect(table_name):
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.post(
            "/api/v1/admin/action",
            json={"action": "delete", "user_id": "user1"},
            headers={"Authorization": "Bearer test-admin-token"},
        )

        assert response.status_code == status.HTTP_200_OK

    @patch("app.api.v1.admin.get_supabase_admin")
    def test_admin_unauthorized_action(self, mock_get_supabase_admin, client, regular_user):
        """Test admin action with non-admin user"""
        mock_supabase = Mock()
        mock_get_supabase_admin.return_value = mock_supabase

        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = Mock(
            data={"role": "user"}
        )

        response = client.post(
            "/api/v1/admin/action",
            json={"action": "promote", "user_id": "user1", "new_role": "admin"},
            headers={"Authorization": "Bearer test-user-token"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("app.api.v1.admin.get_supabase_admin")
    def test_get_module_stats(self, mock_get_supabase_admin, client, admin_user):
        """Test getting module statistics"""
        mock_supabase = Mock()
        mock_get_supabase_admin.return_value = mock_supabase

        mock_supabase.table.return_value.select.return_value.execute.return_value = Mock(
            data=[{"id": "mod1", "title": "Module 1"}, {"id": "mod2", "title": "Module 2"}]
        )

        response = client.get("/api/v1/admin/modules/stats", headers={"Authorization": "Bearer test-admin-token"})

        assert response.status_code == status.HTTP_200_OK
