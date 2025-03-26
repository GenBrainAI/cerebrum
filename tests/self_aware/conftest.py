"""
Shared fixtures for Self-Aware Cerebrum tests.
"""

import pytest
import pytest_asyncio
import asyncio
import os
import tempfile
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Override sys.path to prioritize our mocks for problematic imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "mocks"))

# Create mock class for GitHub
class MockGitHub:
    def __init__(self, *args, **kwargs):
        self.repos = {}
    
    def get_repo(self, repo_name):
        return MagicMock()

# Apply the mock to bypass GitHub authentication issues
import github.MainClass
github.MainClass.Github = MockGitHub

@pytest_asyncio.fixture(scope="function")
def event_loop():
    """Create an instance of the default event loop for each test function."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    # Close the loop explicitly
    if loop.is_running():
        loop.stop()
    if not loop.is_closed():
        loop.close()

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

@pytest.fixture
def mock_github():
    """Provide a mock GitHub instance."""
    return MockGitHub()

@pytest.fixture
def mock_github_tool():
    """Mock GitHub tool."""
    mock = MagicMock()
    mock.get_repo_info = AsyncMock(return_value={
        "name": "test-repo",
        "full_name": "username/test-repo",
        "description": "Test repository",
        "url": "https://github.com/username/test-repo",
        "stars": 10,
        "forks": 5,
        "open_issues": 2
    })
    return mock 