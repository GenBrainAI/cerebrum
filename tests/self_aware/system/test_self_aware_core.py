"""
Tests for the CerebrumSystemCore class.

These tests verify the functionality of the Cerebrum System Core, including
initialization, codebase search, command execution, and context management.
"""

import os
import sys
import json
import pytest
import pytest_asyncio
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, List, Any, Optional

# Add project root to Python path
project_root = str(Path(__file__).parents[2])  # Go up two levels to reach project root
sys.path.append(project_root)

from src.server.self_aware_core import CerebrumSystemCore
from src.server.context.unified_context_manager import UnifiedContextManager
from src.server.system.codebase_vector_store import CodeSnippet
from src.server.system.terminal_command_executor import CommandExecutionResult

# Test configuration
TEST_CONFIG = {
    "base_path": "test_persistent_state/cerebrum_system",
    "context": {
        "max_tokens": 8192,
        "default_model": "gpt-4",
        "enable_history": True,
        "history_max_items": 10,
        "default_compression_strategy": "summarize"
    },
    "security": {
        "max_execution_time": 60,
        "max_output_size": 1048576,
        "blocked_commands": [
            "rm -rf /",
            "sudo",
            "chmod 777"
        ]
    },
    "vector_store": {
        "embedding_model": "text-embedding-ada-002",
        "embedding_dimension": 1536,
        "similarity_threshold": 0.7,
        "max_files": 10000,
        "excluded_dirs": [
            ".git", "node_modules", "venv", "env", "__pycache__", 
            "dist", "build", ".vscode", ".idea"
        ],
        "excluded_patterns": [
            r"\.pyc$", r"\.class$", r"\.o$", r"\.so$", r"\.a$",
            r"\.dll$", r"\.exe$", r"\.bin$", r"\.dat$", r"\.log$"
        ],
        "included_extensions": [
            ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css",
            ".java", ".c", ".cpp", ".h", ".hpp", ".go", ".rs",
            ".rb", ".php", ".swift", ".kt", ".sh", ".md",
            ".json", ".yml", ".yaml", ".toml", ".sql"
        ],
        "chunk_size": 1000,
        "chunk_overlap": 200
    }
}

@pytest.fixture
def mock_unified_context_manager():
    """Create a mock UnifiedContextManager."""
    mock = AsyncMock(spec=UnifiedContextManager)
    
    # Mock list_operations
    mock.list_operations = AsyncMock(return_value=[])
    
    # Mock create_operation
    mock.create_operation = AsyncMock(return_value="cerebrum_system")
    
    # Mock initialize_codebase_index
    mock.initialize_codebase_index = AsyncMock(return_value={
        "indexed_files": 10,
        "total_files": 10,
        "skipped_files": 0
    })
    
    # Mock add_to_operation_context
    mock.add_to_operation_context = AsyncMock(return_value="context_id")
    
    # Mock execute_command
    mock.execute_command = AsyncMock(return_value=CommandExecutionResult(
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
    ))
    
    # Mock search_codebase
    mock.search_codebase = AsyncMock(return_value=[
        CodeSnippet(
            file_path="src/server/self_aware_core.py",
            content="def search_code(self, query: str, top_k: int = 5):",
            start_line=100,
            end_line=110,
            language="python",
            relevance_score=0.9
        )
    ])
    
    # Mock get_file_content
    mock.get_file_content = AsyncMock(return_value="Test file content")
    
    # Mock get_operation_context
    mock.get_operation_context = AsyncMock(return_value="Test context")
    
    # Mock get_codebase_stats
    mock.get_codebase_stats = AsyncMock(return_value={
        "total_files": 10,
        "total_lines": 1000,
        "languages": {
            "python": 5,
            "javascript": 3,
            "markdown": 2
        },
        "last_updated": "2023-01-01T00:00:00"
    })
    
    # Mock pending commands
    mock.get_pending_command_approvals = AsyncMock(return_value=[])
    
    # Mock approved command
    mock.execute_approved_command = AsyncMock(return_value=CommandExecutionResult(
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
    ))
    
    # Mock reject command
    mock.reject_command = AsyncMock(return_value=True)
    
    # Mock refresh_codebase
    mock.refresh_codebase = AsyncMock(return_value={
        "indexed_files": 2,
        "total_files": 10,
        "skipped_files": 8
    })
    
    return mock

@pytest_asyncio.fixture
async def core(mock_unified_context_manager, tmp_path):
    """Create a CerebrumSystemCore instance with mocked components."""
    # Create the core with the mocked UnifiedContextManager
    core = CerebrumSystemCore(
        base_path=str(tmp_path / "cerebrum_system"),
        codebase_root=".",
        config=TEST_CONFIG
    )
    
    # Replace the context_manager with our mock
    core.context_manager = mock_unified_context_manager
    
    # Initialize the core
    await core.initialize()
    
    yield core
    
    # Cleanup
    if os.path.exists(TEST_CONFIG["base_path"]):
        import shutil
        shutil.rmtree(TEST_CONFIG["base_path"])

@pytest.mark.asyncio
async def test_initialize_operation(core, mock_unified_context_manager):
    """Test initializing the system operation."""
    # The core is already initialized in the fixture
    assert core._initialized is True
    
    # Test initializing operation explicitly
    operation_id = await core.initialize_operation(operation_id=None)
    
    # Verify that list_operations was called
    mock_unified_context_manager.list_operations.assert_called()
    
    # Verify that create_operation was called correctly
    mock_unified_context_manager.create_operation.assert_called()
    assert operation_id == "cerebrum_system"

@pytest.mark.asyncio
async def test_index_codebase(core, mock_unified_context_manager):
    """Test indexing the codebase."""
    result = await core.index_codebase(incremental=True)
    
    # Verify that initialize_codebase_index was called
    mock_unified_context_manager.initialize_codebase_index.assert_called_with(incremental=True)
    
    # Verify the result
    assert result == {
        "indexed_files": 10,
        "total_files": 10,
        "skipped_files": 0
    }

@pytest.mark.asyncio
async def test_search_code(core, mock_unified_context_manager):
    """Test searching the codebase."""
    results = await core.search_code(query="search_code", top_k=5)
    
    # Verify that search_codebase was called
    mock_unified_context_manager.search_codebase.assert_called_with(
        operation_id="cerebrum_system",
        query="search_code",
        top_k=5,
        add_to_context=True,
        context_priority=70
    )
    
    # Verify the results
    assert len(results) == 1
    assert results[0].file_path == "src/server/self_aware_core.py"
    assert "search_code" in results[0].content

@pytest.mark.asyncio
async def test_execute_command(core, mock_unified_context_manager):
    """Test executing a command."""
    result = await core.execute_command(
        command="ls -la",
        working_directory=".",
        timeout=30,
        requires_approval=False
    )
    
    # Verify that execute_command was called
    mock_unified_context_manager.execute_command.assert_called_with(
        operation_id="cerebrum_system",
        command="ls -la",
        working_directory=".",
        environment_vars=None,
        timeout=30,
        requires_approval=False,
        add_to_context=True,
        context_priority=60
    )
    
    # Verify the result
    assert result.command == "ls -la"
    assert "file1.txt" in result.stdout
    assert result.exit_code == 0

@pytest.mark.asyncio
async def test_command_requiring_approval(core):
    """Test executing a command that requires approval."""
    approval_id = await core.execute_command(
        command="rm -rf *",
        requires_approval=True
    )
    
    # Verify that the command was added to pending approvals
    assert isinstance(approval_id, str)
    assert approval_id in core.pending_approvals
    assert core.pending_approvals[approval_id]["command"] == "rm -rf *"

@pytest.mark.asyncio
async def test_get_pending_approvals(core):
    """Test getting pending approvals."""
    # Add a pending approval
    approval_id = await core.execute_command("rm -rf *", requires_approval=True)
    
    # Get pending approvals
    approvals = await core.get_pending_approvals()
    
    # Verify the result
    assert len(approvals) == 1
    assert approvals[0]["id"] == approval_id
    assert approvals[0]["command"] == "rm -rf *"

@pytest.mark.asyncio
async def test_execute_approved_command(core, mock_unified_context_manager):
    """Test executing an approved command."""
    # Add a pending approval
    approval_id = await core.execute_command("cat file.txt", requires_approval=True)
    
    # Execute the approved command
    result = await core.execute_approved_command(approval_id)
    
    # Verify that execute_command was called
    mock_unified_context_manager.execute_command.assert_called_with(
        operation_id="cerebrum_system",
        command="cat file.txt",
        working_directory=core.codebase_root,
        timeout=30,
        requires_approval=False,
        add_to_context=True,
        context_priority=60,
        environment_vars=None
    )
    
    # Verify the result
    assert result.command == "ls -la"  # This is from our mock

@pytest.mark.asyncio
async def test_reject_command(core):
    """Test rejecting a command."""
    # Add a pending approval
    approval_id = await core.execute_command("rm -rf *", requires_approval=True)
    
    # Reject the command
    result = await core.reject_command(approval_id)
    
    # Verify the result
    assert result is True
    assert approval_id not in core.pending_approvals

@pytest.mark.asyncio
async def test_add_to_context(core, mock_unified_context_manager):
    """Test adding to the context."""
    context_id = await core.add_to_context(
        content="Test content",
        source_type="test",
        metadata={"test": "value"}
    )
    
    # Verify that add_to_operation_context was called
    mock_unified_context_manager.add_to_operation_context.assert_called_with(
        operation_id="cerebrum_system",
        content="Test content",
        source="test",
        priority=None,
        metadata={"test": "value"}
    )
    
    # Verify the result
    assert context_id == "context_id"

@pytest.mark.asyncio
async def test_get_context(core, mock_unified_context_manager):
    """Test getting the context."""
    context = await core.get_context(max_tokens=1000, include_metadata=False)
    
    # Verify that get_operation_context was called
    mock_unified_context_manager.get_operation_context.assert_called_with(
        operation_id="cerebrum_system",
        max_tokens=1000,
        include_metadata=False
    )
    
    # Verify the result
    assert context == "Test context"

@pytest.mark.asyncio
async def test_get_file_content(core, mock_unified_context_manager):
    """Test getting file content."""
    content = await core.get_file_content(file_path="test.py")
    
    # Verify that get_file_content was called
    mock_unified_context_manager.get_file_content.assert_called_with(
        operation_id="cerebrum_system",
        file_path="test.py",
        add_to_context=True,
        context_priority=65
    )
    
    # Verify the result
    assert content == "Test file content"

@pytest.mark.asyncio
async def test_get_codebase_stats(core, mock_unified_context_manager):
    """Test getting codebase stats."""
    stats = await core.get_codebase_stats()
    
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
async def test_refresh_codebase(core, mock_unified_context_manager):
    """Test refreshing the codebase."""
    stats = await core.refresh_codebase()
    
    # Verify that index_codebase was called with incremental=True
    mock_unified_context_manager.initialize_codebase_index.assert_called_with(incremental=True)
    
    # Verify the result
    assert stats == {
        "indexed_files": 10,
        "total_files": 10,
        "skipped_files": 0
    } 