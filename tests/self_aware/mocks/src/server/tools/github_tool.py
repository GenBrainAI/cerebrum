"""
Mock GitHub tool for testing.
"""
from typing import Dict, Any, List, Optional
from unittest.mock import MagicMock, AsyncMock

class GitHubTool:
    """Mock GitHub tool for testing."""
    
    def __init__(self, token=None, repo_name=None):
        """Initialize the mock GitHub tool."""
        self.token = token
        self.repo_name = repo_name
        self.github = MagicMock()
        self.repo = MagicMock()
    
    async def get_repo_info(self) -> Dict[str, Any]:
        """Get information about the repository."""
        return {
            "name": "test-repo",
            "full_name": "username/test-repo",
            "description": "Test repository",
            "url": "https://github.com/username/test-repo",
            "stars": 10,
            "forks": 5,
            "open_issues": 2
        }
    
    async def list_issues(self, state: str = "open") -> List[Dict[str, Any]]:
        """List issues in the repository."""
        return [
            {
                "number": 1,
                "title": "Test issue 1",
                "state": "open",
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-02T00:00:00Z",
                "body": "This is a test issue",
                "labels": ["bug", "priority:high"]
            },
            {
                "number": 2,
                "title": "Test issue 2",
                "state": "open",
                "created_at": "2023-01-03T00:00:00Z",
                "updated_at": "2023-01-04T00:00:00Z",
                "body": "This is another test issue",
                "labels": ["enhancement"]
            }
        ]
    
    async def get_file_content(self, path: str, ref: Optional[str] = None) -> Optional[str]:
        """Get the content of a file in the repository."""
        return f"Mock content for file {path}"
    
    async def list_files(self, path: str = "", ref: Optional[str] = None) -> List[Dict[str, Any]]:
        """List files in a directory in the repository."""
        return [
            {"name": "file1.py", "path": f"{path}/file1.py", "type": "file", "size": 100},
            {"name": "file2.py", "path": f"{path}/file2.py", "type": "file", "size": 200},
            {"name": "subdir", "path": f"{path}/subdir", "type": "dir"}
        ]
    
    async def create_issue(self, title: str, body: str, labels: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create a new issue in the repository."""
        return {
            "number": 3,
            "title": title,
            "state": "open",
            "created_at": "2023-01-05T00:00:00Z",
            "updated_at": "2023-01-05T00:00:00Z",
            "body": body,
            "labels": labels or []
        }
    
    async def list_pull_requests(self, state: str = "open") -> List[Dict[str, Any]]:
        """List pull requests in the repository."""
        return [
            {
                "number": 1,
                "title": "Test PR 1",
                "state": "open",
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-02T00:00:00Z",
                "body": "This is a test PR",
                "labels": ["bug", "ready-for-review"]
            }
        ]
    
    async def create_pull_request(self, title: str, body: str, base: str, head: str) -> Dict[str, Any]:
        """Create a new pull request in the repository."""
        return {
            "number": 2,
            "title": title,
            "state": "open",
            "created_at": "2023-01-05T00:00:00Z",
            "updated_at": "2023-01-05T00:00:00Z",
            "body": body,
            "base": base,
            "head": head
        } 