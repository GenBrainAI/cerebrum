import pytest
import os
from typing import Dict, Any
from pathlib import Path

from src.server.context.knowledge_base import KnowledgeBase

@pytest.fixture
def knowledge_base(tmp_path):
    """Create a test knowledge base instance."""
    kb = KnowledgeBase(base_path=str(tmp_path / "test_kb"))
    return kb

@pytest.fixture
def sample_domain_knowledge() -> list[Dict[str, Any]]:
    """Sample knowledge entries for testing."""
    return [
        {
            "content": "Python is a high-level programming language.",
            "domain": "programming",
            "metadata": {
                "tags": ["python", "language"],
                "level": "beginner"
            }
        },
        {
            "content": "ChromaDB is a vector database for AI applications.",
            "domain": "databases",
            "metadata": {
                "tags": ["vector-db", "ai"],
                "level": "intermediate"
            }
        }
    ]

@pytest.mark.asyncio
async def test_knowledge_base_add_knowledge(knowledge_base, sample_domain_knowledge):
    """Test adding knowledge to knowledge base."""
    for entry in sample_domain_knowledge:
        entry_id = await knowledge_base.add_knowledge(
            content=entry["content"],
            domain=entry["domain"],
            metadata=entry["metadata"]
        )
        assert entry_id is not None

@pytest.mark.asyncio
async def test_knowledge_base_get_knowledge(knowledge_base, sample_domain_knowledge):
    """Test retrieving knowledge from knowledge base."""
    entry_ids = []
    for entry in sample_domain_knowledge:
        entry_id = await knowledge_base.add_knowledge(
            content=entry["content"],
            domain=entry["domain"],
            metadata=entry["metadata"]
        )
        entry_ids.append(entry_id)
    
    results = await knowledge_base.get_knowledge(domain="programming")
    assert len(results) > 0
    assert results[0]["domain"] == "programming"
    
    results = await knowledge_base.get_knowledge(metadata_filter={"tags": ["vector-db"]})
    assert len(results) > 0
    assert "vector-db" in results[0]["metadata"]["tags"]

@pytest.mark.asyncio
async def test_knowledge_base_export_import(knowledge_base, sample_domain_knowledge, tmp_path):
    """Test exporting and importing domain knowledge."""
    for entry in sample_domain_knowledge:
        await knowledge_base.add_knowledge(
            content=entry["content"],
            domain=entry["domain"],
            metadata=entry["metadata"]
        )
    
    export_path = await knowledge_base.export_domain(
        domain="programming",
        export_path=str(tmp_path / "export.json")
    )
    assert os.path.exists(export_path)
    
    new_kb = KnowledgeBase(base_path=str(tmp_path / "new_kb"))
    imported_count = await new_kb.import_domain(export_path)
    assert imported_count > 0
    
    results = await new_kb.get_knowledge(domain="programming")
    assert len(results) > 0

@pytest.mark.asyncio
async def test_knowledge_base_update_knowledge(knowledge_base, sample_domain_knowledge):
    """Test updating existing knowledge entries."""
    entry = sample_domain_knowledge[0]
    entry_id = await knowledge_base.add_knowledge(
        content=entry["content"],
        domain=entry["domain"],
        metadata=entry["metadata"]
    )
    
    updated_content = "Updated Python language description"
    success = await knowledge_base.update_knowledge(entry_id, updated_content)
    assert success
    
    entry = await knowledge_base.get_entry(entry_id)
    assert entry is not None
    assert entry["content"] == updated_content

@pytest.mark.asyncio
async def test_knowledge_base_delete_knowledge(knowledge_base, sample_domain_knowledge):
    """Test deleting existing knowledge entries."""
    entry = sample_domain_knowledge[0]
    entry_id = await knowledge_base.add_knowledge(
        content=entry["content"],
        domain=entry["domain"],
        metadata=entry["metadata"]
    )
    
    success = await knowledge_base.delete_knowledge(entry_id)
    assert success
    
    entry = await knowledge_base.get_entry(entry_id)
    assert entry is None