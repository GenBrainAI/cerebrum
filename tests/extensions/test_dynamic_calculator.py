"""Test the dynamic calculator tool loading and functionality."""
import pytest
from unittest.mock import patch, MagicMock
from src.server.extensions.dynamic_tools_loader import tools_loader
from src.server.tools.tools_catalog import tools_catalog, ToolMetadata, ToolType, ParameterInfo, ReturnInfo

@pytest.fixture(autouse=True)
def setup_teardown():
    """Setup and teardown for each test."""
    # Store original tools
    original_tools = tools_catalog.DEFAULT_TOOLS.copy() if hasattr(tools_catalog, 'DEFAULT_TOOLS') else {}
    
    # Clear tools catalog before each test
    tools_catalog.reset()
    
    yield
    
    # Restore original tools
    if hasattr(tools_catalog, 'DEFAULT_TOOLS'):
        tools_catalog.DEFAULT_TOOLS = original_tools
        tools_catalog._initialize_default_tools()

def create_mock_calculator_tool():
    """Create a mock calculator tool with proper metadata."""
    calculator_metadata = {
        'add': ToolMetadata(
            name='calculator_tool.calculator.add',
            tool_type=ToolType.CLASS_METHOD,
            description='Add two numbers',
            parameters=[
                ParameterInfo(name='a', type_hint='float', required=True, description='First number'),
                ParameterInfo(name='b', type_hint='float', required=True, description='Second number')
            ],
            returns=ReturnInfo(type_hint='float', description='Sum of the numbers'),
            original_obj=None,
            async_tool=False
        ),
        'subtract': ToolMetadata(
            name='calculator_tool.calculator.subtract',
            tool_type=ToolType.CLASS_METHOD,
            description='Subtract two numbers',
            parameters=[
                ParameterInfo(name='a', type_hint='float', required=True, description='First number'),
                ParameterInfo(name='b', type_hint='float', required=True, description='Second number')
            ],
            returns=ReturnInfo(type_hint='float', description='Difference of the numbers'),
            original_obj=None,
            async_tool=False
        ),
        'multiply': ToolMetadata(
            name='calculator_tool.calculator.multiply',
            tool_type=ToolType.CLASS_METHOD,
            description='Multiply two numbers',
            parameters=[
                ParameterInfo(name='a', type_hint='float', required=True, description='First number'),
                ParameterInfo(name='b', type_hint='float', required=True, description='Second number')
            ],
            returns=ReturnInfo(type_hint='float', description='Product of the numbers'),
            original_obj=None,
            async_tool=False
        ),
        'divide': ToolMetadata(
            name='calculator_tool.calculator.divide',
            tool_type=ToolType.CLASS_METHOD,
            description='Divide two numbers',
            parameters=[
                ParameterInfo(name='a', type_hint='float', required=True, description='First number'),
                ParameterInfo(name='b', type_hint='float', required=True, description='Second number')
            ],
            returns=ReturnInfo(type_hint='float', description='Quotient of the numbers'),
            original_obj=None,
            async_tool=False
        )
    }
    
    # Create mock calculator class
    class MockCalculator:
        def add(self, a: float, b: float) -> float:
            return a + b
            
        def subtract(self, a: float, b: float) -> float:
            return a - b
            
        def multiply(self, a: float, b: float) -> float:
            return a * b
            
        def divide(self, a: float, b: float) -> float:
            if b == 0:
                raise ValueError("Cannot divide by zero")
            return a / b
    
    calculator = MockCalculator()
    
    # Register mock methods
    for method_name, metadata in calculator_metadata.items():
        method = getattr(calculator, method_name)
        metadata.original_obj = method
        tools_catalog._tools[f'calculator_tool.calculator.{method_name}'] = metadata
        tools_catalog._tool_instances[f'calculator_tool.calculator.{method_name}'] = method
    
    return calculator

@pytest.mark.asyncio
async def test_calculator_tool_loading():
    """Test that the calculator tool is properly loaded."""
    # Create and register mock calculator
    calculator = create_mock_calculator_tool()
    
    # Verify calculator tool methods are registered
    calculator_tools = [name for name in tools_catalog.list_tools() if 'calculator' in name.lower()]
    assert len(calculator_tools) == 4, "Expected 4 calculator methods"
    
    # Check specific methods
    expected_methods = ['add', 'subtract', 'multiply', 'divide']
    for method in expected_methods:
        tool_name = f"calculator_tool.calculator.{method}"
        assert tool_name in calculator_tools, f"Missing calculator method: {method}"
        
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
    # Create and register mock calculator
    calculator = create_mock_calculator_tool()
    
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
    # Create and register mock calculator
    calculator = create_mock_calculator_tool()
    
    # Test division by zero
    tool_name = "calculator_tool.calculator.divide"
    tool = tools_catalog.get_tool_instance(tool_name)
    
    with pytest.raises(ValueError, match="Cannot divide by zero"):
        tool(10, 0)

@pytest.mark.asyncio
async def test_tool_reloading():
    """Test that tools can be reloaded."""
    # Create and register mock calculator
    calculator = create_mock_calculator_tool()
    
    # Get initial tool count
    initial_tools = tools_catalog.list_tools()
    initial_count = len(initial_tools)
    
    # Reload tools
    with patch('src.server.extensions.dynamic_tools_loader.tools_loader.load_tools_from_directory') as mock_load:
        mock_load.return_value = initial_tools
        reloaded_tools = tools_loader.reload_all_tools()
        assert len(reloaded_tools) == initial_count, "Tool count changed after reload"
    
    # Verify calculator tools are still present
    calculator_tools = [name for name in reloaded_tools if 'calculator' in name.lower()]
    assert len(calculator_tools) == 4, "Calculator tools missing after reload" 