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
        status="pending"
    )
    
    task2 = Task(
        id="task2",
        name="Task 2",
        description="Second task in sequence",
        tasksmanager_id="test_tm",
        status="pending",
        input_from_tasks=["task1"]  # Takes input from task1
    )
    
    task3 = Task(
        id="task3",
        name="Task 3",
        description="Third task in sequence",
        tasksmanager_id="test_tm",
        status="pending",
        input_from_tasks=["task2"]  # Takes input from task2
    )
    
    # Add tasks to the persistence model
    persistence_model.tasks.create(task1)
    persistence_model.tasks.create(task2)
    persistence_model.tasks.create(task3)
    
    # Create task runner with a mocked run_task method
    task_runner = TaskRunner(persistence_model)
    
    # Mock the run_task method to return predetermined results
    original_run_task = task_runner.run_task
    
    async def mock_run_task(tasksmanager_id, task_id, running_extra_params=None):
        # Call the original to maintain side effects like status updates
        if task_id == "task1":
            return {"response": "Task 1 output", "status": "success"}
        elif task_id == "task2":
            # Verify task2 receives task1's output
            if running_extra_params and 'previous_task_outputs' in running_extra_params:
                assert 'task1' in running_extra_params['previous_task_outputs']
                assert running_extra_params['previous_task_outputs']['task1'] == "Task 1 output"
            return {"response": "Task 2 output based on Task 1", "status": "success"}
        elif task_id == "task3":
            # Verify task3 receives task2's output
            if running_extra_params and 'previous_task_outputs' in running_extra_params:
                assert 'task2' in running_extra_params['previous_task_outputs']
                assert running_extra_params['previous_task_outputs']['task2'] == "Task 2 output based on Task 1"
            return {"response": "Task 3 output based on Task 2", "status": "success"}
        return await original_run_task(tasksmanager_id, task_id, running_extra_params)
    
    # Apply the mock
    task_runner.run_task = mock_run_task
    
    # Run the task sequence
    results = await task_runner.run_task_sequence(
        tasksmanager_id="test_tm",
        task_ids=["task1", "task2", "task3"]
    )
    
    # Verify all tasks ran successfully
    assert len(results) == 3
    assert "task1" in results
    assert "task2" in results
    assert "task3" in results
    
    # Verify task results
    assert results["task1"]["response"] == "Task 1 output"
    assert results["task2"]["response"] == "Task 2 output based on Task 1"
    assert results["task3"]["response"] == "Task 3 output based on Task 2"
    
    # Verify task status updates
    task1_updated = persistence_model.tasks.read("task1")
    task2_updated = persistence_model.tasks.read("task2")
    task3_updated = persistence_model.tasks.read("task3")
    
    assert task1_updated.status == "completed"
    assert task2_updated.status == "completed"
    assert task3_updated.status == "completed"
    
    # Verify output_data was updated
    assert "result" in task1_updated.output_data
    assert task1_updated.output_data["result"] == "Task 1 output"
    
    assert "result" in task2_updated.output_data
    assert task2_updated.output_data["result"] == "Task 2 output based on Task 1"
    
    assert "result" in task3_updated.output_data
    assert task3_updated.output_data["result"] == "Task 3 output based on Task 2"


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
        status="pending"
    )
    
    task2 = Task(
        id="task2",
        name="Task 2 (Will fail)",
        description="Second task in sequence that will fail",
        tasksmanager_id="test_tm",
        status="pending",
        input_from_tasks=["task1"]
    )
    
    task3 = Task(
        id="task3",
        name="Task 3",
        description="Third task in sequence",
        tasksmanager_id="test_tm",
        status="pending",
        input_from_tasks=["task2"]
    )
    
    # Add tasks to the persistence model
    persistence_model.tasks.create(task1)
    persistence_model.tasks.create(task2)
    persistence_model.tasks.create(task3)
    
    # Create task runner with a mocked run_task method
    task_runner = TaskRunner(persistence_model)
    
    # Mock the run_task method to make task2 fail
    original_run_task = task_runner.run_task
    
    async def mock_run_task(tasksmanager_id, task_id, running_extra_params=None):
        if task_id == "task1":
            return {"response": "Task 1 output", "status": "success"}
        elif task_id == "task2":
            raise Exception("Simulated error in Task 2")
        elif task_id == "task3":
            return {"response": "Task 3 output", "status": "success"}
        return await original_run_task(tasksmanager_id, task_id, running_extra_params)
    
    # Apply the mock
    task_runner.run_task = mock_run_task
    
    # Run the task sequence
    results = await task_runner.run_task_sequence(
        tasksmanager_id="test_tm",
        task_ids=["task1", "task2", "task3"]
    )
    
    # Verify all tasks were processed
    assert len(results) == 3
    assert "task1" in results
    assert "task2" in results
    assert "task3" in results
    
    # Verify task1 succeeded
    assert "response" in results["task1"]
    assert results["task1"]["response"] == "Task 1 output"
    
    # Verify task2 failed
    assert "error" in results["task2"]
    assert "Simulated error in Task 2" in results["task2"]["error"]
    assert results["task2"]["status"] == "failed"
    
    # Verify task3 still ran (as we continue after errors)
    assert "response" in results["task3"]
    
    # Verify task status updates
    task1_updated = persistence_model.tasks.read("task1")
    task2_updated = persistence_model.tasks.read("task2")
    task3_updated = persistence_model.tasks.read("task3")
    
    assert task1_updated.status == "completed"
    assert task2_updated.status == "failed"
    assert task3_updated.status == "completed"
    
    # Verify task2 error message was saved
    assert task2_updated.error is not None
    assert "Simulated error in Task 2" in task2_updated.error


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
        status="pending"
    )
    
    task2 = Task(
        id="task2",
        name="Task 2",
        description="Second task",
        tasksmanager_id="test_tm",
        status="pending",
        input_from_tasks=["task1"]
    )
    
    task3 = Task(
        id="task3",
        name="Task 3",
        description="Third task",
        tasksmanager_id="test_tm",
        status="pending",
        input_from_tasks=["task1"]  # Also depends on task1
    )
    
    task4 = Task(
        id="task4",
        name="Task 4",
        description="Fourth task that depends on multiple tasks",
        tasksmanager_id="test_tm",
        status="pending",
        input_from_tasks=["task2", "task3"]  # Depends on both task2 and task3
    )
    
    # Add tasks to the persistence model
    persistence_model.tasks.create(task1)
    persistence_model.tasks.create(task2)
    persistence_model.tasks.create(task3)
    persistence_model.tasks.create(task4)
    
    # Create task runner with a mocked run_task method
    task_runner = TaskRunner(persistence_model)
    
    # Mock the run_task method to return predetermined results
    original_run_task = task_runner.run_task
    
    async def mock_run_task(tasksmanager_id, task_id, running_extra_params=None):
        if task_id == "task1":
            return {"response": "Task 1 output", "status": "success"}
        elif task_id == "task2":
            return {"response": "Task 2 output", "status": "success"}
        elif task_id == "task3":
            return {"response": "Task 3 output", "status": "success"}
        elif task_id == "task4":
            # Verify task4 receives outputs from task2 and task3
            if running_extra_params and 'previous_task_outputs' in running_extra_params:
                assert 'task2' in running_extra_params['previous_task_outputs']
                assert 'task3' in running_extra_params['previous_task_outputs']
                assert running_extra_params['previous_task_outputs']['task2'] == "Task 2 output"
                assert running_extra_params['previous_task_outputs']['task3'] == "Task 3 output"
            return {"response": "Task 4 output combining Task 2 and Task 3", "status": "success"}
        return await original_run_task(tasksmanager_id, task_id, running_extra_params)
    
    # Apply the mock
    task_runner.run_task = mock_run_task
    
    # Run the task sequence
    results = await task_runner.run_task_sequence(
        tasksmanager_id="test_tm",
        task_ids=["task1", "task2", "task3", "task4"]
    )
    
    # Verify all tasks ran successfully
    assert len(results) == 4
    assert "task1" in results
    assert "task2" in results
    assert "task3" in results
    assert "task4" in results
    
    # Verify task4 received inputs from both task2 and task3
    task4_updated = persistence_model.tasks.read("task4")
    assert task4_updated.input_data is not None
    assert "previous_task_outputs" in task4_updated.input_data
    assert "task2" in task4_updated.input_data["previous_task_outputs"]
    assert "task3" in task4_updated.input_data["previous_task_outputs"]
    
    # Verify final output
    assert results["task4"]["response"] == "Task 4 output combining Task 2 and Task 3" 