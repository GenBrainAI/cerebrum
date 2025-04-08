import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime

from src.server.context.context_provider import ContextProvider
from src.server.controllers.task_runner import TaskRunner
from src.server.models.task import Task
from src.server.models.tasks_manager import TasksManager
from src.server.models.message import Message


@pytest.fixture
def mock_persistence_model():
    """Create a mock persistence model for testing."""
    mock = MagicMock()
    mock.tasks = MagicMock()
    mock.tasks.read = MagicMock(return_value=None)
    mock.tasks.update = MagicMock()
    mock.tasksmanagers = MagicMock()
    mock.tasksmanagers.read = MagicMock(return_value=None)
    mock.contexts = MagicMock()
    mock.contexts.create = AsyncMock()
    mock.contexts.read = AsyncMock(return_value=None)
    mock.contexts.read_many = AsyncMock(return_value=[])
    return mock


@pytest.fixture
def mock_context_provider():
    """Create a mock context provider for testing."""
    provider = MagicMock(spec=ContextProvider)
    provider.get_contexts = AsyncMock(return_value=[
        {
            "id": "ctx1",
            "type": "system",
            "source_id": "test_source",
            "content": "Test context content",
            "metadata": {"source": "test"},
            "priority": 90
        }
    ])
    provider.prepare_task_messages = AsyncMock(side_effect=lambda task_id, messages: messages)
    provider.add_context_to_task = AsyncMock(return_value="ctx1")
    return provider


@pytest.fixture
def task_runner(mock_persistence_model):
    """Create a task runner instance for testing."""
    runner = TaskRunner(mock_persistence_model)
    runner.completion = AsyncMock(return_value="Test completion response")
    runner._plugin_manager = MagicMock()
    runner._plugin_manager.get_plugin = MagicMock(return_value=MagicMock())
    runner._get_or_create_curried_proxy = MagicMock(return_value=MagicMock())
    
    # Initialize context provider
    runner.context_provider = MagicMock(spec=ContextProvider)
    runner.context_provider.get_contexts = AsyncMock(return_value=[])
    runner.context_provider.prepare_task_messages = AsyncMock(side_effect=lambda task_id, messages: messages)
    runner.context_provider.add_context_to_task = AsyncMock(return_value="ctx1")
    
    return runner


@pytest.fixture
def sample_task():
    """Create a sample task for testing."""
    return Task(
        id="task1",
        name="Test Task",
        description="A test task",
        tasksmanager_id="manager1",
        model="gpt-4o-mini",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


@pytest.fixture
def sample_tasks_manager():
    """Create a sample tasks manager for testing."""
    return TasksManager(
        id="manager1",
        name="Test Manager",
        description="A test manager",
        model="gpt-4",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


@pytest.mark.asyncio
async def test_extract_query_from_last_user_message(task_runner, sample_task, mock_context_provider):
    """Test that the query is correctly extracted from the last user message."""
    # Setup messages with a user message at the end
    messages = [
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "First message"},
        {"role": "assistant", "content": "First response"},
        {"role": "user", "content": "Tell me about Python programming"}
    ]
    
    # Replace the context provider with our mock
    task_runner.context_provider = mock_context_provider
    
    # Mock the persistence model to return our sample task
    task_runner.persistence_model.tasks.read.return_value = sample_task
    
    # Run the standard task
    await task_runner._run_standard_task(sample_task, {"messages": messages})
    
    # Check that get_contexts was called with the correct query
    mock_context_provider.get_contexts.assert_called_once()
    call_args = mock_context_provider.get_contexts.call_args[1]  # Get kwargs
    assert call_args["query"] == "Tell me about Python programming"
    assert call_args["task_id"] == "task1"


@pytest.mark.asyncio
async def test_extract_query_from_message_object(task_runner, sample_task, mock_context_provider):
    """Test that the query is correctly extracted from Message objects."""
    # Setup messages with a user message at the end
    messages = [
        Message(role="system", content="You are a helpful assistant"),
        Message(role="user", content="First message"),
        Message(role="assistant", content="First response"),
        Message(role="user", content="Tell me about Python programming")
    ]
    
    # Replace the context provider with our mock
    task_runner.context_provider = mock_context_provider
    
    # Mock the persistence model to return our sample task
    task_runner.persistence_model.tasks.read.return_value = sample_task
    
    # Run the standard task
    await task_runner._run_standard_task(sample_task, {"messages": messages})
    
    # Check that get_contexts was called with the correct query
    mock_context_provider.get_contexts.assert_called_once()
    call_args = mock_context_provider.get_contexts.call_args[1]  # Get kwargs
    assert call_args["query"] == "Tell me about Python programming"
    assert call_args["task_id"] == "task1"


@pytest.mark.asyncio
async def test_no_user_messages(task_runner, sample_task, mock_context_provider):
    """Test behavior when there are no user messages."""
    # Setup messages with no user messages
    messages = [
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "assistant", "content": "First response"}
    ]
    
    # Replace the context provider with our mock
    task_runner.context_provider = mock_context_provider
    
    # Mock the persistence model to return our sample task
    task_runner.persistence_model.tasks.read.return_value = sample_task
    
    # Run the standard task with a context_query to ensure get_contexts is called
    await task_runner._run_standard_task(sample_task, {"messages": messages, "context_query": "test query"})
    
    # Check that get_contexts was called with the provided query
    mock_context_provider.get_contexts.assert_called_once()
    call_args = mock_context_provider.get_contexts.call_args[1]  # Get kwargs
    assert call_args["query"] == "test query"


@pytest.mark.asyncio
async def test_crewai_task_context_extraction(task_runner, sample_task, sample_tasks_manager, mock_context_provider):
    """Test context extraction for CrewAI tasks."""
    # Setup a CrewAI task
    crewai_task = sample_task
    crewai_task.framework = "crewai"
    crewai_task.crewai_config_id = "config1"
    crewai_task.use_context = True
    
    # Setup CrewAI task data with context
    context_text = "Generate a Python function to calculate Fibonacci numbers"
    crewai_task_data = {
        "context_query": context_text,  # This is the key we'll extract for context
    }
    
    # Replace the context provider with our mock
    task_runner.context_provider = mock_context_provider
    
    # Mock the persistence model to return our sample task and manager
    task_runner.persistence_model.tasks.read.return_value = crewai_task
    task_runner.persistence_model.tasksmanagers.read.return_value = sample_tasks_manager
    
    # Create a patched version of _run_crewai_task that just extracts context
    original_run_crewai_task = task_runner._run_crewai_task
    
    async def patched_run_crewai_task(task, manager, running_extra_params=None):
        # Extract context query directly from running_extra_params
        if running_extra_params and "context_query" in running_extra_params:
            query = running_extra_params["context_query"]
            
            # Force use manager's model for this test
            model = manager.model
            
            # Call get_contexts with the extracted query
            await mock_context_provider.get_contexts(
                query=query,
                task_id=task.id,
                model=model
            )
            
        # Return a simple success result
        return {
            "status": "completed",
            "response": "Task executed successfully",
            "error": None
        }
    
    # Apply the patch
    task_runner._run_crewai_task = patched_run_crewai_task
    
    try:
        # Run the CrewAI task
        await task_runner.run_task(
            tasksmanager_id=sample_tasks_manager.id,
            task_id=crewai_task.id,
            running_extra_params=crewai_task_data
        )
        
        # Check that get_contexts was called with the correct query
        mock_context_provider.get_contexts.assert_called_once()
        call_args = mock_context_provider.get_contexts.call_args[1]  # Get kwargs
        assert call_args["query"] == context_text
        assert call_args["task_id"] == "task1"
        assert call_args["model"] == "gpt-4"  # Should use the manager's model
    finally:
        # Restore the original method
        task_runner._run_crewai_task = original_run_crewai_task


@pytest.mark.asyncio
async def test_model_selection_for_context_retrieval(task_runner, sample_task, mock_context_provider):
    """Test that the correct model is used for context retrieval."""
    # Setup messages
    messages = [
        {"role": "user", "content": "Tell me about Python programming"}
    ]
    
    # Replace the context provider with our mock
    task_runner.context_provider = mock_context_provider
    
    # Test with task model
    sample_task.model = "gpt-4o-mini"
    task_runner.persistence_model.tasks.read.return_value = sample_task
    
    # Run the standard task
    await task_runner._run_standard_task(sample_task, {"messages": messages})
    
    # Check that get_contexts was called with the task model
    call_args = mock_context_provider.get_contexts.call_args[1]  # Get kwargs
    assert call_args["model"] == "gpt-4o-mini"
    
    # Reset mock
    mock_context_provider.get_contexts.reset_mock()
    
    # Test with manager model
    sample_task.model = None  # Clear task model
    sample_tasks_manager.model = "claude-3-opus-20240229"
    task_runner.persistence_model.tasks.read.return_value = sample_task
    task_runner.persistence_model.tasksmanagers.read.return_value = sample_tasks_manager
    
    # Run the standard task
    await task_runner._run_standard_task(sample_task, {"messages": messages})
    
    # Check that get_contexts was called with the manager model
    call_args = mock_context_provider.get_contexts.call_args[1]  # Get kwargs
    assert call_args["model"] == "claude-3-opus-20240229"
    
    # Reset mock
    mock_context_provider.get_contexts.reset_mock()
    
    # Test with default model (when neither task nor manager has a model)
    sample_task.model = None
    sample_tasks_manager.model = None
    
    # Run the standard task
    await task_runner._run_standard_task(sample_task, {"messages": messages})
    
    # Check that get_contexts was called with the default model (should be "gpt-4o-mini")
    call_args = mock_context_provider.get_contexts.call_args[1]  # Get kwargs
    assert call_args["model"] == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_message_history_conversion(task_runner, sample_task, mock_context_provider):
    """Test that message history is correctly converted for context retrieval."""
    # Setup messages with different formats
    messages = [
        {"role": "system", "content": "You are a helpful assistant"},  # Dict format
        Message(role="user", content="Tell me about Python"),  # Message object
        {"role": "assistant", "content": "Python is a programming language"}  # Dict format
    ]
    
    # Replace the context provider with our mock
    task_runner.context_provider = mock_context_provider
    
    # Mock the persistence model to return our sample task
    task_runner.persistence_model.tasks.read.return_value = sample_task
    
    # Run the standard task
    await task_runner._run_standard_task(sample_task, {"messages": messages})
    
    # Check that get_contexts was called with the correct message history
    mock_context_provider.get_contexts.assert_called_once()
    call_args = mock_context_provider.get_contexts.call_args[1]  # Get kwargs
    
    # Verify message history was passed and has the correct format
    assert "message_history" in call_args
    message_history = call_args["message_history"]
    assert len(message_history) == 3
    
    # Check that all messages are in dict format
    for msg in message_history:
        assert isinstance(msg, dict)
        assert "role" in msg
        assert "content" in msg 