import pytest
import uuid
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from src.server.models.task import Task
from src.server.models.tasks_manager import TasksManager, TaskSequence
from src.server.controllers.task_sequence_controller import TaskSequenceController

@pytest.fixture
def mock_persistence():
    """Create a mock persistence model for testing."""
    persistence = MagicMock()
    
    # Set up tasks with proper return_value for read method
    tasks_crud = MagicMock()
    persistence.tasks = tasks_crud
    
    # Set up tasksmanagers
    tasksmanagers_crud = MagicMock()
    persistence.tasksmanagers = tasksmanagers_crud
    
    return persistence

@pytest.fixture
def mock_task_runner():
    """Create a mock task runner for testing."""
    task_runner = MagicMock()
    task_runner.run_task = AsyncMock()
    return task_runner

@pytest.fixture
def sequence_controller(mock_persistence, mock_task_runner):
    """Create a TaskSequenceController with mocked dependencies."""
    controller = TaskSequenceController(mock_persistence)
    controller.set_task_runner(mock_task_runner)
    return controller

@pytest.fixture
def setup_sequence_test_data(mock_persistence):
    """Set up test data for sequence tests."""
    tasksmanager_id = str(uuid.uuid4())
    task_ids = [f"task{i}" for i in range(1, 4)]
    
    # Create tasks
    tasks = {}
    for task_id in task_ids:
        task = Task(
            id=task_id,
            name=f"Test Task {task_id}",
            tasksmanager_id=tasksmanager_id,
            data={},
            input_data={},
            output_data={},
            input_from_tasks=[]
        )
        tasks[task_id] = task
    
    # Mock task read method
    def mock_read_task(task_id):
        return tasks.get(task_id)
    
    mock_persistence.tasks.read.side_effect = mock_read_task
    
    # Create sequence
    sequence = TaskSequence(
        id="test-sequence",
        name="Test Sequence",
        task_ids=task_ids,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    # Create TasksManager
    tasksmanager = MagicMock(spec=TasksManager)
    tasksmanager.id = tasksmanager_id
    tasksmanager.name = "Test Manager"
    tasksmanager.get_sequence.return_value = sequence
    
    # Mock tasksmanager read method
    mock_persistence.tasksmanagers.read.return_value = tasksmanager
    
    # Return test data
    return {
        "tasksmanager_id": tasksmanager_id,
        "task_ids": task_ids,
        "tasks": tasks,
        "sequence": sequence,
        "tasksmanager": tasksmanager
    }

@pytest.mark.asyncio
async def test_execute_sequence(sequence_controller, mock_task_runner, setup_sequence_test_data):
    """Test executing a sequence of tasks."""
    test_data = setup_sequence_test_data
    
    # Set up task runner mock to return different results for each task
    async def mock_run_task(tasksmanager_id, task_id, running_extra_params=None, inside_sequence=False):
        assert inside_sequence is True, "Task must be run with inside_sequence=True"
        return f"Result for {task_id}"
    
    mock_task_runner.run_task.side_effect = mock_run_task
    
    # Execute sequence
    result = await sequence_controller.execute_sequence(
        tasksmanager_id=test_data["tasksmanager_id"],
        task_ids=test_data["task_ids"]
    )
    
    # Assertions
    assert "results" in result
    assert "execution_status" in result
    
    # Check execution status
    status = result["execution_status"]
    assert status["tasksmanager_id"] == test_data["tasksmanager_id"]
    assert status["task_ids"] == test_data["task_ids"]
    assert status["status"] == "completed"
    assert len(status["completed_tasks"]) == len(test_data["task_ids"])
    assert not status["failed_tasks"]
    
    # Check that run_task was called for each task
    assert mock_task_runner.run_task.call_count == len(test_data["task_ids"])
    
    # Verify results exist for each task
    for task_id in test_data["task_ids"]:
        assert task_id in result["results"]
        assert result["results"][task_id]["response"] == f"Result for {task_id}"

@pytest.mark.asyncio
async def test_execute_sequence_by_id(sequence_controller, mock_task_runner, setup_sequence_test_data):
    """Test executing a sequence by ID."""
    test_data = setup_sequence_test_data
    
    # Set up task runner mock to return different results for each task
    async def mock_run_task(tasksmanager_id, task_id, running_extra_params=None, inside_sequence=False):
        assert inside_sequence is True, "Task must be run with inside_sequence=True"
        return f"Result for {task_id}"
    
    mock_task_runner.run_task.side_effect = mock_run_task
    
    # Execute sequence by ID
    result = await sequence_controller.execute_sequence_by_id(
        tasksmanager_id=test_data["tasksmanager_id"],
        sequence_id="test-sequence"
    )
    
    # Assertions
    assert "results" in result
    assert "execution_status" in result
    
    # Check sequence lookup
    test_data["tasksmanager"].get_sequence.assert_called_once_with("test-sequence")
    
    # Check that run_task was called for each task
    assert mock_task_runner.run_task.call_count == len(test_data["task_ids"])
    
    # Verify results exist for each task
    for task_id in test_data["task_ids"]:
        assert task_id in result["results"]

@pytest.mark.asyncio
async def test_execute_sequence_with_task_error(sequence_controller, mock_task_runner, setup_sequence_test_data):
    """Test sequence execution with a task error."""
    test_data = setup_sequence_test_data
    
    # Set up task runner mock to fail on the second task
    task_count = 0
    async def mock_run_task(tasksmanager_id, task_id, running_extra_params=None, inside_sequence=False):
        nonlocal task_count
        task_count += 1
        if task_count == 2:
            raise ValueError("Task execution failed")
        return f"Result for {task_id}"
    
    mock_task_runner.run_task.side_effect = mock_run_task
    
    # Execute sequence
    result = await sequence_controller.execute_sequence(
        tasksmanager_id=test_data["tasksmanager_id"],
        task_ids=test_data["task_ids"]
    )
    
    # Assertions
    assert "results" in result
    assert "execution_status" in result
    
    # Check execution status
    status = result["execution_status"]
    assert status["status"] == "failed"
    assert len(status["completed_tasks"]) == 1
    assert len(status["failed_tasks"]) == 1
    assert test_data["task_ids"][0] in status["completed_tasks"]
    assert test_data["task_ids"][1] in status["failed_tasks"]
    
    # Check that only the first and second tasks were attempted
    assert mock_task_runner.run_task.call_count == 2
    
    # Verify results exist for the first task and error for the second
    assert test_data["task_ids"][0] in result["results"]
    assert test_data["task_ids"][1] in result["results"]
    assert "error" in result["results"][test_data["task_ids"][1]]
    assert "failed" in result["results"][test_data["task_ids"][1]]["status"]

@pytest.mark.asyncio
async def test_recursion_prevention(sequence_controller, mock_task_runner, setup_sequence_test_data):
    """Test that sequence execution prevents recursion."""
    test_data = setup_sequence_test_data
    
    # Set up a task mock that tries to run the same sequence
    task_count = 0
    async def mock_run_task(tasksmanager_id, task_id, running_extra_params=None, inside_sequence=False):
        nonlocal task_count
        task_count += 1
        
        # Try to cause recursion on the first task
        if task_count == 1:
            try:
                # Try to execute the same sequence again
                await sequence_controller.execute_sequence_by_id(
                    tasksmanager_id=test_data["tasksmanager_id"],
                    sequence_id="test-sequence"
                )
            except Exception:
                # Ignore expected errors from test mocks
                pass
            
        return f"Result for {task_id}"
    
    mock_task_runner.run_task.side_effect = mock_run_task
    
    # Execute sequence
    result = await sequence_controller.execute_sequence_by_id(
        tasksmanager_id=test_data["tasksmanager_id"],
        sequence_id="test-sequence"
    )
    
    # Assertions
    assert "results" in result
    assert "execution_status" in result
    
    # Check execution status
    status = result["execution_status"]
    assert status["status"] == "completed"
    
    # Verify the final count matches the number of tasks in the original sequence
    # and not a multiple (which would indicate recursion happened)
    assert task_count == len(test_data["task_ids"]) 