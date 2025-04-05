"""
Test the TaskHierarchyController's task handover functionality.

This test covers the run_task_sequence method of the TaskHierarchyController.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
import json

from src.server.views.controllers.task_view_controller import TaskHierarchyController
from src.server.controllers.task_runner import TaskRunner
from src.server.models.task import Task
from src.server.models.tasks_manager import TasksManager
from src.server.persistence.in_memory_persistence import InMemoryPersistenceModel

class TestControllerHandover:
    """Test cases for TaskHierarchyController's task handover functionality."""
    
    @pytest.fixture
    def persistence_model(self):
        """Create an in-memory persistence model for testing."""
        return InMemoryPersistenceModel()
    
    @pytest.fixture
    def controller(self, persistence_model):
        """Create a TaskHierarchyController with mock persistence model."""
        controller = TaskHierarchyController(persistence_model)
        controller.task_runner = None  # Will be mocked in tests
        return controller
    
    @pytest.fixture
    def tasks_setup(self, persistence_model):
        """Set up tasks in the persistence model for testing."""
        task_manager = TasksManager(
            id="test_tm",
            name="Test TaskManager"
        )
        persistence_model.tasksmanagers.create(task_manager)
        
        tasks = []
        for i in range(1, 4):
            task = Task(
                id=f"task{i}",
                name=f"Task {i}",
                description=f"Task {i} description",
                tasksmanager_id="test_tm"
            )
            persistence_model.tasks.create(task)
            tasks.append(task)
        
        # Set up dependencies
        tasks[1].input_from_tasks = ["task1"]  # Task 2 depends on Task 1
        tasks[2].input_from_tasks = ["task2"]  # Task 3 depends on Task 2
        
        persistence_model.tasks.update("task2", tasks[1])
        persistence_model.tasks.update("task3", tasks[2])
        
        return tasks
    
    @pytest.mark.asyncio
    async def test_run_task_sequence(self, controller, persistence_model, tasks_setup):
        """Test the run_task_sequence method."""
        # Mock the TaskRunner instance
        mock_task_runner = AsyncMock(spec=TaskRunner)
        mock_task_runner.initialize = AsyncMock()
        controller.task_runner = mock_task_runner
        
        # Mock the run_task method to return predefined results
        async def mock_run_task(tasksmanager_id, task_id, running_extra_params=None):
            return {"response": f"Output for {task_id}", "status": "success"}
        
        mock_task_runner.run_task = AsyncMock(side_effect=mock_run_task)
        mock_task_runner.run_task_sequence = AsyncMock(return_value={
            "task1": {"response": "Output for task1", "status": "success"},
            "task2": {"response": "Output for task2", "status": "success"},
            "task3": {"response": "Output for task3", "status": "success"}
        })
        
        # Run the task sequence
        results = await controller.run_task_sequence(
            tasksmanager_id="test_tm",
            task_ids=["task1", "task2", "task3"]
        )
        
        # Verify task runner was initialized
        assert controller.task_runner == mock_task_runner
        
        # Verify run_task_sequence was called with correct parameters
        mock_task_runner.run_task_sequence.assert_called_once_with(
            tasksmanager_id="test_tm",
            task_ids=["task1", "task2", "task3"],
            initial_context=None
        )
        
        # Verify results
        assert "task1" in results
        assert "task2" in results
        assert "task3" in results
        assert results["task1"]["response"] == "Output for task1"
        assert results["task2"]["response"] == "Output for task2"
        assert results["task3"]["response"] == "Output for task3"
    
    @pytest.mark.asyncio
    async def test_run_task_sequence_with_params(self, controller, persistence_model, tasks_setup):
        """Test run_task_sequence with extra parameters."""
        # Mock the TaskRunner instance
        mock_task_runner = AsyncMock(spec=TaskRunner)
        mock_task_runner.initialize = AsyncMock()
        controller.task_runner = mock_task_runner
        
        # Run the task sequence with extra parameters
        extra_params = {"param1": "value1", "param2": "value2"}
        
        await controller.run_task_sequence(
            tasksmanager_id="test_tm",
            task_ids=["task1", "task2"],
            running_extra_params=extra_params
        )
        
        # Verify run_task_sequence was called with the extra parameters
        mock_task_runner.run_task_sequence.assert_called_once_with(
            tasksmanager_id="test_tm",
            task_ids=["task1", "task2"],
            initial_context=extra_params
        )
    
    @pytest.mark.asyncio
    async def test_run_task_sequence_error_handling(self, controller, persistence_model, tasks_setup):
        """Test error handling in run_task_sequence."""
        # Mock the TaskRunner instance to raise an exception
        mock_task_runner = AsyncMock(spec=TaskRunner)
        mock_task_runner.initialize = AsyncMock()
        mock_task_runner.run_task_sequence = AsyncMock(side_effect=Exception("Test error"))
        controller.task_runner = mock_task_runner
        
        # Run the task sequence and check for error in the response
        result = await controller.run_task_sequence(
            tasksmanager_id="test_tm",
            task_ids=["task1", "task2"]
        )
        
        # Verify the error is returned in the result
        assert "error" in result
        assert "Test error" in result["error"]
        
        # Verify the method was called
        mock_task_runner.run_task_sequence.assert_called_once_with(
            tasksmanager_id="test_tm",
            task_ids=["task1", "task2"],
            initial_context=None
        ) 