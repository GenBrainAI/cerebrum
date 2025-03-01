"""
Unit tests for the Terminal Command Executor.
"""

import os
import json
import pytest
import shutil
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

from src.server.system.terminal_command_executor import (
    TerminalCommandExecutor,
    SecurityConfig,
    CommandValidationResult,
    CommandExecutionResult
)

@pytest.fixture
def temp_log_dir(tmp_path):
    """Create a temporary directory for command logs."""
    log_dir = tmp_path / "test_command_logs"
    log_dir.mkdir(exist_ok=True)
    yield log_dir
    # Cleanup
    shutil.rmtree(log_dir)

@pytest.fixture
def security_config(temp_log_dir):
    """Create a test security configuration."""
    return SecurityConfig(
        allowed_commands=["ls", "echo", "cat", "pwd"],
        blocked_commands=["rm", "sudo", "chmod"],
        allowed_patterns=[],
        blocked_patterns=[r"rm\s+-rf", r"sudo"],
        max_execution_time=5,
        max_output_size=1024,
        sandbox_type="subprocess",
        log_commands=True,
        log_output=True,
        log_directory=str(temp_log_dir),
        require_approval_for_risk_level="medium"
    )

@pytest.fixture
def command_executor(security_config):
    """Create a test command executor instance."""
    executor = TerminalCommandExecutor(config=security_config)
    return executor

@pytest.mark.asyncio
async def test_validate_command_valid(command_executor):
    """Test validating a valid command."""
    # Test a simple valid command
    result = await command_executor.validate_command("echo 'Hello, World!'")
    
    assert result.is_valid is True
    assert result.risk_level == "low"
    assert result.requires_approval is False
    assert result.sanitized_command == "echo 'Hello, World!'"

@pytest.mark.asyncio
async def test_validate_command_blocked(command_executor):
    """Test validating a blocked command."""
    # Test a blocked command
    result = await command_executor.validate_command("sudo apt-get update")
    
    assert result.is_valid is False
    assert result.risk_level == "high"
    assert result.requires_approval is True
    assert "blocked" in result.reason.lower()

@pytest.mark.asyncio
async def test_validate_command_blocked_pattern(command_executor):
    """Test validating a command matching a blocked pattern."""
    # Test a command matching a blocked pattern
    result = await command_executor.validate_command("rm -rf /some/directory")
    
    assert result.is_valid is False
    assert result.risk_level == "high"
    assert result.requires_approval is True
    assert "blocked" in result.reason.lower()

@pytest.mark.asyncio
async def test_validate_command_medium_risk(command_executor):
    """Test validating a medium risk command."""
    # Test a command with shell metacharacters
    result = await command_executor.validate_command("echo 'Hello' | grep 'Hello'")
    
    assert result.is_valid is True
    assert result.risk_level == "medium"
    assert result.requires_approval is True
    assert result.validation_details["contains_shell_metacharacters"] is True

@pytest.mark.asyncio
async def test_validate_command_empty(command_executor):
    """Test validating an empty command."""
    # Test an empty command
    result = await command_executor.validate_command("   ")
    
    assert result.is_valid is False
    assert "empty" in result.reason.lower()

@pytest.mark.asyncio
async def test_execute_command_simple(command_executor):
    """Test executing a simple command."""
    # Execute a simple command
    result = await command_executor.execute_command("echo 'Hello, World!'", requires_approval=False)
    
    assert isinstance(result, CommandExecutionResult)
    assert result.exit_code == 0
    assert "Hello, World!" in result.stdout
    assert result.stderr == ""
    assert result.sandbox_type == command_executor.config.sandbox_type
    
    # Check that the command was logged
    log_files = list(Path(command_executor.config.log_directory).glob("*.json"))
    assert len(log_files) == 1
    
    # Check log content
    with open(log_files[0], 'r') as f:
        log_data = json.load(f)
        assert log_data["command"] == "echo 'Hello, World!'"
        assert log_data["exit_code"] == 0
        assert "Hello, World!" in log_data["stdout"]

@pytest.mark.asyncio
async def test_execute_command_with_working_directory(command_executor, tmp_path):
    """Test executing a command with a specific working directory."""
    # Create a test file in a temporary directory
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    test_file = test_dir / "test.txt"
    test_file.write_text("Test content")
    
    # Execute command in the test directory
    result = await command_executor.execute_command(
        "cat test.txt",
        working_directory=str(test_dir),
        requires_approval=False
    )
    
    assert result.exit_code == 0
    assert "Test content" in result.stdout
    assert result.working_directory == str(test_dir)

@pytest.mark.asyncio
async def test_execute_command_with_environment_vars(command_executor):
    """Test executing a command with environment variables."""
    # Execute command with environment variables
    result = await command_executor.execute_command(
        "echo $TEST_VAR",
        environment_vars={"TEST_VAR": "Test value"},
        requires_approval=False
    )
    
    assert result.exit_code == 0
    assert "Test value" in result.stdout
    assert "TEST_VAR" in result.environment_vars

@pytest.mark.asyncio
async def test_execute_command_with_timeout(command_executor):
    """Test executing a command with timeout."""
    # Execute a command that should timeout
    result = await command_executor.execute_command(
        "sleep 10",
        timeout=1,
        requires_approval=False
    )
    
    assert result.exit_code == -1
    assert "execution timed out" in result.stderr.lower()
    assert result.metadata["error"] == "timeout"

@pytest.mark.asyncio
async def test_execute_command_with_error(command_executor):
    """Test executing a command that produces an error."""
    # Execute a command that should fail
    result = await command_executor.execute_command(
        "cat nonexistent_file.txt",
        requires_approval=False
    )
    
    assert result.exit_code != 0
    assert "no such file" in result.stderr.lower() or "cannot open" in result.stderr.lower()

@pytest.mark.asyncio
async def test_execute_command_requiring_approval(command_executor):
    """Test executing a command that requires approval."""
    # Execute a command that requires approval
    result = await command_executor.execute_command(
        "echo 'Hello' | grep 'Hello'"  # Medium risk due to pipe
    )
    
    # Result should be an approval ID
    assert isinstance(result, str)
    
    # Check pending approvals
    pending_approvals = command_executor.get_pending_approvals()
    assert len(pending_approvals) == 1
    assert pending_approvals[0]["approval_id"] == result
    assert pending_approvals[0]["command"] == "echo 'Hello' | grep 'Hello'"
    assert pending_approvals[0]["risk_level"] == "medium"

@pytest.mark.asyncio
async def test_execute_approved_command(command_executor):
    """Test executing an approved command."""
    # Submit a command that requires approval
    approval_id = await command_executor.execute_command(
        "echo 'Hello' | grep 'Hello'"  # Medium risk due to pipe
    )
    
    # Execute the approved command
    result = await command_executor.execute_approved_command(approval_id)
    
    assert isinstance(result, CommandExecutionResult)
    assert result.exit_code == 0
    assert "Hello" in result.stdout
    
    # Check that the command is no longer pending
    pending_approvals = command_executor.get_pending_approvals()
    assert len(pending_approvals) == 0

@pytest.mark.asyncio
async def test_reject_command(command_executor):
    """Test rejecting a command."""
    # Submit a command that requires approval
    approval_id = await command_executor.execute_command(
        "echo 'Hello' | grep 'Hello'"  # Medium risk due to pipe
    )
    
    # Reject the command
    result = command_executor.reject_command(approval_id)
    
    assert result is True
    
    # Check that the command is no longer pending
    pending_approvals = command_executor.get_pending_approvals()
    assert len(pending_approvals) == 0
    
    # Try to execute the rejected command
    with pytest.raises(ValueError):
        await command_executor.execute_approved_command(approval_id)

@pytest.mark.asyncio
async def test_get_execution_history(command_executor):
    """Test getting execution history."""
    # Execute multiple commands
    await command_executor.execute_command("echo 'Command 1'", requires_approval=False)
    await command_executor.execute_command("echo 'Command 2'", requires_approval=False)
    await command_executor.execute_command("cat nonexistent_file.txt", requires_approval=False)  # This will fail
    
    # Get all history
    history = command_executor.get_execution_history()
    assert len(history) == 3
    
    # Get successful commands
    successful = command_executor.get_execution_history(filter_successful=True)
    assert len(successful) == 2
    assert all(result.exit_code == 0 for result in successful)
    
    # Get failed commands
    failed = command_executor.get_execution_history(filter_successful=False)
    assert len(failed) == 1
    assert all(result.exit_code != 0 for result in failed)
    
    # Get limited history
    limited = command_executor.get_execution_history(limit=2)
    assert len(limited) == 2
    assert limited[0].command == "echo 'Command 2'"
    assert limited[1].command == "cat nonexistent_file.txt"

@pytest.mark.asyncio
async def test_custom_security_config():
    """Test with a custom security configuration."""
    # Create a custom config that requires approval for all commands
    config = SecurityConfig(
        require_approval_for_risk_level="all",
        log_commands=False
    )
    
    executor = TerminalCommandExecutor(config=config)
    
    # Even a simple command should require approval
    result = await executor.execute_command("echo 'Hello'")
    
    assert isinstance(result, str)  # Approval ID
    
    # Check pending approvals
    pending_approvals = executor.get_pending_approvals()
    assert len(pending_approvals) == 1
    assert pending_approvals[0]["command"] == "echo 'Hello'" 