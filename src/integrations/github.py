"""
GitHub API integration for Agent360.
"""

from typing import Dict, Any, List, Optional
from .base import BaseIntegration

class GitHubIntegration(BaseIntegration):
    """Integration with GitHub API."""
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self, api_token: str):
        """Initialize GitHub integration.
        
        Args:
            api_token: GitHub API token
        """
        super().__init__(api_token)
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get GitHub authentication headers."""
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    async def health_check(self) -> bool:
        """Check if GitHub API is accessible."""
        try:
            await self._make_request("GET", f"{self.BASE_URL}/rate_limit")
            return True
        except Exception:
            return False
    
    async def create_issue(
        self,
        repo: str,
        title: str,
        body: str,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create a new issue in a repository.
        
        Args:
            repo: Repository in format 'owner/repo'
            title: Issue title
            body: Issue description
            labels: Optional list of labels
            assignees: Optional list of assignees
            
        Returns:
            Created issue data
        """
        data = {
            "title": title,
            "body": body,
            "labels": labels or [],
            "assignees": assignees or []
        }
        
        return await self._make_request(
            "POST",
            f"{self.BASE_URL}/repos/{repo}/issues",
            data=data
        )
    
    async def list_pull_requests(
        self,
        repo: str,
        state: str = "open",
        sort: str = "created",
        direction: str = "desc"
    ) -> List[Dict[str, Any]]:
        """List pull requests in a repository.
        
        Args:
            repo: Repository in format 'owner/repo'
            state: PR state (open, closed, all)
            sort: Sort field (created, updated, popularity)
            direction: Sort direction (asc, desc)
            
        Returns:
            List of pull requests
        """
        params = {
            "state": state,
            "sort": sort,
            "direction": direction
        }
        
        return await self._make_request(
            "GET",
            f"{self.BASE_URL}/repos/{repo}/pulls",
            params=params
        )
    
    async def create_comment(
        self,
        repo: str,
        issue_number: int,
        body: str
    ) -> Dict[str, Any]:
        """Create a comment on an issue or pull request.
        
        Args:
            repo: Repository in format 'owner/repo'
            issue_number: Issue or PR number
            body: Comment text
            
        Returns:
            Created comment data
        """
        data = {"body": body}
        
        return await self._make_request(
            "POST",
            f"{self.BASE_URL}/repos/{repo}/issues/{issue_number}/comments",
            data=data
        )
    
    async def get_repository(self, repo: str) -> Dict[str, Any]:
        """Get repository information.
        
        Args:
            repo: Repository in format 'owner/repo'
            
        Returns:
            Repository data
        """
        return await self._make_request(
            "GET",
            f"{self.BASE_URL}/repos/{repo}"
        )
