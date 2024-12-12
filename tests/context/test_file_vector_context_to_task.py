import pytest
import pytest_asyncio
from pathlib import Path
import io
from datetime import datetime
from unittest.mock import MagicMock, patch
from typing import List, Dict, Any, Optional
import json

from src.server.context.vector_store import VectorStore, VectorStoreConfig
from src.server.context.context_provider import ContextProvider, ContextReference
from src.server.models.task_context_model import TaskContext

# Sample text that's larger than default chunk size (1000 chars)
SAMPLE_TEXT = """
Chapter 1: The Beginning

In the world of artificial intelligence, there exists a fundamental question about consciousness and self-awareness. 
Can machines truly think? This question, first posed by Alan Turing in his seminal paper "Computing Machinery and Intelligence," 
has sparked decades of philosophical and scientific debate.

The Turing test, proposed as a measure of machine intelligence, suggests that if a computer can engage in conversation 
in a way that's indistinguishable from a human, it can be considered intelligent. However, critics argue that this is a 
superficial measure that doesn't truly capture the essence of consciousness or understanding.

Modern AI systems, particularly large language models, have demonstrated remarkable capabilities in natural language processing, 
pattern recognition, and problem-solving. Yet they still face significant challenges in areas like common sense reasoning, 
causal understanding, and genuine comprehension of context.

Chapter 2: The Evolution

As we move forward in the field of AI, new architectures and approaches continue to emerge. Deep learning, reinforcement 
learning, and neural networks have revolutionized what's possible in artificial intelligence. These advances have led to 
breakthroughs in areas like computer vision, speech recognition, and natural language processing.

The development of transformer models marked a significant milestone in AI history. These models, with their attention 
mechanisms and parallel processing capabilities, have set new benchmarks in language understanding and generation.
"""

@pytest.fixture
def vector_store() -> VectorStore:
    """Create a test vector store instance."""
    config = VectorStoreConfig(
        chunk_size=200,
        chunk_overlap=50,
        persist_directory="test_vector_store"
    )
    store = VectorStore(config=config, base_path="test_persistent_state/vector_store")
    yield store
    # Cleanup after tests
    for idx in store.indices.values():
        try:
            store.client.delete_collection(idx.name)
        except:
            pass

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
    
    # Set up mock context DB with strict checking
    mock_context_db = MagicMock(spec=['store_context', 'get_contexts', 'vector_store'])
    
    # Track all method calls
    stored_contexts: Dict[str, List[Dict[str, Any]]] = {}
    
    # Create the store_context mock with tracking
    store_context_mock = MagicMock()
    async def mock_store_context(task_id: str, context_type: str, source_id: str, 
                               metadata: dict, priority: int = 50) -> None:
        """Mock storing context."""
        store_context_mock(task_id, context_type, source_id, metadata, priority)
        
        if task_id not in stored_contexts:
            stored_contexts[task_id] = []
            
        stored_contexts[task_id].append({
            "type": context_type,
            "source_id": source_id,
            "metadata": metadata,
            "priority": priority
        })
    
    # Create the get_contexts mock with tracking
    get_contexts_mock = MagicMock()
    async def mock_get_contexts(task_id: str, context_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get stored contexts for a task."""
        get_contexts_mock(task_id, context_types)
        
        contexts = stored_contexts.get(task_id, [])
        if context_types:
            contexts = [c for c in contexts if c["type"] in context_types]
        return contexts
    
    # Set up the mock methods with tracking
    mock_context_db.store_context = mock_store_context
    mock_context_db.get_contexts = mock_get_contexts
    mock_context_db.stored_contexts = stored_contexts
    
    # Add call tracking
    mock_context_db.store_context.mock = store_context_mock
    mock_context_db.get_contexts.mock = get_contexts_mock
    
    # Set up vector store
    mock_context_db.vector_store = VectorStore(
        config=VectorStoreConfig(persist_directory="test_vector_store"),
        base_path="test_persistent_state/vector_store"
    )
    
    # Create a mock task context class
    class MockTaskContext:
        def __init__(self, task_id: str):
            self.task_id = task_id
            self.contexts: List[ContextReference] = []
            self.use_context: bool = True
            self.inherit_manager_context: bool = True
            
        def add_context(self, type: str, source_id: str, metadata: Dict, priority: int = 50) -> ContextReference:
            """Add a context reference to this task context."""
            context_ref = ContextReference(
                type=type,
                source_id=source_id,
                metadata=metadata or {},
                priority=priority
            )
            self.contexts.append(context_ref)
            return context_ref
    
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
    
    # Create and inject the mock task context manager
    mock_task_context_manager = MockTaskContextManager()
    provider.task_context_manager = mock_task_context_manager
    
    # Inject mocks
    provider.persistence_model = mock_persistence
    provider.context_db = mock_context_db
    
    await provider.initialize()
    
    return provider

@pytest.fixture
def mock_task() -> Dict[str, Any]:
    """Create a mock task for testing."""
    return {
        "id": "test_task_123",
        "name": "Test Task",
        "description": "A test task for vector context",
        "status": "pending"
    }

@pytest.mark.asyncio
async def test_vector_store_file_processing(vector_store):
    """Test processing a file into vector store chunks."""
    # Create a mock file
    file_content = SAMPLE_TEXT.encode('utf-8')
    mock_file = io.BytesIO(file_content)
    mock_file.name = "test_document.txt"
    
    # Create an index
    index_name = vector_store.create_index("test_index", "Test index for unit testing")
    
    # Add file to index
    metadata = {
        "original_name": mock_file.name,
        "file_type": "text/plain",
        "size": len(file_content),
        "added_at": datetime.now().isoformat()
    }
    
    chunk_ids = await vector_store.add_file_to_index(
        index_name=index_name,
        file_path_or_obj=mock_file,
        metadata=metadata
    )
    
    # Verify chunks were created
    assert len(chunk_ids) > 1, "File should be split into multiple chunks"
    
    # Get index contents
    contents = await vector_store.get_index_contents(index_name)
    assert len(contents) == len(chunk_ids), "All chunks should be retrievable"
    
    # Verify metadata
    for content in contents:
        assert content.get("metadata", {}).get("original_name") == mock_file.name
        assert "chunk_index" in content.get("metadata", {}), "Each chunk should have a chunk_index"
        assert "total_chunks" in content.get("metadata", {}), "Each chunk should have total_chunks count"
        assert content.get("metadata", {}).get("total_chunks") == len(chunk_ids)
        assert isinstance(content.get("metadata", {}).get("chunk_index"), int), "chunk_index should be an integer"
        assert 0 <= content.get("metadata", {}).get("chunk_index") < len(chunk_ids), "chunk_index should be within bounds"

@pytest.mark.asyncio
async def test_vector_context_in_task(vector_store: VectorStore, 
                                    context_provider: ContextProvider, 
                                    mock_task: Dict[str, Any]):
    """Test adding vector context to a task and retrieving it."""
    # Create test file and index
    file_content = SAMPLE_TEXT.encode('utf-8')
    mock_file = io.BytesIO(file_content)
    mock_file.name = "test_document.txt"
    
    index_name = vector_store.create_index("task_test_index", "Test index for task context")
    
    # Add file to index
    chunk_ids = await vector_store.add_file_to_index(
        index_name=index_name,
        file_path_or_obj=mock_file,
        metadata={
            "original_name": mock_file.name,
            "file_type": "text/plain",
            "size": len(file_content),
            "added_at": datetime.now().isoformat(),
            "task_id": mock_task["id"]
        }
    )
    
    # Breakpoint 1: Verify chunk IDs were created
    print("\n=== Breakpoint 1 ===")
    print(f"Chunk IDs created: {chunk_ids}")
    print(f"Number of chunks: {len(chunk_ids)}")
    
    # Add context to task
    context_metadata = {
        "index_name": index_name,
        "chunk_ids": chunk_ids,
        "filters": {
            "file_ids": chunk_ids
        }
    }
    
    # Breakpoint 2: Before storing context
    print("\n=== Breakpoint 2 ===")
    print(f"Task ID: {mock_task['id']}")
    print(f"Context metadata: {context_metadata}")
    
    context_ref = await context_provider.add_context_to_task(
        task_id=mock_task["id"],
        type="vector",
        source_id=f"ctx_{chunk_ids[0]}",
        metadata=context_metadata,
        priority=50
    )
    
    # Breakpoint 3: After storing context
    print("\n=== Breakpoint 3 ===")
    print(f"Context reference: {context_ref.__dict__ if context_ref else None}")
    print(f"Stored contexts: {context_provider.context_db.stored_contexts}")
    print(f"store_context called: {context_provider.context_db.store_context.mock.called}")
    print(f"store_context call args: {context_provider.context_db.store_context.mock.call_args_list}")
    
    # After storing context
    print("\n=== Method Calls ===")
    print(f"Store context calls: {context_provider.context_db.store_context.mock.call_args_list}")
    print(f"Get contexts calls: {context_provider.context_db.get_contexts.mock.call_args_list}")
    
    # Breakpoint 3a: Before context retrieval
    print("\n=== Breakpoint 3a ===")
    print(f"About to retrieve contexts for task: {mock_task['id']}")
    print(f"Context provider state:")
    print(f"- Persistence model: {context_provider.persistence_model}")
    print(f"- Context DB: {context_provider.context_db}")
    
    # Retrieve contexts
    task_contexts = await context_provider.get_task_contexts(
        task_id=mock_task["id"],
        context_types=["vector"]
    )
    
    # Breakpoint 3b: Immediately after get_task_contexts
    print("\n=== Breakpoint 3b ===")
    print(f"Raw task_contexts result: {task_contexts}")
    print(f"Context provider internal state:")
    print(f"- Task contexts manager: {context_provider.task_context_manager}")
    print(f"- Current task contexts: {context_provider.task_context_manager._task_contexts if hasattr(context_provider.task_context_manager, '_task_contexts') else 'Not available'}")
    
    # Breakpoint 4: After retrieving contexts
    print("\n=== Breakpoint 4 ===")
    print(f"Retrieved contexts: {task_contexts}")
    print(f"Task ID used: {mock_task['id']}")
    print(f"Context types requested: ['vector']")
    print(f"All stored contexts: {context_provider.context_db.stored_contexts}")
    
    # Verify context was added
    assert len(task_contexts) > 0, "Vector context should be added to task"
    vector_context = task_contexts[0]
    assert vector_context.get("type") == "vector", f"Expected type 'vector', got {vector_context.get('type')}"
    assert vector_context.get("metadata", {}).get("index_name") == index_name, \
        f"Expected index_name '{index_name}', got {vector_context.get('metadata', {}).get('index_name')}"
    assert len(vector_context.get("metadata", {}).get("chunk_ids", [])) == len(chunk_ids), \
        f"Expected {len(chunk_ids)} chunk IDs, got {len(vector_context.get('metadata', {}).get('chunk_ids', []))}"

@pytest.mark.asyncio
async def test_vector_store_cleanup(vector_store):
    """Test cleanup of vector store indices."""
    # Create test indices
    index1 = vector_store.create_index("test_index1", "Test index 1")
    index2 = vector_store.create_index("test_index2", "Test index 2")
    
    # Verify indices were created
    indices = await vector_store.list_indices()
    assert len(indices) == 2, "Should have created 2 test indices"
    
    # Delete indices
    for idx in indices:
        await vector_store.delete_index(idx["name"])
    
    # Verify cleanup
    indices = await vector_store.list_indices()
    assert len(indices) == 0, "All test indices should be deleted"

@pytest.mark.asyncio
async def test_single_context_add_and_retrieve(context_provider: ContextProvider, mock_task: Dict[str, Any]):
    """Test adding and retrieving a single context chunk."""
    # Create a simple context
    test_context = {
        "task_id": mock_task["id"],
        "type": "vector",
        "source_id": "test_chunk_1",
        "metadata": {
            "index_name": "test_index",
            "chunk_ids": ["test_chunk_1"],
            "content": "This is a test chunk",
            "filters": {
                "file_ids": ["test_chunk_1"]
            }
        },
        "priority": 50
    }
    
    print("\n=== Adding Single Context ===")
    print(f"Test context to add: {json.dumps(test_context, indent=2)}")
    
    # Add context to task
    context_ref = await context_provider.add_context_to_task(
        task_id=test_context["task_id"],
        type=test_context["type"],
        source_id=test_context["source_id"],
        metadata=test_context["metadata"],
        priority=test_context["priority"]
    )
    
    print("\n=== Context Addition Results ===")
    print(f"Context reference: {context_ref.__dict__ if context_ref else None}")
    print(f"Stored contexts: {context_provider.context_db.stored_contexts}")
    
    # Verify context was stored
    assert context_ref is not None, "Context reference should not be None"
    assert isinstance(context_ref, ContextReference), "Should return a ContextReference"
    assert context_ref.type == "vector", "Context type should be 'vector'"
    assert context_ref.source_id == "test_chunk_1", "Source ID should match"
    assert context_ref.priority == 50, "Priority should match"
    
    # Get contexts and verify
    contexts = await context_provider.get_task_contexts(
        task_id=mock_task["id"],
        context_types=["vector"]
    )
    
    print(f"\nRetrieved contexts: {json.dumps(contexts, default=str, indent=2)}")
    
    # Verify context retrieval
    assert len(contexts) == 1, "Should retrieve exactly one context"
    retrieved_context = contexts[0]
    assert retrieved_context.get("type") == "vector", "Retrieved context should be vector type"
    assert retrieved_context.get("source_id") == "test_chunk_1", "Source ID should match"
    assert retrieved_context.get("metadata", {}).get("index_name") == "test_index", "Index name should match"
    assert len(retrieved_context.get("metadata", {}).get("chunk_ids", [])) == 1, "Should have one chunk ID"
    assert retrieved_context.get("metadata", {}).get("content") == "This is a test chunk", "Content should match"

class MockContextDB:
    def __init__(self):
        self.vector_store = MockVectorStore()
        self.stored_contexts = {}
        
    async def store_context(self, task_id: str, context_type: str, source_id: str, 
                          metadata: dict, priority: int = 50) -> None:
        """Mock storing context."""
        if task_id not in self.stored_contexts:
            self.stored_contexts[task_id] = []
            
        # Store as a dictionary instead of creating a TaskContext
        self.stored_contexts[task_id].append({
            "type": context_type,
            "source_id": source_id,
            "metadata": metadata,
            "priority": priority
        })
        
    async def get_contexts(self, task_id: str, context_types: List[str] = None) -> List[Dict[str, Any]]:
        """Get stored contexts for a task."""
        contexts = self.stored_contexts.get(task_id, [])
        if context_types:
            contexts = [c for c in contexts if c["type"] in context_types]
        return contexts
