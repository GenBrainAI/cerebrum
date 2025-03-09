"""
Test suite for Task Flow Framework.
Tests the creation and execution of task flows with the Alice in Wonderland example.
"""

import pytest
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from unittest.mock import MagicMock, patch, AsyncMock
import uuid
import json
import os
import sys

from src.server.models.task import Task
from src.server.models.message import Message
from src.server.models.tasks_manager import TasksManager
from src.server.persistence.in_memory_persistence import InMemoryPersistenceModel
from src.server.controllers.task_runner import TaskRunner
from src.server.controllers.prompt_transformer import PromptTransformer, MessageTransformer
from src.server.controllers.task_flow_manager import TaskFlowManager, TaskFlow, TaskFlowStep

logger = logging.getLogger(__name__)

@pytest.fixture
def persistence_model():
    """Create a persistence model for testing."""
    return InMemoryPersistenceModel()

@pytest.fixture
def alice_bob_setup(persistence_model):
    """Set up the Alice and Bob task flow for testing."""
    # Create a task manager for our agents
    manager = TasksManager(
        name="Alice and Bob Task Flow",
        description="A flow with two agents: Alice answers questions about Alice in Wonderland, and Bob adds timestamps",
        model="gpt-4o-mini"
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
    # Initialize synchronously for testing
    loop = asyncio.get_event_loop()
    loop.run_until_complete(flow_manager.initialize())
    
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
        "flow_manager": flow_manager,
        "flow": flow,
        "manager": manager,
        "alice_task": alice_task,
        "bob_task": bob_task
    }

class MockTaskRunner:
    """Mock task runner for testing."""
    
    def __init__(self):
        self.run_count = 0
        self.last_task_id = None
        self.last_params = None
    
    async def run_task(self, tasksmanager_id, task_id, running_extra_params=None):
        """Mock run_task method."""
        self.run_count += 1
        self.last_task_id = task_id
        self.last_params = running_extra_params
        
        return {
            "response": "Mock response",
            "status": "completed"
        }
    
    async def run_flow(self, flow_id, initial_context=None, session_id=None):
        """Mock run_flow method."""
        return {
            "flow_id": flow_id,
            "session_id": session_id or "mock-session-id",
            "results": [
                {
                    "step_index": 0,
                    "task_id": "mock-task-id-1",
                    "name": "Alice",
                    "result": {
                        "response": "In 'Alice in Wonderland', Alice meets the Red Queen and the White Queen.",
                        "status": "completed"
                    },
                    "status": "completed"
                },
                {
                    "step_index": 1,
                    "task_id": "mock-task-id-2",
                    "name": "Bob",
                    "result": {
                        "response": "20/02/2025 19:30 In 'Alice in Wonderland', Alice meets the Red Queen and the White Queen.",
                        "status": "completed"
                    },
                    "status": "completed"
                }
            ],
            "completed": True,
            "context": initial_context or {}
        }

@pytest.mark.asyncio
async def test_task_flow_creation(alice_bob_setup):
    """Test the creation of a task flow."""
    setup = alice_bob_setup  # No await here
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

@pytest.mark.asyncio
async def test_task_flow_execution(alice_bob_setup):
    """Test the execution of a task flow."""
    setup = alice_bob_setup  # No await here
    flow_manager = setup["flow_manager"]
    flow = setup["flow"]
    
    # Replace the task runner with a mock
    mock_runner = MockTaskRunner()
    flow_manager.task_runner = mock_runner
    
    # Prepare the initial context with a user question
    user_question = "Which Queen did Alice meet in the book?"
    context = {
        "user_question": user_question,
        "messages": [
            Message(role="user", content=user_question)
        ]
    }
    
    # Execute the flow
    result = await flow_manager.execute_flow(flow.id, initial_context=context)
    
    # Check that the flow executed correctly
    assert result["flow_id"] == flow.id
    assert result["completed"] is True
    assert len(result["results"]) == 2
    
    # Check Alice's result
    alice_result = result["results"][0]
    assert alice_result["name"] == "Alice"
    assert "Red Queen" in alice_result["result"]["response"]
    assert "White Queen" in alice_result["result"]["response"]
    
    # Check Bob's result
    bob_result = result["results"][1]
    assert bob_result["name"] == "Bob"
    assert "20/02/2025 19:30" in bob_result["result"]["response"]
    assert "Red Queen" in bob_result["result"]["response"]
    assert "White Queen" in bob_result["result"]["response"]

@pytest.mark.asyncio
async def test_task_flow_step_execution(alice_bob_setup):
    """Test the execution of a single step in a task flow."""
    setup = alice_bob_setup  # No await here
    flow_manager = setup["flow_manager"]
    flow = setup["flow"]
    
    # Replace the task runner with a mock
    mock_runner = MockTaskRunner()
    flow_manager.task_runner = mock_runner
    
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
    
    # Check that the step executed correctly
    assert result["step_index"] == 0
    assert result["name"] == "Alice"
    assert result["status"] == "completed"
    assert "response" in result["result"]
    
    # Check that only Alice's task was executed
    assert mock_runner.run_count == 1
    assert mock_runner.last_task_id == setup["alice_task"].id

@pytest.mark.asyncio
async def test_prompt_transformer():
    """Test the PromptTransformer class."""
    # Create a simple transformer
    transformer = PromptTransformer(
        instructions="Please add the date and time to the following text"
    )
    
    # Transform a simple string
    result = transformer.transform("This is a test")
    assert result == "Please add the date and time to the following text: This is a test"
    
    # Transform a dict with a response
    result = transformer.transform({"response": "This is a test"})
    assert result == "Please add the date and time to the following text: This is a test"
    
    # Create messages for a task
    task = Task(
        name="Test Task",
        messages=[
            Message(role="system", content="You are a test assistant")
        ]
    )
    
    messages = transformer.create_messages("This is a test", task)
    assert len(messages) == 2
    assert messages[0].role == "system"
    assert messages[0].content == "You are a test assistant"
    assert messages[1].role == "user"
    assert messages[1].content == "Please add the date and time to the following text: This is a test"

@pytest.mark.asyncio
async def test_message_transformer():
    """Test the MessageTransformer class."""
    # Create a mock source task with get_session_messages method
    source_task = MagicMock()
    source_task.messages = [Message(role="system", content="You are a source assistant")]
    source_task.get_session_messages.return_value = [
        Message(role="user", content="Hello"),
        Message(role="assistant", content="Hi there")
    ]
    
    # Create target task
    target_task = Task(
        name="Target Task",
        messages=[
            Message(role="system", content="You are a target assistant")
        ]
    )
    
    # Create a message transformer
    transformer = MessageTransformer(
        include_system_messages=True,
        include_history=True,
        max_history=2
    )
    
    # Transform messages
    messages = transformer.transform(
        source_task,
        target_task,
        session_id="test-session",
        additional_content="Please process this"
    )
    
    # Check the transformed messages
    assert len(messages) == 4  # Updated to expect 4 messages
    assert messages[0].role == "system"
    assert messages[0].content == "You are a target assistant"
    assert messages[1].role == "user"
    assert messages[1].content == "Hello"
    assert messages[2].role == "assistant"  # This message was missing in our original assertion
    assert messages[2].content == "Hi there"
    assert messages[3].role == "user"
    assert messages[3].content == "Please process this: Hi there" 