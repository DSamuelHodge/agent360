"""
Jira API integration for Agent360.
"""

from typing import Dict, Any, List, Optional
from .base import BaseIntegration

class JiraIntegration(BaseIntegration):
    """Integration with Jira API."""
    
    def __init__(self, api_token: str, domain: str):
        """Initialize Jira integration.
        
        Args:
            api_token: Jira API token
            domain: Jira domain (e.g., 'your-domain.atlassian.net')
        """
        super().__init__(api_token)
        self.base_url = f"https://{domain}/rest/api/3"
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get Jira authentication headers."""
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    async def health_check(self) -> bool:
        """Check if Jira API is accessible."""
        try:
            await self._make_request("GET", f"{self.base_url}/myself")
            return True
        except Exception:
            return False
    
    async def create_issue(
        self,
        project_key: str,
        summary: str,
        description: str,
        issue_type: str = "Task",
        priority: Optional[str] = None,
        labels: Optional[List[str]] = None,
        assignee: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new Jira issue.
        
        Args:
            project_key: Project identifier
            summary: Issue summary
            description: Issue description
            issue_type: Issue type (Task, Bug, Story, etc.)
            priority: Issue priority
            labels: Optional list of labels
            assignee: Optional assignee account ID
            
        Returns:
            Created issue data
        """
        data = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": description}]
                        }
                    ]
                },
                "issuetype": {"name": issue_type}
            }
        }
        
        if priority:
            data["fields"]["priority"] = {"name": priority}
        if labels:
            data["fields"]["labels"] = labels
        if assignee:
            data["fields"]["assignee"] = {"accountId": assignee}
        
        return await self._make_request(
            "POST",
            f"{self.base_url}/issue",
            data=data
        )
    
    async def get_issue(self, issue_key: str) -> Dict[str, Any]:
        """Get issue details.
        
        Args:
            issue_key: Issue identifier (e.g., 'PROJ-123')
            
        Returns:
            Issue data
        """
        return await self._make_request(
            "GET",
            f"{self.base_url}/issue/{issue_key}"
        )
    
    async def add_comment(
        self,
        issue_key: str,
        comment: str
    ) -> Dict[str, Any]:
        """Add a comment to an issue.
        
        Args:
            issue_key: Issue identifier
            comment: Comment text
            
        Returns:
            Created comment data
        """
        data = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": comment}]
                    }
                ]
            }
        }
        
        return await self._make_request(
            "POST",
            f"{self.base_url}/issue/{issue_key}/comment",
            data=data
        )
    
    async def transition_issue(
        self,
        issue_key: str,
        transition_id: str
    ) -> None:
        """Transition an issue to a new status.
        
        Args:
            issue_key: Issue identifier
            transition_id: ID of the transition to perform
        """
        data = {
            "transition": {"id": transition_id}
        }
        
        await self._make_request(
            "POST",
            f"{self.base_url}/issue/{issue_key}/transitions",
            data=data
        )
