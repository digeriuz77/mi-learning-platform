"""
Tests for Authentication API endpoints
"""
import pytest
from fastapi import status
from unittest.mock import Mock, patch


class TestAuthAPI:
    """Test suite for Authentication API"""

    def test_root_endpoint(self, client):
        """Test the root endpoint returns API info"""
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "docs" in data

    def test_health_check(self, client):
        """Test the health check endpoint"""
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "healthy"}

    @patch('app.api.v1.auth.get_supabase')
    def test_register_success(self, mock_get_supabase, client, mock_supabase_client, sample_user):
        """Test successful user registration"""
        mock_get_supabase.return_value = mock_supabase_client
        
        # Mock the auth response
        mock_auth_response = Mock()
        mock_auth_response.user = Mock(
            id=sample_user["id"],
            email=sample_user["email"],
            created_at=sample_user["created_at"]
        )
        mock_auth_response.session = Mock(access_token="test-access-token")
        mock_supabase_client.auth.sign_up.return_value = mock_auth_response
        
        response = client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "password123",
            "display_name": "Test User"
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == "test@example.com"

    @patch('app.api.v1.auth.get_supabase')
    def test_register_duplicate_email(self, mock_get_supabase, client, mock_supabase_client):
        """Test registration with duplicate email fails"""
        mock_get_supabase.return_value = mock_supabase_client
        
        # Mock the auth response to simulate duplicate email
        mock_supabase_client.auth.sign_up.side_effect = Exception("User already registered")
        
        response = client.post("/api/v1/auth/register", json={
            "email": "existing@example.com",
            "password": "password123",
            "display_name": "Test User"
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_invalid_email(self, client):
        """Test registration with invalid email fails"""
        response = client.post("/api/v1/auth/register", json={
            "email": "invalid-email",
            "password": "password123",
            "display_name": "Test User"
        })
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_short_password(self, client):
        """Test registration with short password fails"""
        response = client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "12345",  # Less than 6 characters
            "display_name": "Test User"
        })
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch('app.api.v1.auth.get_supabase')
    def test_login_success(self, mock_get_supabase, client, mock_supabase_client, sample_user):
        """Test successful login"""
        mock_get_supabase.return_value = mock_supabase_client
        
        # Mock the auth response
        mock_auth_response = Mock()
        mock_auth_response.user = Mock(
            id=sample_user["id"],
            email=sample_user["email"],
            created_at=sample_user["created_at"]
        )
        mock_auth_response.session = Mock(access_token="test-access-token")
        mock_supabase_client.auth.sign_in_with_password.return_value = mock_auth_response
        
        # Mock profile lookup
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(data=[])
        
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == "test@example.com"

    @patch('app.api.v1.auth.get_supabase')
    def test_login_invalid_credentials(self, mock_get_supabase, client, mock_supabase_client):
        """Test login with invalid credentials fails"""
        mock_get_supabase.return_value = mock_supabase_client
        
        mock_supabase_client.auth.sign_in_with_password.side_effect = Exception("Invalid login credentials")
        
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "wrongpassword"
        })
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_missing_fields(self, client):
        """Test login with missing fields fails"""
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com"
            # Missing password
        })
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch('app.api.v1.auth.get_supabase')
    @patch('app.api.v1.auth.get_current_user')
    def test_logout_success(self, mock_get_current_user, mock_get_supabase, client, mock_supabase_client, sample_user):
        """Test successful logout"""
        mock_get_supabase.return_value = mock_supabase_client
        mock_get_current_user.return_value = sample_user
        
        response = client.post("/api/v1/auth/logout", headers={"Authorization": "Bearer test-token"})
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Successfully logged out"

    def test_protected_endpoint_without_auth(self, client):
        """Test accessing protected endpoint without authentication fails"""
        response = client.get("/api/v1/modules")
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_protected_endpoint_with_invalid_auth(self, client):
        """Test accessing protected endpoint with invalid token fails"""
        response = client.get("/api/v1/modules", headers={"Authorization": "Bearer invalid-token"})
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
