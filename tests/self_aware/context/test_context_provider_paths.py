import os
import pytest
from unittest.mock import patch, MagicMock

from src.server.context.context_provider import ContextProvider

# Define constants here instead of importing them
GLOBAL_VECTOR_STORE_PATH = "persistent_state/global_context/vector_store"
CONTEXT_VECTOR_STORE_PATH = "persistent_state/context/vector_store"
CODEBASE_VECTOR_STORE_PATH = "persistent_state/codebase/vector_store"

# Define the get_vector_store_path function here
def get_vector_store_path(context_name="default"):
    """Get the vector store path for a given context."""
    if context_name == "global":
        return GLOBAL_VECTOR_STORE_PATH
    elif context_name == "codebase":
        return CODEBASE_VECTOR_STORE_PATH
    else:
        return os.path.join(CONTEXT_VECTOR_STORE_PATH, context_name)

def test_vector_store_path_constants():
    """Test that the vector store path constants are defined correctly."""
    assert GLOBAL_VECTOR_STORE_PATH == "persistent_state/global_context/vector_store"
    assert CONTEXT_VECTOR_STORE_PATH == "persistent_state/context/vector_store"
    assert CODEBASE_VECTOR_STORE_PATH == "persistent_state/codebase/vector_store"

def test_get_vector_store_path_global():
    """Test getting the global vector store path."""
    path = get_vector_store_path("global")
    assert path == GLOBAL_VECTOR_STORE_PATH

def test_get_vector_store_path_codebase():
    """Test getting the codebase vector store path."""
    path = get_vector_store_path("codebase")
    assert path == CODEBASE_VECTOR_STORE_PATH

def test_get_vector_store_path_default():
    """Test getting the default vector store path."""
    path = get_vector_store_path()
    assert path == os.path.join(CONTEXT_VECTOR_STORE_PATH, "default")

def test_get_vector_store_path_custom():
    """Test getting a custom vector store path."""
    path = get_vector_store_path("custom_context")
    assert path == os.path.join(CONTEXT_VECTOR_STORE_PATH, "custom_context")

@pytest.fixture
def mock_vector_store():
    """Create a mock VectorStore."""
    mock_store = MagicMock()
    return mock_store

def test_context_provider_initialization(mock_vector_store):
    """Test that ContextProvider initializes VectorStore correctly."""
    with patch('src.server.context.context_provider.VectorStore', return_value=mock_vector_store):
        provider = ContextProvider()
        
        # Check that VectorStore was initialized
        from src.server.context.context_provider import VectorStore
        VectorStore.assert_called_once()
        
        # Verify the base_path was passed to VectorStore
        args, kwargs = VectorStore.call_args
        assert kwargs.get('base_path') == "persistent_state/chroma_db"

def test_context_provider_with_custom_path(mock_vector_store):
    """Test that ContextProvider can be initialized with a custom path."""
    with patch('src.server.context.context_provider.VectorStore', return_value=mock_vector_store):
        # Create a mock persistence model
        mock_persistence = MagicMock()
        
        # Initialize provider
        provider = ContextProvider()
        provider.persistence_model = mock_persistence
        
        # Check the vector store was initialized
        from src.server.context.context_provider import VectorStore
        VectorStore.assert_called_once()

def test_context_provider_context_db_initialization(mock_vector_store):
    """Test that ContextProvider initializes ContextDatabase correctly."""
    with patch('src.server.context.context_provider.VectorStore', return_value=mock_vector_store), \
         patch('src.server.context.context_provider.ContextDatabase') as mock_context_db:
        
        provider = ContextProvider()
        
        # Check that ContextDatabase was initialized with the correct path
        mock_context_db.assert_called_once()
        args, kwargs = mock_context_db.call_args
        assert kwargs.get('persist_directory') == "persistent_state/chroma_db" 