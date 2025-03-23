import pytest
import tempfile
import os
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_knowledge_system():
    """Create a mock knowledge system for testing."""
    mock = MagicMock()
    
    # Add stored_data attribute to store analysis results
    mock.stored_data = {}
    
    # Mock store methods
    async def mock_store_component_analysis(component_path, result):
        mock.stored_data[f"analysis_{component_path}"] = result
        
    async def mock_store_dependency_map(component_path, dep_map):
        mock.stored_data[f"deps_{component_path}"] = dep_map
        
    async def mock_store_optimization_opportunities(component_path, opportunities):
        mock.stored_data[f"opps_{component_path}"] = opportunities
        
    async def mock_store_component_documentation(component_path, documentation):
        mock.stored_data[f"docs_{component_path}"] = documentation
    
    # Set the mock methods
    mock.store_component_analysis = mock_store_component_analysis
    mock.store_dependency_map = mock_store_dependency_map
    mock.store_optimization_opportunities = mock_store_optimization_opportunities
    mock.store_component_documentation = mock_store_component_documentation
    
    # Mock codebase path
    mock.codebase_path = os.getcwd()
    
    return mock

@pytest.fixture
def temp_python_file():
    """Create a temporary Python file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
        f.write(b"""
import os
import sys
from typing import Dict, List

class TestClass:
    \"\"\"Test class docstring.\"\"\"
    
    def __init__(self):
        \"\"\"Initialize the test class.\"\"\"
        self.value = 42
        
    def test_method(self, param: int) -> str:
        \"\"\"Test method docstring.\"\"\"
        return str(param + self.value)
        
def test_function(param1: str, param2: int = 0) -> Dict[str, List[int]]:
    \"\"\"Test function docstring.\"\"\"
    return {"result": [int(param1) + param2]}
""")
        temp_file = f.name
    
    yield temp_file
    
    # Clean up the temporary file
    if os.path.exists(temp_file):
        os.remove(temp_file)

@pytest.fixture
def sample_ast(temp_python_file):
    """Parse a sample Python file and return its AST."""
    import ast
    with open(temp_python_file, 'r') as f:
        content = f.read()
    return ast.parse(content) 