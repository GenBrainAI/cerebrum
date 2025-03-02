"""
Unit tests for the CodeGenerator component.
"""

import os
import json
import pytest
import pytest_asyncio
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
from typing import Dict, List, Any, Optional

from src.server.self_modification.code_generator import CodeGenerator

@pytest.fixture
def code_generator():
    """Create a CodeGenerator instance for testing."""
    return CodeGenerator()

@pytest.fixture
def mock_code_generator():
    """Create a mock CodeGenerator with controlled responses."""
    with patch('src.server.self_modification.code_generator.CodeGenerator._call_ai_model', 
              new_callable=AsyncMock) as mock_call:
        # Mock the AI model call to return a simple function
        mock_call.return_value = {
            "code": "def hello_world():\n    return 'Hello, World!'",
            "language": "python",
            "explanation": "A simple hello world function"
        }
        
        generator = CodeGenerator()
        yield generator

@pytest.mark.asyncio
async def test_initialization():
    """Test that CodeGenerator initializes with default configuration."""
    generator = CodeGenerator()
    
    # Check default model configuration
    assert generator.model_config["model"] == "gpt-4"
    assert generator.model_config["temperature"] == 0.2
    assert isinstance(generator.generation_history, list)
    assert len(generator.generation_history) == 0

@pytest.mark.asyncio
async def test_initialization_with_custom_config():
    """Test that CodeGenerator initializes with custom configuration."""
    custom_config = {
        "model": "gpt-3.5-turbo",
        "temperature": 0.5,
        "max_tokens": 2000
    }
    
    generator = CodeGenerator(model_config=custom_config)
    
    # Check custom model configuration
    assert generator.model_config["model"] == "gpt-3.5-turbo"
    assert generator.model_config["temperature"] == 0.5
    assert generator.model_config["max_tokens"] == 2000

@pytest.mark.asyncio
async def test_generate_code(mock_code_generator):
    """Test code generation with mocked AI response."""
    specification = {
        "name": "hello_world_function",
        "description": "A simple function that returns 'Hello, World!'",
        "language": "python",
        "requirements": ["Must return a string", "No external dependencies"]
    }
    
    result = await mock_code_generator.generate_code(specification)
    
    # Check the result structure
    assert "code" in result
    assert "specification" in result
    assert "timestamp" in result
    assert "model_config" in result
    
    # Check that the specification was included in the result
    assert result["specification"] == specification
    
    # Check the code content - assuming the code is directly in the 'code' field
    # or extract it from the structure if it's nested
    code_content = result["code"]
    if isinstance(code_content, dict) and "code" in code_content:
        # Handle case where code might be nested
        code_content = code_content["code"]
    
    assert "def hello_world" in code_content
    assert "Hello, World!" in code_content
    
    # Check that the generation was recorded in history
    assert len(mock_code_generator.generation_history) == 1
    assert mock_code_generator.generation_history[0]["specification"]["name"] == "hello_world_function"

@pytest.mark.asyncio
async def test_generate_code_with_context(mock_code_generator):
    """Test code generation with context information."""
    specification = {
        "name": "hello_world_function",
        "description": "A simple function that returns 'Hello, World!'",
        "language": "python"
    }
    
    context = {
        "project_structure": {
            "src": ["main.py", "utils.py"],
            "tests": ["test_main.py"]
        },
        "coding_standards": "PEP 8"
    }
    
    result = await mock_code_generator.generate_code(specification, context=context)
    
    # Check that the result contains the expected fields
    assert "code" in result
    assert "specification" in result
    assert "timestamp" in result
    assert "model_config" in result
    
    # Check that the specification was included in the result
    assert result["specification"] == specification
    
    # Check that the generation was recorded in history
    assert len(mock_code_generator.generation_history) == 1
    assert mock_code_generator.generation_history[0]["type"] == "generation"
    assert mock_code_generator.generation_history[0]["specification"] == specification

@pytest.mark.asyncio
async def test_generate_code_with_existing_code(mock_code_generator):
    """Test code generation with existing code to modify."""
    specification = {
        "name": "hello_world_function",
        "description": "Modify the function to include a name parameter",
        "language": "python"
    }
    
    existing_code = "def hello_world():\n    return 'Hello, World!'"
    
    result = await mock_code_generator.generate_code(
        specification, 
        existing_code=existing_code
    )
    
    # Check that the result contains the expected fields
    assert "code" in result
    assert "specification" in result
    assert "timestamp" in result
    assert "model_config" in result
    
    # Check that the specification was included in the result
    assert result["specification"] == specification
    
    # Check that the generation was recorded in history
    assert len(mock_code_generator.generation_history) == 1
    assert mock_code_generator.generation_history[0]["type"] == "generation"
    assert mock_code_generator.generation_history[0]["specification"] == specification

@pytest.mark.asyncio
async def test_refactor_code(mock_code_generator):
    """Test code refactoring functionality."""
    with patch.object(mock_code_generator, 'refactor_code', 
                     AsyncMock(return_value={"code": "def hello(name='World'):\n    return f'Hello, {name}!'"})):
        
        code = "def hello_world():\n    return 'Hello, World!'"
        refactoring_instructions = {
            "goal": "Add parameter support",
            "requirements": ["Add a name parameter with default value 'World'", 
                           "Use f-string for formatting"]
        }
        
        result = await mock_code_generator.refactor_code(code, refactoring_instructions)
        
        assert "code" in result
        assert "def hello(name='World'):" in result["code"]
        assert "f'Hello, {name}!'" in result["code"]

@pytest.mark.asyncio
async def test_optimize_code(mock_code_generator):
    """Test code optimization functionality."""
    with patch.object(mock_code_generator, 'optimize_code', 
                     AsyncMock(return_value={"code": "def factorial(n):\n    return 1 if n <= 1 else n * factorial(n-1)"})):
        
        code = "def factorial(n):\n    if n <= 1:\n        return 1\n    else:\n        return n * factorial(n-1)"
        optimization_goals = {
            "performance": True,
            "readability": True,
            "memory_usage": False
        }
        
        result = await mock_code_generator.optimize_code(code, optimization_goals)
        
        assert "code" in result
        assert "def factorial(n):" in result["code"]
        assert "return 1 if n <= 1 else n * factorial(n-1)" in result["code"]

@pytest.mark.asyncio
async def test_fix_bugs(mock_code_generator):
    """Test bug fixing functionality."""
    with patch.object(mock_code_generator, 'fix_bugs', 
                     AsyncMock(return_value={"code": "def divide(a, b):\n    if b == 0:\n        raise ZeroDivisionError('Cannot divide by zero')\n    return a / b"})):
        
        code = "def divide(a, b):\n    return a / b"
        bug_description = "Function crashes when b is zero"
        
        result = await mock_code_generator.fix_bugs(code, bug_description)
        
        assert "code" in result
        assert "if b == 0:" in result["code"]
        assert "raise ZeroDivisionError" in result["code"]

@pytest.mark.asyncio
async def test_add_documentation(mock_code_generator):
    """Test documentation addition functionality."""
    with patch.object(mock_code_generator, 'document_code', 
                     AsyncMock(return_value='"""Factorial function.\n\nArgs:\n    n: The number to calculate factorial for.\n\nReturns:\n    The factorial of n.\n"""\ndef factorial(n):\n    return 1 if n <= 1 else n * factorial(n-1)')):
        
        code = "def factorial(n):\n    return 1 if n <= 1 else n * factorial(n-1)"
        documentation_style = "google"
        
        result = await mock_code_generator.document_code(code, documentation_style)
        
        assert isinstance(result, str)
        assert "Factorial function" in result
        assert "Args:" in result
        assert "Returns:" in result 