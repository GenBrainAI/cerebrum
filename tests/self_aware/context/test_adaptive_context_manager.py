"""
Unit tests for the Adaptive Context Manager.
"""

import os
import json
import pytest
import shutil
from pathlib import Path
from datetime import datetime
import asyncio
from typing import Dict, List, Any, Optional

from src.server.context.adaptive_context_manager import (
    AdaptiveContextManager,
    ContextConfig,
    ContextItem,
    CompressionStrategy,
    count_tokens
)

@pytest.fixture
def temp_context_dir(tmp_path):
    """Create a temporary directory for context storage."""
    context_dir = tmp_path / "test_adaptive_context"
    context_dir.mkdir(exist_ok=True)
    yield context_dir
    # Cleanup
    shutil.rmtree(context_dir)

@pytest.fixture
def context_config(temp_context_dir):
    """Create a test context configuration."""
    return ContextConfig(
        base_path=str(temp_context_dir),
        default_model="gpt-4",
        max_tokens=1000,  # Smaller for testing
        default_compression_strategy="truncate",
        enable_history=True,
        history_max_items=10
    )

@pytest.fixture
def context_manager(context_config):
    """Create a test context manager instance."""
    manager = AdaptiveContextManager(config=context_config)
    return manager

@pytest.fixture
def sample_context_items():
    """Create sample context items for testing."""
    return [
        ContextItem(
            id="item1",
            content="This is a test context item with high priority.",
            source="test",
            priority=80,
            metadata={"type": "test"}
        ),
        ContextItem(
            id="item2",
            content="This is another test context item with medium priority. " * 5,
            source="test",
            priority=50,
            metadata={"type": "test"}
        ),
        ContextItem(
            id="item3",
            content="This is a low priority context item that might be compressed. " * 10,
            source="test",
            priority=20,
            metadata={"type": "test"}
        )
    ]

@pytest.mark.asyncio
async def test_create_context(context_manager):
    """Test creating a new context."""
    operation_id = "test_operation"
    result = await context_manager.create_context(operation_id)
    
    # Check result
    assert result == operation_id
    
    # Check that context was created
    assert operation_id in context_manager.active_contexts
    
    # Check that metadata file was created
    metadata_path = context_manager.contexts_dir / f"{operation_id}_metadata.json"
    assert metadata_path.exists()
    
    # Check metadata content
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
        assert metadata["id"] == operation_id
        assert "created_at" in metadata
        assert "last_modified" in metadata
        assert metadata["engine_type"] == context_manager.config.default_model
        assert metadata["max_tokens"] == context_manager.config.max_tokens
        assert metadata["item_count"] == 0
        assert metadata["total_tokens"] == 0

@pytest.mark.asyncio
async def test_add_to_context(context_manager, sample_context_items):
    """Test adding items to a context."""
    operation_id = "test_operation"
    
    # Add first item
    item_id = await context_manager.add_to_context(
        operation_id,
        sample_context_items[0]
    )
    
    # Check that item was added
    assert operation_id in context_manager.active_contexts
    assert item_id in context_manager.active_contexts[operation_id]
    
    # Check that item file was created
    item_path = context_manager.contexts_dir / f"{operation_id}_{item_id}.json"
    assert item_path.exists()
    
    # Add string content
    content = "This is a string content test."
    source = "string_test"
    string_item_id = await context_manager.add_to_context(
        operation_id,
        content,
        source=source,
        priority=60,
        metadata={"type": "string_test"}
    )
    
    # Check that string item was added
    assert string_item_id in context_manager.active_contexts[operation_id]
    
    # Check metadata was updated
    metadata_path = context_manager.contexts_dir / f"{operation_id}_metadata.json"
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
        assert metadata["item_count"] == 2
        assert metadata["total_tokens"] > 0

@pytest.mark.asyncio
async def test_get_context(context_manager, sample_context_items):
    """Test retrieving context."""
    operation_id = "test_operation"
    
    # Add items
    for item in sample_context_items:
        await context_manager.add_to_context(operation_id, item)
    
    # Get context as string
    context = await context_manager.get_context(operation_id)
    
    # Check that all items are included
    for item in sample_context_items:
        assert item.content in context
    
    # Get context with metadata
    context_with_metadata = await context_manager.get_context(
        operation_id,
        include_metadata=True
    )
    
    # Check metadata
    assert "content" in context_with_metadata
    assert "items" in context_with_metadata
    assert "total_tokens" in context_with_metadata
    assert "item_count" in context_with_metadata
    assert context_with_metadata["item_count"] == len(sample_context_items)
    
    # Get context with token limit
    limited_context = await context_manager.get_context(
        operation_id,
        max_tokens=50
    )
    
    # Check that limited context is shorter
    assert len(limited_context) < len(context)

@pytest.mark.asyncio
async def test_update_context_item(context_manager, sample_context_items):
    """Test updating a context item."""
    operation_id = "test_operation"
    
    # Add item
    item = sample_context_items[0]
    item_id = await context_manager.add_to_context(operation_id, item)
    
    # Update item
    new_content = "This is updated content."
    new_priority = 90
    result = await context_manager.update_context_item(
        operation_id,
        item_id,
        content=new_content,
        priority=new_priority
    )
    
    # Check result
    assert result is True
    
    # Check that item was updated
    updated_item = context_manager.active_contexts[operation_id][item_id]
    assert updated_item.content == new_content
    assert updated_item.priority == new_priority
    
    # Check that item file was updated
    item_path = context_manager.contexts_dir / f"{operation_id}_{item_id}.json"
    with open(item_path, 'r') as f:
        data = json.load(f)
        assert data["content"] == new_content
        assert data["priority"] == new_priority

@pytest.mark.asyncio
async def test_remove_from_context(context_manager, sample_context_items):
    """Test removing an item from context."""
    operation_id = "test_operation"
    
    # Add items
    item_ids = []
    for item in sample_context_items:
        item_id = await context_manager.add_to_context(operation_id, item)
        item_ids.append(item_id)
    
    # Remove one item
    result = await context_manager.remove_from_context(operation_id, item_ids[0])
    
    # Check result
    assert result is True
    
    # Check that item was removed
    assert item_ids[0] not in context_manager.active_contexts[operation_id]
    
    # Check that item file was removed
    item_path = context_manager.contexts_dir / f"{operation_id}_{item_ids[0]}.json"
    assert not item_path.exists()
    
    # Check metadata was updated
    metadata_path = context_manager.contexts_dir / f"{operation_id}_metadata.json"
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
        assert metadata["item_count"] == len(sample_context_items) - 1

@pytest.mark.asyncio
async def test_delete_context(context_manager, sample_context_items):
    """Test deleting an entire context."""
    operation_id = "test_operation"
    
    # Add items
    for item in sample_context_items:
        await context_manager.add_to_context(operation_id, item)
    
    # Delete context
    result = await context_manager.delete_context(operation_id)
    
    # Check result
    assert result is True
    
    # Check that context was removed from memory
    assert operation_id not in context_manager.active_contexts
    
    # Check that all files were removed
    for path in context_manager.contexts_dir.glob(f"{operation_id}_*.json"):
        assert False, f"File should have been deleted: {path}"

@pytest.mark.asyncio
async def test_compression(context_manager):
    """Test context compression."""
    operation_id = "test_compression"
    
    # Create a context with small max_tokens
    await context_manager.create_context(
        operation_id,
        max_tokens=100  # Very small for testing
    )
    
    # Add a large item that will trigger compression
    large_content = "This is a test sentence that will be repeated many times. " * 20
    item_id = await context_manager.add_to_context(
        operation_id,
        large_content,
        source="test",
        priority=20  # Low priority to ensure it gets compressed
    )
    
    # Check that compression was applied
    item = context_manager.active_contexts[operation_id][item_id]
    assert "compression" in item.metadata
    assert item.token_count <= 100
    
    # Check compression metadata
    compression = item.metadata["compression"]
    assert compression["strategy"] in ["truncate", "summarize_fallback_to_truncate"]
    assert compression["original_tokens"] > compression["compressed_tokens"]

@pytest.mark.asyncio
async def test_load_context_from_disk(context_manager, sample_context_items):
    """Test loading context from disk."""
    operation_id = "test_load"
    
    # Add items
    for item in sample_context_items:
        await context_manager.add_to_context(operation_id, item)
    
    # Clear memory cache
    context_manager.active_contexts = {}
    
    # Get context (should load from disk)
    context = await context_manager.get_context(operation_id)
    
    # Check that context was loaded
    assert operation_id in context_manager.active_contexts
    assert len(context_manager.active_contexts[operation_id]) == len(sample_context_items)
    
    # Check content
    for item in sample_context_items:
        assert item.content in context

@pytest.mark.asyncio
async def test_list_contexts(context_manager):
    """Test listing all contexts."""
    # Create multiple contexts
    await context_manager.create_context("context1")
    await context_manager.create_context("context2")
    await context_manager.create_context("context3")
    
    # List contexts
    contexts = await context_manager.list_contexts()
    
    # Check result
    assert len(contexts) == 3
    context_ids = [c["id"] for c in contexts]
    assert "context1" in context_ids
    assert "context2" in context_ids
    assert "context3" in context_ids

@pytest.mark.asyncio
async def test_get_context_stats(context_manager, sample_context_items):
    """Test getting context statistics."""
    operation_id = "test_stats"
    
    # Add items
    for item in sample_context_items:
        await context_manager.add_to_context(operation_id, item)
    
    # Get stats
    stats = await context_manager.get_context_stats(operation_id)
    
    # Check stats
    assert stats["operation_id"] == operation_id
    assert stats["item_count"] == len(sample_context_items)
    assert stats["total_tokens"] > 0
    assert "sources" in stats
    assert "priority_distribution" in stats
    assert "compression_applied" in stats

@pytest.mark.asyncio
async def test_custom_compression_strategy(context_manager):
    """Test registering and using a custom compression strategy."""
    # Define custom strategy
    def custom_compression(context_item, max_tokens):
        """Custom compression that adds a prefix."""
        truncated = context_manager._truncate_compression(context_item, max_tokens - 10)
        truncated.content = "[COMPRESSED] " + truncated.content
        truncated.metadata["compression"]["strategy"] = "custom"
        return truncated
    
    # Register custom strategy
    context_manager.register_compression_strategy(
        CompressionStrategy(
            name="custom",
            description="Custom compression strategy",
            compression_fn=custom_compression,
            priority_threshold=40,
            token_threshold=500
        )
    )
    
    # Set as default
    context_manager.config.default_compression_strategy = "custom"
    
    # Create context with small max_tokens
    operation_id = "test_custom_compression"
    await context_manager.create_context(
        operation_id,
        max_tokens=100
    )
    
    # Add large item
    large_content = "This is a test sentence that will be repeated many times. " * 20
    item_id = await context_manager.add_to_context(
        operation_id,
        large_content,
        source="test",
        priority=30
    )
    
    # Check that custom compression was applied
    item = context_manager.active_contexts[operation_id][item_id]
    assert item.content.startswith("[COMPRESSED]")
    assert item.metadata["compression"]["strategy"] == "custom"

def test_count_tokens():
    """Test token counting function."""
    # Test with simple text
    text = "This is a test sentence."
    tokens = count_tokens(text)
    assert tokens > 0
    
    # Test with longer text
    long_text = "This is a longer test sentence that should have more tokens. " * 10
    long_tokens = count_tokens(long_text)
    assert long_tokens > tokens 