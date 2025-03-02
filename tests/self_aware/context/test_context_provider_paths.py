import os
import pytest
from unittest.mock import patch, MagicMock

from src.server.context.context_provider import (
    ContextProvider,
    get_vector_store_path,
    GLOBAL_VECTOR_STORE_PATH,
    CONTEXT_VECTOR_STORE_PATH,
    CODEBASE_VECTOR_STORE_PATH
)

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
def mock_chroma_vector_store():
    """Create a mock ChromaVectorStore."""
    mock_store = MagicMock()
    return mock_store

def test_context_provider_global_path(mock_chroma_vector_store):
    """Test that ContextProvider uses the correct path for global context."""
    with patch('src.server.context.context_provider.ChromaVectorStore', return_value=mock_chroma_vector_store):
        provider = ContextProvider(is_global=True)
        
        # Check that ChromaVectorStore was initialized with the correct path
        from src.server.context.context_provider import ChromaVectorStore
        ChromaVectorStore.assert_called_once()
        
        # Get the config argument from the call
        _, kwargs = ChromaVectorStore.call_args
        config = kwargs.get('config')
        
        # Check that the persist_directory is set to the global path
        assert config.persist_directory == GLOBAL_VECTOR_STORE_PATH
        assert kwargs.get('base_path') == GLOBAL_VECTOR_STORE_PATH

def test_context_provider_default_path(mock_chroma_vector_store):
    """Test that ContextProvider uses the correct path for default context."""
    with patch('src.server.context.context_provider.ChromaVectorStore', return_value=mock_chroma_vector_store):
        provider = ContextProvider(is_global=False)
        
        # Check that ChromaVectorStore was initialized with the correct path
        from src.server.context.context_provider import ChromaVectorStore
        ChromaVectorStore.assert_called_once()
        
        # Get the config argument from the call
        _, kwargs = ChromaVectorStore.call_args
        config = kwargs.get('config')
        
        # Check that the persist_directory is set to the default path
        default_path = os.path.join(CONTEXT_VECTOR_STORE_PATH, "default")
        assert config.persist_directory == default_path
        assert kwargs.get('base_path') == default_path

def test_context_provider_vector_store_config(mock_chroma_vector_store):
    """Test that ContextProvider configures the vector store correctly."""
    with patch('src.server.context.context_provider.ChromaVectorStore', return_value=mock_chroma_vector_store):
        provider = ContextProvider(is_global=False)
        
        # Check that ChromaVectorStore was initialized with the correct config
        from src.server.context.context_provider import ChromaVectorStore
        ChromaVectorStore.assert_called_once()
        
        # Get the config argument from the call
        _, kwargs = ChromaVectorStore.call_args
        config = kwargs.get('config')
        
        # Check the config parameters
        assert config.collection_name == "context"
        assert config.embedding_model == "text-embedding-3-small" 