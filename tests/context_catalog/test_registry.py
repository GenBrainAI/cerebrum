"""Tests for the Context Catalog Registry."""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any

from src.context_catalog.registry import ContextCatalogRegistry
from src.context_catalog.metadata import (
    ContextMetadata,
    StorageInfo,
    AccessControl,
    StorageBackend,
    SourceType,
    DataType,
    AccessLevel
)
from src.context_catalog.exceptions import (
    ValidationError,
    AccessError,
    RelationshipError
)


@pytest.fixture
def storage_config() -> Dict[str, Any]:
    """Create test storage configuration."""
    return {
        "file_storage_path": "test_storage"
    }


@pytest.fixture
def test_metadata() -> ContextMetadata:
    """Create test metadata."""
    return ContextMetadata(
        source_type=SourceType.KNOWLEDGE_BASE,
        data_type=DataType.TEXT,
        domain="test_domain",
        purpose="test_purpose",
        storage_info=StorageInfo(
            backend=StorageBackend.FILE,
            location="test_location",
            format="json"
        ),
        access_control=AccessControl(
            level=AccessLevel.PRIVATE,
            owner_id="test_user"
        )
    )


@pytest.fixture
async def registry(storage_config: Dict[str, Any]) -> ContextCatalogRegistry:
    """Create test registry instance."""
    return ContextCatalogRegistry(storage_config)


@pytest.mark.asyncio
async def test_register_context(
    registry: ContextCatalogRegistry,
    test_metadata: ContextMetadata
):
    """Test context registration."""
    content = {"test": "data"}
    context_id = await registry.register_context(
        content=content,
        metadata=test_metadata
    )
    
    assert context_id is not None
    assert context_id in registry.entries
    assert registry.entries[context_id].metadata == test_metadata


@pytest.mark.asyncio
async def test_get_context_info(
    registry: ContextCatalogRegistry,
    test_metadata: ContextMetadata
):
    """Test retrieving context information."""
    content = {"test": "data"}
    context_id = await registry.register_context(
        content=content,
        metadata=test_metadata
    )
    
    entry = await registry.get_context_info(context_id)
    assert entry.id == context_id
    assert entry.metadata == test_metadata


@pytest.mark.asyncio
async def test_update_context(
    registry: ContextCatalogRegistry,
    test_metadata: ContextMetadata
):
    """Test updating context."""
    content = {"test": "data"}
    context_id = await registry.register_context(
        content=content,
        metadata=test_metadata
    )
    
    new_content = {"updated": "data"}
    await registry.update_context(
        context_id,
        {"content": new_content}
    )
    
    entry = await registry.get_context_info(context_id)
    stored_content = await registry.storage_manager.retrieve_context(
        entry.storage_info
    )
    assert stored_content == new_content


@pytest.mark.asyncio
async def test_add_relationship(
    registry: ContextCatalogRegistry,
    test_metadata: ContextMetadata
):
    """Test adding relationships between contexts."""
    content1 = {"test": "data1"}
    content2 = {"test": "data2"}
    
    context_id1 = await registry.register_context(
        content=content1,
        metadata=test_metadata
    )
    context_id2 = await registry.register_context(
        content=content2,
        metadata=test_metadata
    )
    
    await registry.add_relationship(context_id1, context_id2)
    
    relationships = await registry.get_related_contexts(context_id1)
    assert context_id2 in relationships["dependencies"]


@pytest.mark.asyncio
async def test_access_control(
    registry: ContextCatalogRegistry,
    test_metadata: ContextMetadata
):
    """Test access control."""
    content = {"test": "data"}
    context_id = await registry.register_context(
        content=content,
        metadata=test_metadata,
        user_id="test_user"
    )
    
    # Test access denied
    with pytest.raises(AccessError):
        await registry.get_context_info(
            context_id,
            user_id="unauthorized_user"
        )
    
    # Test access allowed for owner
    entry = await registry.get_context_info(
        context_id,
        user_id="test_user"
    )
    assert entry.id == context_id


@pytest.mark.asyncio
async def test_expired_access(
    registry: ContextCatalogRegistry,
    test_metadata: ContextMetadata
):
    """Test expired access control."""
    # Set expiration to past date
    test_metadata.access_control.expiration = (
        datetime.utcnow() - timedelta(days=1)
    )
    
    content = {"test": "data"}
    context_id = await registry.register_context(
        content=content,
        metadata=test_metadata,
        user_id="test_user"
    )
    
    # Test access denied due to expiration
    with pytest.raises(AccessError):
        await registry.get_context_info(
            context_id,
            user_id="test_user"
        )


@pytest.mark.asyncio
async def test_delete_context(
    registry: ContextCatalogRegistry,
    test_metadata: ContextMetadata
):
    """Test context deletion."""
    content = {"test": "data"}
    context_id = await registry.register_context(
        content=content,
        metadata=test_metadata
    )
    
    await registry.delete_context(context_id)
    
    with pytest.raises(RelationshipError):
        await registry.get_context_info(context_id) 