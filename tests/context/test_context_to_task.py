import pytest
import pytest_asyncio
from uuid import UUID, uuid4
from datetime import datetime
from typing import Dict, List, Optional, Any
import json
from pathlib import Path
from unittest.mock import MagicMock

from src.server.models.task_context_model import TaskContextManager, TaskContext, ContextReference
from src.server.context.context_provider import ContextProvider
from src.server.models.message import Message

class MockVectorStore:
    def __init__(self):
        self.base_path = Path("test_persistent_state/vector_store")
        self.metadata_dir = self.base_path / "metadata"
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.config = type('Config', (), {'collection_name': 'test_collection'})()
        self.client = self  # Make the mock self-referential for the ChromaDB interface
        self.stored_documents = {}
        self.embedding_function = lambda x: [0.0] * 384  # Mock embedding function that returns zero vector
        
    def get_or_create_collection(self, name: str, embedding_function: Any = None):
        """Mock ChromaDB collection creation."""
        return self  # Return self as the collection
        
    def add(self, documents: List[str], metadatas: List[Dict], ids: List[str]):
        """Mock ChromaDB add method."""
        for doc, metadata, id in zip(documents, metadatas, ids):
            self.stored_documents[id] = {
                "content": doc,
                "metadata": metadata
            }
            # Also save to metadata file for backward compatibility
            metadata_file = self.metadata_dir / f"{id}.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f)
                
    async def get_filtered_items(self, filters: Dict, limit: int = 5) -> List[Dict]:
        """Get items matching the filters."""
        print(f"\nDebug - MockVectorStore.get_filtered_items:")
        print(f"Filters: {filters}")
        print(f"Limit: {limit}")
        print(f"Stored documents: {self.stored_documents}")
        
        if 'file_ids' in filters:
            results = []
            for file_id in filters['file_ids']:
                # First check in stored documents
                if file_id in self.stored_documents:
                    doc = self.stored_documents[file_id]
                    results.append({
                        "content": doc["content"],
                        "metadata": doc["metadata"]
                    })
                    continue
                    
                # Fall back to metadata file
                metadata_file = self.metadata_dir / f"{file_id}.json"
                if metadata_file.exists():
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                        results.append({
                            "content": metadata.get('content', ''),
                            "metadata": metadata
                        })
            
            print(f"Returning results: {results}")
            return results[:limit]
        return []
        
    async def get_content(self, content_id: str) -> Optional[Dict[str, Any]]:
        """Get content by ID."""
        # For test_chunk_1, return test content directly
        if content_id == "test_chunk_1":
            return {
                "content": "This is a test chunk",
                "metadata": {
                    "index_name": "test_index",
                    "chunk_ids": ["test_chunk_1"],
                    "file_ids": ["test_chunk_1"]
                }
            }
            
        # Otherwise try to read from file
        metadata_file = self.metadata_dir / f"{content_id}.json"
        if metadata_file.exists():
            print(f"Found metadata file: {metadata_file}")
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
                print(f"Loaded metadata: {metadata}")
                return {
                    "content": metadata.get('content', ''),
                    "metadata": metadata
                }
        print(f"Metadata file not found: {metadata_file}")
        return None

class MockContextDB:
    def __init__(self):
        self.vector_store = MockVectorStore()
        self.stored_contexts = {}
        
    async def store_context(self, task_id: str, context_type: str, source_id: str, 
                          metadata: dict, priority: int = 50) -> None:
        """Mock storing context."""
        if task_id not in self.stored_contexts:
            self.stored_contexts[task_id] = []
            
        # Store context with content from metadata
        context = {
            "type": context_type,
            "source_id": source_id,
            "metadata": metadata,
            "priority": priority,
            "content": metadata.get("content", "")
        }
        
        # If this is a vector context, try to get content from vector store
        if context_type == "vector" and metadata.get("filters"):
            try:
                items = await self.vector_store.get_filtered_items(
                    filters=metadata["filters"],
                    limit=1
                )
                if items:
                    context["content"] = items[0]["content"]
                    context["metadata"].update(items[0]["metadata"])
            except Exception as e:
                print(f"Error getting vector content: {str(e)}")
        
        self.stored_contexts[task_id].append(context)
        
    async def get_contexts(self, task_id: str, context_types: List[str] = None) -> List[Dict[str, Any]]:
        """Get stored contexts for a task."""
        contexts = self.stored_contexts.get(task_id, [])
        if context_types:
            contexts = [c for c in contexts if c["type"] in context_types]
        
        # For each context, get the actual content
        enriched_contexts = []
        for context in contexts:
            try:
                if context["type"] == "vector":
                    # Get content from vector store
                    if "filters" in context["metadata"]:
                        items = await self.vector_store.get_filtered_items(
                            filters=context["metadata"]["filters"],
                            limit=1
                        )
                        if items:
                            enriched_contexts.append({
                                **context,
                                "content": items[0]["content"],
                                "metadata": {
                                    **context["metadata"],
                                    **items[0]["metadata"]
                                }
                            })
                            continue
                    else:
                        content = await self.vector_store.get_content(context["source_id"])
                        if content:
                            enriched_contexts.append({
                                **context,
                                "content": content["content"],
                                "metadata": {
                                    **context["metadata"],
                                    **content["metadata"]
                                }
                            })
                            continue
                
                # For other types or if vector content not found, use stored content
                enriched_contexts.append(context)
            except Exception as e:
                print(f"Error getting context content: {str(e)}")
                # Still include the context even if there was an error
                enriched_contexts.append(context)
        
        return enriched_contexts

class MockKnowledgeBase:
    def __init__(self):
        self.entries = {}

    async def get_entry(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """Get knowledge base entry by ID."""
        # For test content, return directly
        if entry_id == "know1":
            return {
                "content": "Test knowledge content",
                "metadata": {
                    "domain": "test",
                    "tags": ["test"],
                    "created_at": datetime.now().isoformat()
                }
            }
            
        # Otherwise try to get from stored entries
        if entry_id in self.entries:
            return self.entries[entry_id]
        return None

class MockSystemContext:
    def __init__(self):
        self.contexts = {}

    def add_context(self, name: str, content: str, description: Optional[str] = None, 
                   tags: Optional[List[str]] = None, format: str = "text", 
                   category: str = "general") -> str:
        """Add a context entry."""
        context_id = str(uuid4())
        self.contexts[context_id] = {
            "content": content,
            "description": description,
            "tags": tags or [],
            "format": format,
            "category": category
        }
        return context_id

    def get_context(self, context_id: str) -> Optional[str]:
        """Get context content by ID."""
        if context_id in self.contexts:
            return self.contexts[context_id]["content"]
        return None

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

@pytest_asyncio.fixture
async def context_provider() -> ContextProvider:
    """Create a test context provider instance."""
    provider = ContextProvider()
    
    # Create mock persistence model
    mock_persistence = MagicMock()
    mock_persistence.tasks.read.return_value = type("Task", (), {
        "id": "test_task_123",
        "tasksmanager_id": "manager1"
    })
    
    # Set up mock context DB
    mock_context_db = MockContextDB()
    
    # Set up mock system context
    mock_system_context = MockSystemContext()
    provider.system_context = mock_system_context
    
    # Mock task context manager
    class MockTaskContext:
        def __init__(self, task_id: str):
            self.task_id = task_id
            self.contexts: List[ContextReference] = []
            self.use_context: bool = True
            self.inherit_manager_context: bool = True
            self.context_db = mock_context_db
            
        async def add_context(self, type: str, source_id: str, metadata: Dict, priority: int = 50) -> ContextReference:
            """Add a context reference to this task context."""
            # Store context in context DB
            await self.context_db.store_context(
                task_id=self.task_id,
                context_type=type,
                source_id=source_id,
                metadata=metadata,
                priority=priority
            )
            
            # Create and store reference
            context_ref = ContextReference(
                type=type,
                source_id=source_id,
                metadata=metadata or {},
                priority=priority
            )
            self.contexts.append(context_ref)
            return context_ref
            
        def update_context_config(self, use_context: Optional[bool] = None, inherit_manager_context: Optional[bool] = None) -> bool:
            """Update context configuration."""
            if use_context is not None:
                self.use_context = use_context
            if inherit_manager_context is not None:
                self.inherit_manager_context = inherit_manager_context
            return True
            
        async def get_contexts(self, context_types: List[str] = None) -> List[Dict[str, Any]]:
            """Get contexts for the task."""
            return await self.context_db.get_contexts(
                task_id=self.task_id,
                context_types=context_types
            )
    
    # Mock task context manager
    class MockTaskContextManager:
        def __init__(self):
            self.contexts = {}
            
        def get_task_context(self, task_id: str) -> MockTaskContext:
            if task_id not in self.contexts:
                self.contexts[task_id] = MockTaskContext(task_id)
            return self.contexts[task_id]
            
        def create_task_context(self, task_id: str) -> MockTaskContext:
            self.contexts[task_id] = MockTaskContext(task_id)
            return self.contexts[task_id]
    
    mock_task_context_manager = MockTaskContextManager()
    provider.task_context_manager = mock_task_context_manager
    
    # Inject mocks
    provider.persistence_model = mock_persistence
    provider.context_db = mock_context_db
    
    await provider.initialize()
    
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
    await manager_context.add_context(
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
    assert any(c["type"] == "system" and c["content"] == "Manager system context" for c in contexts), "Should inherit manager's system context"

    # Test with inheritance disabled
    task_context.update_context_config(inherit_manager_context=False)
    contexts = await context_provider.get_task_contexts(task_id)
    print(f"\nContexts with inheritance disabled: {contexts}")
    assert len(contexts) == 0, "Should not inherit when disabled"

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

    # Verify initial configuration
    assert task_context.use_context is True, "Context should be enabled by default"
    assert task_context.inherit_manager_context is True, "Manager context inheritance should be enabled by default"

    # Add system context entry
    system_context_id = context_provider.system_context.add_context(
        name="test_context",
        content="Test system context",
        description="Test context for message preparation"
    )

    # Add a system context reference to the task
    await task_context.add_context(
        type="system",
        source_id=system_context_id,
        priority=1,
        metadata={"content": "Test system context"}
    )

    # Store context in context DB
    await context_provider.context_db.store_context(
        task_id=task_id,
        context_type="system",
        source_id=system_context_id,
        metadata={"content": "Test system context"},
        priority=1
    )

    print("\n=== Debug Info ===")
    print(f"Task context: {task_context.__dict__ if task_context else None}")
    print(f"Stored contexts: {context_provider.context_db.stored_contexts}")
    print(f"Task contexts: {[c.__dict__ for c in task_context.contexts]}")
    print(f"System contexts: {context_provider.system_context.contexts}")

    # Test message preparation with context enabled
    messages = [Message(role="user", content="Test message")]
    prepared_messages = await context_provider.prepare_task_messages(
        task_id=task_id,
        messages=messages
    )

    print("\n=== Prepared Messages (Context Enabled) ===")
    for msg in prepared_messages:
        print(f"Role: {msg.role}")
        print(f"Content: {msg.content}")

    # Verify messages with context enabled
    assert len(prepared_messages) > len(messages), "Should have added context messages"
    assert any("Test system context" in msg.content for msg in prepared_messages), "Should include system context content"

    # Test message preparation with context disabled
    task_context.update_context_config(use_context=False)
    prepared_messages = await context_provider.prepare_task_messages(
        task_id=task_id,
        messages=messages
    )

    print("\n=== Prepared Messages (Context Disabled) ===")
    for msg in prepared_messages:
        print(f"Role: {msg.role}")
        print(f"Content: {msg.content}")

    # Verify messages with context disabled
    assert len(prepared_messages) == len(messages), "Should not add context messages when disabled"
    assert not any("Test system context" in msg.content for msg in prepared_messages), "Should not include system context content"

@pytest.mark.asyncio
async def test_context_priority_ordering(context_provider):
    """Test that contexts are properly ordered by priority."""
    task_id = "task1"
    task_context = context_provider.task_context_manager.create_task_context(task_id)

    # Add contexts with different priorities
    await task_context.add_context(
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

    await task_context.add_context(
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

    # Verify ordering by priority
    for i in range(len(contexts) - 1):
        assert contexts[i]["priority"] >= contexts[i + 1]["priority"], "Contexts should be ordered by priority (highest first)"

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
    await task_context.add_context(
        type="system",
        source_id="sys1",
        metadata={"content": "System context"}
    )

    await task_context.add_context(
        type="vector",
        source_id="vec1",
        metadata={"content": "Vector context"}
    )

    await task_context.add_context(
        type="knowledge",
        source_id="know1",
        metadata={"content": "Knowledge context"}
    )

    print("\n=== Debug Info ===")
    print(f"Task context: {task_context.__dict__ if task_context else None}")
    print(f"Stored contexts: {context_provider.context_db.stored_contexts}")
    print(f"Task contexts: {[c.__dict__ for c in task_context.contexts]}")

    # Get all contexts
    all_contexts = await context_provider.get_task_contexts("task1")
    print(f"\nAll contexts: {all_contexts}")
    assert len(all_contexts) == 3, "Should have all contexts"

    # Get only system contexts
    system_contexts = await context_provider.get_task_contexts("task1", context_types=["system"])
    print(f"\nSystem contexts: {system_contexts}")
    assert len(system_contexts) == 1, "Should have one system context"
    assert system_contexts[0]["type"] == "system", "Should be system type"

    # Get only vector contexts
    vector_contexts = await context_provider.get_task_contexts("task1", context_types=["vector"])
    print(f"\nVector contexts: {vector_contexts}")
    assert len(vector_contexts) == 1, "Should have one vector context"
    assert vector_contexts[0]["type"] == "vector", "Should be vector type"

    # Get multiple types
    mixed_contexts = await context_provider.get_task_contexts("task1", context_types=["system", "knowledge"])
    print(f"\nMixed contexts: {mixed_contexts}")
    assert len(mixed_contexts) == 2, "Should have two contexts"
    types = {c["type"] for c in mixed_contexts}
    assert types == {"system", "knowledge"}, "Should have correct types"

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
        "size": 1000,
        "file_id": mock_file_id  # Add file_id to metadata
    }

    print("\n=== Test Setup ===")
    print(f"Mock file ID: {mock_file_id}")
    print(f"Mock file metadata: {mock_file_metadata}")

    # Initialize ChromaDB collection
    vector_store = context_provider.context_db.vector_store
    collection = vector_store.client.get_or_create_collection(
        name=vector_store.config.collection_name,
        embedding_function=vector_store.embedding_function
    )

    # Add content directly to ChromaDB
    collection.add(
        documents=[mock_file_content],
        metadatas=[mock_file_metadata],
        ids=[mock_file_id]
    )

    # Create metadata directory and file
    metadata_dir = context_provider.context_db.vector_store.base_path / 'metadata'
    metadata_dir.mkdir(parents=True, exist_ok=True)

    print(f"Metadata directory: {metadata_dir}")

    metadata_file = metadata_dir / f"{mock_file_id}.json"
    print(f"Writing metadata to: {metadata_file}")
    with open(metadata_file, 'w') as f:
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

    print("\n=== Adding Context ===")
    print(f"Task ID: {task_id}")
    print(f"Context metadata: {metadata}")

    # Add context to task
    context_ref = await task_context.add_context(
        type="vector",
        source_id=str(uuid4()),
        metadata=metadata,
        priority=50
    )

    print("\n=== Debug Info ===")
    print(f"Context reference: {context_ref.__dict__ if context_ref else None}")
    print(f"Task context: {task_context.__dict__ if task_context else None}")
    print(f"Stored contexts: {task_context.context_db.stored_contexts}")
    print(f"Task contexts: {[c.__dict__ for c in task_context.contexts]}")

    # Test vector store directly
    print("\n=== Testing Vector Store ===")
    items = await task_context.context_db.vector_store.get_filtered_items(
        filters=metadata['filters'],
        limit=1
    )
    print(f"Direct vector store query result: {items}")

    # Verify context was added
    assert context_ref is not None, "Context reference should not be None"
    assert isinstance(context_ref, ContextReference), "Should return a ContextReference"
    assert context_ref.type == "vector", "Context type should be 'vector'"
    assert context_ref.priority == 50, "Priority should match"

    # Verify context was stored in task_context
    assert len(task_context.contexts) > 0, "Task context should have contexts"

    # Verify context was stored in context_db
    stored_contexts = await task_context.context_db.get_contexts(task_id)
    assert len(stored_contexts) > 0, "Context DB should have stored contexts"

    # Get contexts and verify
    contexts = await task_context.get_contexts()
    print(f"\n=== Retrieved Contexts ===")
    print(f"Contexts: {contexts}")
    assert len(contexts) > 0, "Should have at least one context"

    # Verify content was retrieved from vector store
    for context in contexts:
        assert context["type"] == "vector", "Context type should be vector"
        assert context["content"] == mock_file_content, "Content should match mock file"
        assert context["metadata"]["filename"] == mock_file_metadata["filename"], "Metadata should match"
