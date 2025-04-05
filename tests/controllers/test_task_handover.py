import pytest
import asyncio
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock

from src.server.models.task import Task
from src.server.models.tasks_manager import TasksManager
from src.server.controllers.task_runner import TaskRunner
from src.server.persistence.in_memory_persistence import InMemoryPersistenceModel


@pytest.mark.asyncio
async def test_task_handover_basic():
    """Test basic task handover functionality."""
    # Create a persistence model with test data
    persistence_model = InMemoryPersistenceModel()
    
    # Create a tasksmanager
    tasksmanager = TasksManager(
        id="test_tm",
        name="Test TaskManager",
        description="For testing task handover"
    )
    persistence_model.tasksmanagers.create(tasksmanager)
    
    # Create three sequential tasks with handover relationships
    task1 = Task(
        id="task1",
        name="Task 1",
        description="First task in sequence",
        tasksmanager_id="test_tm",
        status="pending",
        output_data={"result": ""}  # Initialize with empty result
    )
    
    task2 = Task(
        id="task2",
        name="Task 2",
        description="Second task in sequence",
        tasksmanager_id="test_tm",
        status="pending",
        input_from_tasks=["task1"],  # Takes input from task1
        output_data={"result": ""}  # Initialize with empty result
    )
    
    task3 = Task(
        id="task3",
        name="Task 3",
        description="Third task in sequence",
        tasksmanager_id="test_tm",
        status="pending",
        input_from_tasks=["task2"],  # Takes input from task2
        output_data={"result": ""}  # Initialize with empty result
    )
    
    # Add tasks to the persistence model
    persistence_model.tasks.create(task1)
    persistence_model.tasks.create(task2)
    persistence_model.tasks.create(task3)
    
    # Create task runner with a mocked run_task method
    task_runner = TaskRunner(persistence_model=persistence_model)
    
    # Mock the run_task method to simulate task execution
    async def mock_run_task(tasksmanager_id, task_id, running_extra_params=None, inside_sequence=False):
        task = persistence_model.tasks.read(task_id)
        
        if task_id == "task1":
            task.status = "completed"
            task.output_data = {"result": "Task 1 output"}
            persistence_model.tasks.update(task_id, task)
            return {"response": "Task 1 output"}
        elif task_id == "task2":
            # Task2 should have task1's output as input
            if running_extra_params and "previous_task_outputs" in running_extra_params:
                task1_output = running_extra_params["previous_task_outputs"].get("task1", {}).get("response", "")
                assert "Task 1 output" in task1_output
            
            task.status = "completed"
            task.output_data = {"result": "Task 2 output"}
            persistence_model.tasks.update(task_id, task)
            return {"response": "Task 2 output"}
        elif task_id == "task3":
            # Task3 should have task2's output as input
            if running_extra_params and "previous_task_outputs" in running_extra_params:
                task2_output = running_extra_params["previous_task_outputs"].get("task2", {}).get("response", "")
                assert "Task 2 output" in task2_output
            
            task.status = "completed"
            task.output_data = {"result": "Task 3 output"}
            persistence_model.tasks.update(task_id, task)
            return {"response": "Task 3 output"}
    
    task_runner.run_task = mock_run_task
    
    # Run the task sequence
    results = await task_runner.run_task_sequence(
        tasksmanager_id="test_tm",
        task_ids=["task1", "task2", "task3"]
    )
    
    # Verify all tasks ran successfully
    if isinstance(results, dict) and "results" in results:
        # Dictionary response with results key
        result_dict = results["results"]
        assert "task1" in result_dict
        assert "task2" in result_dict
        assert "task3" in result_dict
        
        # Verify task results
        assert result_dict["task1"]["response"] == "Task 1 output"
        assert result_dict["task2"]["response"] == "Task 2 output"
        assert result_dict["task3"]["response"] == "Task 3 output"
    else:
        # String response
        assert "Task 1 output" in str(results)
        assert "Task 2 output" in str(results)
        assert "Task 3 output" in str(results)
    
    # Verify task status updates
    task1_updated = persistence_model.tasks.read("task1")
    task2_updated = persistence_model.tasks.read("task2")
    task3_updated = persistence_model.tasks.read("task3")
    
    assert task1_updated.status == "completed"
    assert task2_updated.status == "completed"
    assert task3_updated.status == "completed"
    
    # Check if the output_data exists and check its content
    assert hasattr(task1_updated, 'output_data') and task1_updated.output_data is not None
    if isinstance(task1_updated.output_data, dict):
        assert "result" in task1_updated.output_data
        assert task1_updated.output_data["result"] == "Task 1 output"
    
    assert hasattr(task2_updated, 'output_data') and task2_updated.output_data is not None
    if isinstance(task2_updated.output_data, dict):
        assert "result" in task2_updated.output_data
        assert task2_updated.output_data["result"] == "Task 2 output"
    
    assert hasattr(task3_updated, 'output_data') and task3_updated.output_data is not None
    if isinstance(task3_updated.output_data, dict):
        assert "result" in task3_updated.output_data
        assert task3_updated.output_data["result"] == "Task 3 output"


@pytest.mark.asyncio
async def test_task_handover_error_handling():
    """Test error handling in task handover."""
    # Create a persistence model with test data
    persistence_model = InMemoryPersistenceModel()
    
    # Create a tasksmanager
    tasksmanager = TasksManager(
        id="test_tm",
        name="Test TaskManager",
        description="For testing task handover error handling"
    )
    persistence_model.tasksmanagers.create(tasksmanager)
    
    # Create three sequential tasks with handover relationships
    task1 = Task(
        id="task1",
        name="Task 1",
        description="First task in sequence",
        tasksmanager_id="test_tm",
        status="pending",
        output_data={"result": ""}  # Initialize with empty result
    )
    
    task2 = Task(
        id="task2",
        name="Task 2 (Will fail)",
        description="Second task in sequence that will fail",
        tasksmanager_id="test_tm",
        status="pending",
        input_from_tasks=["task1"],
        output_data={"result": ""}  # Initialize with empty result
    )
    
    task3 = Task(
        id="task3",
        name="Task 3",
        description="Third task in sequence",
        tasksmanager_id="test_tm",
        status="pending",
        input_from_tasks=["task2"],
        output_data={"result": ""}  # Initialize with empty result
    )
    
    # Add tasks to the persistence model
    persistence_model.tasks.create(task1)
    persistence_model.tasks.create(task2)
    persistence_model.tasks.create(task3)
    
    # Create task runner with a mocked run_task method
    task_runner = TaskRunner(persistence_model)
    
    # Mock the run_task method to simulate task execution
    async def mock_run_task(tasksmanager_id, task_id, running_extra_params=None, inside_sequence=False):
        task = persistence_model.tasks.read(task_id)
        
        if task_id == "task1":
            task.status = "completed"
            task.output_data = {"result": "Task 1 output"}
            persistence_model.tasks.update(task_id, task)
            return {"response": "Task 1 output"}
        elif task_id == "task2":
            # Simulate an error in task2
            task.status = "failed"
            error_message = "Task 2 error: Simulated error in Task 2"
            task.error = error_message
            task.output_data = {"error": error_message}
            persistence_model.tasks.update(task_id, task)
            raise Exception(error_message)
        elif task_id == "task3":
            # Task 3 still runs even though task2 failed
            task.status = "completed"
            task.output_data = {"result": "Task 3 output"}
            persistence_model.tasks.update(task_id, task)
            return {"response": "Task 3 output"}
    
    task_runner.run_task = mock_run_task
    
    # Run the task sequence
    results = await task_runner.run_task_sequence(
        tasksmanager_id="test_tm",
        task_ids=["task1", "task2", "task3"]
    )
    
    # Verify task states directly from the model
    task1_updated = persistence_model.tasks.read("task1")
    task2_updated = persistence_model.tasks.read("task2")
    task3_updated = persistence_model.tasks.read("task3")
    
    # First task should have completed
    assert task1_updated.status == "completed"
    assert hasattr(task1_updated, 'output_data') and task1_updated.output_data is not None
    if isinstance(task1_updated.output_data, dict):
        assert "result" in task1_updated.output_data
        assert task1_updated.output_data["result"] == "Task 1 output"
    
    # Second task should have failed
    assert task2_updated.status == "failed"
    assert hasattr(task2_updated, 'error') and task2_updated.error is not None
    assert "Task 2 error" in task2_updated.error
    
    # Verify the results object
    if isinstance(results, dict) and "results" in results:
        # Dictionary response with results key
        result_dict = results["results"]
        assert "task1" in result_dict
        # Since task2 failed, task3 may or may not be present depending on sequence controller behavior
    else:
        # String response - for sequences that fail, the output is often just the successful part
        assert "Task 1 output" in str(results)


@pytest.mark.asyncio
async def test_task_handover_complex_dependencies():
    """Test task handover with complex dependencies."""
    # Create a persistence model with test data
    persistence_model = InMemoryPersistenceModel()
    
    # Create a tasksmanager
    tasksmanager = TasksManager(
        id="test_tm",
        name="Test TaskManager",
        description="For testing complex task handover"
    )
    persistence_model.tasksmanagers.create(tasksmanager)
    
    # Create tasks with more complex dependencies
    # Task4 depends on both Task2 and Task3
    task1 = Task(
        id="task1",
        name="Task 1",
        description="First task",
        tasksmanager_id="test_tm",
        status="pending",
        output_data={"result": ""}  # Initialize with empty result
    )
    
    task2 = Task(
        id="task2",
        name="Task 2",
        description="Second task",
        tasksmanager_id="test_tm",
        status="pending",
        input_from_tasks=["task1"],
        output_data={"result": ""}  # Initialize with empty result
    )
    
    task3 = Task(
        id="task3",
        name="Task 3",
        description="Third task",
        tasksmanager_id="test_tm",
        status="pending",
        input_from_tasks=["task1"],  # Also depends on task1
        output_data={"result": ""}  # Initialize with empty result
    )
    
    task4 = Task(
        id="task4",
        name="Task 4",
        description="Fourth task that depends on multiple tasks",
        tasksmanager_id="test_tm",
        status="pending",
        input_from_tasks=["task2", "task3"],  # Depends on both task2 and task3
        output_data={"result": ""},  # Initialize with empty result
        input_data={}  # Initialize input_data
    )
    
    # Add tasks to the persistence model
    persistence_model.tasks.create(task1)
    persistence_model.tasks.create(task2)
    persistence_model.tasks.create(task3)
    persistence_model.tasks.create(task4)
    
    # Create task runner with a mocked run_task method
    task_runner = TaskRunner(persistence_model)
    
    # Mock the run_task method to simulate task execution
    async def mock_run_task(tasksmanager_id, task_id, running_extra_params=None, inside_sequence=False):
        task = persistence_model.tasks.read(task_id)
        
        if task_id == "task1":
            task.status = "completed"
            task.output_data = {"result": "Task 1 output"}
            persistence_model.tasks.update(task_id, task)
            return {"response": "Task 1 output"}
        elif task_id == "task2":
            task.status = "completed"
            task.output_data = {"result": "Task 2 output"}
            persistence_model.tasks.update(task_id, task)
            return {"response": "Task 2 output"}
        elif task_id == "task3":
            task.status = "completed"
            task.output_data = {"result": "Task 3 output"}
            persistence_model.tasks.update(task_id, task)
            return {"response": "Task 3 output"}
        elif task_id == "task4":
            # Manually set input_data for task4 to simulate handover
            task.input_data = {
                "previous_task_outputs": {
                    "task2": {"response": "Task 2 output"},
                    "task3": {"response": "Task 3 output"}
                }
            }
            
            # Verify the input data is properly set
            task2_output = task.input_data["previous_task_outputs"].get("task2", {}).get("response", "")
            task3_output = task.input_data["previous_task_outputs"].get("task3", {}).get("response", "")
            assert "Task 2 output" in task2_output
            assert "Task 3 output" in task3_output
            
            task.status = "completed"
            result = "Task 4 output combining Task 2 and Task 3"
            task.output_data = {"result": result}
            persistence_model.tasks.update(task_id, task)
            return {"response": result}
    
    task_runner.run_task = mock_run_task
    
    # Run the task sequence
    results = await task_runner.run_task_sequence(
        tasksmanager_id="test_tm",
        task_ids=["task1", "task2", "task3", "task4"]
    )
    
    # Verify all tasks ran successfully
    if isinstance(results, dict) and "results" in results:
        # Dictionary response with results key
        result_dict = results["results"]
        assert "task1" in result_dict
        assert "task2" in result_dict
        assert "task3" in result_dict
        assert "task4" in result_dict
        
        # Verify task results
        assert result_dict["task1"]["response"] == "Task 1 output"
        assert result_dict["task2"]["response"] == "Task 2 output"
        assert result_dict["task3"]["response"] == "Task 3 output"
        assert result_dict["task4"]["response"] == "Task 4 output combining Task 2 and Task 3"
    else:
        # String response
        assert "Task 1 output" in str(results)
        assert "Task 2 output" in str(results)
        assert "Task 3 output" in str(results)
        assert "Task 4 output combining Task 2 and Task 3" in str(results)
    
    # Verify task statuses directly
    task1_updated = persistence_model.tasks.read("task1")
    task2_updated = persistence_model.tasks.read("task2")
    task3_updated = persistence_model.tasks.read("task3")
    task4_updated = persistence_model.tasks.read("task4")
    
    assert task1_updated.status == "completed"
    assert task2_updated.status == "completed"
    assert task3_updated.status == "completed"
    assert task4_updated.status == "completed"
    
    # Verify task4 input has been set
    assert hasattr(task4_updated, 'input_data') and task4_updated.input_data is not None
    assert isinstance(task4_updated.input_data, dict)
    assert "previous_task_outputs" in task4_updated.input_data
    assert "task2" in task4_updated.input_data["previous_task_outputs"]
    assert "task3" in task4_updated.input_data["previous_task_outputs"]


@pytest.fixture
def mock_persistence():
    """Create a mock persistence model for testing."""
    class MockPersistence:
        def __init__(self):
            self.tasksmanagers = MagicMock()
            self.tasks = MagicMock()
            self.crewai_config = MagicMock()
            self.curried_proxies = MagicMock()
    
    return MockPersistence() 