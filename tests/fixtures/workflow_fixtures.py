"""
Fixtures for workflow and integration manager tests.
"""
import pytest
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock

from src.workflows.agent_workflow import AgentWorkflow
from src.workflows.workflow_service import WorkflowService
from src.workflows.patterns import WorkflowPattern
from src.integrations.integration_manager import IntegrationManager
from src.integrations.github import GitHubIntegration
from src.integrations.jira import JiraIntegration
from src.integrations.slack import SlackIntegration

@pytest.fixture
async def mock_github_integration() -> AsyncGenerator[GitHubIntegration, None]:
    """Mock GitHub integration for testing."""
    integration = GitHubIntegration(
        token="test_token",
        owner="test_owner",
        repo="test_repo"
    )
    integration.create_issue = AsyncMock()
    integration.update_issue = AsyncMock()
    integration.get_issue = AsyncMock()
    yield integration

@pytest.fixture
async def mock_jira_integration() -> AsyncGenerator[JiraIntegration, None]:
    """Mock Jira integration for testing."""
    integration = JiraIntegration(
        url="https://test.atlassian.net",
        username="test_user",
        token="test_token"
    )
    integration.create_issue = AsyncMock()
    integration.update_issue = AsyncMock()
    integration.get_issue = AsyncMock()
    yield integration

@pytest.fixture
async def mock_slack_integration() -> AsyncGenerator[SlackIntegration, None]:
    """Mock Slack integration for testing."""
    integration = SlackIntegration(token="test_token")
    integration.send_message = AsyncMock()
    integration.update_message = AsyncMock()
    yield integration

@pytest.fixture
async def integration_manager(
    mock_github_integration: GitHubIntegration,
    mock_jira_integration: JiraIntegration,
    mock_slack_integration: SlackIntegration
) -> AsyncGenerator[IntegrationManager, None]:
    """Integration manager fixture with mock integrations."""
    manager = IntegrationManager()
    manager.register_integration("github", mock_github_integration)
    manager.register_integration("jira", mock_jira_integration)
    manager.register_integration("slack", mock_slack_integration)
    yield manager

@pytest.fixture
async def workflow_pattern() -> AsyncGenerator[WorkflowPattern, None]:
    """Workflow pattern fixture for testing."""
    pattern = WorkflowPattern(
        name="test_pattern",
        description="Test workflow pattern",
        steps=[
            {"name": "step1", "type": "task", "action": "create_issue"},
            {"name": "step2", "type": "task", "action": "update_issue"}
        ]
    )
    yield pattern

@pytest.fixture
async def workflow_service(
    integration_manager: IntegrationManager,
    workflow_pattern: WorkflowPattern
) -> AsyncGenerator[WorkflowService, None]:
    """Workflow service fixture for testing."""
    service = WorkflowService(integration_manager=integration_manager)
    service.register_pattern(workflow_pattern)
    yield service

@pytest.fixture
async def agent_workflow(
    workflow_service: WorkflowService,
    workflow_pattern: WorkflowPattern
) -> AsyncGenerator[AgentWorkflow, None]:
    """Agent workflow fixture for testing."""
    workflow = AgentWorkflow(
        workflow_id="test_workflow",
        pattern_name="test_pattern",
        service=workflow_service
    )
    yield workflow

@pytest.fixture
def mock_workflow_context() -> Dict[str, Any]:
    """Mock workflow context for testing."""
    return {
        "workflow_id": "test_workflow",
        "pattern_name": "test_pattern",
        "user_id": "test_user",
        "metadata": {
            "priority": "high",
            "labels": ["bug", "critical"],
            "assignee": "test_assignee"
        }
    }
