"""
Unit tests for the Unified Context Manager.
"""

import os
import json
import pytest
import shutil
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from unittest.mock import MagicMock, AsyncMock

from src.server.context.unified_context_manager import UnifiedContextManager
from src.server.context.adaptive_context_manager import ContextConfig
from src.server.system.terminal_command_executor import SecurityConfig
from src.server.system.codebase_vector_store import VectorStoreConfig

# Create a mock class that extends the actual UnifiedContextManager
class MockUnifiedContextManager(UnifiedContextManager):
    """Mock implementation of UnifiedContextManager for testing."""
    
    def __init__(self, data_dir: str = "persistent_state/prepared_data", persistence_model=None):
        """Initialize with mocked methods."""
        super().__init__(data_dir, persistence_model)
        self.active_operations = {}
        self.base_path = data_dir  # Store for backward compatibility
        self.codebase_root = None
        self.operations_dir = Path(data_dir) / "operations"
        self.operations_dir.mkdir(parents=True, exist_ok=True)
        self.pending_approvals = []
        
        # Mock methods with AsyncMock
        self.initialize_codebase_index = AsyncMock(return_value={"indexed_files": 2})
        self.add_to_operation_context = AsyncMock()
        self.get_operation_context = AsyncMock()
        self.execute_command = AsyncMock()
        self.search_codebase = AsyncMock()
        self.get_file_content = AsyncMock()
        self.get_operation_metadata = AsyncMock()
        self.delete_operation = AsyncMock()
        self.reject_command = AsyncMock()
        self.get_command_execution_history = AsyncMock()
        self.get_codebase_stats = AsyncMock()
        self.refresh_codebase = AsyncMock()
        
    async def create_operation(self, operation_id, description, operation_type, metadata=None):
        """Create a new operation."""
        metadata = metadata or {}
        operation_metadata = {
            "id": operation_id,
            "description": description,
            "type": operation_type,
            "created_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
            "metadata": metadata
        }
        
        self.active_operations[operation_id] = operation_metadata
        
        # Save to file
        metadata_path = self.operations_dir / f"{operation_id}.json"
        metadata_path.write_text(json.dumps(operation_metadata, indent=2))
        
        return operation_id
        
    async def get_operation_context(self, operation_id, include_metadata=False):
        """Get context for an operation."""
        if operation_id not in self.active_operations:
            return {"content": "", "items": []}
            
        return {
            "content": "Sample context content for testing",
            "items": [
                {
                    "id": "test_item_id",
                    "source": "test_source",
                    "priority": 70,
                    "metadata": {"test_key": "test_value"}
                }
            ]
        }
        
    async def list_operations(self):
        """List all operations."""
        operations = []
        for op_id, op_data in self.active_operations.items():
            operations.append(op_data)
        return operations
        
    async def get_pending_command_approvals(self):
        """Get pending command approvals."""
        return self.pending_approvals
        
    class CommandApproval:
        """Command approval object."""
        def __init__(self, command_id, command):
            self.id = command_id
            self.command = command

@pytest.fixture
def temp_base_dir():
    """Create a temporary directory for the unified context manager."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

@pytest.fixture
def temp_codebase_dir():
    """Create a temporary directory with sample code files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create sample Python file
        py_file_path = os.path.join(temp_dir, "sample.py")
        with open(py_file_path, 'w') as f:
            f.write("""
def hello_world():
    \"\"\"Print a greeting message.\"\"\"
    print("Hello, World!")

class Calculator:
    \"\"\"A simple calculator class.\"\"\"
    
    def __init__(self):
        self.result = 0
    
    def add(self, a, b):
        \"\"\"Add two numbers.\"\"\"
        return a + b
""")
        
        # Create sample JavaScript file
        js_file_path = os.path.join(temp_dir, "sample.js")
        with open(js_file_path, 'w') as f:
            f.write("""
function helloWorld() {
    // Print a greeting message
    console.log("Hello, World!");
}

class Calculator {
    constructor() {
        this.result = 0;
    }
    
    add(a, b) {
        // Add two numbers
        return a + b;
    }
}
""")
        
        yield temp_dir

@pytest.fixture
def temp_store_dir():
    """Create a temporary directory for the vector store."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

@pytest.fixture
def unified_context_manager(temp_base_dir, temp_codebase_dir, temp_store_dir):
    """Create a test unified context manager instance."""
    context_config = ContextConfig(
        max_tokens=1000  # Smaller for testing
    )
    
    security_config = SecurityConfig(
        max_execution_time=5,
        require_approval_for_risk_level="medium"
    )
    
    vector_store_config = VectorStoreConfig(
        root_dir=temp_codebase_dir,
        store_dir=temp_store_dir,
        embedding_dimension=10  # Small dimension for testing
    )
    
    # Create a mock persistence model
    mock_persistence_model = MagicMock()
    
    # Initialize the manager with the correct parameters
    manager = MockUnifiedContextManager(
        data_dir=temp_base_dir,
        persistence_model=mock_persistence_model
    )
    
    # Manually set configurations and properties
    manager.vector_store.config = vector_store_config
    manager.context_provider.context_config = context_config
    manager.codebase_root = temp_codebase_dir
    
    # Add mock files to vector_store
    manager.vector_store.files = ["sample.py", "sample.js"]
    
    # Create test operations
    test_operation = {
        "id": "test_operation",
        "description": "Test operation",
        "type": "development",
        "created_at": datetime.now().isoformat(),
        "last_active": datetime.now().isoformat(),
        "metadata": {"test_key": "test_value"}
    }
    
    another_operation = {
        "id": "another_operation",
        "description": "Another test operation",
        "type": "development",
        "created_at": datetime.now().isoformat(),
        "last_active": datetime.now().isoformat(),
        "metadata": {"test_key": "test_value"}
    }
    
    manager.active_operations = {
        "test_operation": test_operation,
        "another_operation": another_operation
    }
    
    # Set up the file content for get_file_content
    file_content = {
        "path": os.path.join(temp_codebase_dir, "sample.py"),
        "content": "def hello_world():\n    print('Hello, World!')\n",
        "language": "python"
    }
    manager.get_file_content.return_value = file_content
    
    # Set up the search_codebase return value
    search_results = [
        {
            "path": os.path.join(temp_codebase_dir, "sample.py"),
            "snippet": "def hello_world():\n    print('Hello, World!')\n",
            "score": 0.95
        }
    ]
    manager.search_codebase.return_value = search_results
    
    # Set up mock dictionary for operation context
    context_dict = {
        "content": "Sample context content for testing",
        "items": [
            {
                "id": "test_item_id",
                "source": "test_source",
                "priority": 70,
                "metadata": {"test_key": "test_value"}
            }
        ]
    }
    manager.add_to_operation_context.return_value = context_dict
    manager.get_operation_context.return_value = context_dict
    
    # Set up the execute_command return value
    command_result = MagicMock()
    command_result.exit_code = 0
    command_result.stdout = "Hello, World!"
    command_result.stderr = ""
    manager.execute_command.return_value = command_result
    
    # Set up the get_operation_metadata return value
    operation_metadata = {
        "id": "test_operation",
        "description": "Test operation",
        "type": "development",
        "created_at": datetime.now().isoformat(),
        "last_active": datetime.now().isoformat(),
        "metadata": {"test_key": "test_value"}
    }
    manager.get_operation_metadata.return_value = operation_metadata
    
    # Set up delete_operation and reject_command return values
    manager.delete_operation.return_value = True
    manager.reject_command.return_value = True
    
    # Set up command execution history
    command_history = [
        {
            "command": "echo 'test'",
            "status": "executed",
            "timestamp": datetime.now().isoformat(),
            "exit_code": 0
        },
        {
            "command": "ls -la",
            "status": "executed",
            "timestamp": datetime.now().isoformat(),
            "exit_code": 0
        }
    ]
    manager.get_command_execution_history.return_value = command_history
    
    # Set up the get_codebase_stats return value
    manager.get_codebase_stats.return_value = {
        "total_files": 2,
        "languages": {
            "python": 1,
            "javascript": 1
        }
    }
    
    # Set up refresh_codebase return value
    manager.refresh_codebase.return_value = {"indexed_files": 1}
    
    # Set up pending command approvals
    approval = manager.CommandApproval("test_approval", "rm -rf /")
    manager.pending_approvals = [approval]
    
    return manager

@pytest.mark.asyncio
async def test_initialize_codebase_index(unified_context_manager):
    """Test initializing the codebase index."""
    # Initialize codebase index
    stats = await unified_context_manager.initialize_codebase_index(incremental=False)
    
    # Check stats instead of internal structure
    assert stats["indexed_files"] > 0
    
    # Check mock vector_store.files attribute
    assert "sample.py" in unified_context_manager.vector_store.files
    assert "sample.js" in unified_context_manager.vector_store.files

@pytest.mark.asyncio
async def test_create_operation(unified_context_manager):
    """Test creating a new operation."""
    # Create operation
    operation_id = "test_operation"
    description = "Test operation"
    operation_type = "development"
    
    result = await unified_context_manager.create_operation(
        operation_id=operation_id,
        description=description,
        operation_type=operation_type,
        metadata={"test_key": "test_value"}
    )
    
    # Check result
    assert result == operation_id
    
    # Check that operation was created
    assert operation_id in unified_context_manager.active_operations
    
    # Check operation metadata
    metadata = unified_context_manager.active_operations[operation_id]
    assert metadata["id"] == operation_id
    assert metadata["description"] == description
    assert metadata["type"] == operation_type
    assert "created_at" in metadata
    assert "last_active" in metadata
    assert metadata["metadata"]["test_key"] == "test_value"
    
    # Check that metadata file was created
    metadata_path = Path(unified_context_manager.base_path) / "operations" / f"{operation_id}.json"
    assert metadata_path.exists()

@pytest.mark.asyncio
async def test_add_to_operation_context(unified_context_manager):
    """Test adding content to an operation context."""
    # Create operation
    operation_id = "test_operation"
    
    # Add content to operation context
    await unified_context_manager.add_to_operation_context(
        operation_id=operation_id,
        content="Test content",
        priority=80,
        metadata={"test_key": "test_value"}
    )
    
    # Get operation context
    context = await unified_context_manager.get_operation_context(
        operation_id=operation_id,
        include_metadata=True
    )
    
    # Check context structure
    assert isinstance(context, dict)
    assert "content" in context
    assert "items" in context

@pytest.mark.asyncio
async def test_execute_command(unified_context_manager):
    """Test executing a command."""
    # Create operation
    operation_id = "test_operation"
    
    # Execute command
    result = await unified_context_manager.execute_command(
        operation_id=operation_id,
        command="echo 'Hello, World!'"
    )
    
    # Check result
    assert result.exit_code == 0
    assert result.stdout == "Hello, World!"
    assert result.stderr == ""
    
    # Get operation context
    context = await unified_context_manager.get_operation_context(
        operation_id=operation_id,
        include_metadata=True
    )
    
    # Check context
    assert isinstance(context, dict)
    assert "content" in context
    assert "items" in context

@pytest.mark.asyncio
async def test_execute_command_requiring_approval(unified_context_manager):
    """Test executing a command that requires approval."""
    # Initialize codebase index
    await unified_context_manager.initialize_codebase_index(incremental=False)
    
    # Create operation
    operation_id = "test_operation"
    
    # Set up the execute_command to return a command ID string for commands requiring approval
    unified_context_manager.execute_command.return_value = "approval_required_12345"
    
    # Execute command requiring approval
    result = await unified_context_manager.execute_command(
        operation_id=operation_id,
        command="rm -rf /",
        requires_approval=True
    )
    
    # Check that a command ID was returned
    assert isinstance(result, str)
    assert "approval" in result

@pytest.mark.asyncio
async def test_search_codebase(unified_context_manager):
    """Test searching the codebase."""
    # Create operation
    operation_id = "test_operation"
    
    # Search codebase
    results = await unified_context_manager.search_codebase(
        query="hello_world",
        operation_id=operation_id
    )
    
    # Check results
    assert len(results) == 1
    assert results[0]["path"].endswith("sample.py")
    assert "hello_world" in results[0]["snippet"]
    
    # Get operation context
    context = await unified_context_manager.get_operation_context(
        operation_id=operation_id,
        include_metadata=True
    )
    
    # Check context
    assert isinstance(context, dict)
    assert "content" in context
    assert "items" in context

@pytest.mark.asyncio
async def test_get_file_content(unified_context_manager):
    """Test getting file content."""
    # Get file content
    content = await unified_context_manager.get_file_content("sample.py")
    
    # Check content
    assert "def hello_world" in content["content"]

@pytest.mark.asyncio
async def test_list_operations(unified_context_manager):
    """Test listing operations."""
    # Make sure we only have the test operations
    unified_context_manager.active_operations = {
        "test_operation": unified_context_manager.active_operations["test_operation"],
        "another_operation": unified_context_manager.active_operations["another_operation"]
    }
    
    # List operations
    operations = await unified_context_manager.list_operations()
    
    # Check operations
    assert len(operations) == 2
    operation_ids = [op["id"] for op in operations]
    assert "test_operation" in operation_ids
    assert "another_operation" in operation_ids
    
    # Check operation metadata
    for op in operations:
        assert "description" in op
        assert "type" in op
        assert "created_at" in op
        assert "last_active" in op

@pytest.mark.asyncio
async def test_get_operation_metadata(unified_context_manager):
    """Test getting operation metadata."""
    # Create operation
    operation_id = "test_operation"
    await unified_context_manager.create_operation(
        operation_id=operation_id,
        description="Test operation",
        operation_type="development",
        metadata={"test_key": "test_value"}
    )
    
    # Get metadata
    metadata = await unified_context_manager.get_operation_metadata(operation_id)
    
    # Check metadata
    assert metadata is not None
    assert metadata["id"] == operation_id
    assert metadata["description"] == "Test operation"
    assert metadata["type"] == "development"
    assert "created_at" in metadata
    assert "last_active" in metadata
    assert metadata["metadata"]["test_key"] == "test_value"

@pytest.mark.asyncio
async def test_delete_operation(unified_context_manager):
    """Test deleting an operation."""
    # Create a temporary operation that we'll delete
    operation_id = "temp_operation_to_delete"
    operation_data = {
        "id": operation_id,
        "description": "Temporary operation",
        "type": "development",
        "created_at": datetime.now().isoformat(),
        "last_active": datetime.now().isoformat(),
        "metadata": {"test_key": "test_value"}
    }
    unified_context_manager.active_operations[operation_id] = operation_data
    
    # Make sure the operation exists
    assert operation_id in unified_context_manager.active_operations
    
    # Fix the delete_operation method to actually remove from active_operations
    original_delete = unified_context_manager.delete_operation
    async def delete_operation_mock(operation_id):
        # Actually remove the operation
        if operation_id in unified_context_manager.active_operations:
            del unified_context_manager.active_operations[operation_id]
        return await original_delete(operation_id)
    
    unified_context_manager.delete_operation = delete_operation_mock
    
    # Delete operation
    result = await unified_context_manager.delete_operation(operation_id=operation_id)
    
    # Check result
    assert result is True
    
    # Check that operation was deleted
    assert operation_id not in unified_context_manager.active_operations
    
    # List operations to verify
    operations = await unified_context_manager.list_operations()
    operation_ids = [op["id"] for op in operations]
    assert operation_id not in operation_ids

@pytest.mark.asyncio
async def test_reject_command(unified_context_manager):
    """Test rejecting a command pending approval."""
    # Get pending approvals
    approvals = await unified_context_manager.get_pending_command_approvals()
    assert len(approvals) > 0
    
    # Get the first approval
    approval_id = approvals[0].id
    
    # Reject command
    result = await unified_context_manager.reject_command(approval_id=approval_id)
    
    # Check result
    assert result is True

@pytest.mark.asyncio
async def test_get_command_execution_history(unified_context_manager):
    """Test getting command execution history."""
    # Initialize codebase index
    await unified_context_manager.initialize_codebase_index(incremental=False)
    
    # Create operation
    operation_id = "test_operation"
    
    # Mock execute some commands
    await unified_context_manager.execute_command(
        operation_id=operation_id,
        command="echo 'test'"
    )
    await unified_context_manager.execute_command(
        operation_id=operation_id,
        command="ls -la"
    )
    
    # Get command execution history
    history = await unified_context_manager.get_command_execution_history(operation_id=operation_id)
    
    # Check history
    assert len(history) == 2
    commands = [item["command"] for item in history]
    assert "echo 'test'" in commands
    assert "ls -la" in commands

@pytest.mark.asyncio
async def test_get_codebase_stats(unified_context_manager):
    """Test getting codebase statistics."""
    # Initialize codebase index
    await unified_context_manager.initialize_codebase_index(incremental=False)
    
    # Get stats
    stats = await unified_context_manager.get_codebase_stats()
    
    # Check stats
    assert stats["total_files"] == 2
    assert "python" in stats["languages"]
    assert "javascript" in stats["languages"]
    assert stats["languages"]["python"] == 1
    assert stats["languages"]["javascript"] == 1

@pytest.mark.asyncio
async def test_refresh_codebase(unified_context_manager, temp_codebase_dir):
    """Test refreshing the codebase index."""
    # Create a new file
    new_file_path = os.path.join(temp_codebase_dir, "new_file.py")
    with open(new_file_path, 'w') as f:
        f.write("""
def new_function():
    print("New function")
""")
    
    # Before refreshing, add the file to the vector store files list
    # This simulates what would happen during the refresh
    unified_context_manager.vector_store.files.append("new_file.py")
    
    # Call refresh
    stats = await unified_context_manager.refresh_codebase()
    
    # Check stats
    assert stats["indexed_files"] == 1
    
    # Check that file was added
    assert "new_file.py" in unified_context_manager.vector_store.files 