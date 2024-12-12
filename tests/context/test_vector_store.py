import pytest
import numpy as np
from typing import Dict, Any
from src.server.context.vector_store import VectorStore
from datetime import datetime

@pytest.mark.asyncio
async def test_vector_store_add_items(vector_store, sample_code_content):
    """Test adding items to vector store."""
    try:
        # Get list of code content
        contents = list(sample_code_content.values())
        
        # Generate embeddings
        embeddings = vector_store._safe_embed(contents)
        
        # Create metadata for each file
        metadatas = [{
            "file_path": f,
            "type": "code",
            "added_at": datetime.now().isoformat()
        } for f in sample_code_content.keys()]
        
        # Add items to vector store
        stats = await vector_store.add_items(
            embeddings=embeddings,
            metadatas=metadatas,
            contents=contents
        )
        
        # Verify results
        assert isinstance(stats, dict)
        assert stats["processed"] == len(sample_code_content)
        assert stats["failed"] == 0
        assert len(stats["ids"]) == len(sample_code_content)
        
        # Verify items were stored
        collection = vector_store.client.get_collection(vector_store.config.collection_name)
        stored_items = collection.get(ids=stats["ids"])
        assert len(stored_items["ids"]) == len(sample_code_content)
        
    except Exception as e:
        pytest.fail(f"Test failed with error: {str(e)}")


@pytest.mark.asyncio
async def test_vector_store_search(vector_store, sample_code_content):
    """Test searching vector store."""
    try:
        # Get list of code content
        contents = list(sample_code_content.values())
        
        # Generate embeddings
        embeddings = vector_store._safe_embed(contents)
        
        # Create metadata for each file
        metadatas = [{
            "file_path": f,
            "type": "code",
            "added_at": datetime.now().isoformat()
        } for f in sample_code_content.keys()]
        
        # Add items to store
        add_stats = await vector_store.add_items(
            embeddings=embeddings,
            metadatas=metadatas,
            contents=contents
        )
        
        # Verify items were added
        assert add_stats["processed"] == len(contents), "All items should be processed"
        assert len(add_stats["ids"]) == len(contents), "All items should have IDs"
        
        # Verify items were stored
        collection = vector_store.client.get_collection(vector_store.config.collection_name)
        stored_items = collection.get(ids=add_stats["ids"])
        assert len(stored_items["ids"]) == len(contents), "All items should be stored"
        
        print("\n=== Search Debug ===")
        print(f"Number of stored items: {len(stored_items['ids'])}")
        print(f"Search query embedding shape: {len(embeddings[0])}")
        
        # Search using first embedding as query
        results = await vector_store.search(
            embedding=embeddings[0],
            filters={"type": "code"},
            limit=2
        )
        
        print(f"Search results: {results}")
        
        # Verify search results
        assert len(results) > 0, "Search should return at least one result"
        assert isinstance(results[0], dict), "Results should be dictionaries"
        assert "content" in results[0], "Results should contain content"
        assert "metadata" in results[0], "Results should contain metadata"
        assert "relevance" in results[0], "Results should contain relevance score"
        assert results[0]["metadata"]["type"] == "code", "Result should match filter"
        
    except Exception as e:
        print(f"\nError details: {str(e)}")
        pytest.fail(f"Test failed with error: {str(e)}")

@pytest.mark.asyncio
async def test_vector_store_update_embeddings(vector_store, sample_code_content):
    """Test updating embeddings in vector store."""
    try:
        # Get list of code content
        contents = list(sample_code_content.values())
        
        # Generate initial embeddings
        embeddings = vector_store._safe_embed(contents)
        
        # Create metadata for each file
        metadatas = [{
            "file_path": f,
            "type": "code",
            "added_at": datetime.now().isoformat()
        } for f in sample_code_content.keys()]
        
        # First add items and get the IDs
        add_stats = await vector_store.add_items(
            embeddings=embeddings,
            metadatas=metadatas,
            contents=contents
        )
        
        # Verify items were added
        assert add_stats["processed"] == len(contents), "All items should be processed"
        assert len(add_stats["ids"]) == len(contents), "All items should have IDs"
        
        # Store the generated IDs
        generated_ids = add_stats["ids"]
        
        # Verify items were stored
        collection = vector_store.client.get_collection(vector_store.config.collection_name)
        stored_items = collection.get(ids=generated_ids)
        assert len(stored_items["ids"]) == len(contents), "All items should be stored"
        
        print("\n=== Update Debug ===")
        print(f"Number of items to update: {len(generated_ids)}")
        
        # Generate new embeddings and update
        new_embeddings = vector_store._safe_embed(contents)
        update_stats = await vector_store.update_embeddings(
            ids=generated_ids,
            embeddings=new_embeddings
        )
        
        print(f"Update stats: {update_stats}")
        
        # Verify update results
        assert update_stats["processed"] == len(contents), "All items should be processed"
        assert update_stats["failed"] == 0, "No updates should fail"
        
        # Verify the updates were applied
        updated_items = collection.get(ids=generated_ids)
        assert len(updated_items["ids"]) == len(contents), "All items should still exist"
        
    except Exception as e:
        print(f"\nError details: {str(e)}")
        pytest.fail(f"Test failed with error: {str(e)}")