import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime

from src.server.context.context_provider import ContextProvider
from src.server.models.task import Task
from src.server.models.message import Message


@pytest.fixture
def mock_persistence_model():
    """Create a mock persistence model for testing."""
    mock = MagicMock()
    mock.tasks = MagicMock()
    mock.tasks.read = MagicMock(return_value=None)
    mock.tasksmanagers = MagicMock()
    mock.tasksmanagers.read = MagicMock(return_value=None)
    mock.contexts = MagicMock()
    mock.contexts.create = AsyncMock()
    mock.contexts.read = AsyncMock(return_value=None)
    mock.contexts.read_many = AsyncMock(return_value=[])
    
    # Mock vector store contexts
    mock.vector_stores = MagicMock()
    mock.vector_stores.read_many = AsyncMock(return_value=[
        {
            "id": "vs1",
            "name": "Test Vector Store",
            "description": "A test vector store",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
    ])
    
    # Mock knowledge base contexts
    mock.knowledge_bases = MagicMock()
    mock.knowledge_bases.read_many = AsyncMock(return_value=[
        {
            "id": "kb1",
            "name": "Test Knowledge Base",
            "description": "A test knowledge base",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
    ])
    
    # Mock code contexts
    mock.code_repositories = MagicMock()
    mock.code_repositories.read_many = AsyncMock(return_value=[
        {
            "id": "repo1",
            "name": "Test Repository",
            "description": "A test repository",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
    ])
    
    return mock


@pytest.fixture
def context_provider(mock_persistence_model):
    """Create a context provider instance for testing."""
    provider = ContextProvider()
    provider.persistence_model = mock_persistence_model
    return provider


@pytest.mark.asyncio
async def test_get_contexts_basic(context_provider, mock_persistence_model):
    """Test basic context retrieval functionality."""
    # Mock task contexts
    mock_persistence_model.contexts.read_many.return_value = [
        {
            "id": "ctx1",
            "type": "system",
            "source_id": "system1",
            "content": "System context content",
            "metadata": {"source": "system"},
            "priority": 90
        }
    ]
    
    # Mock context database search
    context_provider.context_db = MagicMock()
    context_provider.context_db.search_context = AsyncMock(return_value=[
        {
            "id": "vs_item1",
            "content": "Vector store content",
            "metadata": {"source": "vector_store"},
            "relevance": 0.95
        }
    ])
    
    # Mock token calculation to return a fixed number
    with patch.object(context_provider, '_calculate_token_budget', return_value={'available_tokens': 6000, 'total_tokens': 8000}):
        # Get contexts
        contexts = await context_provider.get_contexts(
            query="Test query",
            model="gpt-4",
            task_id="task1"
        )
        
        # Check results - should have both system and vector contexts
        assert len(contexts) >= 1  # At least the vector context
        vector_contexts = [c for c in contexts if c["type"] == "vector"]
        assert len(vector_contexts) == 1


@pytest.mark.asyncio
async def test_get_contexts_token_limit(context_provider, mock_persistence_model):
    """Test that contexts are limited by available tokens."""
    # Create a long system context that will use most of the token space
    long_content = "System context " * 1000  # Approximately 2000 tokens
    
    # Mock task contexts
    mock_persistence_model.contexts.read_many.return_value = [
        {
            "id": "ctx1",
            "type": "system",
            "source_id": "system1",
            "content": long_content,
            "metadata": {"source": "system"},
            "priority": 90
        }
    ]
    
    # Mock context database search
    context_provider.context_db = MagicMock()
    context_provider.context_db.search_context = AsyncMock(return_value=[
        {
            "id": "vs_item1",
            "content": "Vector store content",
            "metadata": {"source": "vector_store"},
            "relevance": 0.95
        }
    ])
    
    # Mock token calculation to return a small number of available tokens
    with patch.object(context_provider, '_calculate_token_budget', return_value={'available_tokens': 10, 'total_tokens': 100}):
        with patch.object(context_provider, '_estimate_token_count', side_effect=lambda text: 5 if text == "Vector store content" else 2000):
            # Get contexts
            contexts = await context_provider.get_contexts(
                query="Test query",
                model="gpt-4",
                task_id="task1"
            )
            
            # Should only include the vector context due to token limits
            assert len(contexts) == 1
            assert contexts[0]["type"] == "vector"


@pytest.mark.asyncio
async def test_get_contexts_message_history(context_provider, mock_persistence_model):
    """Test that message history affects token calculation."""
    # Mock task contexts
    mock_persistence_model.contexts.read_many.return_value = [
        {
            "id": "ctx1",
            "type": "system",
            "source_id": "system1",
            "content": "System context content",
            "metadata": {"source": "system"},
            "priority": 90
        }
    ]
    
    # Create message history
    message_history = [
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there! How can I help you today?"},
        {"role": "user", "content": "Tell me about Python"}
    ]
    
    # Mock context database search
    context_provider.context_db = MagicMock()
    context_provider.context_db.search_context = AsyncMock(return_value=[
        {
            "id": "vs_item1",
            "content": "Vector store content",
            "metadata": {"source": "vector_store"},
            "relevance": 0.95
        }
    ])
    
    # Mock token calculation
    with patch.object(context_provider, '_calculate_token_budget') as mock_calc:
        mock_calc.return_value = {'available_tokens': 6000, 'total_tokens': 8000}
        
        # Get contexts with message history
        await context_provider.get_contexts(
            query="Test query",
            model="gpt-4",
            task_id="task1",
            message_history=message_history
        )
        
        # Check that _calculate_token_budget was called with the correct parameters
        mock_calc.assert_called_once()
        args = mock_calc.call_args.args
        assert args[0] == "gpt-4"  # model
        assert args[2] == message_history  # message_history


@pytest.mark.asyncio
async def test_get_contexts_different_models(context_provider, mock_persistence_model):
    """Test that different models have different token limits."""
    # Mock task contexts
    mock_persistence_model.contexts.read_many.return_value = [
        {
            "id": "ctx1",
            "type": "system",
            "source_id": "system1",
            "content": "System context content",
            "metadata": {"source": "system"},
            "priority": 90
        }
    ]

    # Mock context database search
    context_provider.context_db = MagicMock()
    context_provider.context_db.search_context = AsyncMock(return_value=[
        {
            "id": "vs_item1",
            "content": "Vector store content",
            "metadata": {"source": "vector_store"},
            "relevance": 0.95
        }
    ])

    # Test with different models
    with patch.object(context_provider, '_calculate_token_budget') as mock_calc:
        mock_calc.return_value = {'available_tokens': 6000, 'total_tokens': 8000}

        # GPT-4
        await context_provider.get_contexts(
            query="Test query",
            model="gpt-4",
            task_id="task1"
        )
        mock_calc.assert_called_once()
        assert mock_calc.call_args.args[0] == "gpt-4"  # First positional arg is model
        mock_calc.reset_mock()

        # GPT-3.5
        await context_provider.get_contexts(
            query="Test query",
            model="gpt-3.5-turbo",
            task_id="task1"
        )
        mock_calc.assert_called_once()
        assert mock_calc.call_args.args[0] == "gpt-3.5-turbo"
        mock_calc.reset_mock()

        # Claude
        await context_provider.get_contexts(
            query="Test query",
            model="claude-3-opus-20240229",
            task_id="task1"
        )
        mock_calc.assert_called_once()
        assert mock_calc.call_args.args[0] == "claude-3-opus-20240229"


@pytest.mark.asyncio
async def test_context_sorting_by_priority(context_provider, mock_persistence_model):
    """Test that contexts are sorted by priority."""
    # Create system contexts with different priorities
    system_contexts = [
        {
            "id": "ctx1",
            "type": "system",
            "source_id": "system1",
            "content": "Low priority system context",
            "metadata": {"source": "system"},
            "priority": 30
        },
        {
            "id": "ctx2",
            "type": "system",
            "source_id": "system2",
            "content": "High priority system context",
            "metadata": {"source": "system"},
            "priority": 90
        },
        {
            "id": "ctx3",
            "type": "system",
            "source_id": "system3",
            "content": "Medium priority system context",
            "metadata": {"source": "system"},
            "priority": 60
        }
    ]

    # Mock get_task_contexts to return different results based on context_types
    async def mock_get_task_contexts(task_id, context_types=None):
        if context_types == ["system"]:
            return system_contexts
        elif context_types is None:
            # Return all contexts when no specific type is requested
            return system_contexts
        else:
            return []  # No contexts for other types

    context_provider.get_task_contexts = AsyncMock(side_effect=mock_get_task_contexts)

    # Mock context database
    context_provider.context_db = MagicMock()
    context_provider.context_db.search_context = AsyncMock(return_value=[])

    # Mock token calculation to return a fixed number
    with patch.object(context_provider, '_calculate_token_budget', return_value={'available_tokens': 6000, 'total_tokens': 8000}):
        # Mock token estimation to return a small value so all contexts fit
        with patch.object(context_provider, '_estimate_token_count', return_value=10):
            # Get contexts
            contexts = await context_provider.get_contexts(
                query="Test query",
                model="gpt-4",
                task_id="task1"
            )

            # Check that contexts are sorted by priority (highest first)
            assert len(contexts) == 3
            assert contexts[0]["priority"] == 90  # High priority first
            assert contexts[1]["priority"] == 60  # Medium priority second 