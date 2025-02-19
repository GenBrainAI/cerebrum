"""Example usage of the Context Catalog System."""

import asyncio
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


async def main():
    """Demonstrate Context Catalog System usage."""
    # Initialize registry
    storage_config = {
        "file_storage_path": "example_storage"
    }
    registry = ContextCatalogRegistry(storage_config)
    
    # Create metadata for a knowledge base entry
    kb_metadata = ContextMetadata(
        source_type=SourceType.KNOWLEDGE_BASE,
        data_type=DataType.TEXT,
        domain="machine_learning",
        purpose="Store ML model documentation",
        storage_info=StorageInfo(
            backend=StorageBackend.FILE,
            location="ml_docs",
            format="json"
        ),
        access_control=AccessControl(
            level=AccessLevel.SHARED,
            owner_id="admin",
            allowed_users=["data_scientist1", "data_scientist2"],
            expiration=datetime.utcnow() + timedelta(days=30)
        ),
        tags=["machine_learning", "documentation", "models"]
    )
    
    # Register knowledge base content
    kb_content = {
        "model_name": "ResNet50",
        "description": "Deep residual learning model for image recognition",
        "parameters": {
            "layers": 50,
            "input_shape": [224, 224, 3],
            "output_classes": 1000
        },
        "performance_metrics": {
            "accuracy": 0.76,
            "top_5_accuracy": 0.92
        }
    }
    
    kb_id = await registry.register_context(
        content=kb_content,
        metadata=kb_metadata,
        user_id="admin"
    )
    print(f"Registered knowledge base context: {kb_id}")
    
    # Create metadata for a code context
    code_metadata = ContextMetadata(
        source_type=SourceType.CODE,
        data_type=DataType.CODE,
        domain="machine_learning",
        purpose="ResNet50 implementation",
        storage_info=StorageInfo(
            backend=StorageBackend.FILE,
            location="ml_code",
            format="python"
        ),
        access_control=AccessControl(
            level=AccessLevel.PRIVATE,
            owner_id="data_scientist1"
        ),
        tags=["machine_learning", "code", "resnet"]
    )
    
    # Register code content
    code_content = """
    def create_resnet50():
        model = ResNet50(
            include_top=True,
            weights='imagenet',
            input_shape=(224, 224, 3),
            classes=1000
        )
        return model
    """
    
    code_id = await registry.register_context(
        content=code_content,
        metadata=code_metadata,
        user_id="data_scientist1"
    )
    print(f"Registered code context: {code_id}")
    
    # Add relationship between contexts
    await registry.add_relationship(
        code_id,
        kb_id,
        user_id="data_scientist1"
    )
    print("Added relationship between code and knowledge base contexts")
    
    # Retrieve and display context information
    kb_entry = await registry.get_context_info(
        kb_id,
        include_relationships=True,
        user_id="data_scientist1"
    )
    print("\nKnowledge Base Context:")
    print(f"ID: {kb_entry.id}")
    print(f"Domain: {kb_entry.metadata.domain}")
    print(f"Tags: {kb_entry.metadata.tags}")
    print(f"Access Level: {kb_entry.metadata.access_control.level}")
    
    code_entry = await registry.get_context_info(
        code_id,
        include_relationships=True,
        user_id="data_scientist1"
    )
    print("\nCode Context:")
    print(f"ID: {code_entry.id}")
    print(f"Domain: {code_entry.metadata.domain}")
    print(f"Tags: {code_entry.metadata.tags}")
    print(f"Dependencies: {code_entry.relationships.dependencies}")
    
    # Update knowledge base content
    kb_updates = {
        "content": {
            **kb_content,
            "performance_metrics": {
                "accuracy": 0.78,
                "top_5_accuracy": 0.94
            }
        }
    }
    
    await registry.update_context(
        kb_id,
        kb_updates,
        user_id="admin"
    )
    print("\nUpdated knowledge base performance metrics")
    
    # Get related contexts
    related = await registry.get_related_contexts(
        kb_id,
        user_id="admin"
    )
    print("\nContexts related to knowledge base:")
    print(f"Dependents: {related['dependents']}")
    print(f"Dependencies: {related['dependencies']}")


if __name__ == "__main__":
    asyncio.run(main()) 