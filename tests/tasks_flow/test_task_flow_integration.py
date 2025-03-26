"""
Integration test for Task Flow Framework.
Tests the creation and execution of task flows with the real TaskRunner.
"""

import pytest
import pytest_asyncio
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, cast
import uuid
import json
import os
import sys
from unittest.mock import MagicMock, patch, AsyncMock

from src.server.models.task import Task
from src.server.models.message import Message
from src.server.models.tasks_manager import TasksManager
from src.server.persistence.in_memory_persistence import InMemoryPersistenceModel
from src.server.controllers.task_runner import TaskRunner
from src.server.controllers.prompt_transformer import PromptTransformer, MessageTransformer
from src.server.controllers.task_flow_manager import TaskFlowManager, TaskFlow, TaskFlowStep

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MessageValidationError(Exception):
    """Custom exception for message validation errors."""
    pass

def validate_message_objects(messages: List[Any], source: str = "unknown") -> None:
    """Helper function to validate that all messages are Message objects."""
    if not messages:
        logger.warning(f"No messages provided from {source}")
        return
        
    logger.info(f"Validating {len(messages)} messages from {source}")
    for i, msg in enumerate(messages):
        if not isinstance(msg, Message):
            error_msg = f"Invalid message type from {source}: {type(msg)}. Only Message objects are allowed."
            logger.error(error_msg)
            raise MessageValidationError(error_msg)
        
        if not hasattr(msg, 'role') or not hasattr(msg, 'content'):
            error_msg = f"Message from {source} is missing required attributes: {msg}"
            logger.error(error_msg)
            raise MessageValidationError(error_msg)
            
        if not isinstance(msg.role, str) or not isinstance(msg.content, str):
            error_msg = f"Message from {source} has invalid attribute types: role={type(msg.role)}, content={type(msg.content)}"
            logger.error(error_msg)
            raise MessageValidationError(error_msg)
            
        if msg.role not in ["system", "user", "assistant"]:
            error_msg = f"Message from {source} has invalid role: {msg.role}"
            logger.error(error_msg)
            raise MessageValidationError(error_msg)
            
        logger.info(f"Message {i} from {source} is valid: role={msg.role}, content={msg.content[:30]}...")
    
    logger.info(f"All {len(messages)} messages from {source} are valid")

@pytest.fixture
def persistence_model():
    """Create a persistence model for testing."""
    return InMemoryPersistenceModel()

@pytest_asyncio.fixture
async def task_runner(persistence_model):
    """Create a task runner for testing."""
    runner = TaskRunner(persistence_model)
    await runner.initialize()
    return runner

@pytest_asyncio.fixture
async def alice_bob_setup(persistence_model, task_runner):
    """Set up the Alice and Bob task flow for testing."""
    # Create a task manager for our agents
    manager = TasksManager(
        name="Alice and Bob Task Flow Integration",
        description="A flow with two agents: Alice answers questions about Alice in Wonderland, and Bob adds timestamps",
        model="gpt-4-turbo-preview"  # Using a more recent model
    )
    manager = persistence_model.tasksmanagers.create(manager)
    
    # Create Alice agent task
    alice_task = Task(
        name="Alice Agent",
        description="Answer questions about Alice in Wonderland",
        tasksmanager_id=manager.id,
        agent_role="Literature Expert",
        messages=[
            Message(
                role="system",
                content="""You are an expert on the book 'Alice in Wonderland' by Lewis Carroll.
                You have a comprehensive knowledge of the characters, plot, themes, and details of the book.
                Answer questions about the book accurately and concisely.
                """
            )
        ]
    )
    alice_task = persistence_model.tasks.create(alice_task)
    
    # Create Bob agent task
    bob_task = Task(
        name="Bob Agent",
        description="Add date and time to text",
        tasksmanager_id=manager.id,
        agent_role="Timestamp Specialist",
        messages=[
            Message(
                role="system",
                content="""You are a specialist in adding timestamps to text.
                When you receive text, add the current date and time at the beginning of the text.
                Format the date and time as DD/MM/YYYY HH:MM.
                Example: "20/02/2025 19:30 The Queen of Hearts"
                """
            )
        ]
    )
    bob_task = persistence_model.tasks.create(bob_task)
    
    # Create a task flow manager
    flow_manager = TaskFlowManager(persistence_model)
    flow_manager.task_runner = task_runner
    await flow_manager.initialize()
    
    # Create a task flow
    flow = flow_manager.create_flow(
        name="Alice and Bob Flow",
        description="Alice answers questions about Alice in Wonderland, then Bob adds timestamps",
        tasksmanager_id=manager.id
    )
    
    # Create a prompt transformer for Bob
    bob_transformer = PromptTransformer(
        instructions="Please add the date and time to the following text"
    )
    
    # Add Alice and Bob to the flow
    flow.add_task(alice_task.id, name="Alice")
    flow.add_task(bob_task.id, name="Bob", transformer=bob_transformer)
    
    return {
        "persistence_model": persistence_model,
        "task_runner": task_runner,
        "flow_manager": flow_manager,
        "flow": flow,
        "manager": manager,
        "alice_task": alice_task,
        "bob_task": bob_task
    }

class MockTaskRunner:
    """Mock task runner for testing."""
    def __init__(self, persistence_model):
        self.persistence_model = persistence_model
    
    async def run_task(self, tasksmanager_id: str, task_id: str, running_extra_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Mock run_task method."""
        task = self.persistence_model.tasks.read(task_id)
        
        logger.info(f"Mock run_task called for task: {task.name}")
        logger.info(f"  tasksmanager_id: {tasksmanager_id}")
        logger.info(f"  task_id: {task_id}")
        logger.info(f"  running_extra_params keys: {running_extra_params.keys() if running_extra_params else None}")
        
        # Validate messages
        if running_extra_params and "messages" in running_extra_params:
            try:
                validate_message_objects(running_extra_params["messages"], f"task {task.name}")
            except MessageValidationError as e:
                logger.error(f"Message validation failed: {str(e)}")
                return {
                    "status": "failed",
                    "response": f"Message validation failed: {str(e)}",
                    "error": str(e)
                }
        
        # Get the user's question if available
        user_question = ""
        if running_extra_params and "messages" in running_extra_params:
            for msg in running_extra_params["messages"]:
                if msg.role == "user":
                    user_question = msg.content
                    break
        
        if "Alice" in task.name:
            # Return different responses based on the question
            if "Cheshire Cat" in user_question:
                return {
                    "status": "completed",
                    "response": "The Cheshire Cat is a fictional cat from Lewis Carroll's novel Alice's Adventures in Wonderland. The cat is known for its distinctive mischievous grin and its ability to appear and disappear at will, sometimes leaving only its grin behind.",
                    "error": None
                }
            else:
                return {
                    "status": "completed",
                    "response": "In 'Alice in Wonderland', Alice meets two queens: the Red Queen and the White Queen. The Red Queen is known for her temper and famous phrase 'Off with their heads!', while the White Queen is more gentle but quite peculiar with her backward-thinking logic.",
                    "error": None
                }
        elif "Bob" in task.name:
            current_date = datetime.now().strftime("%d/%m/%Y %H:%M")
            input_text = self._extract_input_text(running_extra_params)
            return {
                "status": "completed",
                "response": f"{current_date} {input_text}",
                "error": None
            }
        
        return {"status": "completed", "response": "Default response", "error": None}
    
    def _extract_input_text(self, running_extra_params: Optional[Dict[str, Any]]) -> str:
        """Extract input text from messages."""
        if not running_extra_params or "messages" not in running_extra_params:
            return ""
            
        for msg in running_extra_params["messages"]:
            if msg.role == "user":
                text = msg.content
                # Remove transformer instructions if present
                if "Please add the date and time to the following text" in text:
                    text = text.replace("Please add the date and time to the following text: ", "")
                    text = text.replace("Please add the date and time to the following text:", "").strip()
                return text
        return ""

@pytest.mark.asyncio
async def test_task_flow_creation(alice_bob_setup):
    """Test the creation of a task flow."""
    setup = alice_bob_setup
    flow = setup["flow"]
    
    # Check that the flow was created correctly
    assert flow.name == "Alice and Bob Flow"
    assert flow.description == "Alice answers questions about Alice in Wonderland, then Bob adds timestamps"
    assert flow.tasksmanager_id == setup["manager"].id
    
    # Check that the steps were added correctly
    assert len(flow.steps) == 2
    assert flow.steps[0].task_id == setup["alice_task"].id
    assert flow.steps[0].name == "Alice"
    assert flow.steps[1].task_id == setup["bob_task"].id
    assert flow.steps[1].name == "Bob"
    assert flow.steps[1].transformer is not None
    assert isinstance(flow.steps[1].transformer, PromptTransformer)

@pytest.mark.asyncio
async def test_task_flow_execution_with_real_runner(alice_bob_setup, monkeypatch):
    """Test the execution of a task flow with the real TaskRunner."""
    setup = alice_bob_setup
    flow = setup["flow"]
    task_runner = setup["task_runner"]
    
    # Create and apply the mock
    mock_runner = MockTaskRunner(setup["persistence_model"])
    monkeypatch.setattr(TaskRunner, "run_task", mock_runner.run_task)
    
    # Prepare the initial context with a user question
    user_question = "Which Queen did Alice meet in the book?"
    context = {
        "user_question": user_question,
        "messages": [
            Message(role="user", content=user_question)
        ]
    }
    
    # Execute the flow
    result = await task_runner.run_flow(flow.id, initial_context=context)
    
    # Check flow execution
    assert result["flow_id"] == flow.id
    assert result["completed"] is True
    assert len(result["results"]) == 2
    
    # Check Alice's result
    alice_result = result["results"][0]
    assert alice_result["name"] == "Alice"
    assert "Red Queen" in alice_result["result"]["response"]
    assert "White Queen" in alice_result["result"]["response"]
    assert alice_result["result"]["status"] == "completed"
    assert alice_result["result"]["error"] is None
    
    # Check Bob's result
    bob_result = result["results"][1]
    assert bob_result["name"] == "Bob"
    assert datetime.now().strftime("%d/%m") in bob_result["result"]["response"]
    assert "Red Queen" in bob_result["result"]["response"]
    assert "White Queen" in bob_result["result"]["response"]
    assert bob_result["result"]["status"] == "completed"
    assert bob_result["result"]["error"] is None

@pytest.mark.asyncio
async def test_task_flow_step_execution_with_real_runner(alice_bob_setup, monkeypatch):
    """Test the execution of a single step in a task flow with the real TaskRunner."""
    setup = alice_bob_setup
    flow_manager = setup["flow_manager"]
    flow = setup["flow"]
    
    # Create and apply the mock
    mock_runner = MockTaskRunner(setup["persistence_model"])
    monkeypatch.setattr(TaskRunner, "run_task", mock_runner.run_task)
    
    # Prepare the context with a user question
    user_question = "Who is the Cheshire Cat?"
    context = {
        "user_question": user_question,
        "messages": [
            Message(role="user", content=user_question)
        ]
    }
    
    # Execute just the first step (Alice)
    result = await flow_manager.execute_flow_step(flow.id, 0, context)
    
    # Check step execution
    assert result["step_index"] == 0
    assert result["name"] == "Alice"
    assert result["status"] == "completed"
    assert result["result"]["status"] == "completed"
    assert result["result"]["error"] is None
    assert "Cheshire Cat" in result["result"]["response"]
    assert "mischievous grin" in result["result"]["response"]

@pytest.mark.asyncio
async def test_message_object_validation():
    """Test that Message objects are properly validated."""
    # Test valid messages
    valid_messages = [
        Message(role="user", content="Hello"),
        Message(role="system", content="You are a helpful assistant"),
        Message(role="assistant", content="How can I help you?")
    ]
    
    # Should not raise an exception
    validate_message_objects(valid_messages, "test")
    
    # Test invalid message types
    invalid_messages = [
        {"role": "user", "content": "This is a dict, not a Message object"},
        Message(role="user", content="This is valid"),
        "This is a string, not a Message object"
    ]
    
    # Should raise MessageValidationError
    with pytest.raises(MessageValidationError):
        validate_message_objects(invalid_messages, "test")
    
    # Test invalid role
    invalid_role_messages = [
        Message(role="invalid_role", content="This has an invalid role")
    ]
    
    # Should raise MessageValidationError
    with pytest.raises(MessageValidationError):
        validate_message_objects(invalid_role_messages, "test")
    
    # Test invalid attribute types using dict initialization
    with pytest.raises(ValueError):
        Message(role=123, content="Invalid role type")  # type: ignore
    
    with pytest.raises(ValueError):
        Message(role="user", content=456)  # type: ignore 