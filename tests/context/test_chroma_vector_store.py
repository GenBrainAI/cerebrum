import os
import pytest
import pytest_asyncio
import asyncio
import tempfile
import shutil
from pathlib import Path

from src.server.context.chroma_vector_store import ChromaVectorStore, VectorStoreConfig

@pytest.fixture
def vector_store_config():
    """Create a test vector store configuration."""
    return VectorStoreConfig(
        batch_size=10,
        chunk_size=500,
        chunk_overlap=50,
        collection_name="test_collection"
    )

@pytest_asyncio.fixture
async def vector_store(vector_store_config):
    """Create a test vector store instance with cleanup."""
    # Create a temporary directory for the test
    temp_dir = tempfile.mkdtemp(prefix="test_chroma_db_")
    
    # Create the vector store
    store = ChromaVectorStore(config=vector_store_config, base_path=temp_dir)
    
    yield store
    
    # Cleanup after tests
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.mark.asyncio
async def test_create_index(vector_store):
    """Test creating a new index."""
    # Create a new index
    index_name = await vector_store.create_index("test_index", "Test index description")
    
    # Verify the index was created
    indices = await vector_store.list_indices()
    assert any(idx["name"] == index_name for idx in indices)
    
    # Check the description
    for idx in indices:
        if idx["name"] == index_name:
            assert idx["description"] == "Test index description"
            break

@pytest.mark.asyncio
async def test_add_text_and_search(vector_store):
    """Test adding text to the vector store and searching for it."""
    # Create a test index
    index_name = await vector_store.create_index("test_search", "Test search index")
    
    # Add some text to the index
    test_text = "This is a test document about artificial intelligence and machine learning."
    metadata = {"source": "test", "category": "ai"}
    
    # Create a temporary file with the test text
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as temp_file:
        temp_file.write(test_text)
        temp_file_path = temp_file.name
    
    try:
        # Add the file to the index
        chunk_ids = await vector_store.add_file_to_index(
            index_name=index_name,
            file_path_or_obj=temp_file_path,
            metadata=metadata
        )
        
        # Verify chunks were created
        assert len(chunk_ids) > 0
        
        # Search for relevant content
        results = await vector_store.search_index(
            index_name=index_name,
            query="artificial intelligence",
            limit=5
        )
        
        # Verify search results
        assert len(results) > 0
        assert any("artificial intelligence" in result["content"] for result in results)
        
        # Test filtering
        filtered_results = await vector_store.search_index(
            index_name=index_name,
            query="machine learning",
            filters={"category": "ai"},
            limit=5
        )
        
        # Verify filtered results
        assert len(filtered_results) > 0
    finally:
        # Clean up the temporary file
        os.unlink(temp_file_path)

@pytest.mark.asyncio
async def test_delete_index(vector_store):
    """Test deleting an index."""
    # Create a new index
    index_name = await vector_store.create_index("test_delete", "Test delete index")
    
    # Verify the index was created
    indices_before = await vector_store.list_indices()
    assert any(idx["name"] == index_name for idx in indices_before)
    
    # Delete the index
    result = await vector_store.delete_index(index_name)
    assert result is True
    
    # Verify the index was deleted
    indices_after = await vector_store.list_indices()
    assert not any(idx["name"] == index_name for idx in indices_after)

@pytest.mark.asyncio
@pytest.mark.skip(reason="Migration functionality needs to be fixed separately")
async def test_migration_utility(vector_store):
    """Test the migration utility function."""
    # Create a mock old vector store structure
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create mock index.json and embeddings.json files
        index_data = {
            "test_id_1": {
                "content": "Test content 1",
                "type": "text",
                "created_at": "2023-01-01T00:00:00"
            },
            "test_id_2": {
                "content": "Test content 2",
                "type": "text",
                "created_at": "2023-01-02T00:00:00"
            }
        }
        
        embeddings_data = {
            "test_id_1": [0.1, 0.2, 0.3, 0.4, 0.5],
            "test_id_2": [0.5, 0.4, 0.3, 0.2, 0.1]
        }
        
        # Write mock files
        with open(os.path.join(temp_dir, "index.json"), "w") as f:
            import json
            json.dump(index_data, f)
            
        with open(os.path.join(temp_dir, "embeddings.json"), "w") as f:
            import json
            json.dump(embeddings_data, f)
        
        # Test migration
        try:
            result = await vector_store.migrate_from_custom_store(temp_dir)
            
            # Verify migration results
            assert result["total"] == 2
            assert result["processed"] == 2
            assert result["skipped"] == 0
            
            # Verify data was migrated
            items = await vector_store.get_all_items()
            assert len(items) == 2
            assert any(item["content"] == "Test content 1" for item in items)
            assert any(item["content"] == "Test content 2" for item in items)
            
        except Exception as e:
            pytest.fail(f"Migration test failed: {str(e)}") 