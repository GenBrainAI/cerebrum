"""
Shared fixtures for Self-Aware Cerebrum tests.
"""

import pytest
import pytest_asyncio
import asyncio
import os
import tempfile
from pathlib import Path
import ast
from typing import Dict, List

@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir 

@pytest.fixture
def sample_python_code():
    """Fixture providing sample Python code for testing."""
    return '''
class TestClass:
    """Test class docstring."""
    
    def __init__(self, value: int):
        self.value = value
        
    def test_method(self, x: int) -> int:
        """Test method docstring."""
        if x > 0:
            return x + self.value
        return self.value
        
def test_function(a: int, b: int) -> int:
    """Test function docstring."""
    return a + b
'''

@pytest.fixture
def sample_ast(sample_python_code):
    """Fixture providing AST of sample code."""
    return ast.parse(sample_python_code)

@pytest.fixture
def temp_python_file(sample_python_code):
    """Fixture providing a temporary Python file with sample code."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(sample_python_code)
        temp_path = f.name
        
    yield temp_path
    os.unlink(temp_path)

@pytest.fixture
def mock_knowledge_system():
    """Fixture providing a mock knowledge system."""
    class MockKnowledgeSystem:
        def __init__(self):
            self.codebase_path = Path.cwd()
            self.stored_data = {}
            
        async def store_component_analysis(self, path, result):
            self.stored_data[f"analysis_{path}"] = result
            
        async def store_dependency_map(self, path, dep_map):
            self.stored_data[f"deps_{path}"] = dep_map
            
        async def store_optimization_opportunities(self, path, opps):
            self.stored_data[f"opps_{path}"] = opps
            
        async def store_component_documentation(self, path, docs):
            self.stored_data[f"docs_{path}"] = docs
            
    return MockKnowledgeSystem()

@pytest.fixture
def mock_telemetry_system():
    """Fixture providing a mock telemetry system."""
    class MockTelemetrySystem:
        def __init__(self):
            self.codebase_path = Path.cwd()
            self.collected_data = {}
            
        async def collect_metrics(self, component):
            return {
                "execution_times": {"test_func": [0.1, 0.2, 0.3]},
                "memory_usage": {"total": 1000, "peak": 1500},
                "cpu_usage": {"user": 0.5, "system": 0.3},
                "io_operations": {"reads": 100, "writes": 50}
            }
            
    return MockTelemetrySystem()

@pytest.fixture
def sample_telemetry_data():
    """Fixture providing sample telemetry data."""
    return [
        {
            "timestamp": 1000.0,
            "execution_times": {
                "test_func": [0.1, 0.2, 0.3],
                "other_func": [0.5, 0.6]
            },
            "memory_usage": {
                "total_size": 1000,
                "peak_size": 1500,
                "rss": 2000,
                "vms": 3000
            },
            "cpu_usage": {
                "user": 0.5,
                "system": 0.3
            },
            "io_operations": {
                "reads": 100,
                "writes": 50
            }
        },
        {
            "timestamp": 1001.0,
            "execution_times": {
                "test_func": [0.15, 0.25],
                "other_func": [0.55, 0.65]
            },
            "memory_usage": {
                "total_size": 1100,
                "peak_size": 1600,
                "rss": 2100,
                "vms": 3100
            },
            "cpu_usage": {
                "user": 0.6,
                "system": 0.4
            },
            "io_operations": {
                "reads": 110,
                "writes": 55
            }
        }
    ] 