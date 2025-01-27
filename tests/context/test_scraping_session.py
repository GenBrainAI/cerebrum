import pytest
from datetime import datetime
from src.server.models.scraping_session import ScrapingSession, ScrapingTargetType, ScrapingContentType

def test_create_session():
    """Test creating a new scraping session."""
    session = ScrapingSession(
        name="Test Session",
        description="Test description",
        target_type=ScrapingTargetType.KNOWLEDGE_BASE,
        content_type=ScrapingContentType.WEB
    )
    
    assert session.name == "Test Session"
    assert session.description == "Test description"
    assert session.target_type == ScrapingTargetType.KNOWLEDGE_BASE
    assert session.content_type == ScrapingContentType.WEB
    assert session.status == "active"
    assert len(session.entries) == 0

def test_add_entry():
    """Test adding an entry to a session."""
    session = ScrapingSession(name="Test Session")
    entry = {
        "content": "Test content",
        "metadata": {"source": "test.com"}
    }
    
    session.add_entry(entry)
    assert len(session.entries) == 1
    assert session.entries[0]["content"] == "Test content"
    assert "added_at" in session.entries[0]
    assert "session_id" in session.entries[0]

def test_enable_disable_target():
    """Test enabling and disabling targets."""
    session = ScrapingSession(
        name="Test Session",
        target_type=ScrapingTargetType.KNOWLEDGE_BASE
    )
    
    # Initially only knowledge base should be enabled
    assert session.target_configs[ScrapingTargetType.KNOWLEDGE_BASE]["enabled"]
    assert not session.target_configs[ScrapingTargetType.VECTOR_STORE]["enabled"]
    
    # Enable vector store
    session.enable_target(ScrapingTargetType.VECTOR_STORE)
    assert session.target_configs[ScrapingTargetType.VECTOR_STORE]["enabled"]
    assert session.target_type == ScrapingTargetType.MULTI
    
    # Disable knowledge base
    session.disable_target(ScrapingTargetType.KNOWLEDGE_BASE)
    assert not session.target_configs[ScrapingTargetType.KNOWLEDGE_BASE]["enabled"]
    assert session.target_type == ScrapingTargetType.VECTOR_STORE

def test_update_target_config():
    """Test updating target configuration."""
    session = ScrapingSession(name="Test Session")
    
    # Update vector store config
    session.update_target_config(
        ScrapingTargetType.VECTOR_STORE,
        {
            "chunk_size": 500,
            "chunk_overlap": 100
        }
    )
    
    config = session.target_configs[ScrapingTargetType.VECTOR_STORE]
    assert config["chunk_size"] == 500
    assert config["chunk_overlap"] == 100

def test_get_entries_by_type():
    """Test filtering entries by type."""
    session = ScrapingSession(name="Test Session")
    
    # Add entries of different types
    session.add_entry({
        "content": "Web content",
        "content_type": "web",
        "metadata": {}
    })
    session.add_entry({
        "content": "Code content",
        "content_type": "code",
        "metadata": {}
    })
    
    web_entries = session.get_entries_by_type("web")
    code_entries = session.get_entries_by_type("code")
    
    assert len(web_entries) == 1
    assert len(code_entries) == 1
    assert web_entries[0]["content"] == "Web content"
    assert code_entries[0]["content"] == "Code content"

def test_session_serialization():
    """Test converting session to and from dict."""
    session = ScrapingSession(
        name="Test Session",
        description="Test description",
        target_type=ScrapingTargetType.MULTI,
        content_type=ScrapingContentType.WEB
    )
    
    # Add an entry
    session.add_entry({
        "content": "Test content",
        "metadata": {"source": "test.com"}
    })
    
    # Convert to dict
    session_dict = session.to_dict()
    
    # Create new session from dict
    new_session = ScrapingSession.from_dict(session_dict)
    
    assert new_session.name == session.name
    assert new_session.description == session.description
    assert new_session.target_type == session.target_type
    assert new_session.content_type == session.content_type
    assert len(new_session.entries) == len(session.entries)
    assert new_session.entries[0]["content"] == session.entries[0]["content"] 