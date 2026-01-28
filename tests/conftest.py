"""
Pytest configuration and fixtures
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, MagicMock

from app.main import app
from app.config import settings


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def mock_supabase_client():
    """Create a mock Supabase client"""
    mock_client = MagicMock()
    
    # Mock auth methods
    mock_client.auth = MagicMock()
    mock_client.auth.sign_up = MagicMock()
    mock_client.auth.sign_in_with_password = MagicMock()
    mock_client.auth.sign_out = MagicMock()
    mock_client.auth.get_user = MagicMock()
    
    # Mock table methods
    mock_table = MagicMock()
    mock_table.select = MagicMock(return_value=mock_table)
    mock_table.insert = MagicMock(return_value=mock_table)
    mock_table.update = MagicMock(return_value=mock_table)
    mock_table.delete = MagicMock(return_value=mock_table)
    mock_table.eq = MagicMock(return_value=mock_table)
    mock_table.order = MagicMock(return_value=mock_table)
    mock_table.limit = MagicMock(return_value=mock_table)
    mock_table.execute = MagicMock(return_value=MagicMock(data=[]))
    
    mock_client.table = MagicMock(return_value=mock_table)
    
    return mock_client


@pytest.fixture
def sample_user():
    """Return a sample user object"""
    return {
        "id": "test-user-id-123",
        "email": "test@example.com",
        "display_name": "Test User",
        "created_at": "2026-01-01T00:00:00Z"
    }


@pytest.fixture
def sample_module():
    """Return a sample learning module"""
    return {
        "id": "test-module-id-123",
        "module_number": 1,
        "title": "Test Module",
        "slug": "test-module",
        "learning_objective": "Learn test techniques",
        "technique_focus": "Open Questions",
        "stage_of_change": "Precontemplation",
        "description": "A test module for testing",
        "points": 500,
        "dialogue_content": {
            "start_node": "node_1",
            "nodes": [
                {
                    "id": "node_1",
                    "patient_statement": "I don't know if I want to change.",
                    "patient_context": "Initial resistance",
                    "practitioner_choices": [
                        {
                            "text": "Tell me more about that.",
                            "technique": "Open Question",
                            "next_node_id": "node_2",
                            "feedback": "Good open question."
                        },
                        {
                            "text": "You need to change right now!",
                            "technique": "Righting Reflex",
                            "next_node_id": "node_3",
                            "feedback": "This creates resistance."
                        }
                    ]
                }
            ]
        }
    }


@pytest.fixture
def sample_progress():
    """Return a sample user progress object"""
    return {
        "id": "test-progress-id-123",
        "user_id": "test-user-id-123",
        "module_id": "test-module-id-123",
        "status": "in_progress",
        "current_node_id": "node_1",
        "nodes_completed": [],
        "points_earned": 0,
        "completion_score": 0,
        "techniques_demonstrated": {},
        "started_at": "2026-01-01T00:00:00Z"
    }


@pytest.fixture
def auth_headers():
    """Return authentication headers for testing"""
    return {"Authorization": "Bearer test-token-123"}
