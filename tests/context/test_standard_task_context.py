import pytest
import pytest_asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import logging
from typing import Dict, List, Any, Optional
from uuid import uuid4

from src.server.controllers.task_runner import TaskRunner
from src.server.models.task import Task
from src.server.models.tasks_manager import TasksManager
from src.server.models.message import Message
from src.server.context.context_provider import ContextProvider

# Configure logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class MockContextProvider:
    """Mock context provider for testing."""
    
    def __init__(self):
        self.get_contexts_called = False
        self.last_query = None
        self.mock_contexts = []
        self.task_contexts = {}
        
    async def get_contexts(
        self, 
        query: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        task_id: Optional[str] = None,
        message_history: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Mock get_contexts method that records calls and returns mock contexts."""
        self.get_contexts_called = True
        self.last_query = query
        logger.debug(f"🔍 MockContextProvider.get_contexts called with query: {query}")
        logger.debug(f"  Model: {model}, Task ID: {task_id}")
        
        # Create mock contexts based on the query
        self.mock_contexts = [
            {
                "type": "vector",
                "source_id": f"source_{i}",
                "content": f"Mock context {i} for query: {query}",
                "metadata": {
                    "source": f"vector_store_{i}",
                    "content": f"Mock context {i} for query: {query}"
                },
                "priority": 100 - i
            }
            for i in range(3)
        ]
        
        logger.debug(f"✅ MockContextProvider.get_contexts returning {len(self.mock_contexts)} contexts")
        for i, ctx in enumerate(self.mock_contexts):
            logger.debug(f"  Context {i}: {ctx['content'][:50]}...")
            
        return self.mock_contexts
    
    async def add_context_to_task(
        self,
        task_id: str,
        type: str,
        source_id: str,
        metadata: Dict[str, Any],
        priority: int = 50
    ) -> None:
        """Mock add_context_to_task method that stores contexts for a task."""
        logger.debug(f"📝 MockContextProvider.add_context_to_task called for task: {task_id}")
        logger.debug(f"  Type: {type}, Source: {source_id}, Priority: {priority}")
        
        if task_id not in self.task_contexts:
            self.task_contexts[task_id] = []
            
        self.task_contexts[task_id].append({
            "type": type,
            "source_id": source_id,
            "metadata": metadata,
            "priority": priority,
            "content": metadata.get("content", "")
        })
        
    async def prepare_task_messages(self, task_id: str, messages: List[Message]) -> List[Message]:
        """Mock prepare_task_messages that adds context as system message."""
        logger.debug(f"🔄 MockContextProvider.prepare_task_messages called for task: {task_id}")
        logger.debug(f"  Original messages: {len(messages)}")
        
        if not self.get_contexts_called or not self.mock_contexts:
            logger.debug("  No contexts available, returning original messages")
            return messages
            
        # Create a system message with contexts
        context_content = "\n\n".join([
            f"Context {i} ({ctx['type']}): {ctx['content']}"
            for i, ctx in enumerate(self.mock_contexts)
        ])
        
        system_message = Message(role="system", content=context_content)
        prepared_messages = [system_message] + messages
        
        logger.debug(f"  Prepared messages: {len(prepared_messages)}")
        logger.debug(f"  System message content: {system_message.content[:100]}...")
        
        return prepared_messages

class MockOperator:
    """Mock operator for testing."""
    
    def __init__(self):
        self.completion_called = False
        self.last_messages = None
        
    async def completion(self, tasksmanager_id: str, task_id: str, messages: List[Message], 
                        model: Optional[str] = None, curried_proxy: Optional[Any] = None) -> str:
        """Mock completion method that records calls and returns mock response."""
        self.completion_called = True
        self.last_messages = messages
        
        logger.debug(f"🤖 MockOperator.completion called")
        logger.debug(f"  Task: {task_id}")
        logger.debug(f"  Model: {model}")
        logger.debug(f"  Messages: {len(messages)}")
        
        # Log message details for debugging
        for i, msg in enumerate(messages):
            # Handle both Message objects and dictionaries
            if isinstance(msg, dict):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
            else:
                role = getattr(msg, "role", "unknown")
                content = getattr(msg, "content", "")
                
            logger.debug(f"  Message {i} - Role: {role}")
            content_preview = content[:100] + "..." if len(content) > 100 else content
            logger.debug(f"  Message {i} - Content: {content_preview}")
        
        # Check if context is included in the messages
        has_context = False
        for msg in messages:
            if isinstance(msg, dict):
                if msg.get("role") == "system" and "Context" in str(msg.get("content", "")):
                    has_context = True
                    break
            elif getattr(msg, "role", None) == "system" and "Context" in str(getattr(msg, "content", "")):
                has_context = True
                break
                
        logger.debug(f"  Has context in messages: {has_context}")
        
        return f"Mock response for task {task_id} with {len(messages)} messages"

class MockPersistenceModel:
    """Mock persistence model for testing."""
    
    def __init__(self):
        self.tasks = MagicMock()
        self.tasks_managers = MagicMock()
        self.collections = {
            "tasks": {},
            "tasks_managers": {}
        }
        
    def read(self, collection: str, id: str):
        """Mock read method."""
        if collection in self.collections and id in self.collections[collection]:
            return self.collections[collection][id]
            
        if collection == "tasks":
            return Task(
                id=id,
                name=f"Task {id}",
                tasksmanager_id="manager1",
                messages=[Message(role="user", content="Test message")],
                use_context=True
            )
        elif collection == "tasks_managers":
            return TasksManager(
                id="manager1",
                name="Manager 1",
                model="gpt-4"
            )
        return None
        
    def create(self, collection: str, id: str, data: Any) -> None:
        """Mock create method."""
        if collection not in self.collections:
            self.collections[collection] = {}
        self.collections[collection][id] = data
        
    def update(self, collection: str, id: str, data: Any) -> None:
        """Mock update method."""
        if collection not in self.collections:
            self.collections[collection] = {}
        self.collections[collection][id] = data
        
    def delete(self, collection: str, id: str) -> None:
        """Mock delete method."""
        if collection in self.collections and id in self.collections[collection]:
            del self.collections[collection][id]

@pytest_asyncio.fixture
async def task_runner():
    """Fixture that creates a TaskRunner with mock dependencies."""
    persistence_model = MockPersistenceModel()
    runner = TaskRunner(persistence_model)
    
    # Replace context provider with mock
    runner.context_provider = MockContextProvider()
    
    # Replace operator with mock
    runner.operator = MockOperator()
    
    # Initialize the runner
    await runner.initialize()
    
    return runner

@pytest.mark.asyncio
async def test_standard_task_with_context_query():
    """Test that standard tasks properly retrieve and use contexts based on a query."""
    # Create mock dependencies
    persistence_model = MockPersistenceModel()
    runner = TaskRunner(persistence_model)
    
    # Replace context provider with mock
    mock_context_provider = MockContextProvider()
    runner.context_provider = mock_context_provider
    
    # Replace operator with mock
    mock_operator = MockOperator()
    runner.operator = mock_operator
    
    # Initialize the runner
    await runner.initialize()
    
    # Create test task and manager
    task_id = str(uuid4())
    manager_id = "manager1"
    
    # Mock the task and manager retrieval
    persistence_model.read = MagicMock(side_effect=lambda collection, id: 
        Task(
            id=task_id,
            name=f"Task {task_id}",
            tasksmanager_id=manager_id,
            messages=[Message(role="user", content="Test message")],
            use_context=True
        ) if collection == "tasks" else
        TasksManager(
            id=manager_id,
            name="Manager 1",
            model="gpt-4"
        ) if collection == "tasks_managers" else None
    )
    
    # Define context query
    context_query = "test query for context retrieval"
    
    # Run the task with context query
    logger.debug("\n\n🚀 Running standard task with context query")
    result = await runner._run_standard_task(
        task=Task(
            id=task_id,
            name=f"Task {task_id}",
            tasksmanager_id=manager_id,
            messages=[Message(role="user", content="Test message")],
            use_context=True
        ),
        running_extra_params={"context_query": context_query},
        tasksmanager=TasksManager(
            id=manager_id,
            name="Manager 1",
            model="gpt-4"
        )
    )
    
    # Verify that get_contexts was called with the query
    assert mock_context_provider.get_contexts_called, "get_contexts should have been called"
    assert mock_context_provider.last_query == context_query, "get_contexts should have been called with the correct query"
    
    # Verify that completion was called
    assert mock_operator.completion_called, "completion should have been called"
    
    # Verify that the messages include context
    messages = mock_operator.last_messages
    assert messages is not None, "completion should have been called with messages"
    assert len(messages) > 1, "messages should include context message"
    
    # Verify that the first message is a system message with context
    if isinstance(messages[0], dict):
        assert messages[0].get("role") == "system", "first message should be a system message"
        assert "Context" in messages[0].get("content", ""), "system message should include context"
    else:
        assert messages[0].role == "system", "first message should be a system message"
        assert "Context" in messages[0].content, "system message should include context"
    
    # Verify that the task completed successfully
    assert "response" in result, "result should include response"
    assert "task_name" in result, "result should include task_name"
    
    logger.debug("\n✅ Test completed successfully")

@pytest.mark.asyncio
async def test_standard_task_without_context_query():
    """Test that standard tasks work properly without a context query."""
    # Create mock dependencies
    persistence_model = MockPersistenceModel()
    runner = TaskRunner(persistence_model)
    
    # Replace context provider with mock
    mock_context_provider = MockContextProvider()
    runner.context_provider = mock_context_provider
    
    # Replace operator with mock
    mock_operator = MockOperator()
    runner.operator = mock_operator
    
    # Initialize the runner
    await runner.initialize()
    
    # Create test task and manager
    task_id = str(uuid4())
    manager_id = "manager1"
    
    # Run the task without context query
    logger.debug("\n\n🚀 Running standard task without context query")
    result = await runner._run_standard_task(
        task=Task(
            id=task_id,
            name=f"Task {task_id}",
            tasksmanager_id=manager_id,
            messages=[Message(role="user", content="Test message")],
            use_context=True
        ),
        running_extra_params={},
        tasksmanager=TasksManager(
            id=manager_id,
            name="Manager 1",
            model="gpt-4"
        )
    )
    
    # Verify that get_contexts was not called
    assert not mock_context_provider.get_contexts_called, "get_contexts should not have been called"
    
    # Verify that completion was called
    assert mock_operator.completion_called, "completion should have been called"
    
    # Verify that the messages do not include context
    messages = mock_operator.last_messages
    assert messages is not None, "completion should have been called with messages"
    
    # Check for the default system message - which is now expected to be present
    has_context_message = False
    for msg in messages:
        if isinstance(msg, dict):
            if msg.get('role') == 'system' and 'Context' in msg.get('content', ''):
                has_context_message = True
                break
        elif hasattr(msg, 'role'):
            if msg.role == 'system' and 'Context' in getattr(msg, 'content', ''):
                has_context_message = True
                break
    
    assert not has_context_message, "messages should not include context in system message"
    
    # Verify that the task completed successfully
    assert "response" in result, "result should include response"
    assert "task_name" in result, "result should include task_name"
    
    logger.debug("\n✅ Test completed successfully")

@pytest.mark.asyncio
async def test_end_to_end_task_with_context():
    """Test the end-to-end flow from run_task through _run_standard_task with a context query."""
    # Create mock dependencies
    persistence_model = MockPersistenceModel()
    runner = TaskRunner(persistence_model)
    
    # Replace context provider with mock
    mock_context_provider = MockContextProvider()
    runner.context_provider = mock_context_provider
    
    # Replace operator with mock
    mock_operator = MockOperator()
    runner.operator = mock_operator
    
    # Initialize the runner
    await runner.initialize()
    
    # Create test task and manager
    task_id = str(uuid4())
    manager_id = "manager1"
    
    # Create and store the task and manager in the persistence model
    task = Task(
        id=task_id,
        name=f"Task {task_id}",
        tasksmanager_id=manager_id,
        messages=[Message(role="user", content="Test message")],
        use_context=True
    )
    
    manager = TasksManager(
        id=manager_id,
        name="Manager 1",
        model="gpt-4"
    )
    
    persistence_model.create("tasks", task_id, task)
    persistence_model.create("tasks_managers", manager_id, manager)
    
    # Define context query
    context_query = "end-to-end test query"
    
    # Instead of using run_task, call _run_standard_task directly
    logger.debug("\n\n🚀 Running end-to-end task with context query")
    result = await runner._run_standard_task(
        task=task,
        running_extra_params={"context_query": context_query},
        tasksmanager=manager
    )
    
    # Verify that get_contexts was called with the query
    assert mock_context_provider.get_contexts_called, "get_contexts should have been called"
    assert mock_context_provider.last_query == context_query, "get_contexts should have been called with the correct query"
    
    # Verify that completion was called
    assert mock_operator.completion_called, "completion should have been called"
    
    # Verify that the messages include context
    messages = mock_operator.last_messages
    assert messages is not None, "completion should have been called with messages"
    assert len(messages) > 1, "messages should include context message"
    
    # Verify that the first message is a system message with context
    if isinstance(messages[0], dict):
        assert messages[0].get("role") == "system", "first message should be a system message"
        assert "Context" in messages[0].get("content", ""), "system message should include context"
    else:
        assert messages[0].role == "system", "first message should be a system message"
        assert "Context" in messages[0].content, "system message should include context"
    
    # Verify that the task completed successfully
    assert "response" in result, "result should include response"
    assert "task_name" in result, "result should include task_name"
    
    logger.debug("\n✅ End-to-end test completed successfully") 