import pytest
import os
from typing import Dict, Any

from src.server.context.knowledge_base import KnowledgeBase

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
    
    results = knowledge_base.get_knowledge(domain="programming")
    assert len(results) > 0
    assert results[0]["domain"] == "programming"
    
    results = knowledge_base.get_knowledge(tags=["vector-db"])
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
    
    export_path = knowledge_base.export_domain(  # Remove await
        domain="programming",
        export_path=str(tmp_path / "export.json")
    )
    assert os.path.exists(export_path)
    
    new_kb = KnowledgeBase(str(tmp_path / "new_kb"))
    imported_count = await new_kb.import_domain(export_path)
    assert imported_count > 0
    
    results = new_kb.get_knowledge(domain="programming")
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
    updated_metadata = {**entry["metadata"], "updated": True}
    
    updated_entry = await knowledge_base.update_knowledge(
        entry_id=entry_id,
        content=updated_content,
        metadata=updated_metadata
    )
    
    assert updated_entry["content"] == updated_content
    assert updated_entry["metadata"]["updated"] == True

@pytest.mark.asyncio
async def test_knowledge_base_delete_knowledge(knowledge_base, sample_domain_knowledge):
    """Test deleting knowledge entries."""
    entry = sample_domain_knowledge[0]
    entry_id = await knowledge_base.add_knowledge(
        content=entry["content"],
        domain=entry["domain"],
        metadata=entry["metadata"]
    )
    
    success = await knowledge_base.delete_knowledge(entry_id)
    assert success
    
    results = knowledge_base.get_knowledge(entry_id=entry_id)
    assert len(results) == 0