"""Example of integrating the Data Catalog with Cerebrum."""

import asyncio
from typing import Dict, Any, List
from datetime import datetime

from src.context_catalog.integration import CerebrumDataCatalog
from src.context_catalog.metadata import AccessLevel


async def main():
    """Demonstrate integration with Cerebrum."""
    # Initialize catalog
    catalog = CerebrumDataCatalog(
        storage_path="cerebrum_data",
        default_owner="cerebrum_system"
    )
    
    # Example 1: Managing ML Model Knowledge
    print("\n=== Example 1: ML Model Knowledge Management ===")
    
    # Register model documentation
    model_doc_id = await catalog.register_knowledge_base(
        content={
            "model_name": "GPT-4",
            "description": "Advanced language model",
            "capabilities": [
                "Text generation",
                "Code completion",
                "Question answering"
            ],
            "performance_metrics": {
                "accuracy": 0.95,
                "latency": "100ms"
            }
        },
        domain="language_models",
        purpose="Model documentation and capabilities",
        tags=["gpt4", "language_model", "documentation"],
        description="Documentation for GPT-4 model",
        access_level=AccessLevel.SHARED,
        owner_id="ai_team"
    )
    print(f"Registered model documentation: {model_doc_id}")
    
    # Register model embeddings
    embeddings_id = await catalog.register_vector_store(
        vectors=[
            [0.1, 0.2, 0.3],  # Example embeddings
            [0.4, 0.5, 0.6]
        ],
        documents=[
            "GPT-4 is an advanced language model",
            "The model excels at text generation"
        ],
        model_info={
            "embedding_model": "sentence-transformers",
            "dimension": 3
        },
        domain="language_models",
        purpose="Model description embeddings",
        tags=["gpt4", "embeddings"],
        description="Vector embeddings for model documentation",
        owner_id="ai_team"
    )
    print(f"Registered model embeddings: {embeddings_id}")
    
    # Link documentation and embeddings
    await catalog.link_contexts(model_doc_id, embeddings_id)
    print("Linked documentation with embeddings")
    
    # Example 2: Code and System Artifacts
    print("\n=== Example 2: Code and System Artifacts ===")
    
    # Register training code
    training_code_id = await catalog.register_code_context(
        code="""
        def train_model(config):
            model = load_model(config)
            data = load_training_data()
            trained_model = train(model, data)
            save_model(trained_model)
        """,
        domain="model_training",
        purpose="GPT-4 training code",
        tags=["training", "gpt4", "code"],
        description="Training script for GPT-4",
        owner_id="ml_engineer"
    )
    print(f"Registered training code: {training_code_id}")
    
    # Register model weights
    weights_id = await catalog.register_system_context(
        content={
            "format": "pytorch",
            "size": "350GB",
            "parameters": "175B",
            "checkpoint": "path/to/weights"
        },
        domain="model_artifacts",
        purpose="Trained model weights",
        data_format="pytorch",
        tags=["weights", "gpt4", "trained"],
        description="Trained weights for GPT-4",
        owner_id="ml_engineer"
    )
    print(f"Registered model weights: {weights_id}")
    
    # Link code and weights
    await catalog.link_contexts(training_code_id, weights_id)
    print("Linked training code with weights")
    
    # Example 3: Data Discovery
    print("\n=== Example 3: Data Discovery ===")
    
    # Find all GPT-4 related data
    gpt4_data = await catalog.find_by_tags(["gpt4"])
    print(f"\nFound {len(gpt4_data)} GPT-4 related entries:")
    for entry in gpt4_data:
        print(f"- {entry.metadata.purpose} ({entry.metadata.source_type})")
    
    # Find model documentation
    kb_entries = await catalog.find_knowledge_base(
        domain="language_models"
    )
    print(f"\nFound {len(kb_entries)} knowledge base entries:")
    for entry in kb_entries:
        print(f"- {entry.metadata.purpose}")
    
    # Example 4: Usage Analysis
    print("\n=== Example 4: Usage Analysis ===")
    
    # Get usage stats for model documentation
    doc_stats = await catalog.get_usage_stats(model_doc_id)
    print("\nModel documentation usage:")
    print(f"- Access count: {doc_stats['access_count']}")
    print(f"- Last accessed: {doc_stats['last_accessed']}")
    print("- Operations:", doc_stats['operation_counts'])
    
    # Get related data
    related_data = await catalog.get_related_data(model_doc_id)
    print("\nData related to model documentation:")
    print(f"- Dependencies: {len(related_data['dependencies'])}")
    print(f"- Dependents: {len(related_data['dependents'])}")


if __name__ == "__main__":
    asyncio.run(main()) 