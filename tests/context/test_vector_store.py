import pytest
import numpy as np
from typing import Dict, Any
from src.server.context.vector_store import VectorStore

@pytest.mark.asyncio
async def test_vector_store_add_items(vector_store, sample_code_content):
    """Test adding items to vector store."""
    try:
        # Get list of code content
        contents = list(sample_code_content.values())
        
        # Generate embeddings - note no await here
        embeddings = vector_store._safe_embed(contents)  # Remove await
        
        # Create metadata for each file
        metadatas = [{"file_path": f, "type": "code"} for f in sample_code_content.keys()]
        
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

    except Exception as e:
        pytest.fail(f"Test failed with error: {str(e)}")


@pytest.mark.asyncio
async def test_vector_store_search(vector_store, sample_code_content):
    """Test searching vector store."""
    try:
        contents = list(sample_code_content.values())
        embeddings = vector_store._safe_embed(contents)  # Remove await
        metadatas = [{"file_path": f, "type": "code"} for f in sample_code_content.keys()]
        
        # Add items to store
        await vector_store.add_items(embeddings, metadatas, contents)
        
        # Search using first embedding as query
        results = await vector_store.search(
            embedding=embeddings[0],
            filters={"type": "code"},
            limit=2
        )
        
        assert len(results) > 0
        assert "content" in results[0]
        assert "metadata" in results[0]
        assert "relevance" in results[0]
    except Exception as e:
        pytest.fail(f"Test failed with error: {str(e)}")

@pytest.mark.asyncio
async def test_vector_store_update_embeddings(vector_store, sample_code_content):
    """Test updating embeddings in vector store."""
    try:
        contents = list(sample_code_content.values())
        embeddings = vector_store._safe_embed(contents)  # Remove await
        metadatas = [{"file_path": f, "type": "code"} for f in sample_code_content.keys()]
        
        # First add items and get the IDs
        add_stats = await vector_store.add_items(embeddings, metadatas, contents)
        assert add_stats["processed"] == len(contents)
        
        # Store the generated IDs
        generated_ids = add_stats["ids"]
        assert len(generated_ids) == len(contents)
        
        # Generate new embeddings and update
        new_embeddings = vector_store._safe_embed(contents)  # Remove await
        update_stats = await vector_store.update_embeddings(
            ids=generated_ids,  # Use the generated IDs instead of file names
            embeddings=new_embeddings
        )
        
        assert update_stats["processed"] == len(contents)
        assert update_stats["failed"] == 0
    except Exception as e:
        pytest.fail(f"Test failed with error: {str(e)}")