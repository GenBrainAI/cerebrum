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
        {"role": "user", "content": "Tell me about Python"}
    ]
    
    # Set the context provider on the task runner
    task_runner.context_provider = mock_context_provider
    
    # Run the task
    result = await task_runner._run_standard_task(
        task=sample_task,
        running_extra_params={"messages": messages}
    )
    
    # Check that get_contexts was called with the correct query
    mock_context_provider.get_contexts.assert_called_once()
    call_args = mock_context_provider.get_contexts.call_args[1]
    assert call_args["query"] == "Tell me about Python"
    assert call_args["model"] == "gpt-4o-mini"
    assert call_args["task_id"] == "task1"


@pytest.mark.asyncio
async def test_extract_query_from_message_object(task_runner, sample_task, mock_context_provider):
    """Test that the query is correctly extracted from Message objects."""
    # Setup messages with Message objects
    messages = [
        Message(role="system", content="You are a helpful assistant"),
        Message(role="user", content="First message"),
        Message(role="assistant", content="First response"),
        Message(role="user", content="Tell me about Python")
    ]
    
    # Set the context provider on the task runner
    task_runner.context_provider = mock_context_provider
    
    # Run the task
    result = await task_runner._run_standard_task(
        task=sample_task,
        running_extra_params={"messages": messages}
    )
    
    # Check that get_contexts was called with the correct query
    mock_context_provider.get_contexts.assert_called_once()
    call_args = mock_context_provider.get_contexts.call_args[1]
    assert call_args["query"] == "Tell me about Python"
    assert call_args["model"] == "gpt-4o-mini"
    assert call_args["task_id"] == "task1"


@pytest.mark.asyncio
async def test_no_user_messages(task_runner, sample_task, mock_context_provider):
    """Test that no query is extracted when there are no user messages."""
    # Setup messages with no user messages
    messages = [
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "assistant", "content": "How can I help you?"}
    ]
    
    # Set the context provider on the task runner
    task_runner.context_provider = mock_context_provider
    
    # Run the task
    result = await task_runner._run_standard_task(
        task=sample_task,
        running_extra_params={"messages": messages}
    )
    
    # Check that get_contexts was not called
    mock_context_provider.get_contexts.assert_not_called()


@pytest.mark.asyncio
async def test_crewai_task_context_extraction(task_runner, sample_task, sample_tasks_manager, mock_context_provider):
    """Test that context is correctly extracted for CrewAI tasks."""
    # Setup CrewAI task data with context field
    crewai_task_data = {
        "id": "crewai_task1",
        "name": "CrewAI Test Task",
        "description": "A test CrewAI task",
        "agent": "test_agent",
        "expected_output": "Test output",
        "context": "Tell me about Python"
    }
    
    # Set the context provider on the task runner
    task_runner.context_provider = mock_context_provider
    
    # Mock the plugin manager and plugin
    mock_plugin = MagicMock()
    mock_plugin.create_agent = AsyncMock(return_value=MagicMock())
    mock_plugin.execute_task = AsyncMock(return_value={"status": "success", "response": "Test response"})
    
    # Set up the plugin manager to return our mock plugin
    task_runner._plugin_manager = MagicMock()
    task_runner._plugin_manager.get_plugin = MagicMock(return_value=mock_plugin)
    
    # Mock the _get_or_create_curried_proxy method
    task_runner._get_or_create_curried_proxy = MagicMock(return_value=MagicMock())
    
    # Run the CrewAI task
    result = await task_runner._run_crewai_task(
        task=sample_task,
        running_extra_params={"crewai_task": crewai_task_data},
        tasksmanager=sample_tasks_manager
    )
    
    # Verify that the context from crewai_task was used as the query
    mock_context_provider.get_contexts.assert_called_once()
    call_args = mock_context_provider.get_contexts.call_args[1]
    assert call_args["query"] == "Tell me about Python"
    assert call_args["model"] == "gpt-4"
    assert call_args["task_id"] == "task1"


@pytest.mark.asyncio
async def test_model_selection_for_context_retrieval(task_runner, sample_task, mock_context_provider):
    """Test that the correct model is selected for context retrieval."""
    # Setup messages
    messages = [
        {"role": "user", "content": "Tell me about Python"}
    ]
    
    # Create a task with no model
    task_no_model = Task(
        id="task2",
        name="Test Task No Model",
        description="A test task without a model",
        tasksmanager_id="manager1",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    # Create a tasks manager with a model
    tasks_manager = TasksManager(
        id="manager1",
        name="Test Manager",
        description="A test manager",
        model="gpt-4-turbo",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    # Patch the persistence model to return our tasks manager
    task_runner.persistence_model.tasksmanagers.read.return_value = tasks_manager
    
    # Set the context provider on the task runner
    task_runner.context_provider = mock_context_provider
    
    # Run the task with no model (should use manager's model)
    result = await task_runner._run_standard_task(
        task=task_no_model,
        running_extra_params={"messages": messages}
    )
    
    # Check that get_contexts was called with the manager's model
    mock_context_provider.get_contexts.assert_called_once()
    call_args = mock_context_provider.get_contexts.call_args[1]
    assert call_args["query"] == "Tell me about Python"
    assert call_args["model"] == "gpt-4-turbo"
    assert call_args["task_id"] == "task2"


@pytest.mark.asyncio
async def test_message_history_conversion(task_runner, sample_task, mock_context_provider):
    """Test that message history is correctly converted for token calculation."""
    # Setup messages with different formats
    messages = [
        {"role": "system", "content": "You are a helpful assistant"},  # Dict
        Message(role="user", content="Tell me about Python"),  # Message object
        MagicMock(role="assistant", content="Python is a programming language", to_dict=MagicMock(return_value={"role": "assistant", "content": "Python is a programming language"}))  # Object with to_dict
    ]
    
    # Set the context provider on the task runner
    task_runner.context_provider = mock_context_provider
    
    # Run the task
    result = await task_runner._run_standard_task(
        task=sample_task,
        running_extra_params={"messages": messages}
    )
    
    # Check that get_contexts was called with the correct message history
    mock_context_provider.get_contexts.assert_called_once()
    call_args = mock_context_provider.get_contexts.call_args[1]
    assert call_args["query"] == "Tell me about Python"
    assert "message_history" in call_args
    assert len(call_args["message_history"]) == 3
    
    # Check that each message was converted correctly
    history = call_args["message_history"]
    assert history[0] == {"role": "system", "content": "You are a helpful assistant"}
    assert isinstance(history[1], dict)
    assert history[1]["role"] == "user"
    assert history[1]["content"] == "Tell me about Python"
    assert history[2] == {"role": "assistant", "content": "Python is a programming language"} 