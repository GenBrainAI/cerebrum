import os
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to Python path
project_root = str(Path(__file__).parents[3])
if project_root not in sys.path:
    sys.path.append(project_root)

from src.server.extensions.dynamic_tools_loader import DynamicToolsLoader, tools_loader
from src.server.tools.tools_catalog import tools_catalog


@pytest.fixture
def temp_tools_dir(tmp_path):
    """Create a temporary directory with some test tool files."""
    tools_dir = tmp_path / "test_tools"
    tools_dir.mkdir()
    
    # Create a test function tool
    func_tool = tools_dir / "function_tool.py"
    func_tool.write_text('''
def test_function(param1: str, param2: int = 42) -> str:
    """A test function tool.
    
    Args:
        param1: First parameter
        param2: Second parameter with default
        
    Returns:
        A test string
    """
    return f"{param1} {param2}"

def another_function() -> None:
    """Another test function."""
    pass
''')

    # Create a test class tool
    class_tool = tools_dir / "class_tool.py"
    class_tool.write_text('''
class TestTool:
    """A test class tool."""
    
    def __init__(self):
        self.value = 42
        
    def method1(self, param: str) -> str:
        """First test method.
        
        Args:
            param: Test parameter
            
        Returns:
            Modified parameter
        """
        return f"Modified {param}"
        
    def method2(self) -> int:
        """Second test method.
        
        Returns:
            The value
        """
        return self.value

class AnotherTool:
    """Another test tool."""
    pass
''')

    # Create a test instance tool
    instance_tool = tools_dir / "instance_tool.py"
    instance_tool.write_text('''
class ConfiguredTool:
    """A pre-configured tool."""
    def __init__(self, config):
        self.config = config
        
    def get_config(self):
        """Get the configuration."""
        return self.config

# Pre-configured instance
configured_tool = ConfiguredTool({"key": "value"})

# Another instance
another_instance = ConfiguredTool({"other": "config"})
''')
    
    return tools_dir


@pytest.fixture(autouse=True)
def clear_catalog():
    """Clear the tools catalog before each test."""
    # Store original tools
    original_tools = tools_catalog.DEFAULT_TOOLS.copy()
    
    # Clear all tools
    tools_catalog._tools.clear()
    tools_catalog._tool_instances.clear()
    tools_catalog._functions.clear()
    tools_catalog._classes.clear()
    tools_catalog._openapi_tools.clear()
    tools_catalog._ai_tools.clear()
    
    yield
    
    # Restore original tools
    tools_catalog.DEFAULT_TOOLS = original_tools
    tools_catalog.reset_to_defaults()


def test_singleton():
    """Test that DynamicToolsLoader is a singleton."""
    loader1 = DynamicToolsLoader()
    loader2 = DynamicToolsLoader()
    assert loader1 is loader2
    assert tools_loader is loader1


def test_load_tools_from_directory(temp_tools_dir):
    """Test loading tools from a directory."""
    registered = tools_loader.load_tools_from_directory(temp_tools_dir)
    
    # Check function tools
    assert "function_tool.test_function" in registered
    assert "function_tool.another_function" in registered
    assert "function_tool.test_function" in tools_catalog._functions
    
    # Check class tools
    assert "class_tool.TestTool" in registered
    assert "class_tool.AnotherTool" in registered
    assert "class_tool.TestTool" in tools_catalog._classes
    
    # Check instance tools
    assert "instance_tool.configured_tool" in registered
    assert "instance_tool.another_instance" in registered
    assert "instance_tool.configured_tool" in tools_catalog._tool_instances
    
    # Check metadata
    tool_meta = tools_catalog.get_tool("function_tool.test_function")
    assert tool_meta is not None
    assert len(tool_meta.parameters) == 2
    assert tool_meta.parameters[0].name == "param1"
    assert tool_meta.parameters[1].name == "param2"
    assert tool_meta.parameters[1].default == 42


def test_load_tools_by_type(temp_tools_dir):
    """Test loading and categorizing tools by type."""
    tools_loader.load_tools_from_directory(temp_tools_dir)
    
    tools_by_type = tools_catalog.list_tools_by_type()
    
    # Check functions
    assert "function_tool.test_function" in tools_by_type["functions"]
    assert "function_tool.another_function" in tools_by_type["functions"]
    
    # Check classes
    assert "class_tool.TestTool" in tools_by_type["classes"]
    assert "class_tool.AnotherTool" in tools_by_type["classes"]
    
    # Check instances
    assert "instance_tool.configured_tool" in tools_by_type["instances"]
    assert "instance_tool.another_instance" in tools_by_type["instances"]


def test_reload_module(temp_tools_dir):
    """Test reloading a module."""
    # First load
    tools_loader.load_tools_from_directory(temp_tools_dir)
    initial_tools = set(tools_catalog.list_tools())
    
    # Modify a tool file
    func_tool = temp_tools_dir / "function_tool.py"
    original_content = func_tool.read_text()
    new_content = original_content + '''
def new_function():
    """A new test function."""
    return "new"
'''
    func_tool.write_text(new_content)
    
    # Reload the module
    tools_loader.reload_module("function_tool")
    
    # Check that the new function was added
    assert "function_tool.new_function" in tools_catalog.list_tools()
    assert "function_tool.new_function" in tools_catalog._functions
    
    # Cleanup
    func_tool.write_text(original_content)


def test_initialize_with_nonexistent_directory():
    """Test initialization with a non-existent directory."""
    # Create a new instance with a non-existent directory
    nonexistent_dir = Path('/nonexistent')
    with patch.object(tools_loader, 'default_tools_dir', nonexistent_dir):
        result = tools_loader.initialize()
        assert result == []


def test_error_handling(temp_tools_dir):
    """Test error handling for invalid tools."""
    # Create an invalid tool file
    invalid_tool = temp_tools_dir / "invalid_tool.py"
    invalid_tool.write_text('this is not valid Python code')
    
    # Should not raise an exception, but log the error
    registered = tools_loader.load_tools_from_directory(temp_tools_dir)
    assert "invalid_tool" not in [tool.split('.')[0] for tool in registered]


def test_unregister_module(temp_tools_dir):
    """Test unregistering a module."""
    # First load tools
    tools_loader.load_tools_from_directory(temp_tools_dir)
    initial_tools = set(tools_catalog.list_tools())
    
    # Unregister one module
    tools_loader._unregister_module("function_tool")
    
    # Check that the module's tools were removed
    remaining_tools = set(tools_catalog.list_tools())
    removed_tools = initial_tools - remaining_tools
    
    # Verify removal from all storages
    assert all(tool.startswith("function_tool.") for tool in removed_tools)
    assert not any(name.startswith("function_tool.") for name in tools_catalog._functions)
    assert not any(name.startswith("function_tool.") for name in tools_catalog._classes)
    assert not any(name.startswith("function_tool.") for name in tools_catalog._tool_instances)


def test_initialize():
    """Test the initialize method."""
    with patch.object(tools_loader, 'load_tools_from_directory') as mock_load:
        mock_load.return_value = ["tool1", "tool2"]
        result = tools_loader.initialize()
        
        mock_load.assert_called_once_with(tools_loader.default_tools_dir)
        assert result == ["tool1", "tool2"]


def test_module_isolation(temp_tools_dir):
    """Test that modules are properly isolated when loading."""
    # Create a module that tries to import another module
    module_a = temp_tools_dir / "module_a.py"
    module_a.write_text('''
def function_a():
    """Test function A."""
    return "a"
''')
    
    module_b = temp_tools_dir / "module_b.py"
    module_b.write_text('''
from module_a import function_a

def function_b():
    """Test function B."""
    return function_a()
''')
    
    # Load tools
    registered = tools_loader.load_tools_from_directory(temp_tools_dir)
    
    # Both modules should be loaded successfully
    assert "module_a.function_a" in registered
    assert "module_b.function_b" in registered 