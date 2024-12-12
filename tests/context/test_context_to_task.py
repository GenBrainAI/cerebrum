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
        self.stored_contexts = {}
        
    async def store_context(self, task_id: str, context_type: str, source_id: str, 
                          metadata: dict, priority: int = 50) -> None:
        """Mock storing context."""
        if task_id not in self.stored_contexts:
            self.stored_contexts[task_id] = []
            
        self.stored_contexts[task_id].append({
            "type": context_type,
            "source_id": source_id,
            "metadata": metadata,
            "priority": priority
        })
        
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
        
    async def get_contexts(self, task_id: str, context_types: List[str] = None) -> List[Dict]:
        """Get stored contexts for a task."""
        contexts = self.stored_contexts.get(task_id, [])
        if context_types:
            contexts = [c for c in contexts if c["type"] in context_types]
        return contexts

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
        def __init__(self):
            self.tasks = {}

        def read(self, task_id: str):
            # Return a mock task object with necessary attributes
            return type("Task", (), {
                "id": task_id,
                "tasksmanager_id": "manager1",
                "contexts": [],
                "use_context": True,
                "inherit_manager_context": True
            })

        def update(self, task_id: str, task):
            self.tasks[task_id] = task
    
    def __init__(self):
        self.tasks = self.Tasks()

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
    context_ref = manager_context.add_context(
        type="system",
        source_id="sys1",
        priority=1,
        metadata={"content": "Manager system context"}
    )
    
    # Store manager context in context DB
    await context_provider.context_db.store_context(
        task_id=manager_context_id,
        context_type="system",
        source_id="sys1",
        metadata={"content": "Manager system context"},
        priority=1
    )
    
    # Create task context without specific contexts
    task_id = "task1"
    task_context = context_provider.task_context_manager.create_task_context(task_id)
    task_context.update_context_config(
        use_context=True,
        inherit_manager_context=True
    )
    
    print("\n=== Debug Info ===")
    print(f"Manager context: {manager_context.__dict__ if manager_context else None}")
    print(f"Task context: {task_context.__dict__ if task_context else None}")
    print(f"Stored contexts: {context_provider.context_db.stored_contexts}")
    
    # Get contexts - should inherit from manager
    contexts = await context_provider.get_task_contexts(task_id)
    print(f"\nRetrieved contexts: {contexts}")
    
    # Verify inheritance
    assert len(contexts) > 0, "Should inherit from manager"
    assert any(c["type"] == "system" for c in contexts), "Should inherit system context"
    
    # Add task-specific context
    task_context_ref = task_context.add_context(
        type="vector",
        source_id="vec1",
        priority=2,
        metadata={"content": "Task vector context"}
    )
    
    # Store task context in context DB
    await context_provider.context_db.store_context(
        task_id=task_id,
        context_type="vector",
        source_id="vec1",
        metadata={"content": "Task vector context"},
        priority=2
    )
    
    # Get contexts again - should include both inherited and task-specific
    contexts = await context_provider.get_task_contexts(task_id)
    print(f"\nRetrieved contexts after adding task context: {contexts}")
    
    # Verify combined contexts
    assert len(contexts) > 1, "Should have both inherited and task contexts"
    assert any(c["type"] == "vector" for c in contexts), "Should have vector context"
    assert any(c["type"] == "system" for c in contexts), "Should have system context"
    
    # Verify priority ordering
    priorities = [c.get("priority", 0) for c in contexts]
    assert priorities == sorted(priorities, reverse=True), "Contexts should be ordered by priority"

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
    task_id = "task1"
    task_context = context_provider.task_context_manager.create_task_context(task_id)
    
    # Add a system context
    context_ref = task_context.add_context(
        type="system",
        source_id="sys1",
        priority=1,
        metadata={"content": "Test system context"}
    )
    
    # Store context in context DB
    await context_provider.context_db.store_context(
        task_id=task_id,
        context_type="system",
        source_id="sys1",
        metadata={"content": "Test system context"},
        priority=1
    )
    
    print("\n=== Debug Info ===")
    print(f"Task context: {task_context.__dict__ if task_context else None}")
    print(f"Stored contexts: {context_provider.context_db.stored_contexts}")
    print(f"Task contexts: {[c.__dict__ for c in task_context.contexts]}")
    
    # Test message preparation
    messages = [Message(role="user", content="test")]
    prepared_messages = await context_provider.prepare_task_messages(
        task_id=task_id,
        messages=messages
    )
    
    print("\n=== Prepared Messages ===")
    for msg in prepared_messages:
        print(f"Role: {msg.role}")
        print(f"Content: {msg.content}")
    
    # Verify messages
    assert len(prepared_messages) > len(messages), "Should have added context messages"
    assert any(msg.role == "system" for msg in prepared_messages), "Should have system messages"
    assert "Test system context" in prepared_messages[0].content, "Should contain system context"
    assert prepared_messages[-1].role == "user", "Last message should be user message"

@pytest.mark.asyncio
async def test_context_priority_ordering(context_provider):
    """Test that contexts are properly ordered by priority."""
    task_id = "task1"
    task_context = context_provider.task_context_manager.create_task_context(task_id)
    
    # Add contexts with different priorities
    task_context.add_context(
        type="system",
        source_id="sys1",
        priority=1,
        metadata={"content": "Lower priority context"}
    )
    
    # Store first context in context DB
    await context_provider.context_db.store_context(
        task_id=task_id,
        context_type="system",
        source_id="sys1",
        metadata={"content": "Lower priority context"},
        priority=1
    )
    
    task_context.add_context(
        type="vector",
        source_id="vec1",
        priority=2,
        metadata={"content": "Higher priority context"}
    )
    
    # Store second context in context DB
    await context_provider.context_db.store_context(
        task_id=task_id,
        context_type="vector",
        source_id="vec1",
        metadata={"content": "Higher priority context"},
        priority=2
    )
    
    print("\n=== Debug Info ===")
    print(f"Task context: {task_context.__dict__ if task_context else None}")
    print(f"Stored contexts: {context_provider.context_db.stored_contexts}")
    print(f"Task contexts: {[c.__dict__ for c in task_context.contexts]}")
    
    # Get contexts and verify ordering
    contexts = await context_provider.get_task_contexts(task_id)
    print(f"\nRetrieved contexts: {contexts}")
    
    # Verify contexts were retrieved
    assert len(contexts) > 0, "Should have retrieved contexts"
    assert len(contexts) == 2, "Should have both contexts"
    
    # Verify higher priority contexts come first
    priorities = [c.get("priority", 0) for c in contexts]
    print(f"\nContext priorities: {priorities}")
    assert priorities == sorted(priorities, reverse=True), "Contexts should be ordered by priority (highest first)"
    
    # Verify specific ordering
    assert contexts[0].get("priority") == 2, "First context should be higher priority"
    assert contexts[1].get("priority") == 1, "Second context should be lower priority"
    assert contexts[0].get("type") == "vector", "Higher priority context should be vector type"
    assert contexts[1].get("type") == "system", "Lower priority context should be system type"

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
    
    # Add context to task
    context_ref = await context_provider.add_context_to_task(
        task_id=task_id,
        type="vector",
        source_id=str(uuid4()),
        priority=50,
        metadata=metadata
    )

    print("\n=== Debug Info ===")
    print(f"Context reference: {context_ref.__dict__ if context_ref else None}")
    print(f"Task context: {task_context.__dict__ if task_context else None}")
    print(f"Stored contexts: {context_provider.context_db.stored_contexts}")
    print(f"Task contexts: {[c.__dict__ for c in task_context.contexts]}")

    # Verify context was added
    assert context_ref is not None, "Context reference should not be None"
    assert isinstance(context_ref, ContextReference), "Should return a ContextReference"
    assert context_ref.type == "vector", "Context type should be 'vector'"
    assert context_ref.priority == 50, "Priority should match"

    # Verify context was stored in task_context
    assert len(task_context.contexts) > 0, "Task context should have contexts"
    
    # Verify context was stored in context_db
    stored_contexts = await context_provider.context_db.get_contexts(task_id)
    assert len(stored_contexts) > 0, "Context DB should have stored contexts"

    # Get contexts and verify
    contexts = await context_provider.get_task_contexts(task_id)
    assert len(contexts) > 0, "Should have at least one context"
    
    # Verify context content
    context = contexts[0]
    assert context.get("type") == "vector", "Retrieved context should be vector type"
    assert context.get("priority") == 50, "Priority should match"
    assert context.get("metadata", {}).get("filters", {}).get("file_ids") == [mock_file_id], \
        "File ID should match in metadata"
