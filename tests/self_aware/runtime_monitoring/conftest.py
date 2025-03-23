"""
Fixtures for runtime monitoring tests.
"""

import pytest
import pytest_asyncio
import asyncio
import tempfile
import os
from unittest.mock import MagicMock, AsyncMock
from dataclasses import dataclass
from typing import Dict, List

@pytest.fixture
def mock_telemetry_system():
    """Mock telemetry system for testing behavior monitor."""
    mock = MagicMock()
    mock.codebase_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    
    # Add required methods/attributes
    mock.collect_metrics = AsyncMock(return_value={
        "execution_times": {"test_function": [0.1, 0.2, 0.15]},
        "memory_usage": {"total": 1000, "peak": 1500}
    })
    
    return mock

@pytest.fixture
def sample_telemetry_data():
    """Sample telemetry data for testing."""
    return [
        {
            "timestamp": 1000.0,
            "execution_times": {
                "function1": [0.1, 0.2, 0.15],
                "function2": [0.3, 0.25]
            },
            "memory_usage": {
                "total_size": 1000,
                "peak_size": 1500,
                "rss": 800,
                "vms": 1200,
                "timestamp": 1000.0
            },
            "errors": [
                {
                    "type": "ValueError",
                    "message": "Test error",
                    "function": "function1",
                    "traceback": "test traceback",
                    "timestamp": 1000.0
                }
            ]
        },
        {
            "timestamp": 1001.0,
            "execution_times": {
                "function1": [0.12, 0.18],
                "function3": [0.5, 0.6]
            },
            "memory_usage": {
                "total_size": 1100,
                "peak_size": 1600,
                "rss": 850,
                "vms": 1250,
                "timestamp": 1001.0
            },
            "errors": []
        }
    ]

@pytest.fixture
def temp_python_file():
    """Create a temporary Python file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as temp_file:
        temp_file.write(b"""
def test_function(x):
    return x + 1

async def async_test_function(x):
    return x * 2
        """)
        temp_file_path = temp_file.name
    
    yield temp_file_path
    
    # Clean up
    if os.path.exists(temp_file_path):
        os.unlink(temp_file_path) 