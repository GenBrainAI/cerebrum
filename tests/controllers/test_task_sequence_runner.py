import pytest
import asyncio
from unittest.mock import patch, MagicMock
from src.server.controllers.task_runner import TaskRunner
from src.server.models.tasks_manager import TasksManager, TaskSequence
from src.server.models.task import Task
import uuid

@pytest.fixture
def mock_persistence():
    """Create a mock persistence model for testing."""
    class MockPersistence:
        def __init__(self):
            self.tasksmanagers = MagicMock()
            self.tasks = MagicMock()
    
    return MockPersistence()

@pytest.mark.asyncio
async def test_run_task_sequence(mock_persistence):
    """Test running a task sequence."""
    # Setup mock data
    tasksmanager_id = str(uuid.uuid4())
    
    # Create task mocks
    task1 = Task(id="task1", name="Task 1", tasksmanager_id=tasksmanager_id)
    task2 = Task(id="task2", name="Task 2", tasksmanager_id=tasksmanager_id)
    task3 = Task(id="task3", name="Task 3", tasksmanager_id=tasksmanager_id)
    
    # Setup mock persistence
    def mock_read_task(task_id):
        if task_id == "task1":
            return task1
        elif task_id == "task2":
            return task2
        elif task_id == "task3":
            return task3
        return None
    
    mock_persistence.tasks.read.side_effect = mock_read_task
    
    # Setup TaskRunner with mock run_task method
    task_runner = TaskRunner(mock_persistence)
    
    async def mock_run_task(tasksmanager_id, task_id, running_extra_params=None):
        # Return a mock result
        return f"Result for {task_id}"
    
    task_runner.run_task = mock_run_task
    
    # Run sequence
    result = await task_runner.run_task_sequence(tasksmanager_id, ["task1", "task2", "task3"])
    
    # Assertions
    assert "results" in result
    assert "execution_status" in result
    assert "task1" in result["results"]
    assert "task2" in result["results"]
    assert "task3" in result["results"]
    assert result["results"]["task1"] == "Result for task1"
    assert result["results"]["task2"] == "Result for task2"
    assert result["results"]["task3"] == "Result for task3"
    
    # Check execution status
    assert result["execution_status"]["tasksmanager_id"] == tasksmanager_id
    assert result["execution_status"]["sequence"] == ["task1", "task2", "task3"]
    assert result["execution_status"]["status"] == "completed"
    assert len(result["execution_status"]["completed_tasks"]) == 3
    assert len(result["execution_status"]["failed_tasks"]) == 0

@pytest.mark.asyncio
async def test_run_task_sequence_with_handover(mock_persistence):
    """Test running a task sequence with data handover."""
    # Setup mock data
    tasksmanager_id = str(uuid.uuid4())
    
    # Create task mocks
    task1 = Task(id="task1", name="Task 1", tasksmanager_id=tasksmanager_id)
    task2 = Task(id="task2", name="Task 2", tasksmanager_id=tasksmanager_id)
    task3 = Task(id="task3", name="Task 3", tasksmanager_id=tasksmanager_id)
    
    # Setup mock persistence
    def mock_read_task(task_id):
        if task_id == "task1":
            return task1
        elif task_id == "task2":
            return task2
        elif task_id == "task3":
            return task3
        return None
    
    mock_persistence.tasks.read.side_effect = mock_read_task
    
    # Setup TaskRunner with mock run_task method
    task_runner = TaskRunner(mock_persistence)
    
    async def mock_run_task(tasksmanager_id, task_id, running_extra_params=None):
        # Return a mock result
        return f"Result for {task_id}"
    
    task_runner.run_task = mock_run_task
    
    # Run sequence
    result = await task_runner.run_task_sequence(tasksmanager_id, ["task1", "task2", "task3"])
    
    # Assertions
    assert "results" in result
    
    # Check that task2 has input from task1
    mock_persistence.tasks.update.assert_any_call("task2", task2)
    assert hasattr(task2, 'input_from_tasks')
    assert "task1" in task2.input_from_tasks
    assert hasattr(task2, 'input_data')
    assert "previous_task_outputs" in task2.input_data
    
    # Check that task3 has input from task2
    mock_persistence.tasks.update.assert_any_call("task3", task3)
    assert hasattr(task3, 'input_from_tasks')
    assert "task2" in task3.input_from_tasks
    assert hasattr(task3, 'input_data')
    assert "previous_task_outputs" in task3.input_data

@pytest.mark.asyncio
async def test_run_task_sequence_with_error(mock_persistence):
    """Test running a task sequence with an error."""
    # Setup mock data
    tasksmanager_id = str(uuid.uuid4())
    
    # Create task mocks
    task1 = Task(id="task1", name="Task 1", tasksmanager_id=tasksmanager_id)
    task2 = Task(id="task2", name="Task 2", tasksmanager_id=tasksmanager_id)
    task3 = Task(id="task3", name="Task 3", tasksmanager_id=tasksmanager_id)
    
    # Setup mock persistence
    def mock_read_task(task_id):
        if task_id == "task1":
            return task1
        elif task_id == "task2":
            return task2
        elif task_id == "task3":
            return task3
        return None
    
    mock_persistence.tasks.read.side_effect = mock_read_task
    
    # Setup TaskRunner with mock run_task method
    task_runner = TaskRunner(mock_persistence)
    
    async def mock_run_task(tasksmanager_id, task_id, running_extra_params=None):
        if task_id == "task2":
            raise ValueError("Task 2 failed")
        return f"Result for {task_id}"
    
    task_runner.run_task = mock_run_task
    
    # Run sequence
    result = await task_runner.run_task_sequence(tasksmanager_id, ["task1", "task2", "task3"])
    
    # Assertions
    assert "execution_status" in result
    assert result["execution_status"]["status"] == "failed"
    assert "task1" in result["results"]
    assert "task2" in result["results"]
    assert "task3" not in result["results"]
    assert len(result["execution_status"]["completed_tasks"]) == 1
    assert len(result["execution_status"]["failed_tasks"]) == 1
    assert "task2" in result["execution_status"]["failed_tasks"]
    assert result["results"]["task2"]["status"] == "failed"
    assert "error" in result["results"]["task2"]

@pytest.mark.asyncio
async def test_run_task_sequence_by_id(mock_persistence):
    """Test running a task sequence by ID."""
    # Setup mock data
    tasksmanager_id = str(uuid.uuid4())
    sequence_id = "seq1"
    
    # Create task manager with sequence
    tasksmanager = TasksManager(
        id=tasksmanager_id,
        name="Test Manager"
    )
    
    sequence = TaskSequence(
        id=sequence_id,
        name="Test Sequence",
        task_ids=["task1", "task2", "task3"]
    )
    
    tasksmanager.add_sequence(sequence)
    
    # Setup mock persistence
    mock_persistence.tasksmanagers.read.return_value = tasksmanager
    
    # Create task runner with mock run_task_sequence
    task_runner = TaskRunner(mock_persistence)
    
    # Create a mock for run_task_sequence
    async def mock_run_task_sequence(tm_id, task_ids, **kwargs):
        assert tm_id == tasksmanager_id
        assert task_ids == ["task1", "task2", "task3"]
        return {
            "results": {
                "task1": "Result for task1",
                "task2": "Result for task2",
                "task3": "Result for task3"
            },
            "execution_status": {
                "status": "completed"
            }
        }
    
    task_runner.run_task_sequence = mock_run_task_sequence
    
    # Run sequence by ID
    result = await task_runner.run_task_sequence_by_id(tasksmanager_id, sequence_id)
    
    # Assertions
    assert "results" in result
    assert "execution_status" in result
    assert result["execution_status"]["status"] == "completed"
    assert "task1" in result["results"]
    assert "task2" in result["results"]
    assert "task3" in result["results"] 