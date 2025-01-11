"""
Integration tests for Agent360 API.
"""
import pytest
from fastapi.testclient import TestClient
from src.api.main import app

@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)

def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_agent_execution(client):
    """Test agent execution endpoint."""
    request_data = {
        "input": {
            "query": "What is the weather in London?",
            "tools": ["rest_tool"]
        },
        "timeout": 30
    }
    
    response = client.post("/api/v1/agent/execute", json=request_data)
    assert response.status_code == 200
    assert "output" in response.json()
    assert "execution_time" in response.json()
    assert "tool_usage" in response.json()

def test_tool_listing(client):
    """Test tool listing endpoint."""
    response = client.get("/api/v1/agent/tools")
    assert response.status_code == 200
    tools = response.json()
    assert isinstance(tools, dict)
    assert len(tools) > 0
    
def test_invalid_request(client):
    """Test invalid request handling."""
    request_data = {
        "input": {}  # Missing required fields
    }
    
    response = client.post("/api/v1/agent/execute", json=request_data)
    assert response.status_code == 422  # Validation error

def test_authentication(client):
    """Test authentication requirements."""
    request_data = {
        "input": {
            "query": "Test query"
        }
    }
    
    # Request without authentication
    response = client.post("/api/v1/agent/execute", json=request_data)
    assert response.status_code == 401  # Unauthorized
    
    # Request with invalid token
    headers = {"Authorization": "Bearer invalid-token"}
    response = client.post(
        "/api/v1/agent/execute",
        json=request_data,
        headers=headers
    )
    assert response.status_code == 401  # Unauthorized
