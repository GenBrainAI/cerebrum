import os
import pytest
import asyncio
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional
import tempfile
from unittest.mock import MagicMock
import chromadb
import io
import uuid

import pytest_asyncio

from src.server.context.vector_store import VectorStore, VectorStoreConfig
from src.server.context.context_database import ContextDatabase
from src.server.context.context_provider import ContextProvider
from src.server.models.task import Task
from src.server.persistence.in_memory_persistence import InMemoryPersistenceModel


@pytest.fixture
def test_dir():
    """Create a temporary directory for testing."""
    test_dir = Path("test_vector_store")
    test_dir.mkdir(exist_ok=True)
    yield test_dir
    # Clean up after tests
    shutil.rmtree(test_dir, ignore_errors=True)


@pytest_asyncio.fixture
async def vector_store(test_dir):
    """Create a vector store for testing."""
    # Use an in-memory client to avoid read-only database issues
    
    # Create a client with in-memory storage
    client = chromadb.Client()
    
    # Create a vector store with the in-memory client
    vs = VectorStore(base_path=str(test_dir))
    vs.client = client  # Replace the client with our in-memory one
    
    # Initialize the indices dictionary
    vs.indices = {}
    
    yield vs
    
    # Clean up - client.reset() is not awaitable
    try:
        vs.client.reset()
    except Exception as e:
        print(f"Warning: Error during cleanup: {str(e)}")
        # Try alternative cleanup
        for collection_name in list(vs.indices.keys()):
            try:
                vs.client.delete_collection(collection_name)
            except Exception:
                pass


@pytest_asyncio.fixture
async def context_db(vector_store):
    """Create a context database for testing with in-memory client."""
    # Create a temporary directory for testing
    temp_dir = tempfile.mkdtemp()
    print(f"Created temporary directory for context_db: {temp_dir}")

    try:
        # Create an in-memory client for the context database with a unique identifier
        # to avoid conflicts with other tests
        unique_id = f"ephemeral_{uuid.uuid4().hex}"
        client = chromadb.EphemeralClient(
            settings=chromadb.Settings(
                anonymized_telemetry=False,
                allow_reset=True
            ),
            tenant=unique_id,  # Use a unique tenant to avoid conflicts
            database=unique_id  # Use a unique database to avoid conflicts
        )
        
        # Create a context database with the in-memory client
        db = ContextDatabase(temp_dir)
        db.vector_store = vector_store
        db.vector_store.client = client  # Replace the client with our in-memory client
        
        yield db
        
        # Clean up after the test
        try:
            # Reset the client and delete collections if necessary
            client.reset()
        except Exception as e:
            print(f"Error cleaning up client: {e}")
        
        # Clean up the temporary directory
        shutil.rmtree(temp_dir)
        print(f"Cleaned up temporary directory: {temp_dir}")
    except Exception as e:
        # Clean up the temporary directory in case of an error
        shutil.rmtree(temp_dir)
        print(f"Cleaned up temporary directory due to error: {temp_dir}")
        raise e


@pytest.mark.asyncio
async def test_vector_store_index_creation(vector_store):
    """Test creating and listing indices in the vector store."""
    # Create a test index
    index_name = "test_index"
    index_id = await vector_store.create_index(index_name, description="Test index")
    
    # Verify the index was created with the vs_ prefix
    assert index_id == "vs_test_index", "Index ID should have vs_ prefix"
    
    # List indices and verify the test index is in the list
    indices = await vector_store.list_indices()
    assert len(indices) >= 1, "Should have at least one index"
    
    # Find the test index in the list
    test_index = next((idx for idx in indices if idx["name"] == index_id), None)
    assert test_index is not None, "Test index should be in the list"
    assert test_index["description"] == "Test index", "Index description should match"


@pytest.mark.asyncio
async def test_add_file_to_index(vector_store):
    """Test adding a file to an index."""
    # Create a test index
    index_name = "test_add_file"
    index_id = await vector_store.create_index(index_name, description="Test index for adding files")
    
    # Create a test file
    test_content = "This is a test file for vector store indexing."
    
    # Add the file to the index
    file_ids = await vector_store.add_file_to_index(
        index_name=index_id,
        file_path_or_obj=io.StringIO(test_content),
        metadata={"test": "metadata"}
    )
    
    # Verify file IDs were returned
    assert len(file_ids) > 0, "Should return at least one file ID"
    
    # Get the collection and verify the document was added
    collection = vector_store.client.get_collection(index_id)
    count = collection.count()
    assert count > 0, "Collection should have at least one document"


@pytest.mark.asyncio
async def test_search_in_index(vector_store):
    """Test searching in an index."""
    # Create a test index
    index_name = "test_search"
    index_id = await vector_store.create_index(index_name, description="Test index for searching")
    
    # Add test documents to the index
    test_docs = [
        "This is a document about Python programming.",
        "This document discusses machine learning concepts.",
        "This is about natural language processing."
    ]
    
    # Add each document to the index
    for i, doc in enumerate(test_docs):
        await vector_store.add_file_to_index(
            index_name=index_id,
            file_path_or_obj=io.StringIO(doc),
            metadata={"doc_id": f"doc{i}"}
        )
    
    # Search for Python-related documents
    results = await vector_store.search_in_index(
        index_name=index_id,
        embedding=vector_store._safe_embed(["Python programming"])[0],
        limit=10
    )
    
    # Verify results were returned
    assert len(results) > 0, "Should return search results"
    
    # Verify the first result is about Python (should be most relevant)
    assert "Python" in results[0]["content"], "First result should be about Python"


@pytest.mark.skip(reason="This test is causing conflicts with ChromaDB instances")
@pytest.mark.asyncio
async def test_context_db_search(context_db):
    """Test searching for context using the context database."""
    # Create a test index
    index_name = "test_context_search"
    index_id = await context_db.vector_store.create_index(index_name, description="Test index for context search")
    
    # Add test documents to the index
    test_docs = [
        "Python is a programming language with clean syntax.",
        "Machine learning is a subset of artificial intelligence.",
        "Natural language processing helps computers understand human language."
    ]
    
    # Add each document to the index
    for i, doc in enumerate(test_docs):
        await context_db.vector_store.add_file_to_index(
            index_name=index_id,
            file_path_or_obj=io.StringIO(doc),
            metadata={"doc_id": f"doc{i}"}
        )
    
    # Search for Python-related context
    results = await context_db.search_context(
        query="Python programming",
        index_name=index_id,
        limit=10
    )
    
    # Verify results were returned
    assert len(results) > 0, "Should return context search results"
    
    # Verify the first result is about Python (should be most relevant)
    assert "Python" in results[0]["content"], "First result should be about Python"
    
    # Verify metadata is included in results
    assert "metadata" in results[0], "Results should include metadata"
    assert "doc_id" in results[0]["metadata"], "Metadata should include doc_id"


@pytest.mark.asyncio
async def test_with_real_brain_file(vector_store):
    """Test with a real brain file content."""
    # Create a test index
    index_name = "test_brain_file"
    index_id = await vector_store.create_index(index_name, description="Test index for brain file")
    
    # Create a test file with brain-like content
    brain_content = """
    # Brain File
    
    ## Introduction
    This is a test brain file for vector store indexing.
    
    ## Key Concepts
    - Vector embeddings
    - Semantic search
    - Context retrieval
    
    ## Code Example
    ```python
    def search_context(query, index_name):
        # Embed the query
        embedding = embed_text(query)
        
        # Search the index
        results = search_in_index(index_name, embedding)
        
        return results
    ```
    
    ## Conclusion
    Vector stores are powerful tools for semantic search.
    """
    
    # Add the file to the index
    file_ids = await vector_store.add_file_to_index(
        index_name=index_id,
        file_path_or_obj=io.StringIO(brain_content),
        metadata={"type": "brain", "topic": "vector_search"}
    )
    
    # Verify file IDs were returned
    assert len(file_ids) > 0, "Should return at least one file ID"
    
    # Search for vector-related content
    results = await vector_store.search_in_index(
        index_name=index_id,
        embedding=vector_store._safe_embed(["vector embeddings for search"])[0],
        limit=10
    )
    
    # Verify results were returned
    assert len(results) > 0, "Should return search results"
    
    # Verify the content includes relevant information
    result_content = results[0]["content"]
    assert "vector" in result_content.lower(), "Result should contain 'vector'"
    assert "search" in result_content.lower(), "Result should contain 'search'"


@pytest.mark.skip(reason="Skipping due to ChromaDB client issues")
@pytest.mark.asyncio
async def test_context_provider_integration():
    """Test integration with context provider."""
    # Create a temporary directory for testing
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Create a vector store with in-memory client
        vs = VectorStore(base_path=temp_dir)
        client = chromadb.EphemeralClient()
        vs.client = client
        
        # Create a context database
        db = ContextDatabase(temp_dir)
        db.vector_store = vs
        
        # Create a context provider
        provider = ContextProvider()
        provider.context_db = db
        
        # Create a mock persistence model
        persistence_model = MagicMock()
        provider.persistence_model = persistence_model
        
        # Mock the task
        task = MagicMock(spec=Task)
        task.id = "task1"
        task.use_context = True
        task.contexts = []
        
        # Mock the persistence model's tasks collection
        class MockTasks:
            def read(self, task_id):
                if task_id == "task1":
                    return task
                return None
        
        persistence_model.tasks = MockTasks()
        
        # Create a test index
        index_name = "test_provider"
        index_id = await vs.create_index(index_name, description="Test index for provider")
        
        # Add test documents to the index
        test_docs = [
            "Python is a versatile programming language used in many fields.",
            "Machine learning models can be trained using Python libraries like TensorFlow and PyTorch.",
            "Natural language processing is used for tasks like sentiment analysis and text classification."
        ]
        
        # Add each document to the index
        for i, doc in enumerate(test_docs):
            await vs.add_file_to_index(
                index_name=index_id,
                file_path_or_obj=io.StringIO(doc),
                metadata={"doc_id": f"doc{i}"}
            )
        
        # Get contexts for a Python-related query
        contexts = await provider.get_contexts(
            query="How to use Python for machine learning?",
            task_id="task1"
        )
        
        # Verify contexts were returned
        assert len(contexts) > 0, "Should return contexts"
        
        # Verify the contexts include relevant information
        python_contexts = [c for c in contexts if "Python" in c["content"]]
        assert len(python_contexts) > 0, "Should include Python-related contexts"
        
    finally:
        # Clean up
        shutil.rmtree(temp_dir)


@pytest.mark.asyncio
async def test_index_name_prefix_handling(vector_store):
    """Test that index names are handled correctly with and without the vs_ prefix."""
    # Test the helper methods
    print("\n🔍 TEST: Testing index name helper methods")
    
    # Test get_full_index_name
    assert vector_store.get_full_index_name("test") == "vs_test"
    assert vector_store.get_full_index_name("vs_test") == "vs_test"
    assert vector_store.get_full_index_name("") == ""
    assert vector_store.get_full_index_name(None) == None
    print("✅ TEST: get_full_index_name works correctly")
    
    # Test get_display_name
    assert vector_store.get_display_name("vs_test") == "test"
    assert vector_store.get_display_name("test") == "test"
    assert vector_store.get_display_name("") == ""
    assert vector_store.get_display_name(None) == None
    print("✅ TEST: get_display_name works correctly")
    
    # Create an index with a name that already has the vs_ prefix
    prefixed_name = "vs_prefixed_test"
    prefixed_id = await vector_store.create_index(prefixed_name, description="Test index with prefix")
    print(f"🔧 TEST: Created index with prefixed name: {prefixed_name}, got ID: {prefixed_id}")
    assert prefixed_id == prefixed_name, "Index ID should match the prefixed name"
    
    # Create an index with a name that doesn't have the vs_ prefix
    unprefixed_name = "unprefixed_test"
    unprefixed_id = await vector_store.create_index(unprefixed_name, description="Test index without prefix")
    print(f"🔧 TEST: Created index with unprefixed name: {unprefixed_name}, got ID: {unprefixed_id}")
    assert unprefixed_id == f"vs_{unprefixed_name}", "Index ID should have vs_ prefix added"
    
    # Verify both indices exist in the vector store
    indices = await vector_store.list_indices()
    index_names = [idx["name"] for idx in indices]
    print(f"🔧 TEST: Listed indices: {index_names}")
    assert prefixed_id in index_names, "Prefixed index should be in the list"
    assert unprefixed_id in index_names, "Unprefixed index with added prefix should be in the list"
    
    # Add a test file to both indices
    test_content = "This is a test file for index name prefix handling."
    
    # Add to prefixed index
    prefixed_file_ids = await vector_store.add_file_to_index(
        index_name=prefixed_id,
        file_path_or_obj=io.StringIO(test_content),
        metadata={"test": "prefixed"}
    )
    print(f"🔧 TEST: Added file to prefixed index, got IDs: {prefixed_file_ids}")
    
    # Add to unprefixed index
    unprefixed_file_ids = await vector_store.add_file_to_index(
        index_name=unprefixed_id,
        file_path_or_obj=io.StringIO(test_content),
        metadata={"test": "unprefixed"}
    )
    print(f"🔧 TEST: Added file to unprefixed index, got IDs: {unprefixed_file_ids}")
    
    # Create a context database for testing search
    db = ContextDatabase()
    db.vector_store = vector_store
    
    # Generate a test embedding
    embedding = await db._safe_embed(["test"])
    assert embedding and len(embedding) > 0, "Should generate a valid embedding"
    
    # Test searching with the prefixed name
    print(f"🔍 TEST: Searching in prefixed index: {prefixed_id}")
    prefixed_results = await db.search_context(
        query="test",
        index_name=prefixed_id,
        min_relevance=0.0  # Set minimum relevance to 0 to get all results
    )
    print(f"🔍 TEST: Found {len(prefixed_results)} results in prefixed index")
    assert len(prefixed_results) > 0, "Should find results in prefixed index"
    
    # Test searching with the unprefixed name (without vs_)
    unprefixed_search_name = vector_store.get_display_name(unprefixed_id)
    print(f"🔍 TEST: Searching in unprefixed index: {unprefixed_search_name}")
    unprefixed_results = await db.search_context(
        query="test",
        index_name=unprefixed_search_name,  # Use the name without vs_ prefix
        min_relevance=0.0  # Set minimum relevance to 0 to get all results
    )
    print(f"🔍 TEST: Found {len(unprefixed_results)} results in unprefixed index")
    assert len(unprefixed_results) > 0, "Should find results in unprefixed index"
    
    # Verify the search results have the correct metadata
    if prefixed_results:
        assert prefixed_results[0]["metadata"].get("test") == "prefixed", "Prefixed results should have correct metadata"
    if unprefixed_results:
        assert unprefixed_results[0]["metadata"].get("test") == "unprefixed", "Unprefixed results should have correct metadata" 