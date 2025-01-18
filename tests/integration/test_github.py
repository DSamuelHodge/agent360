"""
Tests for GitHub integration.
"""

import pytest
from unittest.mock import patch, MagicMock
from src.integrations.github import GitHubIntegration

@pytest.fixture
def github():
    return GitHubIntegration("test-token")

@pytest.mark.asyncio
async def test_create_issue(github):
    with patch.object(github, '_make_request') as mock_request:
        mock_request.return_value = {
            "number": 1,
            "title": "Test Issue",
            "body": "Test Description"
        }
        
        result = await github.create_issue(
            repo="test/repo",
            title="Test Issue",
            body="Test Description",
            labels=["bug"],
            assignees=["user1"]
        )
        
        mock_request.assert_called_once_with(
            "POST",
            "https://api.github.com/repos/test/repo/issues",
            data={
                "title": "Test Issue",
                "body": "Test Description",
                "labels": ["bug"],
                "assignees": ["user1"]
            }
        )
        assert result["number"] == 1
        assert result["title"] == "Test Issue"

@pytest.mark.asyncio
async def test_list_pull_requests(github):
    with patch.object(github, '_make_request') as mock_request:
        mock_request.return_value = [
            {"number": 1, "title": "PR 1"},
            {"number": 2, "title": "PR 2"}
        ]
        
        result = await github.list_pull_requests(
            repo="test/repo",
            state="open"
        )
        
        mock_request.assert_called_once_with(
            "GET",
            "https://api.github.com/repos/test/repo/pulls",
            params={
                "state": "open",
                "sort": "created",
                "direction": "desc"
            }
        )
        assert len(result) == 2
        assert result[0]["number"] == 1

@pytest.mark.asyncio
async def test_create_comment(github):
    with patch.object(github, '_make_request') as mock_request:
        mock_request.return_value = {
            "id": 1,
            "body": "Test Comment"
        }
        
        result = await github.create_comment(
            repo="test/repo",
            issue_number=1,
            body="Test Comment"
        )
        
        mock_request.assert_called_once_with(
            "POST",
            "https://api.github.com/repos/test/repo/issues/1/comments",
            data={"body": "Test Comment"}
        )
        assert result["id"] == 1
        assert result["body"] == "Test Comment"

@pytest.mark.asyncio
async def test_health_check_success(github):
    with patch.object(github, '_make_request') as mock_request:
        mock_request.return_value = {"resources": {}}
        result = await github.health_check()
        assert result is True

@pytest.mark.asyncio
async def test_health_check_failure(github):
    with patch.object(github, '_make_request') as mock_request:
        mock_request.side_effect = Exception("API Error")
        result = await github.health_check()
        assert result is False
