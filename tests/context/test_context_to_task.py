import pytest
from uuid import UUID, uuid4
from datetime import datetime
from typing import Dict, List
import json
from pathlib import Path

from src.server.models.task_context_model import TaskContextManager, TaskContext, ContextReference
from src.server.context.context_provider import ContextProvider
from src.server.models.message import Message

class MockVectorStore:
    def __init__(self):
        self.metadata_dir = Path("test_context_db/metadata")
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        
    async def get_filtered_items(self, filters: Dict, limit: int = 5) -> List[Dict]:
        if 'file_ids' in filters.get('filters', {}):
            results = []
            for file_id in filters['filters']['file_ids']:
                metadata_file = self.metadata_dir / f"{file_id}.json"
                if metadata_file.exists():
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                        results.append({
                            "content": metadata.get('content', ''),
                            "metadata": metadata
                        })
            return results
        return []

class MockContextDB:
    def __init__(self):
        self.vector_store = MockVectorStore()
        
    async def search_context(self, query: str, limit: int, filters: Dict = None) -> List[Dict]:
        # If we have vector store filters, use them
        if filters and ('file_ids' in filters or 'filters' in filters):
            vector_results = await self.vector_store.get_filtered_items(
                filters if 'filters' in filters else {"filters": filters}, 
                limit
            )
            if vector_results:
                return [{
                    "content": item["content"],
                    "metadata": item["metadata"],
                    "relevance": 0.95
                } for item in vector_results]
                
        # Fallback to default test content
        return [
            {
                "content": "Test vector content",
                "metadata": {"source": "test"},
                "relevance": 0.95
            }
        ]

class MockKnowledgeBase:
    def get_knowledge(self, domain: str = None, tags: List[str] = None) -> List[Dict]:
        return [
            {
                "content": "Test knowledge content",
                "metadata": {"domain": domain or "test"}
            }
        ]

class MockSystemContext:
    def get_context(self, context_id: str) -> str:
        return "Test system context"

class MockPersistenceModel:
    class Tasks:
        def read(self, task_id: str):
            if task_id == "task1":
                # Create a mock task with manager ID
                return type("Task", (), {
                    "tasksmanager_id": "manager1",
                    "id": task_id
                })
            return None
    
    tasks = Tasks()

@pytest.fixture
def context_provider():
    provider = ContextProvider()
    provider.context_db = MockContextDB()
    provider.knowledge_base = MockKnowledgeBase()
    provider.system_context = MockSystemContext()
    provider.persistence_model = MockPersistenceModel()
    return provider

@pytest.mark.asyncio
async def test_task_context_basic_operations():
    """Test basic task context operations."""
    manager = TaskContextManager()
    
    # Create task context
    task_context = manager.create_task_context("task1")
    assert task_context.task_id == "task1"
    assert len(task_context.contexts) == 0
    
    # Add context
    context_ref = task_context.add_context(
        type="system",
        source_id="sys1",
        priority=1
    )
    assert isinstance(context_ref, ContextReference)
    assert len(task_context.contexts) == 1
    
    # Remove context
    assert task_context.remove_context(context_ref.id)
    assert len(task_context.contexts) == 0

@pytest.mark.asyncio
async def test_task_context_configuration():
    """Test task context configuration options."""
    manager = TaskContextManager()
    task_context = manager.create_task_context("task1")
    
    # Default configuration
    assert task_context.use_context is True
    assert task_context.inherit_manager_context is True
    
    # Update configuration
    updated = task_context.update_context_config(
        use_context=False,
        inherit_manager_context=False
    )
    assert updated is True
    assert task_context.use_context is False
    assert task_context.inherit_manager_context is False

@pytest.mark.asyncio
async def test_manager_context_inheritance(context_provider):
    """Test context inheritance from task manager."""
    # Setup manager context - note the ID format
    manager_id = "manager1"  # Base manager ID
    manager_context_id = f"manager_{manager_id}"
    
    # Create manager context
    manager_context = context_provider.task_context_manager.create_task_context(manager_context_id)
    manager_context.add_context(
        type="system",
        source_id="sys1",
        priority=1
    )
    
    # Create task context without specific contexts
    task_context = context_provider.task_context_manager.create_task_context("task1")
    task_context.update_context_config(
        use_context=True,
        inherit_manager_context=True
    )
    
    # Get contexts - should inherit from manager
    contexts = await context_provider.get_task_contexts("task1")
    assert len(contexts) > 0  # Should inherit from manager
    assert contexts[0]["type"] == "system"  # Should get system context from manager
    
    # Add task-specific context
    task_context.add_context(
        type="vector",
        source_id="vec1",
        priority=2
    )
    
    # Get contexts - should include both inherited and task-specific
    contexts = await context_provider.get_task_contexts("task1")
    assert len(contexts) > 1
    assert any(c["type"] == "vector" for c in contexts)
    assert any(c["type"] == "system" for c in contexts)

@pytest.mark.asyncio
async def test_context_disabled():
    """Test behavior when context is disabled."""
    manager = TaskContextManager()
    task_context = manager.create_task_context("task1")
    
    # Add context but disable context usage
    task_context.add_context(
        type="system",
        source_id="sys1"
    )
    task_context.update_context_config(use_context=False)
    
    # Context provider should respect the disabled setting
    provider = ContextProvider()
    contexts = await provider.get_task_contexts("task1")
    assert len(contexts) == 0

@pytest.mark.asyncio
async def test_message_preparation(context_provider):
    """Test message preparation with contexts."""
    # Setup task context
    task_context = context_provider.task_context_manager.create_task_context("task1")
    task_context.add_context(
        type="system",
        source_id="sys1",
        priority=1
    )
    
    # Test message preparation
    messages = [Message(role="user", content="test")]
    prepared_messages = await context_provider.prepare_task_messages(
        task_id="task1",
        messages=messages
    )
    
    assert len(prepared_messages) > len(messages)
    assert prepared_messages[0].role == "system"
    assert "context" in prepared_messages[0].content.lower()

@pytest.mark.asyncio
async def test_context_priority_ordering(context_provider):
    """Test that contexts are properly ordered by priority."""
    task_context = context_provider.task_context_manager.create_task_context("task1")
    
    # Add contexts with different priorities
    task_context.add_context(
        type="system",
        source_id="sys1",
        priority=1
    )
    task_context.add_context(
        type="vector",
        source_id="vec1",
        priority=2
    )
    
    contexts = await context_provider.get_task_contexts("task1")
    assert len(contexts) > 0
    # Verify higher priority contexts come first
    priorities = [c.get("priority", 0) for c in contexts]
    assert priorities == sorted(priorities, reverse=True)

@pytest.mark.asyncio
async def test_no_context_inheritance():
    """Test when inheritance is disabled."""
    manager = TaskContextManager()
    
    # Setup manager context
    manager_context = manager.create_task_context("manager_manager1")
    manager_context.add_context(
        type="system",
        source_id="sys1"
    )
    
    # Setup task context with inheritance disabled
    task_context = manager.create_task_context("task1")
    task_context.update_context_config(inherit_manager_context=False)
    
    # Should not get manager contexts
    provider = ContextProvider()
    contexts = await provider.get_task_contexts("task1")
    assert len(contexts) == 0

@pytest.mark.asyncio
async def test_context_type_filtering(context_provider):
    """Test filtering contexts by type."""
    task_context = context_provider.task_context_manager.create_task_context("task1")
    
    # Add different types of contexts
    task_context.add_context(type="system", source_id="sys1")
    task_context.add_context(type="vector", source_id="vec1")
    task_context.add_context(type="knowledge", source_id="kb1")
    
    # Test filtering
    contexts = await context_provider.get_task_contexts(
        task_id="task1",
        context_types=["system"]
    )
    assert all(c["type"] == "system" for c in contexts)

@pytest.mark.asyncio
async def test_add_vector_context_to_task(context_provider):
    """Test adding vector context to a task with file references."""
    # Setup mock file in vector store
    mock_file_id = "5888dd126ee208d8e82720bb5d8154af"
    mock_file_content = "Test content from I, Robot"
    mock_file_metadata = {
        "filename": "Asimov-Isaac-I-Robot.pdf",
        "content": mock_file_content,
        "file_type": "application/pdf",
        "added_at": "2024-03-14T12:00:00",
        "size": 1000
    }

    # Create metadata directory and file
    metadata_dir = context_provider.context_db.vector_store.metadata_dir
    metadata_dir.mkdir(parents=True, exist_ok=True)
    
    with open(metadata_dir / f"{mock_file_id}.json", 'w') as f:
        json.dump(mock_file_metadata, f)

    # Create a task
    task_id = "test_task_1"
    task_context = context_provider.task_context_manager.create_task_context(task_id)
    
    # Add vector context with file reference
    metadata = {
        "filters": {
            "file_ids": [mock_file_id]
        }
    }
    
    context_ref = await context_provider.add_context_to_task(
        task_id=task_id,
        type="vector",
        source_id=str(uuid4()),  # Generate a new UUID for the context
        priority=50,
        metadata=metadata
    )
    
    # Verify context was added
    assert context_ref is not None
    assert context_ref.type == "vector"
    assert context_ref.priority == 50
    
    # Get contexts and verify
    contexts = await context_provider.get_task_contexts(task_id)
    assert len(contexts) > 0
    
    vector_contexts = [c for c in contexts if c["type"] == "vector"]
    assert len(vector_contexts) > 0
    
    # Verify content is retrieved correctly
    first_vector_context = vector_contexts[0]
    assert "content" in first_vector_context
    assert mock_file_content in first_vector_context["content"]
    
    # Verify metadata
    assert "metadata" in first_vector_context
    assert "filters" in first_vector_context["metadata"]
    assert "file_ids" in first_vector_context["metadata"]["filters"]
    assert mock_file_id in first_vector_context["metadata"]["filters"]["file_ids"]
