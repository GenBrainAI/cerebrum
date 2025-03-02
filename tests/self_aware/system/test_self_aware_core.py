"""
Tests for the CerebrumSystemCore class.

These tests verify the functionality of the Cerebrum System Core, including
initialization, codebase search, command execution, and context management.
"""

import os
import sys
import json
import pytest
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# Add project root to Python path
project_root = str(Path(__file__).parents[2])  # Go up two levels to reach project root
sys.path.append(project_root)

from src.server.self_aware_core import CerebrumSystemCore
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
def core():
    """Fixture for creating a CerebrumSystemCore instance with mocked components."""
    # Create a mock for UnifiedContextManager
    mock_ucm = AsyncMock()
    
    # Create a mock for initialize_codebase_index
    mock_ucm.initialize_codebase_index = AsyncMock(return_value={
        "indexed_files": 10,
        "skipped_files": 0,
        "total_files": 10
    })
    
    # Create a mock for create_operation
    mock_ucm.create_operation = AsyncMock(return_value="cerebrum_system")
    
    # Create a mock for add_to_operation_context
    mock_ucm.add_to_operation_context = AsyncMock(return_value="context_id")
    
    # Create a mock for list_operations
    mock_ucm.list_operations = AsyncMock(return_value=[])
    
    # Create a mock for search_codebase
    mock_ucm.search_codebase = AsyncMock()
    
    # Create a mock for execute_command
    mock_ucm.execute_command = AsyncMock()
    
    # Create a mock for get_operation_context
    mock_ucm.get_operation_context = AsyncMock()
    
    # Create a mock for get_file_content
    mock_ucm.get_file_content = AsyncMock()
    
    # Create a mock for get_codebase_stats
    mock_ucm.get_codebase_stats = AsyncMock()
    
    # Create the core with the mocked UnifiedContextManager
    core = CerebrumSystemCore(
        base_path=TEST_CONFIG["base_path"],
        codebase_root=".",
        config=TEST_CONFIG
    )
    
    # Replace the context_manager with our mock
    core.context_manager = mock_ucm
    
    yield core
    
    # Cleanup
    if os.path.exists(TEST_CONFIG["base_path"]):
        import shutil
        shutil.rmtree(TEST_CONFIG["base_path"])

@pytest.mark.asyncio
async def test_initialization(core):
    """Test that the core initializes correctly."""
    # Initialize the core
    result = await core.initialize()
    
    # Verify that the core was initialized
    assert result is True
    
    # Verify that the UnifiedContextManager was initialized
    assert core.context_manager.initialize_codebase_index.called
    assert core.context_manager.create_operation.called
    assert core.context_manager.add_to_operation_context.called

@pytest.mark.asyncio
async def test_search_code(core):
    """Test searching the codebase."""
    # Mock the search_codebase method
    mock_results = [
        CodeSnippet(
            file_path="src/server/self_aware_core.py",
            content="def search_code(self, query: str, top_k: int = 5):",
            start_line=100,
            end_line=110,
            language="python",
            relevance_score=0.9
        )
    ]
    core.context_manager.search_codebase.return_value = mock_results
    
    # Search the codebase
    results = await core.search_code("search_code")
    
    # Verify that the search was performed
    assert core.context_manager.search_codebase.called
    call_args = core.context_manager.search_codebase.call_args[1]
    assert call_args["operation_id"] == "cerebrum_system"
    assert call_args["query"] == "search_code"
    assert call_args["top_k"] == 5
    assert call_args["add_to_context"] is True
    assert call_args["context_priority"] == 70
    
    # Verify the results
    assert len(results) == 1
    assert results[0].file_path == "src/server/self_aware_core.py"
    assert "search_code" in results[0].content

@pytest.mark.asyncio
async def test_execute_command(core):
    """Test executing a command."""
    # Mock the execute_command method
    mock_result = CommandExecutionResult(
        command_id="command_id",
        command="ls -la",
        exit_code=0,
        stdout="file1.txt\nfile2.txt",
        stderr="",
        execution_time=0.1,
        started_at="2023-01-01T00:00:00",
        completed_at="2023-01-01T00:00:01",
        working_directory=".",
        environment_vars={},
        sandbox_type="subprocess"
    )
    core.context_manager.execute_command.return_value = mock_result
    
    # Execute a command
    result = await core.execute_command("ls -la")
    
    # Verify that the command was executed
    assert core.context_manager.execute_command.called
    call_args = core.context_manager.execute_command.call_args[1]
    assert call_args["operation_id"] == "cerebrum_system"
    assert call_args["command"] == "ls -la"
    assert call_args["requires_approval"] is True
    assert call_args["add_to_context"] is True
    assert call_args["context_priority"] == 60
    
    # Verify the result
    assert result.command == "ls -la"
    assert "file1.txt" in result.stdout
    assert result.exit_code == 0

@pytest.mark.asyncio
async def test_add_to_context(core):
    """Test adding to the context."""
    # Add to the context
    context_id = await core.add_to_context(
        content="Test content",
        source="test",
        priority=80,
        metadata={"test": "value"}
    )
    
    # Verify that the content was added
    assert core.context_manager.add_to_operation_context.called
    call_args = core.context_manager.add_to_operation_context.call_args[1]
    assert call_args["operation_id"] == "cerebrum_system"
    assert call_args["content"] == "Test content"
    assert call_args["source"] == "test"
    assert call_args["priority"] == 80
    assert call_args["metadata"] == {"test": "value"}
    
    # Verify the result
    assert context_id == "context_id"

@pytest.mark.asyncio
async def test_get_context(core):
    """Test getting the context."""
    # Mock the get_operation_context method
    core.context_manager.get_operation_context.return_value = "Test context"
    
    # Get the context
    context = await core.get_context(max_tokens=1000)
    
    # Verify that the context was retrieved
    assert core.context_manager.get_operation_context.called
    call_args = core.context_manager.get_operation_context.call_args[1]
    assert call_args["operation_id"] == "cerebrum_system"
    assert call_args["max_tokens"] == 1000
    assert call_args["include_metadata"] is False
    
    # Verify the result
    assert context == "Test context"

@pytest.mark.asyncio
async def test_get_file_content(core):
    """Test getting file content."""
    # Mock the get_file_content method
    core.context_manager.get_file_content.return_value = "Test file content"
    
    # Get the file content
    content = await core.get_file_content("test.py")
    
    # Verify that the file content was retrieved
    assert core.context_manager.get_file_content.called
    call_args = core.context_manager.get_file_content.call_args[1]
    assert call_args["operation_id"] == "cerebrum_system"
    assert call_args["file_path"] == "test.py"
    assert call_args["add_to_context"] is True
    assert call_args["context_priority"] == 65
    
    # Verify the result
    assert content == "Test file content"

@pytest.mark.asyncio
async def test_get_codebase_stats(core):
    """Test getting codebase statistics."""
    # Mock the get_codebase_stats method
    mock_stats = {
        "total_files": 100,
        "total_lines": 10000,
        "languages": ["python", "javascript", "html"]
    }
    core.context_manager.get_codebase_stats.return_value = mock_stats
    
    # Get the codebase statistics
    stats = await core.get_codebase_stats()
    
    # Verify that the statistics were retrieved
    assert core.context_manager.get_codebase_stats.called
    
    # Verify the result
    assert stats["total_files"] == 100
    assert stats["total_lines"] == 10000
    assert "python" in stats["languages"] 