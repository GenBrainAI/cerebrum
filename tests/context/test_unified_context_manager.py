import pytest
import os
from pathlib import Path
import tempfile
import json
from datetime import datetime
from typing import Dict, Any
import asyncio
import shutil
from unittest.mock import patch

from src.server.context.unified_context_manager import (
    UnifiedContextManager,
    PreparedData,
    DataSource
)
from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.persistence.in_memory_persistence import InMemoryPersistenceModel

@pytest.fixture(autouse=True)
async def clear_context_db(context_manager):
    """Clear the context database before each test."""
    # Reset any existing data
    await context_manager.context_db.clear()
    await context_manager.knowledge_base.clear()
    await context_manager.vector_store.clear()
    yield
    # Clean up after test
    await context_manager.context_db.clear()
    await context_manager.knowledge_base.clear()
    await context_manager.vector_store.clear()

@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for test data."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
async def context_manager(temp_data_dir):
    """Create a UnifiedContextManager instance with temporary storage."""
    # Reset the persistence model factory to ensure a clean state
    PersistenceModelFactory.reset()
    # Create a new persistence model
    persistence_model = InMemoryPersistenceModel()
    # Create the context manager with the persistence model
    manager = UnifiedContextManager(data_dir=temp_data_dir, persistence_model=persistence_model)
    await manager.initialize()
    return manager

@pytest.fixture
def sample_content():
    """Sample content for testing."""
    return {
        "text": "Sample test content for context testing",
        "code": """
        def test_function():
            return "test"
        """,
        "web": "<html><body>Test web content</body></html>",
        "api": {"key": "value", "data": [1, 2, 3]},
        "metadata": {
            "category": "test",
            "type": "sample"
        }
    }

def test_prepared_data_creation():
    """Test PreparedData class creation and methods."""
    data = PreparedData(
        content="Test content",
        source_type=DataSource.CUSTOM,
        metadata={"category": "test"}
    )
    
    assert data.content == "Test content"
    assert data.source_type == DataSource.CUSTOM
    assert data.metadata == {"category": "test"}
    assert data.data_hash is not None
    assert data.created_at is not None

def test_prepared_data_serialization():
    """Test PreparedData serialization and deserialization."""
    original = PreparedData(
        content="Test content",
        source_type=DataSource.CUSTOM,
        metadata={"category": "test"}
    )
    
    # Convert to dict
    data_dict = original.to_dict()
    
    # Create new instance from dict
    recreated = PreparedData.from_dict(data_dict)
    
    assert recreated.content == original.content
    assert recreated.source_type == original.source_type
    assert recreated.metadata == original.metadata
    assert recreated.data_hash == original.data_hash

@pytest.mark.asyncio
async def test_prepare_custom_data(context_manager, sample_content):
    """Test preparing custom data."""
    # Prepare custom data
    prepared = await context_manager.prepare_data(
        source_type=DataSource.CUSTOM,
        source=sample_content["text"],
        metadata={"type": "text", "category": "test"}
    )
    
    assert prepared.content == sample_content["text"]
    assert prepared.source_type == DataSource.CUSTOM
    assert prepared.metadata["type"] == "text"
    assert prepared.data_hash is not None
    
    # Verify data was saved
    saved_data = context_manager.prepared_data[prepared.data_hash]
    assert saved_data.content == sample_content["text"]

@pytest.mark.asyncio
async def test_prepare_file_data(context_manager, temp_data_dir, sample_content):
    """Test preparing file data."""
    # Create test file
    test_file = Path(temp_data_dir) / "test.txt"
    test_file.write_text(sample_content["text"])
    
    # Prepare file data
    prepared = await context_manager.prepare_data(
        source_type=DataSource.FILE,
        source=str(test_file),
        metadata={"filename": "test.txt"}
    )
    
    assert prepared.content == sample_content["text"]
    assert prepared.source_type == DataSource.FILE
    assert prepared.metadata["filename"] == "test.txt"

@pytest.mark.asyncio
async def test_add_prepared_data_to_context(context_manager, sample_content):
    """Test adding prepared data to task context."""
    # First prepare some data
    prepared = await context_manager.prepare_data(
        source_type=DataSource.CUSTOM,
        source=sample_content["text"],
        metadata={"category": "test"}
    )
    
    # Add to task context
    task_id = "test_task_123"
    success = await context_manager.add_prepared_data_to_context(
        data_hash=prepared.data_hash,
        task_id=task_id,
        context_type="knowledge",
        priority=80
    )
    
    assert success is True
    
    # Verify context was added
    contexts = await context_manager.get_task_context(task_id)
    assert len(contexts) > 0

@pytest.mark.asyncio
async def test_get_prepared_data_with_filters(context_manager, sample_content):
    """Test retrieving prepared data with filters."""
    # Prepare multiple data entries
    data1 = await context_manager.prepare_data(
        source_type=DataSource.CUSTOM,
        source=sample_content["text"],
        metadata={"category": "test", "type": "text"}
    )
    
    data2 = await context_manager.prepare_data(
        source_type=DataSource.CUSTOM,
        source=sample_content["code"],
        metadata={"category": "test", "type": "code"}
    )
    
    # Test filtering by source type
    custom_data = context_manager.get_prepared_data(source_type=DataSource.CUSTOM)
    assert len(custom_data) == 2
    
    # Test filtering by metadata
    code_data = context_manager.get_prepared_data(
        metadata_filter={"type": "code"}
    )
    assert len(code_data) == 1
    assert code_data[0].content == sample_content["code"]

@pytest.mark.asyncio
async def test_data_persistence(temp_data_dir, sample_content):
    """Test that prepared data persists between manager instances."""
    # Create first manager instance and prepare data
    manager1 = UnifiedContextManager(data_dir=temp_data_dir)
    prepared = await manager1.prepare_data(
        source_type=DataSource.CUSTOM,
        source=sample_content["text"],
        metadata={"category": "test"}
    )
    data_hash = prepared.data_hash
    
    # Create second manager instance and verify data loaded
    manager2 = UnifiedContextManager(data_dir=temp_data_dir)
    assert data_hash in manager2.prepared_data
    loaded_data = manager2.prepared_data[data_hash]
    assert loaded_data.content == sample_content["text"]
    assert loaded_data.metadata["category"] == "test"

@pytest.mark.asyncio
async def test_invalid_data_source(context_manager):
    """Test handling of invalid data source type."""
    with pytest.raises(ValueError, match="Unsupported source type"):
        await context_manager.prepare_data(
            source_type="invalid",
            source="test",
            metadata={}
        )

@pytest.mark.asyncio
async def test_invalid_prepared_data_reference(context_manager):
    """Test handling of invalid prepared data reference."""
    with pytest.raises(ValueError):
        await context_manager.add_prepared_data_to_context(
            data_hash="nonexistent",
            task_id="test_task",
            context_type="knowledge"
        )

@pytest.mark.asyncio
async def test_multiple_context_types(context_manager, sample_content):
    """Test adding same prepared data with different context types."""
    # Prepare data
    prepared = await context_manager.prepare_data(
        source_type=DataSource.CUSTOM,
        source=sample_content["code"],
        metadata={"type": "code"}
    )
    
    task_id = "test_task_456"
    
    # Add as knowledge context
    success1 = await context_manager.add_prepared_data_to_context(
        data_hash=prepared.data_hash,
        task_id=task_id,
        context_type="knowledge",
        priority=70
    )
    
    # Add as vector context
    success2 = await context_manager.add_prepared_data_to_context(
        data_hash=prepared.data_hash,
        task_id=task_id,
        context_type="vector",
        priority=80
    )
    
    assert success1 is True
    assert success2 is True
    
    # Verify both contexts
    contexts = await context_manager.get_task_context(task_id)
    assert len(contexts) == 2

@pytest.mark.asyncio
async def test_error_handling(context_manager):
    """Test error handling in various scenarios."""
    # Test invalid source type
    with pytest.raises(ValueError):
        await context_manager.prepare_data(
            source_type="invalid",
            source="test"
        )
    
    # Test invalid data hash
    with pytest.raises(ValueError):
        await context_manager.add_prepared_data_to_context(
            data_hash="nonexistent",
            task_id="test_task",
            context_type="knowledge"
        )
    
    # Test invalid file path
    with pytest.raises(FileNotFoundError):
        await context_manager.prepare_data(
            source_type=DataSource.FILE,
            source="nonexistent.txt"
        )

@pytest.mark.asyncio
async def test_initialize_documentation(context_manager, temp_data_dir):
    """Test documentation initialization."""
    # Create a temporary tool development guide
    docs_dir = Path(temp_data_dir) / "docs"
    docs_dir.mkdir()
    guide_path = docs_dir / "tool_development_guide.md"
    guide_content = "# Test Guide\nThis is a test guide."
    
    with open(guide_path, 'w') as f:
        f.write(guide_content)
    
    # Mock Path to return our test file
    with patch('src.server.context.unified_context_manager.Path') as mock_path_class:
        # Create a mock path instance that returns itself for division
        mock_path = mock_path_class.return_value
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_path.read_text.return_value = guide_content
        mock_path.__truediv__ = lambda self, x: mock_path
        mock_path.__str__.return_value = str(guide_path)
        
        # Make the class return the mock instance
        mock_path_class.return_value = mock_path
        
        # Initialize documentation
        await context_manager._initialize_documentation()
        
        # Verify documentation was added
        assert context_manager._documentation_initialized is True

@pytest.mark.asyncio
async def test_context_integration(context_manager, sample_content):
    """Test integration between different context types."""
    # Prepare data
    prepared = await context_manager.prepare_data(
        source_type=DataSource.CUSTOM,
        source=sample_content["text"],
        metadata=sample_content["metadata"]
    )
    
    task_id = "test_task_456"
    
    # Add as knowledge context
    success1 = await context_manager.add_prepared_data_to_context(
        data_hash=prepared.data_hash,
        task_id=task_id,
        context_type="knowledge"
    )
    
    # Add as vector context
    success2 = await context_manager.add_prepared_data_to_context(
        data_hash=prepared.data_hash,
        task_id=task_id,
        context_type="vector"
    )
    
    assert success1 is True
    assert success2 is True
    
    # Get task contexts
    contexts = await context_manager.get_task_context(task_id)
    assert len(contexts) == 2  # Should have both knowledge and vector contexts 