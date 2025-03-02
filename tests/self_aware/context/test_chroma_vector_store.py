import os
import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.server.context.chroma_vector_store import ChromaVectorStore, VectorStoreConfig

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def test_files_dir(temp_dir):
    """Create a directory with test files."""
    test_dir = Path(temp_dir) / "test_files"
    test_dir.mkdir(exist_ok=True)
    
    # Create some test files
    (test_dir / "test1.py").write_text("def test_function():\n    return 'Hello, World!'")
    (test_dir / "test2.md").write_text("# Test Markdown\nThis is a test markdown file.")
    (test_dir / "test3.txt").write_text("This is a plain text file for testing.")
    (test_dir / "test4.json").write_text('{"name": "Test JSON", "type": "test"}')
    
    # Create a subdirectory with more files
    sub_dir = test_dir / "subdir"
    sub_dir.mkdir(exist_ok=True)
    (sub_dir / "subtest1.py").write_text("def sub_test_function():\n    return 'Hello from subdir!'")
    
    yield test_dir

@pytest.fixture
def vector_store(temp_dir):
    """Create a ChromaVectorStore instance for testing."""
    config = VectorStoreConfig(
        persist_directory=os.path.join(temp_dir, "vector_store"),
        collection_name="test_collection",
        embedding_model="text-embedding-3-small"
    )
    
    store = ChromaVectorStore(
        config=config,
        base_path=os.path.join(temp_dir, "vector_store")
    )
    
    return store

@pytest.mark.asyncio
async def test_process_directory(vector_store, test_files_dir):
    """Test processing a directory of files."""
    # Mock the embedding function to avoid actual API calls
    with patch.object(vector_store, '_safe_embed', return_value=[[0.1] * 1536]):
        # Create an index first
        index_name = await vector_store.create_index("test_index", "Test index for directory processing")
        
        # Process the directory
        result = await vector_store.process_directory(
            index_name=index_name,
            directory_path=str(test_files_dir),
            file_types=[".py", ".md", ".txt", ".json"],
            recursive=True
        )
        
        # Check that all files were processed
        assert result["total_files"] >= 5
        assert result["processed_files"] >= 5
        assert result["skipped_files"] == 0
        assert result["errors"] == 0

@pytest.mark.asyncio
async def test_incremental_processing(vector_store, test_files_dir):
    """Test incremental processing of files."""
    # Mock the embedding function to avoid actual API calls
    with patch.object(vector_store, '_safe_embed', return_value=[[0.1] * 1536]):
        # Create an index first
        index_name = await vector_store.create_index("test_index", "Test index for incremental processing")
        
        # Process the directory first time
        await vector_store.process_directory(
            index_name=index_name,
            directory_path=str(test_files_dir),
            file_types=[".py", ".md", ".txt", ".json"],
            recursive=True
        )
        
        # Add a new file
        (test_files_dir / "new_file.py").write_text("def new_function():\n    return 'New file!'")
        
        # Process the directory again with incremental=True
        result = await vector_store.process_directory(
            index_name=index_name,
            directory_path=str(test_files_dir),
            file_types=[".py", ".md", ".txt", ".json"],
            recursive=True,
            incremental=True
        )
        
        # Check that only new/modified files were processed
        assert result["total_files"] >= 6
        assert result["processed_files"] >= 1
        assert result["skipped_files"] >= 5

@pytest.mark.asyncio
async def test_search_index(vector_store, test_files_dir):
    """Test searching an index."""
    # Mock the embedding function to avoid actual API calls
    with patch.object(vector_store, '_safe_embed', return_value=[[0.1] * 1536]):
        # Create an index first
        index_name = await vector_store.create_index("test_index", "Test index for searching")
        
        # Add a file to the index
        await vector_store.add_file_to_index(
            index_name=index_name,
            file_path_or_obj=str(test_files_dir / "test1.py"),
            metadata={"type": "python"}
        )
        
        # Mock the search results
        mock_results = [
            {
                "id": "1",
                "document": "def test_function():\n    return 'Hello, World!'",
                "metadata": {
                    "file_path": str(test_files_dir / "test1.py"),
                    "type": "python"
                },
                "distance": 0.1
            }
        ]
        
        # Mock the collection's query method
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "ids": [["1"]],
            "documents": [["def test_function():\n    return 'Hello, World!'"]],
            "metadatas": [[{"file_path": str(test_files_dir / "test1.py"), "type": "python"}]],
            "distances": [[0.1]]
        }
        
        with patch.dict(vector_store.indices, {f"vs_{index_name}": mock_collection}):
            results = await vector_store.search_index(
                index_name=index_name,
                query="test function",
                limit=5
            )
            
            # Check that we got the expected results
            assert len(results) >= 1
            assert "document" in results[0]
            assert "metadata" in results[0]

@pytest.mark.asyncio
async def test_get_index_contents(vector_store):
    """Test getting the contents of an index."""
    # Create an index first
    index_name = await vector_store.create_index("test_index", "Test index for getting contents")
    
    # Mock the collection's get method
    mock_collection = MagicMock()
    mock_collection.get.return_value = {
        "ids": ["1", "2"],
        "documents": ["Document 1", "Document 2"],
        "metadatas": [{"key1": "value1"}, {"key2": "value2"}],
        "embeddings": None
    }
    
    with patch.dict(vector_store.indices, {f"vs_{index_name}": mock_collection}):
        contents = await vector_store.get_index_contents(index_name)
        
        # Check that we got the expected contents
        assert len(contents) == 2
        assert contents[0]["id"] == "1"
        assert contents[0]["document"] == "Document 1"
        assert contents[0]["metadata"] == {"key1": "value1"}

@pytest.mark.asyncio
async def test_list_indices(vector_store):
    """Test listing indices."""
    # Create a few indices
    await vector_store.create_index("test_index1", "Test index 1")
    await vector_store.create_index("test_index2", "Test index 2")
    
    # Mock the client's list_collections method
    mock_collection1 = MagicMock()
    mock_collection1.name = "vs_test_index1"
    mock_collection1.count.return_value = 5
    
    mock_collection2 = MagicMock()
    mock_collection2.name = "vs_test_index2"
    mock_collection2.count.return_value = 10
    
    with patch.object(vector_store.client, 'list_collections', return_value=[mock_collection1, mock_collection2]):
        indices = await vector_store.list_indices()
        
        # Check that we got the expected indices
        assert len(indices) == 2
        assert indices[0]["name"] == "test_index1" or indices[1]["name"] == "test_index1"
        assert indices[0]["name"] == "test_index2" or indices[1]["name"] == "test_index2"

@pytest.mark.asyncio
async def test_delete_index(vector_store):
    """Test deleting an index."""
    # Create an index first
    index_name = await vector_store.create_index("test_index", "Test index for deletion")
    
    # Mock the client's delete_collection method
    with patch.object(vector_store.client, 'delete_collection'):
        result = await vector_store.delete_index(index_name)
        
        # Check that the index was deleted
        assert result is True
        vector_store.client.delete_collection.assert_called_once_with(name=f"vs_{index_name}")

@pytest.mark.asyncio
async def test_get_stats(vector_store):
    """Test getting statistics."""
    # Create a few indices
    await vector_store.create_index("test_index1", "Test index 1")
    await vector_store.create_index("test_index2", "Test index 2")
    
    # Mock the collections
    mock_collection1 = MagicMock()
    mock_collection1.name = "vs_test_index1"
    mock_collection1.count.return_value = 5
    
    mock_collection2 = MagicMock()
    mock_collection2.name = "vs_test_index2"
    mock_collection2.count.return_value = 10
    
    with patch.object(vector_store.client, 'list_collections', return_value=[mock_collection1, mock_collection2]), \
         patch.object(vector_store, '_calculate_storage_size', return_value=1024):
        stats = await vector_store.get_stats()
        
        # Check that we got the expected stats
        assert "total_documents" in stats
        assert "total_size_bytes" in stats
        assert "collections" in stats
        assert len(stats["collections"]) == 2 