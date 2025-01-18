"""
Tests for Jira integration.
"""

import pytest
from unittest.mock import patch, MagicMock
from src.integrations.jira import JiraIntegration

@pytest.fixture
def jira():
    return JiraIntegration("test-token", "test.atlassian.net")

@pytest.mark.asyncio
async def test_create_issue(jira):
    with patch.object(jira, '_make_request') as mock_request:
        mock_request.return_value = {
            "id": "10000",
            "key": "TEST-1",
            "self": "https://test.atlassian.net/rest/api/3/issue/10000"
        }
        
        result = await jira.create_issue(
            project_key="TEST",
            summary="Test Issue",
            description="Test Description",
            issue_type="Task",
            priority="High",
            labels=["bug"],
            assignee="user123"
        )
        
        mock_request.assert_called_once()
        call_args = mock_request.call_args[0]
        assert call_args[0] == "POST"
        assert call_args[1] == "https://test.atlassian.net/rest/api/3/issue"
        
        data = mock_request.call_args[1]["data"]
        assert data["fields"]["project"]["key"] == "TEST"
        assert data["fields"]["summary"] == "Test Issue"
        assert data["fields"]["issuetype"]["name"] == "Task"
        assert data["fields"]["priority"]["name"] == "High"
        assert data["fields"]["labels"] == ["bug"]
        assert data["fields"]["assignee"]["accountId"] == "user123"
        
        assert result["key"] == "TEST-1"

@pytest.mark.asyncio
async def test_get_issue(jira):
    with patch.object(jira, '_make_request') as mock_request:
        mock_request.return_value = {
            "id": "10000",
            "key": "TEST-1",
            "fields": {
                "summary": "Test Issue",
                "status": {"name": "To Do"}
            }
        }
        
        result = await jira.get_issue("TEST-1")
        
        mock_request.assert_called_once_with(
            "GET",
            "https://test.atlassian.net/rest/api/3/issue/TEST-1"
        )
        assert result["key"] == "TEST-1"
        assert result["fields"]["summary"] == "Test Issue"

@pytest.mark.asyncio
async def test_add_comment(jira):
    with patch.object(jira, '_make_request') as mock_request:
        mock_request.return_value = {
            "id": "10000",
            "body": {
                "content": [{"text": "Test Comment"}]
            }
        }
        
        result = await jira.add_comment(
            issue_key="TEST-1",
            comment="Test Comment"
        )
        
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[0][0] == "POST"
        assert call_args[0][1] == "https://test.atlassian.net/rest/api/3/issue/TEST-1/comment"
        
        data = call_args[1]["data"]
        assert data["body"]["content"][0]["content"][0]["text"] == "Test Comment"

@pytest.mark.asyncio
async def test_transition_issue(jira):
    with patch.object(jira, '_make_request') as mock_request:
        await jira.transition_issue("TEST-1", "21")
        
        mock_request.assert_called_once_with(
            "POST",
            "https://test.atlassian.net/rest/api/3/issue/TEST-1/transitions",
            data={"transition": {"id": "21"}}
        )

@pytest.mark.asyncio
async def test_health_check_success(jira):
    with patch.object(jira, '_make_request') as mock_request:
        mock_request.return_value = {"accountId": "test123"}
        result = await jira.health_check()
        assert result is True

@pytest.mark.asyncio
async def test_health_check_failure(jira):
    with patch.object(jira, '_make_request') as mock_request:
        mock_request.side_effect = Exception("API Error")
        result = await jira.health_check()
        assert result is False
