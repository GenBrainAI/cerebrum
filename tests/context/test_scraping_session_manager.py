import pytest
import asyncio
from pathlib import Path
import shutil
from datetime import datetime
import tempfile

from src.server.context.scraping_session_manager import ScrapingSessionManager
from src.server.models.scraping_session import ScrapingSession, ScrapingTargetType, ScrapingContentType

@pytest.fixture
def test_base_path(tmp_path):
    """Create a temporary directory for test data."""
    test_dir = tmp_path / "test_scraping_sessions"
    test_dir.mkdir()
    yield str(test_dir)
    shutil.rmtree(str(test_dir))

@pytest.fixture
def manager(test_base_path):
    """Create a test session manager."""
    return ScrapingSessionManager(base_path=test_base_path)

def test_create_session(manager):
    """Test creating a new session."""
    session = manager.create_session(
        name="Test Session",
        description="Test description",
        target_type=ScrapingTargetType.KNOWLEDGE_BASE,
        content_type=ScrapingContentType.WEB
    )
    
    assert session.name == "Test Session"
    assert session.id in manager.sessions
    assert len(manager.sessions) == 1

def test_get_session(manager):
    """Test retrieving a session."""
    session = manager.create_session(name="Test Session")
    retrieved = manager.get_session(session.id)
    
    assert retrieved is not None
    assert retrieved.id == session.id
    assert retrieved.name == session.name

def test_list_sessions(manager):
    """Test listing sessions with filters."""
    # Create sessions with different types
    manager.create_session(
        name="KB Session",
        target_type=ScrapingTargetType.KNOWLEDGE_BASE
    )
    manager.create_session(
        name="VS Session",
        target_type=ScrapingTargetType.VECTOR_STORE
    )
    manager.create_session(
        name="Code Session",
        target_type=ScrapingTargetType.CODE
    )
    
    # Test filtering
    kb_sessions = manager.list_sessions(target_type=ScrapingTargetType.KNOWLEDGE_BASE)
    vs_sessions = manager.list_sessions(target_type=ScrapingTargetType.VECTOR_STORE)
    code_sessions = manager.list_sessions(target_type=ScrapingTargetType.CODE)
    
    assert len(kb_sessions) == 1
    assert len(vs_sessions) == 1
    assert len(code_sessions) == 1
    assert kb_sessions[0].name == "KB Session"
    assert vs_sessions[0].name == "VS Session"
    assert code_sessions[0].name == "Code Session"

@pytest.mark.asyncio
async def test_process_entry(manager):
    """Test processing a scraped entry."""
    # Create test index first
    session_name = "Test Session"
    clean_name = manager._sanitize_index_name(session_name)
    print(f"\nDEBUG - Clean name: {clean_name}")
    
    # Create index with clean name (no vs_ prefix)
    manager.vector_store.create_index(clean_name, "Test index for scraping")
    
    # Create session
    session = manager.create_session(
        name=session_name,
        target_type=ScrapingTargetType.MULTI
    )

    # Enable all targets
    session.enable_target(ScrapingTargetType.KNOWLEDGE_BASE)
    session.enable_target(ScrapingTargetType.VECTOR_STORE)
    session.enable_target(ScrapingTargetType.CODE)

    # Create test entry with code block
    code_content = "def test(): pass"
    entry = {
        "content": "Test content",
        "metadata": {
            "title": "Test Entry",
            "source": "test.com"
        },
        "code_blocks": [
            {
                "language": "python",
                "content": code_content
            }
        ]
    }

    # Create a temporary directory for the code
    with tempfile.TemporaryDirectory() as temp_dir:
        # Write the code to a file
        code_file = Path(temp_dir) / "test.py"
        code_file.write_text(code_content)
        
        # Index the directory containing the code
        await manager.code_catalog.index_directory(
            directory_path=temp_dir,
            analyze_deps=True,
            parse_docs=True
        )

        # Process entry
        await manager.process_entry(session.id, entry)
        
        # Verify entry was added to session
        assert len(session.entries) == 1
        assert session.entries[0]["content"] == "Test content"

@pytest.mark.asyncio
async def test_delete_session(manager):
    """Test deleting a session."""
    session = manager.create_session(name="Test Session")
    
    # Add some content
    entry = {
        "content": "Test content",
        "metadata": {"title": "Test"}
    }
    await manager.process_entry(session.id, entry)
    
    # Delete session without content
    success = await manager.delete_session(session.id, delete_content=False)
    assert success
    assert session.id not in manager.sessions
    
    # Create new session and test deleting with content
    session = manager.create_session(name="Test Session 2")
    await manager.process_entry(session.id, entry)
    success = await manager.delete_session(session.id, delete_content=True)
    assert success
    assert session.id not in manager.sessions

def test_persistence(test_base_path):
    """Test session persistence."""
    # Create manager and session
    manager1 = ScrapingSessionManager(base_path=test_base_path)
    session = manager1.create_session(name="Test Session")
    session_id = session.id
    
    # Create new manager instance
    manager2 = ScrapingSessionManager(base_path=test_base_path)
    
    # Verify session was loaded
    loaded_session = manager2.get_session(session_id)
    assert loaded_session is not None
    assert loaded_session.name == "Test Session" 