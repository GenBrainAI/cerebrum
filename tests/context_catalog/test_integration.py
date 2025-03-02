"""Tests for the Cerebrum Data Catalog integration."""

import pytest
import pytest_asyncio
from typing import Dict, Any, List
from datetime import datetime

from src.context_catalog.integration import CerebrumDataCatalog
from src.context_catalog.metadata import AccessLevel
from src.context_catalog.exceptions import AccessError


@pytest_asyncio.fixture
async def catalog():
    """Create a test catalog instance."""
    return CerebrumDataCatalog(
        storage_path="test_cerebrum_data",
        default_owner="test_system"
    )


class TestCerebrumIntegration:
    """Test Cerebrum integration functionality."""
    
    @pytest.mark.asyncio
    async def test_knowledge_base_workflow(self, catalog: CerebrumDataCatalog):
        """Test complete knowledge base workflow."""
        # Register knowledge base entry
        kb_id = await catalog.register_knowledge_base(
            content={
                "title": "ML Best Practices",
                "content": "Best practices for machine learning..."
            },
            domain="machine_learning",
            purpose="Documentation",
            tags=["ml", "best_practices"],
            description="ML best practices guide",
            access_level=AccessLevel.SHARED,
            owner_id="ml_team"
        )
        
        # Find by domain
        ml_entries = await catalog.find_by_domain("machine_learning")
        assert len(ml_entries) == 1
        assert ml_entries[0].metadata.domain == "machine_learning"
        
        # Find by tags
        tagged_entries = await catalog.find_by_tags(["ml"])
        assert len(tagged_entries) == 1
        assert "ml" in tagged_entries[0].metadata.tags
        
        # Find specifically knowledge base entries
        kb_entries = await catalog.find_knowledge_base(
            tags=["best_practices"]
        )
        assert len(kb_entries) == 1
        assert kb_entries[0].metadata.source_type == "knowledge_base"
    
    @pytest.mark.asyncio
    async def test_vector_store_workflow(self, catalog: CerebrumDataCatalog):
        """Test complete vector store workflow."""
        # Register vector store entry
        vectors = [[0.1, 0.2], [0.3, 0.4]]
        documents = ["doc1", "doc2"]
        model_info = {"name": "bert", "version": "1.0"}
        
        vs_id = await catalog.register_vector_store(
            vectors=vectors,
            documents=documents,
            model_info=model_info,
            domain="embeddings",
            purpose="Document embeddings",
            tags=["embeddings", "bert"],
            description="BERT embeddings for documents",
            owner_id="nlp_team"
        )
        
        # Find vector store entries
        vs_entries = await catalog.find_vector_store(
            tags=["embeddings"]
        )
        assert len(vs_entries) == 1
        assert vs_entries[0].metadata.source_type == "vector_store"
        
        # Get usage stats
        stats = await catalog.get_usage_stats(vs_id)
        assert stats["access_count"] > 0
        assert "read" in stats["operation_counts"]
    
    @pytest.mark.asyncio
    async def test_code_and_system_relationship(
        self,
        catalog: CerebrumDataCatalog
    ):
        """Test relationships between code and system contexts."""
        # Register training code
        code_id = await catalog.register_code_context(
            code="def train(): pass",
            domain="training",
            purpose="Model training code",
            tags=["training", "code"],
            description="Training script",
            owner_id="ml_engineer"
        )
        
        # Register model weights
        weights_id = await catalog.register_system_context(
            content={"weights": "binary_data"},
            domain="model_artifacts",
            purpose="Trained model weights",
            data_format="h5",
            tags=["weights", "trained"],
            description="Trained model weights",
            owner_id="ml_engineer"
        )
        
        # Link code to weights
        await catalog.link_contexts(code_id, weights_id)
        
        # Get related data
        related = await catalog.get_related_data(code_id)
        assert len(related["dependencies"]) == 1
        assert related["dependencies"][0].metadata.tags == ["weights", "trained"]
    
    @pytest.mark.asyncio
    async def test_multi_user_access(self, catalog: CerebrumDataCatalog):
        """Test multi-user access patterns."""
        # Admin creates public resource
        kb_id = await catalog.register_knowledge_base(
            content={"guide": "User guide"},
            domain="documentation",
            purpose="User documentation",
            tags=["docs"],
            access_level=AccessLevel.PUBLIC,
            owner_id="admin"
        )
        
        # Different users access the resource
        users = ["user1", "user2", "user3"]
        for user in users:
            entries = await catalog.find_by_domain(
                "documentation",
                user_id=user
            )
            assert len(entries) == 1
        
        # Check access stats
        stats = await catalog.get_usage_stats(kb_id)
        assert stats["access_count"] >= len(users)
        assert len(stats["access_history"]) >= len(users)
        
        # Verify different users in access history
        accessed_users = {
            record["user_id"]
            for record in stats["access_history"]
        }
        assert all(user in accessed_users for user in users)
    
    @pytest.mark.asyncio
    async def test_data_discovery(self, catalog: CerebrumDataCatalog):
        """Test comprehensive data discovery capabilities."""
        # Register various types of data
        test_data = [
            (
                "register_knowledge_base",
                {
                    "content": {"doc": "ML guide"},
                    "domain": "machine_learning",
                    "purpose": "Documentation",
                    "tags": ["ml", "guide"],
                    "access_level": AccessLevel.PUBLIC
                }
            ),
            (
                "register_vector_store",
                {
                    "vectors": [[0.1]],
                    "documents": ["doc"],
                    "model_info": {"name": "test"},
                    "domain": "machine_learning",
                    "purpose": "Embeddings",
                    "tags": ["ml", "embeddings"],
                    "access_level": AccessLevel.PRIVATE
                }
            ),
            (
                "register_code_context",
                {
                    "code": "def test(): pass",
                    "domain": "testing",
                    "purpose": "Test code",
                    "tags": ["test", "code"],
                    "access_level": AccessLevel.SHARED
                }
            )
        ]
        
        for method_name, params in test_data:
            method = getattr(catalog, method_name)
            await method(**params)
        
        # Test domain-based discovery
        ml_entries = await catalog.find_by_domain("machine_learning")
        assert len(ml_entries) == 2
        
        # Test tag-based discovery
        ml_tagged = await catalog.find_by_tags(["ml"])
        assert len(ml_tagged) == 2
        
        # Test combined criteria
        kb_entries = await catalog.find_knowledge_base(
            domain="machine_learning",
            tags=["guide"]
        )
        assert len(kb_entries) == 1 