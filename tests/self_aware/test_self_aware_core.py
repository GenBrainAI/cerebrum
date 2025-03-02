"""
Unit tests for the Self-Aware Core component.
"""

import os
import json
import pytest
import pytest_asyncio
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
from typing import Dict, List, Any, Optional

from src.server.self_aware_core import CerebrumSystemCore
from src.server.context.unified_context_manager import UnifiedContextManager
from src.server.system.terminal_command_executor import CommandExecutionResult

@pytest.fixture
def mock_unified_context_manager():
    """Create a mock UnifiedContextManager."""
    mock = AsyncMock(spec=UnifiedContextManager)
    
    # Mock list_operations
    mock.list_operations.return_value = []
    
    # Mock create_operation
    mock.create_operation.return_value = "cerebrum_system"
    
    # Mock initialize_codebase_index
    mock.initialize_codebase_index.return_value = {
        "indexed_files": 10,
        "total_files": 10,
        "skipped_files": 0
    }
    
    # Mock execute_command
    mock.execute_command.return_value = CommandExecutionResult(
        command_id="cmd1",
        command="ls -la",
        exit_code=0,
        stdout="file1.txt\nfile2.txt",
        stderr="",
        execution_time=0.1,
        started_at="2023-01-01T00:00:00",
        completed_at="2023-01-01T00:00:01",
        working_directory=".",
        environment_vars={},
        sandbox_type="subprocess",
        metadata={}
    )
    
    # Mock search_codebase
    mock.search_codebase.return_value = []
    
    # Mock get_file_content
    mock.get_file_content.return_value = "file content"
    
    # Mock get_operation_context
    mock.get_operation_context.return_value = "context content"
    
    # Mock add_to_operation_context
    mock.add_to_operation_context.return_value = "item1"
    
    # Mock get_pending_command_approvals
    mock.get_pending_command_approvals.return_value = []
    
    # Mock execute_approved_command
    mock.execute_approved_command.return_value = CommandExecutionResult(
        command_id="cmd2",
        command="cat file.txt",
        exit_code=0,
        stdout="file content",
        stderr="",
        execution_time=0.1,
        started_at="2023-01-01T00:00:00",
        completed_at="2023-01-01T00:00:01",
        working_directory=".",
        environment_vars={},
        sandbox_type="subprocess",
        metadata={}
    )
    
    # Mock reject_command
    mock.reject_command.return_value = True
    
    # Mock get_codebase_stats
    mock.get_codebase_stats.return_value = {
        "total_files": 10,
        "total_lines": 1000,
        "languages": {
            "python": 5,
            "javascript": 3,
            "markdown": 2
        },
        "last_updated": "2023-01-01T00:00:00"
    }
    
    # Mock refresh_codebase
    mock.refresh_codebase.return_value = {
        "indexed_files": 2,
        "total_files": 10,
        "skipped_files": 8
    }
    
    return mock

@pytest_asyncio.fixture
async def cerebrum_system_core(mock_unified_context_manager, tmp_path):
    """Create a CerebrumSystemCore instance with mocked dependencies."""
    with patch("src.server.self_aware_core.UnifiedContextManager", return_value=mock_unified_context_manager):
        core = CerebrumSystemCore(
            base_path=str(tmp_path / "cerebrum_system"),
            codebase_root=".",
            config={}
        )
        # Initialize the core explicitly
        await core.initialize()
        yield core

@pytest.mark.asyncio
async def test_initialize_operation(cerebrum_system_core, mock_unified_context_manager):
    """Test initializing the system operation."""
    # The core is already initialized in the fixture
    assert cerebrum_system_core._initialized is True
    
    # Verify that list_operations was called
    mock_unified_context_manager.list_operations.assert_called_once()
    
    # Verify that create_operation was called
    mock_unified_context_manager.create_operation.assert_called_once_with(
        operation_id="cerebrum_system",
        description="Cerebrum System Core",
        operation_type="system",
        metadata={
            "created_at": mock_unified_context_manager.create_operation.call_args[1]["metadata"]["created_at"],
            "system_type": "cerebrum_system",
            "version": "1.0.0"
        }
    )
    
    # Verify that add_to_operation_context was called
    mock_unified_context_manager.add_to_operation_context.assert_called_with(
        operation_id="cerebrum_system",
        content="Cerebrum System Core initialized.",
        source="system",
        priority=90,
        metadata={
            "type": "initialization",
            "timestamp": mock_unified_context_manager.add_to_operation_context.call_args[1]["metadata"]["timestamp"]
        }
    )
    
    # Verify that initialize_codebase_index was called
    mock_unified_context_manager.initialize_codebase_index.assert_called_with(incremental=True)

@pytest.mark.asyncio
async def test_index_codebase(cerebrum_system_core, mock_unified_context_manager):
    """Test indexing the codebase."""
    result = await cerebrum_system_core.index_codebase(incremental=True)
    
    # Verify that initialize_codebase_index was called
    mock_unified_context_manager.initialize_codebase_index.assert_called_with(incremental=True)
    
    # Verify the result
    assert result == {
        "indexed_files": 10,
        "total_files": 10,
        "skipped_files": 0
    }

@pytest.mark.asyncio
async def test_execute_command(cerebrum_system_core, mock_unified_context_manager):
    """Test executing a command."""
    result = await cerebrum_system_core.execute_command(
        command="ls -la",
        working_directory=".",
        timeout=30,
        requires_approval=True
    )
    
    # Verify that execute_command was called
    mock_unified_context_manager.execute_command.assert_called_once_with(
        operation_id="cerebrum_system",
        command="ls -la",
        working_directory=".",
        environment_vars=None,
        timeout=30,
        requires_approval=True,
        add_to_context=True,
        context_priority=60
    )
    
    # Verify the result
    assert result.command == "ls -la"
    assert result.exit_code == 0
    assert result.stdout == "file1.txt\nfile2.txt"

@pytest.mark.asyncio
async def test_search_code(cerebrum_system_core, mock_unified_context_manager):
    """Test searching the codebase."""
    await cerebrum_system_core.search_code(query="test", top_k=5)
    
    # Verify that search_codebase was called
    mock_unified_context_manager.search_codebase.assert_called_once_with(
        operation_id="cerebrum_system",
        query="test",
        top_k=5,
        add_to_context=True,
        context_priority=70
    )

@pytest.mark.asyncio
async def test_get_file_content(cerebrum_system_core, mock_unified_context_manager):
    """Test getting file content."""
    content = await cerebrum_system_core.get_file_content(file_path="test.py")
    
    # Verify that get_file_content was called
    mock_unified_context_manager.get_file_content.assert_called_once_with(
        operation_id="cerebrum_system",
        file_path="test.py",
        add_to_context=True,
        context_priority=65
    )
    
    # Verify the result
    assert content == "file content"

@pytest.mark.asyncio
async def test_get_context(cerebrum_system_core, mock_unified_context_manager):
    """Test getting the context."""
    context = await cerebrum_system_core.get_context(max_tokens=1000, include_metadata=False)
    
    # Verify that get_operation_context was called
    mock_unified_context_manager.get_operation_context.assert_called_once_with(
        operation_id="cerebrum_system",
        max_tokens=1000,
        include_metadata=False
    )
    
    # Verify the result
    assert context == "context content"

@pytest.mark.asyncio
async def test_add_to_context(cerebrum_system_core, mock_unified_context_manager):
    """Test adding to the context."""
    item_id = await cerebrum_system_core.add_to_context(
        content="test content",
        source="test",
        priority=50,
        metadata={"key": "value"}
    )
    
    # Verify that add_to_operation_context was called
    mock_unified_context_manager.add_to_operation_context.assert_called_with(
        operation_id="cerebrum_system",
        content="test content",
        source="test",
        priority=50,
        metadata={"key": "value"}
    )
    
    # Verify the result
    assert item_id == "item1"

@pytest.mark.asyncio
async def test_get_pending_approvals(cerebrum_system_core, mock_unified_context_manager):
    """Test getting pending approvals."""
    approvals = await cerebrum_system_core.get_pending_approvals()
    
    # Verify that get_pending_command_approvals was called
    mock_unified_context_manager.get_pending_command_approvals.assert_called_once()
    
    # Verify the result
    assert approvals == []

@pytest.mark.asyncio
async def test_execute_approved_command(cerebrum_system_core, mock_unified_context_manager):
    """Test executing an approved command."""
    result = await cerebrum_system_core.execute_approved_command(approval_id="approval1")
    
    # Verify that execute_approved_command was called
    mock_unified_context_manager.execute_approved_command.assert_called_once_with(
        operation_id="cerebrum_system",
        approval_id="approval1",
        add_to_context=True,
        context_priority=60
    )
    
    # Verify the result
    assert result.command == "cat file.txt"
    assert result.exit_code == 0
    assert result.stdout == "file content"

@pytest.mark.asyncio
async def test_reject_command(cerebrum_system_core, mock_unified_context_manager):
    """Test rejecting a command."""
    result = await cerebrum_system_core.reject_command(approval_id="approval1")
    
    # Verify that reject_command was called
    mock_unified_context_manager.reject_command.assert_called_once_with("approval1")
    
    # Verify the result
    assert result is True

@pytest.mark.asyncio
async def test_get_codebase_stats(cerebrum_system_core, mock_unified_context_manager):
    """Test getting codebase stats."""
    stats = await cerebrum_system_core.get_codebase_stats()
    
    # Verify that get_codebase_stats was called
    mock_unified_context_manager.get_codebase_stats.assert_called_once()
    
    # Verify the result
    assert stats == {
        "total_files": 10,
        "total_lines": 1000,
        "languages": {
            "python": 5,
            "javascript": 3,
            "markdown": 2
        },
        "last_updated": "2023-01-01T00:00:00"
    }

@pytest.mark.asyncio
async def test_refresh_codebase(cerebrum_system_core, mock_unified_context_manager):
    """Test refreshing the codebase."""
    result = await cerebrum_system_core.refresh_codebase()
    
    # Verify that refresh_codebase was called
    mock_unified_context_manager.refresh_codebase.assert_called_once()
    
    # Verify the result
    assert result == {
        "indexed_files": 2,
        "total_files": 10,
        "skipped_files": 8
    } 