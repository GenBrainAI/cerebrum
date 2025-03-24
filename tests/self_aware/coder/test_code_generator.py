import pytest
import asyncio
from typing import Dict, Any
from pathlib import Path
import tempfile
import os
from src.server.code_management.code_generator import CodeGenerator, GenerationContext, GenerationType

@pytest.fixture
def code_generator():
    """Fixture to create a CodeGenerator instance."""
    with tempfile.TemporaryDirectory() as temp_dir:
        template_path = Path(temp_dir) / "templates"
        template_path.mkdir()
        
        # Create a test template
        new_code_template = {
            "required_imports": ["typing", "asyncio"],
            "base_classes": [],
            "utility_functions": []
        }
        
        with open(template_path / "new_code.json", "w") as f:
            import json
            json.dump(new_code_template, f)
            
        yield CodeGenerator(template_path=str(template_path))

@pytest.fixture
def generation_context():
    """Fixture to create a GenerationContext instance."""
    return GenerationContext(
        codebase_path="src",
        dependencies={"numpy": "^1.24.0"},
        style_guide={"max_line_length": 100},
        target_language="python",
        framework_constraints=["async"],
        existing_code=None
    )

@pytest.mark.asyncio
async def test_generate_new_code(code_generator, generation_context):
    """Test generating new code."""
    specification = {
        "type": GenerationType.NEW_CODE.value,
        "description": "Test utility function",
        "requirements": {
            "name": "test_function",
            "parameters": ["data: List[int]"],
            "return_type": "int",
            "async": True,
            "documentation": True
        }
    }
    
    result = await code_generator.generate_code(specification, generation_context)
    
    assert result["status"] == "completed"
    assert "code" in result
    assert "test_function" in result["code"]
    assert "async def" in result["code"]
    assert "List[int]" in result["code"]
    assert '"""' in result["code"]  # Check for docstring

@pytest.mark.asyncio
async def test_refactor_code(code_generator, generation_context):
    """Test refactoring code."""
    original_code = """
def old_function(x, y):
    return x + y
    """
    
    requirements = {
        "rename_function": "new_function",
        "add_type_hints": True,
        "make_async": True
    }
    
    result = await code_generator.refactor_code(original_code, requirements, generation_context)
    
    assert result["status"] == "completed"
    assert "code" in result
    assert "new_function" in result["code"]
    assert "async def" in result["code"]
    assert ":" in result["code"]  # Check for type hints

@pytest.mark.asyncio
async def test_optimize_code(code_generator, generation_context):
    """Test optimizing code."""
    code = """
async def slow_function(data: List[int]) -> int:
    result = 0
    for x in data:
        result += x
    return result
    """
    
    optimization_goals = ["performance", "memory_usage"]
    
    result = await code_generator.optimize_code(code, optimization_goals, generation_context)
    
    assert result["status"] == "completed"
    assert "code" in result
    assert "sum(" in result["code"]  # Check for optimized implementation

@pytest.mark.asyncio
async def test_fix_bugs(code_generator, generation_context):
    """Test fixing bugs in code."""
    buggy_code = """
async def divide_numbers(a: int, b: int) -> float:
    return a / b  # Missing zero division check
    """
    
    bug_description = "Function crashes when b is zero"
    test_cases = [{
        "input": {"a": 10, "b": 0},
        "expected_behavior": "Should handle zero division gracefully"
    }]
    
    result = await code_generator.fix_bugs(buggy_code, bug_description, test_cases, generation_context)
    
    assert result["status"] == "completed"
    assert "code" in result
    assert "if b == 0" in result["code"]  # Check for zero division check

@pytest.mark.asyncio
async def test_generation_with_style_formatting(code_generator, generation_context):
    """Test code generation with style formatting."""
    specification = {
        "type": GenerationType.NEW_CODE.value,
        "description": "Test long line formatting",
        "requirements": {
            "name": "long_line_function",
            "parameters": ["very_long_parameter_name: str", "another_long_parameter_name: str"],
            "return_type": "str",
            "async": True,
            "documentation": True
        }
    }
    
    result = await code_generator.generate_code(specification, generation_context)
    
    assert result["status"] == "completed"
    assert "code" in result
    # Check that no line exceeds the max line length
    max_line_length = generation_context.style_guide["max_line_length"]
    assert all(len(line) <= max_line_length for line in result["code"].split("\n"))

@pytest.mark.asyncio
async def test_generation_history(code_generator, generation_context):
    """Test that generation history is maintained."""
    specification = {
        "type": GenerationType.NEW_CODE.value,
        "description": "Test function",
        "requirements": {
            "name": "test_function",
            "parameters": ["data: List[int]"],
            "return_type": "int",
            "async": True
        }
    }
    
    result = await code_generator.generate_code(specification, generation_context)
    
    assert result["id"] in code_generator.generation_history
    history_entry = code_generator.generation_history[result["id"]]
    assert history_entry["status"] == "completed"
    assert history_entry["type"] == GenerationType.NEW_CODE.value

@pytest.mark.asyncio
async def test_error_handling(code_generator, generation_context):
    """Test error handling in code generation."""
    # Invalid specification missing required fields
    invalid_specification = {
        "type": GenerationType.NEW_CODE.value,
        "description": "Test function"
        # Missing requirements
    }
    
    result = await code_generator.generate_code(invalid_specification, generation_context)
    
    assert result["status"] == "failed"
    assert "error" in result 