"""GitHub Integration Client for Issues, Pull Requests, and Releases."""

import logging
from typing import Any, Dict, List, Optional
import httpx
from src.config import settings

logger = logging.getLogger("GitHubClient")

class GitHubClient:
    """Provides direct GitHub API operations alongside the GitHub MCP Server."""

    def __init__(self):
        self.token = settings.GITHUB_TOKEN
        self.repo = settings.GITHUB_REPOSITORY
        self.base_url = "https://api.github.com"

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Antigravity-Agent/1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def list_open_issues(self) -> List[Dict[str, Any]]:
        """Lists open issues for the configured repository."""
        if not self.repo or not self.token:
            logger.warning("GitHub repository or token missing; returning mock issues.")
            return []

        url = f"{self.base_url}/repos/{self.repo}/issues?state=open"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(url, headers=self._headers())
                if res.status_code == 200:
                    return res.json()
        except Exception as e:
            logger.error(f"Error fetching GitHub issues: {e}")
        return []

    async def create_issue_comment(self, issue_number: int, comment: str) -> bool:
        """Posts a triage or status comment to an issue."""
        if not self.repo or not self.token:
            return False

        url = f"{self.base_url}/repos/{self.repo}/issues/{issue_number}/comments"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, headers=self._headers(), json={"body": comment})
                return res.status_code == 201
        except Exception as e:
            logger.error(f"Error posting comment to issue #{issue_number}: {e}")
            return False

    async def create_pull_request(self, title: str, body: str, head_branch: str, base_branch: str = "main") -> Optional[Dict[str, Any]]:
        """Opens a Pull Request for automated fixes or dependency updates."""
        if not self.repo or not self.token:
            return None

        url = f"{self.base_url}/repos/{self.repo}/pulls"
        payload = {
            "title": title,
            "body": body,
            "head": head_branch,
            "base": base_branch,
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(url, headers=self._headers(), json=payload)
                if res.status_code == 201:
                    return res.json()
        except Exception as e:
            logger.error(f"Error creating PR: {e}")
        return None

github_client = GitHubClient()
