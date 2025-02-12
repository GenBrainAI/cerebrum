"""Tests for the Data Catalog functionality."""

import pytest
from datetime import datetime
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


class TestDataCatalogUseCases:
    """Test data catalog functionality through common use cases."""
    
    @pytest.fixture
    def catalog(self) -> ContextCatalogRegistry:
        """Create a test catalog instance."""
        return ContextCatalogRegistry({
            "file_storage_path": "test_storage"
        })
    
    @pytest.mark.asyncio
    async def test_register_knowledge_base_data(self, catalog):
        """Test registering knowledge base data with proper context."""
        # Create knowledge base entry
        kb_metadata = ContextMetadata(
            source_type=SourceType.KNOWLEDGE_BASE,
            data_type=DataType.TEXT,
            domain="machine_learning",
            purpose="ML model documentation",
            storage_info=StorageInfo(
                backend=StorageBackend.MEMORY,
                location="ml_docs",
                format="json"
            ),
            access_control=AccessControl(
                level=AccessLevel.SHARED,
                owner_id="ml_team"
            ),
            tags=["ml", "documentation", "models"],
            description="Documentation for ML models and their performance"
        )
        
        content = {
            "model_name": "ResNet50",
            "description": "Image classification model",
            "performance": {"accuracy": 0.95}
        }
        
        # Register the entry
        kb_id = await catalog.register_context(
            content=content,
            metadata=kb_metadata
        )
        
        # Verify registration
        entry = await catalog.get_context_info(kb_id)
        assert entry.metadata.source_type == SourceType.KNOWLEDGE_BASE
        assert entry.metadata.domain == "machine_learning"
        assert "ml" in entry.metadata.tags
        
        # Verify content is stored correctly
        stored_content = await catalog.storage_manager.retrieve_context(
            entry.storage_info
        )
        assert stored_content["model_name"] == "ResNet50"
    
    @pytest.mark.asyncio
    async def test_register_vector_store_data(self, catalog):
        """Test registering vector store data with proper context."""
        # Create vector store entry
        vs_metadata = ContextMetadata(
            source_type=SourceType.VECTOR_STORE,
            data_type=DataType.VECTOR,
            domain="embeddings",
            purpose="Document embeddings storage",
            storage_info=StorageInfo(
                backend=StorageBackend.MEMORY,
                location="embeddings",
                format="json"
            ),
            access_control=AccessControl(
                level=AccessLevel.PRIVATE,
                owner_id="nlp_team"
            ),
            tags=["embeddings", "nlp", "vectors"],
            description="Document embeddings for semantic search"
        )
        
        content = {
            "vectors": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
            "documents": ["doc1", "doc2"],
            "model": "sentence-transformers"
        }
        
        # Register the entry
        vs_id = await catalog.register_context(
            content=content,
            metadata=vs_metadata
        )
        
        # Verify registration
        entry = await catalog.get_context_info(vs_id)
        assert entry.metadata.source_type == SourceType.VECTOR_STORE
        assert entry.metadata.domain == "embeddings"
        assert "vectors" in entry.metadata.tags
    
    @pytest.mark.asyncio
    async def test_track_data_relationships(self, catalog):
        """Test tracking relationships between different data contexts."""
        # Create source code entry
        code_metadata = ContextMetadata(
            source_type=SourceType.CODE,
            data_type=DataType.CODE,
            domain="ml_training",
            purpose="Training script for ResNet50",
            storage_info=StorageInfo(
                backend=StorageBackend.MEMORY,
                location="code",
                format="python"
            ),
            access_control=AccessControl(
                level=AccessLevel.PRIVATE,
                owner_id="ml_engineer"
            ),
            tags=["training", "ml", "code"]
        )
        
        code_content = """
        def train_resnet():
            model = ResNet50()
            train(model, data)
        """
        
        code_id = await catalog.register_context(
            content=code_content,
            metadata=code_metadata
        )
        
        # Create model weights entry
        weights_metadata = ContextMetadata(
            source_type=SourceType.SYSTEM,
            data_type=DataType.BINARY,
            domain="ml_models",
            purpose="Trained ResNet50 weights",
            storage_info=StorageInfo(
                backend=StorageBackend.MEMORY,
                location="weights",
                format="h5"
            ),
            access_control=AccessControl(
                level=AccessLevel.PRIVATE,
                owner_id="ml_engineer"
            ),
            tags=["weights", "ml", "trained"]
        )
        
        weights_content = {
            "format": "h5",
            "size": "98MB",
            "parameters": "23M"
        }
        
        weights_id = await catalog.register_context(
            content=weights_content,
            metadata=weights_metadata
        )
        
        # Add relationship: code produces weights
        await catalog.add_relationship(
            code_id,
            weights_id,
            relationship_type="produces"
        )
        
        # Verify relationship
        relationships = await catalog.get_related_contexts(code_id)
        assert weights_id in relationships["dependencies"]
        
        # Verify bidirectional tracking
        reverse_relationships = await catalog.get_related_contexts(weights_id)
        assert code_id in reverse_relationships["dependents"]
    
    @pytest.mark.asyncio
    async def test_data_usage_tracking(self, catalog):
        """Test tracking how data is used across the system."""
        # Create a data entry
        data_metadata = ContextMetadata(
            source_type=SourceType.KNOWLEDGE_BASE,
            data_type=DataType.TEXT,
            domain="documentation",
            purpose="API documentation",
            storage_info=StorageInfo(
                backend=StorageBackend.MEMORY,
                location="docs",
                format="json"
            ),
            access_control=AccessControl(
                level=AccessLevel.PUBLIC,
                owner_id="docs_team"
            ),
            tags=["api", "docs"]
        )
        
        content = {
            "endpoint": "/api/v1/data",
            "description": "Data management endpoint"
        }
        
        data_id = await catalog.register_context(
            content=content,
            metadata=data_metadata
        )
        
        # Simulate different usage patterns
        for _ in range(3):
            await catalog.get_context_info(
                data_id,
                user_id="user1"
            )
        
        for _ in range(2):
            await catalog.get_context_info(
                data_id,
                user_id="user2"
            )
        
        # Update content
        await catalog.update_context(
            data_id,
            {"content": {**content, "version": "1.1"}},
            user_id="docs_team"
        )
        
        # Verify usage tracking
        entry = await catalog.get_context_info(data_id)
        assert entry.usage_stats.access_count == 6  # 5 reads + 1 update
        assert "read" in entry.usage_stats.operation_counts
        assert entry.usage_stats.operation_counts["read"] == 5
        assert "update" in entry.usage_stats.operation_counts
        
        # Verify access history
        assert len(entry.access_history) == 6
        assert any(
            record.user_id == "user1"
            for record in entry.access_history
        )
        assert any(
            record.user_id == "user2"
            for record in entry.access_history
        )
    
    @pytest.mark.asyncio
    async def test_data_discovery(self, catalog):
        """Test discovering data contexts based on metadata."""
        # Register multiple entries
        entries = [
            (
                "ML Model",
                ContextMetadata(
                    source_type=SourceType.KNOWLEDGE_BASE,
                    data_type=DataType.TEXT,
                    domain="machine_learning",
                    purpose="Model documentation",
                    storage_info=StorageInfo(
                        backend=StorageBackend.MEMORY,
                        location="ml",
                        format="json"
                    ),
                    access_control=AccessControl(
                        level=AccessLevel.PUBLIC,
                        owner_id="ml_team"
                    ),
                    tags=["ml", "model"]
                )
            ),
            (
                "Training Data",
                ContextMetadata(
                    source_type=SourceType.VECTOR_STORE,
                    data_type=DataType.VECTOR,
                    domain="machine_learning",
                    purpose="Training data embeddings",
                    storage_info=StorageInfo(
                        backend=StorageBackend.MEMORY,
                        location="data",
                        format="json"
                    ),
                    access_control=AccessControl(
                        level=AccessLevel.PRIVATE,
                        owner_id="ml_team"
                    ),
                    tags=["ml", "data", "training"]
                )
            ),
            (
                "API Docs",
                ContextMetadata(
                    source_type=SourceType.KNOWLEDGE_BASE,
                    data_type=DataType.TEXT,
                    domain="documentation",
                    purpose="API documentation",
                    storage_info=StorageInfo(
                        backend=StorageBackend.MEMORY,
                        location="docs",
                        format="json"
                    ),
                    access_control=AccessControl(
                        level=AccessLevel.PUBLIC,
                        owner_id="docs_team"
                    ),
                    tags=["api", "docs"]
                )
            )
        ]
        
        for name, metadata in entries:
            await catalog.register_context(
                content={"name": name},
                metadata=metadata
            )
        
        # Search by domain
        ml_entries = await catalog.search_contexts(
            domain="machine_learning"
        )
        assert len(ml_entries) == 2
        assert all(
            entry.metadata.domain == "machine_learning"
            for entry in ml_entries
        )
        
        # Search by tags
        ml_model_entries = await catalog.search_contexts(
            tags=["ml", "model"]
        )
        assert len(ml_model_entries) == 1
        assert "model" in ml_model_entries[0].metadata.tags
        
        # Search by source type
        kb_entries = await catalog.search_contexts(
            source_type=SourceType.KNOWLEDGE_BASE
        )
        assert len(kb_entries) == 2
        assert all(
            entry.metadata.source_type == SourceType.KNOWLEDGE_BASE
            for entry in kb_entries
        )
        
        # Search by access level
        public_entries = await catalog.search_contexts(
            access_level=AccessLevel.PUBLIC
        )
        assert len(public_entries) == 2
        assert all(
            entry.metadata.access_control.level == AccessLevel.PUBLIC
            for entry in public_entries
        ) 