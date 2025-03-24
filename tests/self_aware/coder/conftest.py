"""Shared test configuration and fixtures."""

import pytest
import logging
import tempfile
import shutil
import os
from pathlib import Path

@pytest.fixture(autouse=True)
def setup_logging():
    """Configure logging for tests."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for tests."""
    temp_dir = tempfile.mkdtemp(prefix='test_workspace_')
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def test_file_path(temp_workspace):
    """Create a test file path in the temporary workspace."""
    return os.path.join(temp_workspace, "test_file.py")

@pytest.fixture
def mock_code():
    """Sample code for testing."""
    return {
        "simple": """
def add(a: int, b: int) -> int:
    \"\"\"Add two numbers.\"\"\"
    return a + b
""",
        "complex": """
from typing import List, Dict, Optional
import asyncio

class DataProcessor:
    \"\"\"Process data asynchronously.\"\"\"
    
    def __init__(self):
        self.data: List[Dict] = []
    
    async def process(self, items: List[Dict]) -> Optional[Dict]:
        \"\"\"Process items asynchronously.\"\"\"
        self.data.extend(items)
        return {"processed": len(items)}
""",
        "unsafe": """
import os
import pickle

def unsafe_operation(user_input):
    eval(user_input)  # Unsafe
    os.system(user_input)  # Also unsafe
    pickle.loads(user_input)  # Still unsafe
"""
    }

@pytest.fixture
def mock_templates():
    """Sample templates for testing."""
    return {
        "new_code": {
            "required_imports": ["typing", "asyncio"],
            "base_classes": [],
            "utility_functions": []
        },
        "refactor": {
            "required_imports": ["typing"],
            "patterns": {
                "async_conversion": {
                    "from": "def {name}",
                    "to": "async def {name}"
                }
            }
        }
    } 