"""
External service integrations for Agent360.
"""

from .github import GitHubIntegration
from .jira import JiraIntegration
from .slack import SlackIntegration

__all__ = ['GitHubIntegration', 'JiraIntegration', 'SlackIntegration']
