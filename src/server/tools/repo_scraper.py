"""Repository scraper for GitHub and GitLab repositories."""

from typing import Dict, List, Optional, Any
import aiohttp
import asyncio
import base64
import re
from urllib.parse import urlparse
from datetime import datetime

class RepoScraper:
    """Scraper for GitHub and GitLab repositories."""
    
    def __init__(self, github_token: Optional[str] = None, gitlab_token: Optional[str] = None):
        """Initialize the repository scraper.
        
        Args:
            github_token: Optional GitHub personal access token
            gitlab_token: Optional GitLab personal access token
        """
        self.github_token = github_token
        self.gitlab_token = gitlab_token
        self.session = None
        self.path_pattern = None  # Pattern for filtering paths
    
    async def _ensure_session(self):
        """Ensure aiohttp session exists."""
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def _close_session(self):
        """Close aiohttp session."""
        if self.session:
            await self.session.close()
            self.session = None
    
    def _get_repo_info(self, url: str) -> Dict[str, str]:
        """Extract repository information from URL.
        
        Args:
            url: Repository URL
            
        Returns:
            Dictionary containing platform, owner, and repo name
        """
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')
        
        if len(path_parts) < 2:
            raise ValueError("Invalid repository URL")
            
        if 'github.com' in parsed.netloc:
            return {
                'platform': 'github',
                'owner': path_parts[0],
                'repo': path_parts[1]
            }
        elif 'gitlab.com' in parsed.netloc:
            return {
                'platform': 'gitlab',
                'owner': path_parts[0],
                'repo': path_parts[1]
            }
        else:
            raise ValueError("Unsupported repository platform")

    def _matches_path_pattern(self, path: str) -> bool:
        """Check if path matches the specified pattern."""
        if not self.path_pattern:
            return True
        return bool(re.search(self.path_pattern, path))

    async def _get_github_files(
        self,
        owner: str,
        repo: str,
        branch: str = 'main',
        max_files: int = 100,
        include_docs: bool = True,
        include_tests: bool = False
    ) -> List[Dict[str, Any]]:
        """Get files from GitHub repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            branch: Branch name
            max_files: Maximum number of files to fetch
            include_docs: Whether to include documentation files
            include_tests: Whether to include test files
            
        Returns:
            List of dictionaries containing file information
        """
        await self._ensure_session()
        
        headers = {}
        if self.github_token:
            headers['Authorization'] = f'token {self.github_token}'
        
        # Get repository contents
        url = f'https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1'
        async with self.session.get(url, headers=headers) as response:
            if response.status != 200:
                raise Exception(f"Error fetching repository contents: {await response.text()}")
            data = await response.json()
        
        files = []
        for item in data['tree']:
            if item['type'] != 'blob':
                continue
                
            path = item['path']
            
            # Apply path pattern filter
            if not self._matches_path_pattern(path):
                continue
            
            # Apply content type filters
            if not include_tests and ('test' in path.lower() or 'spec' in path.lower()):
                continue
            if not include_docs and any(path.lower().endswith(ext) for ext in ['.md', '.rst', '.txt']):
                continue
                
            # Get file content
            url = f'https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}'
            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    continue
                content_data = await response.json()
                
                try:
                    content = base64.b64decode(content_data['content']).decode('utf-8')
                except:
                    continue
                
                files.append({
                    'path': path,
                    'content': content,
                    'sha': item['sha'],
                    'size': item['size'],
                    'type': path.split('.')[-1] if '.' in path else 'unknown'
                })
                
                if len(files) >= max_files:
                    break
        
        return files

    async def _get_gitlab_files(
        self,
        owner: str,
        repo: str,
        branch: str = 'main',
        max_files: int = 100,
        include_docs: bool = True,
        include_tests: bool = False
    ) -> List[Dict[str, Any]]:
        """Get files from GitLab repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            branch: Branch name
            max_files: Maximum number of files to fetch
            include_docs: Whether to include documentation files
            include_tests: Whether to include test files
            
        Returns:
            List of dictionaries containing file information
        """
        await self._ensure_session()
        
        headers = {}
        if self.gitlab_token:
            headers['PRIVATE-TOKEN'] = self.gitlab_token
        
        # URL encode owner/repo
        project = f"{owner}/{repo}"
        project_encoded = project.replace('/', '%2F')
        
        # Get repository tree
        url = f'https://gitlab.com/api/v4/projects/{project_encoded}/repository/tree?recursive=true&ref={branch}'
        async with self.session.get(url, headers=headers) as response:
            if response.status != 200:
                raise Exception(f"Error fetching repository contents: {await response.text()}")
            items = await response.json()
        
        files = []
        for item in items:
            if item['type'] != 'blob':
                continue
                
            path = item['path']
            
            # Apply path pattern filter
            if not self._matches_path_pattern(path):
                continue
            
            # Apply content type filters
            if not include_tests and ('test' in path.lower() or 'spec' in path.lower()):
                continue
            if not include_docs and any(path.lower().endswith(ext) for ext in ['.md', '.rst', '.txt']):
                continue
            
            # Get file content
            url = f'https://gitlab.com/api/v4/projects/{project_encoded}/repository/files/{path}/raw?ref={branch}'
            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    continue
                    
                try:
                    content = await response.text()
                except:
                    continue
                
                files.append({
                    'path': path,
                    'content': content,
                    'id': item['id'],
                    'size': None,  # GitLab API doesn't provide size in tree endpoint
                    'type': path.split('.')[-1] if '.' in path else 'unknown'
                })
                
                if len(files) >= max_files:
                    break
        
        return files

    async def scrape_repository(
        self,
        url: str,
        branch: str = 'main',
        max_files: int = 100,
        include_docs: bool = True,
        include_tests: bool = False,
        path_pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        """Scrape a repository from GitHub or GitLab.
        
        Args:
            url: Repository URL
            branch: Branch name to scrape
            max_files: Maximum number of files to fetch
            include_docs: Whether to include documentation files
            include_tests: Whether to include test files
            path_pattern: Optional regex pattern to filter paths
            
        Returns:
            Dictionary containing scraped repository information and files
        """
        try:
            # Set path pattern for filtering
            self.path_pattern = path_pattern
            
            repo_info = self._get_repo_info(url)
            
            if repo_info['platform'] == 'github':
                files = await self._get_github_files(
                    repo_info['owner'],
                    repo_info['repo'],
                    branch,
                    max_files,
                    include_docs,
                    include_tests
                )
            else:  # gitlab
                files = await self._get_gitlab_files(
                    repo_info['owner'],
                    repo_info['repo'],
                    branch,
                    max_files,
                    include_docs,
                    include_tests
                )
            
            return {
                'url': url,
                'platform': repo_info['platform'],
                'owner': repo_info['owner'],
                'repo': repo_info['repo'],
                'branch': branch,
                'files': files,
                'scraped_at': datetime.now().isoformat(),
                'path_pattern': path_pattern
            }
            
        finally:
            await self._close_session() 