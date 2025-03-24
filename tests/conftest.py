import pytest
import sys
import os
import logging
import tempfile
import shutil
import subprocess
from pathlib import Path

# Add the src directory to the Python path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from ..src.server.main import app
from fastapi.testclient import TestClient

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture(autouse=True)
def setup_logging():
    """Configure logging for tests."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()  # Output to console
        ]
    )
    
    # Reduce noise from third-party libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    
    # Our loggers should remain at DEBUG
    logging.getLogger('src.server').setLevel(logging.DEBUG)
    logging.getLogger('tests').setLevel(logging.DEBUG)

@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for testing."""
    temp_dir = tempfile.mkdtemp()
    old_cwd = os.getcwd()
    os.chdir(temp_dir)
    
    # Create test directories and files
    os.makedirs(".github")
    
    # Initialize git repo
    subprocess.run(["git", "init"], check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], check=True)
    
    yield temp_dir
    
    # Cleanup
    os.chdir(old_cwd)
    shutil.rmtree(temp_dir)

@pytest.fixture
def mock_gh_cli(monkeypatch):
    """Mock GitHub CLI commands with success responses."""
    def mock_run(cmd, *args, **kwargs):
        if "gh" in cmd:
            return subprocess.CompletedProcess(
                cmd, 0, stdout=b"Success", stderr=b""
            )
        return subprocess.run(cmd, *args, **kwargs)
    
    monkeypatch.setattr(subprocess, "run", mock_run)
    return mock_run
