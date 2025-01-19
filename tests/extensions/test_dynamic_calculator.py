"""Test the dynamic calculator tool loading and functionality."""
import pytest
from src.server.extensions.dynamic_tools_loader import tools_loader
from src.server.tools.tools_catalog import tools_catalog

@pytest.fixture(autouse=True)
def setup_teardown():
    """Setup and teardown for each test."""
    # Clear tools catalog before each test
    tools_catalog.reset()
    yield
    tools_catalog.reset()

def test_calculator_tool_loading():
    """Test that the calculator tool is properly loaded."""
    # Initialize tools loader
    registered_tools = tools_loader.initialize()
    
    # Verify calculator tool methods are registered
    calculator_tools = [name for name in registered_tools if 'calculator' in name.lower()]
    assert len(calculator_tools) > 0, "No calculator tools found"
    
    # Check specific methods
    expected_methods = ['add', 'subtract', 'multiply', 'divide']
    for method in expected_methods:
        tool_name = f"calculator_tool.calculator.{method}"
        assert tool_name in registered_tools, f"Missing calculator method: {method}"
        
        # Get tool metadata
        metadata = tools_catalog.get_tool(tool_name)
        assert metadata is not None, f"No metadata found for {tool_name}"
        assert len(metadata.parameters) == 2, f"Expected 2 parameters for {method}"
        
        # Verify parameter types
        for param in metadata.parameters:
            assert param.type_hint == "float", f"Expected float type for {param.name}"

@pytest.mark.asyncio
async def test_calculator_operations():
    """Test that calculator operations work correctly."""
    # Initialize tools loader
    tools_loader.initialize()
    
    # Test each operation
    test_cases = [
        ('add', 5, 3, 8),
        ('subtract', 10, 4, 6),
        ('multiply', 6, 7, 42),
        ('divide', 15, 3, 5),
    ]
    
    for operation, a, b, expected in test_cases:
        tool_name = f"calculator_tool.calculator.{operation}"
        
        # Get tool instance
        tool = tools_catalog.get_tool_instance(tool_name)
        assert tool is not None, f"Failed to get tool instance for {operation}"
        
        # Execute operation
        result = tool(a, b)
        assert result == expected, f"{operation} failed: expected {expected}, got {result}"

@pytest.mark.asyncio
async def test_calculator_error_handling():
    """Test calculator error handling."""
    # Initialize tools loader
    tools_loader.initialize()
    
    # Test division by zero
    tool_name = "calculator_tool.calculator.divide"
    tool = tools_catalog.get_tool_instance(tool_name)
    
    with pytest.raises(ValueError, match="Cannot divide by zero"):
        tool(10, 0)

@pytest.mark.asyncio
async def test_tool_reloading():
    """Test that tools can be reloaded."""
    # Initial load
    initial_tools = tools_loader.initialize()
    initial_count = len(initial_tools)
    
    # Reload tools
    reloaded_tools = tools_loader.reload_all_tools()
    assert len(reloaded_tools) == initial_count, "Tool count changed after reload"
    
    # Verify calculator tools are still present
    calculator_tools = [name for name in reloaded_tools if 'calculator' in name.lower()]
    assert len(calculator_tools) > 0, "Calculator tools missing after reload" 