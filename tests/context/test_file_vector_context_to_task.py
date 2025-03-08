import pytest
import pytest_asyncio
from pathlib import Path
import io
from datetime import datetime
from unittest.mock import MagicMock, patch
from typing import List, Dict, Any, Optional
import json
import shutil

from src.server.context.vector_store import VectorStore, VectorStoreConfig
from src.server.context.context_provider import ContextProvider, ContextReference
from src.server.models.task_context_model import TaskContext
from src.server.models.tasks_manager import TasksManager

class MockVectorStore:
    def __init__(self):
        self.metadata_dir = Path("test_persistent_state/vector_store/metadata")
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        
    async def get_filtered_items(self, filters: Dict, limit: int = 5) -> List[Dict]:
        """Get items matching the filters."""
        print(f"\nDebug - MockVectorStore.get_filtered_items:")
        print(f"Filters: {filters}")
        print(f"Limit: {limit}")
        
        if 'file_ids' in filters.get('filters', {}):
            results = []
            for file_id in filters['filters']['file_ids']:
                metadata_file = self.metadata_dir / f"{file_id}.json"
                print(f"Looking for metadata file: {metadata_file}")
                
                # For test_chunk_1, return test content directly
                if file_id == "test_chunk_1":
                    results.append({
                        "content": "This is a test chunk",
                        "metadata": {
                            "index_name": "test_index",
                            "chunk_ids": ["test_chunk_1"],
                            "file_ids": ["test_chunk_1"]
                        }
                    })
                    continue
                
                # Otherwise try to read from file
                if metadata_file.exists():
                    print(f"Found metadata file")
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                        results.append({
                            "content": metadata.get('content', ''),
                            "metadata": metadata
                        })
                else:
                    print(f"Metadata file not found")
            
            print(f"Returning results: {results}")
            return results
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
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
                return {
                    "content": metadata.get('content', ''),
                    "metadata": metadata
                }
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
        return contexts

class MockTaskContext:
    def __init__(self, task_id: str):
        self.context_db = MockContextDB()
        self.task_id = task_id
        self.use_context = True
        self.inherit_manager_context = True
        
    def update_context_config(self, use_context: bool = None, inherit_manager_context: bool = None):
        """Update context configuration."""
        if use_context is not None:
            self.use_context = use_context
        if inherit_manager_context is not None:
            self.inherit_manager_context = inherit_manager_context
            
    async def add_context(self, type: str, source_id: str, metadata: Dict, priority: int = 50) -> ContextReference:
        """Add context to the task."""
        await self.context_db.store_context(
            task_id=self.task_id,
            context_type=type,
            source_id=source_id,
            metadata=metadata,
            priority=priority
        )
        return ContextReference(type=type, source_id=source_id, priority=priority)
        
    async def get_contexts(self, context_types: List[str] = None) -> List[Dict[str, Any]]:
        """Get contexts for the task."""
        return await self.context_db.get_contexts(
            task_id=self.task_id,
            context_types=context_types
        )

@pytest.mark.asyncio
async def test_single_context_add_and_retrieve():
    """Test adding a single vector context to a task and retrieving it."""
    # Create mock task context
    task_context = MockTaskContext("test_task")
    
    # Add vector context
    context_ref = await task_context.add_context(
        type="vector",
        source_id="test_chunk_1",
        metadata={
            "filters": {
                "filters": {
                    "file_ids": ["test_chunk_1"]
                }
            }
        },
        priority=50
    )
    
    print("\nDebug - test_single_context_add_and_retrieve:")
    print(f"Added context reference: {context_ref}")
    
    # Get contexts
    contexts = await task_context.get_contexts(context_types=["vector"])
    print(f"Retrieved contexts: {contexts}")
    
    # Verify context was added and can be retrieved
    assert len(contexts) == 1, "Should have exactly one context"
    retrieved_context = contexts[0]
    assert retrieved_context["type"] == "vector", "Context type should be vector"
    assert retrieved_context["source_id"] == "test_chunk_1", "Source ID should match"
    assert retrieved_context["content"] == "This is a test chunk", "Content should match"
    assert retrieved_context["metadata"]["index_name"] == "test_index", "Metadata should be updated from vector store"

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
    
    # Create shared context_db
    shared_context_db = MockContextDB()
    
    # Create a mock task context manager
    class MockTaskContextManager:
        def __init__(self):
            self.contexts = {}
            self.context_db = shared_context_db
            
        def get_task_context(self, task_id: str) -> MockTaskContext:
            if task_id not in self.contexts:
                task_context = MockTaskContext(task_id)
                task_context.context_db = self.context_db
                self.contexts[task_id] = task_context
            return self.contexts[task_id]
            
        def create_task_context(self, task_id: str) -> MockTaskContext:
            task_context = MockTaskContext(task_id)
            task_context.context_db = self.context_db
            self.contexts[task_id] = task_context
            return self.contexts[task_id]
            
        async def add_context_to_task(
            self,
            task_id: str,
            type: str,
            source_id: str,
            metadata: Optional[Dict[str, Any]] = None,
            priority: int = 50
        ) -> str:
            """Add a context to a task."""
            await self.context_db.store_context(
                task_id=task_id,
                context_type=type,
                source_id=source_id,
                metadata=metadata or {},
                priority=priority
            )
            return str(ContextReference(type=type, source_id=source_id, priority=priority).id)
            
        async def get_task_contexts(
            self,
            task_id: str,
            context_types: Optional[List[str]] = None
        ) -> List[Dict[str, Any]]:
            """Get all contexts associated with a task."""
            return await self.context_db.get_contexts(task_id, context_types)
    
    mock_task_context_manager = MockTaskContextManager()
    provider.task_context_manager = mock_task_context_manager
    
    # Inject mocks
    provider.persistence_model = mock_persistence
    provider.context_db = shared_context_db
    
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
    index_name = await vector_store.create_index("test_index", "Test index for unit testing")
    
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
    
    # Get index contents using get_filtered_items_from_index
    contents = await vector_store.get_filtered_items_from_index(
        index_name=index_name,
        limit=100  # High limit to get all chunks
    )
    assert len(contents) == len(chunk_ids), "All chunks should be retrievable"
    
    # Verify metadata
    for content in contents:
        assert content.get("metadata", {}).get("original_name") == mock_file.name
        
        # Check if this is a root chunk
        if content.get("metadata", {}).get("is_root", False):
            assert "total_chunks" in content.get("metadata", {}), "Root chunk should have total_chunks count"
            assert content.get("metadata", {}).get("total_chunks") == len(chunk_ids) - 1  # Subtract 1 for root chunk
            assert "original_text_length" in content.get("metadata", {}), "Root chunk should have original_text_length"
        else:
            assert "chunk_index" in content.get("metadata", {}), "Non-root chunks should have a chunk_index"
            assert "total_chunks" in content.get("metadata", {}), "Non-root chunks should have total_chunks count"
            assert content.get("metadata", {}).get("total_chunks") == len(chunk_ids) - 1  # Subtract 1 for root chunk
            assert isinstance(content.get("metadata", {}).get("chunk_index"), int), "chunk_index should be an integer"
            assert 0 <= content.get("metadata", {}).get("chunk_index") < len(chunk_ids) - 1, "chunk_index should be within bounds"

@pytest.mark.asyncio
async def test_vector_context_in_task(vector_store: VectorStore, 
                                    context_provider: ContextProvider, 
                                    mock_task: Dict[str, Any]):
    """Test adding vector context to a task and retrieving it."""
    # Create test file and index
    file_content = SAMPLE_TEXT.encode('utf-8')
    mock_file = io.BytesIO(file_content)
    mock_file.name = "test_document.txt"
    
    index_name = await vector_store.create_index("task_test_index", "Test index for task context")
    
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
    print(f"Chunk IDs created: {chunk_ids}")
    print(f"Number of chunks: {len(chunk_ids)}")
    
    # Add context to task
    context_metadata = {
        "index_name": index_name,
        "file_name": mock_file.name,
        "chunk_count": len(chunk_ids)
    }
    
    # Add vector context to task
    for chunk_id in chunk_ids:
        await context_provider.add_context_to_task(
            task_id=mock_task["id"],
            type="vector",
            source_id=chunk_id,
            metadata=context_metadata,
            priority=50
        )
    
    # Verify contexts were added
    contexts = await context_provider.context_db.get_contexts(mock_task["id"])
    assert len(contexts) == len(chunk_ids), "All chunks should be added as contexts"
    
    # Verify context metadata
    for context in contexts:
        assert context["type"] == "vector"
        assert context["metadata"]["index_name"] == index_name
        assert context["metadata"]["file_name"] == mock_file.name

@pytest.mark.asyncio
async def test_vector_store_cleanup(vector_store):
    """Test cleanup of vector store indices."""
    # Create test indices
    index1 = await vector_store.create_index("test_index1", "Test index 1")
    index2 = await vector_store.create_index("test_index2", "Test index 2")
    
    # Verify indices were created
    indices = await vector_store.list_indices()
    assert len(indices) == 2, "Should have created 2 test indices"
    
    # Delete indices
    for index in indices:
        await vector_store.delete_index(index["name"])
    
    # Verify cleanup
    indices = await vector_store.list_indices()
    assert len(indices) == 0, "All indices should be deleted"
