"""
Unit tests for the AgenticDevelopmentController component.
"""

import os
import json
import pytest
import pytest_asyncio
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
from typing import Dict, List, Any, Optional

from src.server.self_modification.agentic_framework import AgenticDevelopmentController

@pytest.fixture
def mock_code_generator():
    """Create a mock CodeGenerator for testing."""
    mock = AsyncMock()
    
    # Mock generate_code
    mock.generate_code.return_value = {
        "code": "def hello_world():\n    return 'Hello, World!'",
        "language": "python",
        "explanation": "A simple hello world function",
        "metadata": {"generation_time": 1.5}
    }
    
    # Mock refactor_code
    mock.refactor_code.return_value = {
        "code": "def hello(name='World'):\n    return f'Hello, {name}!'",
        "explanation": "Refactored to support custom names"
    }
    
    return mock

@pytest.fixture
def mock_safety_validator():
    """Create a mock SafetyValidator for testing."""
    mock = AsyncMock()
    
    # Mock validate_code
    mock.validate_code.return_value = {
        "id": "validation-123",
        "file_path": "src/hello.py",
        "validation_level": "high",
        "passed": True,
        "static_analysis": {"passed": True, "issues": []},
        "security_scan": {"passed": True, "vulnerabilities": []},
        "test_results": {"passed": True, "test_results": {"passed": 5, "failed": 0}},
        "timestamp": "2023-01-01T00:00:00"
    }
    
    return mock

@pytest.fixture
def mock_integration_manager():
    """Create a mock IntegrationManager for testing."""
    mock = AsyncMock()
    
    # Mock create_integration_plan
    mock.create_integration_plan.return_value = {
        "id": "plan-123",
        "changes": {"src/hello.py": {"content": "def hello():\n    return 'Hello'", "description": "Add hello function"}},
        "status": "created",
        "approval_status": "pending",
        "creation_time": "2023-01-01T00:00:00"
    }
    
    # Mock approve_integration_plan
    mock.approve_integration_plan.return_value = {
        "id": "plan-123",
        "status": "created",
        "approval_status": "approved"
    }
    
    # Mock stage_changes
    mock.stage_changes.return_value = {
        "success": True,
        "staged_files": ["src/hello.py"]
    }
    
    # Mock test_changes
    mock.test_changes.return_value = {
        "success": True,
        "passed": 10,
        "failed": 0
    }
    
    # Mock apply_changes
    mock.apply_changes.return_value = {
        "success": True,
        "commit_hash": "abc123"
    }
    
    return mock

@pytest.fixture
def mock_knowledge_system():
    """Create a mock KnowledgeSystem for testing."""
    mock = AsyncMock()
    
    # Mock get_knowledge
    mock.get_knowledge.return_value = {
        "python_best_practices": [
            "Use meaningful variable names",
            "Write docstrings for functions and classes",
            "Follow PEP 8 style guidelines"
        ],
        "common_patterns": {
            "factory": "Pattern for creating objects without specifying exact class",
            "singleton": "Pattern ensuring a class has only one instance"
        }
    }
    
    # Mock get_knowledge_context to return a serializable object
    mock.get_knowledge_context.return_value = {
        "relevant_knowledge": [
            "Python best practices",
            "Design patterns"
        ]
    }
    
    return mock

@pytest.fixture
def mock_cognitive_orchestrator():
    """Create a mock CognitiveOrchestrator for testing."""
    mock = AsyncMock()
    
    # Mock analyze_requirements to return a serializable object
    mock.analyze_requirements.return_value = {
        "components": ["hello_function", "greeting_service"],
        "dependencies": {"hello_function": [], "greeting_service": ["hello_function"]},
        "complexity": "low"
    }
    
    # Mock create_development_plan to return a serializable object
    mock.create_development_plan.return_value = {
        "tasks": [
            {"id": "task1", "name": "Implement hello_function", "priority": "high"},
            {"id": "task2", "name": "Implement greeting_service", "priority": "medium", "depends_on": ["task1"]}
        ],
        "estimated_time": "2 hours"
    }
    
    return mock

@pytest.fixture
def agentic_controller(mock_code_generator, mock_safety_validator, mock_integration_manager, 
                      mock_knowledge_system, mock_cognitive_orchestrator):
    """Create an AgenticDevelopmentController instance for testing."""
    return AgenticDevelopmentController(
        mock_code_generator,
        mock_safety_validator,
        mock_integration_manager,
        mock_knowledge_system,
        mock_cognitive_orchestrator
    )

@pytest.mark.asyncio
async def test_initialization(mock_code_generator, mock_safety_validator, mock_integration_manager, 
                             mock_knowledge_system, mock_cognitive_orchestrator):
    """Test that AgenticDevelopmentController initializes correctly."""
    controller = AgenticDevelopmentController(
        mock_code_generator,
        mock_safety_validator,
        mock_integration_manager,
        mock_knowledge_system,
        mock_cognitive_orchestrator
    )
    
    # Check that components are properly assigned
    assert controller.code_generator == mock_code_generator
    assert controller.safety_validator == mock_safety_validator
    assert controller.integration_manager == mock_integration_manager
    assert controller.knowledge_system == mock_knowledge_system
    assert controller.cognitive_orchestrator == mock_cognitive_orchestrator
    
    # Check that internal state is initialized
    assert isinstance(controller.development_cycles, dict)
    assert isinstance(controller.development_tasks, dict)
    assert len(controller.development_cycles) == 0
    assert len(controller.development_tasks) == 0

@pytest.mark.asyncio
async def test_initialize_development_cycle(agentic_controller):
    """Test initializing a development cycle."""
    # Patch the analyze_requirements method to avoid the actual call
    with patch.object(agentic_controller, 'analyze_requirements', AsyncMock(return_value={"status": "success"})):
        requirements = {
            "name": "Greeting Service",
            "description": "A service that provides personalized greetings",
            "features": [
                "Support for custom greeting messages",
                "Support for different languages",
                "Time-aware greetings (morning, afternoon, evening)"
            ]
        }
        
        cycle_id = await agentic_controller.initialize_development_cycle(requirements)
        
        # Check that a cycle ID was returned
        assert cycle_id is not None
        assert isinstance(cycle_id, str)
        
        # Check that the cycle was stored
        assert cycle_id in agentic_controller.development_cycles
        
        # Check the cycle properties
        cycle = agentic_controller.development_cycles[cycle_id]
        assert cycle["requirements"] == requirements
        # The status should be "initialized" initially, but the analyze_requirements method changes it
        # So we don't check the exact status, just that it exists
        assert "status" in cycle
        assert "creation_time" in cycle
        assert "phases" in cycle
        assert "analysis" in cycle["phases"]
        assert "planning" in cycle["phases"]

@pytest.mark.asyncio
async def test_get_development_cycle(agentic_controller):
    """Test retrieving a development cycle."""
    # First create a cycle
    requirements = {
        "name": "Greeting Service",
        "description": "A service that provides personalized greetings"
    }
    
    cycle_id = await agentic_controller.initialize_development_cycle(requirements)
    
    # Now retrieve the cycle
    cycle = await agentic_controller.get_development_cycle(cycle_id)
    
    # Check that the retrieved cycle matches the created cycle
    assert cycle["id"] == cycle_id
    assert cycle["requirements"] == requirements
    # The status might be 'planning' or 'analyzing' because initialize_development_cycle 
    # automatically starts the analysis and planning phases
    assert cycle["status"] in ["initialized", "analyzing", "planning"]

@pytest.mark.asyncio
async def test_get_development_cycle_not_found(agentic_controller):
    """Test retrieving a non-existent development cycle."""
    with pytest.raises(ValueError, match="Development cycle not found"):
        await agentic_controller.get_development_cycle("non-existent-id")

@pytest.mark.asyncio
async def test_list_development_cycles(agentic_controller):
    """Test listing all development cycles."""
    # Create a few cycles
    requirements1 = {"name": "Service 1", "description": "Description 1"}
    requirements2 = {"name": "Service 2", "description": "Description 2"}
    
    await agentic_controller.initialize_development_cycle(requirements1)
    await agentic_controller.initialize_development_cycle(requirements2)
    
    # List all cycles
    cycles = await agentic_controller.list_development_cycles()
    
    # Check that we have at least 2 cycles
    assert len(cycles) >= 2
    
    # Check that each cycle has the expected structure
    for cycle in cycles:
        assert "id" in cycle
        assert "requirements" in cycle
        assert "status" in cycle
        assert "creation_time" in cycle

@pytest.mark.asyncio
async def test_create_development_task(agentic_controller):
    """Test creating a development task."""
    # First create a cycle
    requirements = {"name": "Greeting Service", "description": "A service that provides personalized greetings"}
    cycle_id = await agentic_controller.initialize_development_cycle(requirements)
    
    # Now create a task
    task_spec = {
        "name": "Implement hello function",
        "description": "Create a function that returns a greeting message",
        "acceptance_criteria": ["Function returns 'Hello, World!' by default", "Function accepts a name parameter"]
    }
    
    task_id = await agentic_controller.create_development_task(cycle_id, task_spec)
    
    # Check that a task ID was returned
    assert task_id is not None
    assert isinstance(task_id, str)
    
    # Check that the task was stored
    assert task_id in agentic_controller.development_tasks
    
    # Check the task properties
    task = agentic_controller.development_tasks[task_id]
    assert task["cycle_id"] == cycle_id
    assert task["specification"] == task_spec
    assert task["status"] == "created"
    assert "creation_time" in task

@pytest.mark.asyncio
async def test_get_development_task(agentic_controller):
    """Test retrieving a development task."""
    # First create a cycle and task
    cycle_id = await agentic_controller.initialize_development_cycle({"name": "Test Cycle"})
    task_spec = {"name": "Test Task", "description": "A test task"}
    task_id = await agentic_controller.create_development_task(cycle_id, task_spec)
    
    # Now retrieve the task
    task = await agentic_controller.get_development_task(task_id)
    
    # Check that the retrieved task matches the created task
    assert task["id"] == task_id
    assert task["cycle_id"] == cycle_id
    assert task["specification"] == task_spec
    assert task["status"] == "created"

@pytest.mark.asyncio
async def test_list_development_tasks(agentic_controller):
    """Test listing all development tasks for a cycle."""
    # Create a cycle and some tasks
    cycle_id = await agentic_controller.initialize_development_cycle({"name": "Test Cycle"})
    await agentic_controller.create_development_task(cycle_id, {"name": "Task 1"})
    await agentic_controller.create_development_task(cycle_id, {"name": "Task 2"})
    
    # List all tasks for the cycle
    tasks = await agentic_controller.list_development_tasks(cycle_id)
    
    # Check that we have at least 2 tasks
    assert len(tasks) >= 2
    
    # Check that each task has the expected structure and belongs to the cycle
    for task in tasks:
        assert "id" in task
        assert "specification" in task
        assert "status" in task
        assert "creation_time" in task
        assert task["cycle_id"] == cycle_id

@pytest.mark.asyncio
async def test_execute_development_task(agentic_controller):
    """Test executing a development task."""
    # Create a cycle and task
    cycle_id = await agentic_controller.initialize_development_cycle({"name": "Test Cycle"})
    task_spec = {
        "name": "Implement hello function",
        "description": "Create a function that returns a greeting message",
        "file_path": "src/hello.py",
        "language": "python"
    }
    task_id = await agentic_controller.create_development_task(cycle_id, task_spec)
    
    # Execute the task
    result = await agentic_controller.execute_development_task(task_id)
    
    # Check the result structure
    assert "task_id" in result
    assert "status" in result
    assert "code" in result
    assert "validation" in result
    assert "integration_plan" in result
    
    # Check the result content
    assert result["task_id"] == task_id
    assert result["status"] == "completed"
    assert "Hello, World!" in result["code"]
    assert result["validation"]["passed"] is True
    assert result["integration_plan"]["id"] == "plan-123"
    
    # Check that the task status was updated
    assert agentic_controller.development_tasks[task_id]["status"] == "completed"
    assert "result" in agentic_controller.development_tasks[task_id]

@pytest.mark.asyncio
async def test_evaluate_implementation(agentic_controller):
    """Test evaluating a task implementation."""
    # Create a cycle and task
    cycle_id = await agentic_controller.initialize_development_cycle({"name": "Test Cycle"})
    task_spec = {"name": "Test Task", "description": "A test task"}
    task_id = await agentic_controller.create_development_task(cycle_id, task_spec)
    
    # Set up the task with a result
    agentic_controller.development_tasks[task_id]["result"] = {
        "code": "def hello_world():\n    return 'Hello, World!'",
        "validation": {"passed": True},
        "integration_plan": {"id": "plan-123"}
    }
    
    # Mock the evaluation method
    with patch.object(agentic_controller, '_evaluate_implementation', 
                     AsyncMock(return_value={"score": 0.95, "feedback": "Excellent implementation"})):
        
        # Evaluate the implementation
        evaluation = await agentic_controller.evaluate_implementation(task_id)
        
        # Check the evaluation structure
        assert "task_id" in evaluation
        assert "score" in evaluation
        assert "feedback" in evaluation
        
        # Check the evaluation content
        assert evaluation["task_id"] == task_id
        assert evaluation["score"] == 0.95
        assert evaluation["feedback"] == "Excellent implementation"
        
        # Check that the evaluation was stored with the task
        assert "evaluation" in agentic_controller.development_tasks[task_id]
        assert agentic_controller.development_tasks[task_id]["evaluation"] == evaluation

@pytest.mark.asyncio
async def test_integrate_solution(agentic_controller):
    """Test integrating a task solution."""
    # Create a cycle and task
    cycle_id = await agentic_controller.initialize_development_cycle({"name": "Test Cycle"})
    task_spec = {"name": "Test Task", "description": "A test task"}
    task_id = await agentic_controller.create_development_task(cycle_id, task_spec)
    
    # Set up the task with a result containing an integration plan
    integration_plan_id = "plan-123"
    agentic_controller.development_tasks[task_id]["result"] = {
        "code": "def hello_world():\n    return 'Hello, World!'",
        "validation": {"passed": True},
        "integration_plan": {"id": integration_plan_id}
    }
    
    # Integrate the solution
    integration_result = await agentic_controller.integrate_solution(task_id)
    
    # Check the integration result structure
    assert "task_id" in integration_result
    assert "integration_plan_id" in integration_result
    assert "status" in integration_result
    assert "details" in integration_result
    
    # Check the integration result content
    assert integration_result["task_id"] == task_id
    assert integration_result["integration_plan_id"] == integration_plan_id
    assert integration_result["status"] == "integrated"
    assert integration_result["details"]["success"] is True
    assert integration_result["details"]["commit_hash"] == "abc123"
    
    # Check that the integration result was stored with the task
    assert "integration" in agentic_controller.development_tasks[task_id]
    assert agentic_controller.development_tasks[task_id]["integration"] == integration_result
    assert agentic_controller.development_tasks[task_id]["status"] == "integrated"

@pytest.mark.asyncio
async def test_complete_development_cycle(agentic_controller):
    """Test completing a development cycle."""
    # Create a cycle and some tasks
    cycle_id = await agentic_controller.initialize_development_cycle({"name": "Test Cycle"})
    task_id1 = await agentic_controller.create_development_task(cycle_id, {"name": "Task 1"})
    task_id2 = await agentic_controller.create_development_task(cycle_id, {"name": "Task 2"})
    
    # Set up the tasks as completed and integrated
    for task_id in [task_id1, task_id2]:
        agentic_controller.development_tasks[task_id]["status"] = "integrated"
        agentic_controller.development_tasks[task_id]["integration"] = {
            "status": "integrated",
            "details": {"success": True}
        }
    
    # Complete the cycle
    completion_result = await agentic_controller.complete_development_cycle(cycle_id)
    
    # Check the completion result structure
    assert "cycle_id" in completion_result
    assert "status" in completion_result
    assert "completed_tasks" in completion_result
    assert "summary" in completion_result
    
    # Check the completion result content
    assert completion_result["cycle_id"] == cycle_id
    assert completion_result["status"] == "completed"
    assert len(completion_result["completed_tasks"]) == 2
    assert task_id1 in completion_result["completed_tasks"]
    assert task_id2 in completion_result["completed_tasks"]
    
    # Check that the cycle status was updated
    assert agentic_controller.development_cycles[cycle_id]["status"] == "completed"
    assert "completion" in agentic_controller.development_cycles[cycle_id]
    assert agentic_controller.development_cycles[cycle_id]["completion"] == completion_result 