"""Unit tests for the SafetyValidator component."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import tempfile
import os
from datetime import datetime

from src.server.code_management.safety_validator import (
    SafetyValidator,
    ValidationLevel,
    ValidationRule
)

@pytest.fixture
def safety_validator():
    """Create a SafetyValidator instance for testing."""
    return SafetyValidator()

@pytest.fixture
def mock_subprocess_run():
    """Mock subprocess.run for testing."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="No issues found",
            stderr=""
        )
        yield mock_run

@pytest.mark.asyncio
async def test_validate_code_success(safety_validator, mock_subprocess_run):
    """Test successful code validation."""
    code = """
def greet(name: str) -> str:
    return f"Hello, {name}!"
"""
    result = await safety_validator.validate_code(code, "test.py")
    
    assert result["status"] == "completed"
    assert "results" in result
    assert "static_analysis" in result["results"]
    assert "security_scan" in result["results"]
    assert "custom_rules" in result["results"]

@pytest.mark.asyncio
async def test_validate_code_with_security_issues(safety_validator):
    """Test code validation with security issues."""
    code = """
def dangerous_code():
    user_input = input()
    eval(user_input)  # This should trigger security warning
"""
    result = await safety_validator.validate_code(code, "test.py")
    
    assert result["status"] == "completed"
    assert result["results"]["custom_rules"]["status"] == "fail"
    assert len(result["results"]["custom_rules"]["violations"]) > 0
    assert any(v["rule"] == "no_eval" for v in result["results"]["custom_rules"]["violations"])

@pytest.mark.asyncio
async def test_static_analysis(safety_validator, mock_subprocess_run):
    """Test static analysis functionality."""
    code = """
def test_function():
    unused_var = 42
    return None
"""
    result = await safety_validator.static_analysis("test.py")
    
    assert "tools" in result
    assert "issues" in result
    assert isinstance(result["status"], str)

@pytest.mark.asyncio
async def test_security_scan(safety_validator, mock_subprocess_run):
    """Test security scanning functionality."""
    code = """
import os
os.system("echo 'Hello'")  # This should trigger security warning
"""
    result = await safety_validator.security_scan("test.py")
    
    assert "tools" in result
    assert "vulnerabilities" in result
    assert isinstance(result["status"], str)

@pytest.mark.asyncio
async def test_custom_rules_validation(safety_validator):
    """Test custom rules validation."""
    code = """
def unsafe_code():
    exec("print('Hello')")  # This should trigger custom rule
"""
    result = await safety_validator._validate_custom_rules(code)
    
    assert result["status"] == "fail"
    assert len(result["violations"]) > 0
    assert any(v["rule"] == "no_exec" for v in result["violations"])

@pytest.mark.asyncio
async def test_validation_with_different_levels(safety_validator):
    """Test validation with different validation levels."""
    code = "print('Hello, World!')"
    
    for level in ["basic", "standard", "strict", "custom"]:
        result = await safety_validator.validate_code(code, "test.py")
        assert result["status"] == "completed"

@pytest.mark.asyncio
async def test_validation_with_sandbox(safety_validator):
    """Test validation with sandbox enabled."""
    safety_validator.security_config["sandbox"]["enabled"] = True
    
    code = "print('Hello, World!')"
    result = await safety_validator.validate_code(code, "test.py")
    
    assert result["status"] == "completed"

@pytest.mark.asyncio
async def test_validation_history(safety_validator):
    """Test validation history tracking."""
    code = "print('Hello, World!')"
    result = await safety_validator.validate_code(code, "test.py")
    
    assert result["id"] in safety_validator.validation_history
    assert safety_validator.validation_history[result["id"]]["status"] == "completed"

@pytest.mark.asyncio
async def test_error_handling(safety_validator):
    """Test error handling during validation."""
    with patch.object(safety_validator, 'static_analysis',
                     side_effect=Exception("Test error")):
        result = await safety_validator.validate_code("print('Hello')", "test.py")
        
        assert result["status"] == "failed"
        assert "error" in result
        assert "Test error" in result["error"] 