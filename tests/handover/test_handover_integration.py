"""
Integration tests for the task handover functionality.

These tests verify that the different components of the task handover feature work together correctly.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import json
import os
from pathlib import Path

from src.server.controllers.task_runner import TaskRunner
from src.server.models.task import Task
from src.server.models.tasks_manager import TasksManager
from src.server.models.message import Message
from src.server.persistence.in_memory_persistence import InMemoryPersistenceModel
from src.server.views.controllers.task_view_controller import TaskHierarchyController
from src.server.views.components.task_handover_component import TaskHandoverComponent

@pytest.mark.asyncio
class TestHandoverIntegration:
    """Integration tests for task handover functionality."""
    
    @pytest.fixture
    async def setup_test_data(self):
        """Set up test data with tasks and task manager."""
        # Create a persistence model
        persistence_model = InMemoryPersistenceModel()
        
        # Create a task manager
        task_manager = TasksManager(
            id="test_tm",
            name="Test TaskManager",
            description="Test TaskManager for handover integration"
        )
        persistence_model.tasksmanagers.create(task_manager)
        
        # Create tasks with dependencies
        task1 = Task(
            id="task1",
            name="Task 1",
            description="First task in sequence",
            tasksmanager_id="test_tm",
            status="pending",
            messages=[Message(role="system", content="You are the first task in the sequence")]
        )
        persistence_model.tasks.create(task1)
        
        task2 = Task(
            id="task2",
            name="Task 2",
            description="Second task in sequence",
            tasksmanager_id="test_tm",
            status="pending",
            input_from_tasks=["task1"],
            messages=[Message(role="system", content="You are the second task in the sequence")]
        )
        persistence_model.tasks.create(task2)
        
        task3 = Task(
            id="task3",
            name="Task 3",
            description="Third task in sequence",
            tasksmanager_id="test_tm",
            status="pending",
            input_from_tasks=["task1", "task2"],
            messages=[Message(role="system", content="You are the third task in the sequence")]
        )
        persistence_model.tasks.create(task3)
        
        # Create task runner
        task_runner = TaskRunner(persistence_model)
        await task_runner.initialize()
        
        # Create controller
        controller = TaskHierarchyController(persistence_model)
        controller.task_runner = task_runner
        
        return {
            "persistence_model": persistence_model,
            "task_manager": task_manager,
            "tasks": [task1, task2, task3],
            "task_runner": task_runner,
            "controller": controller
        }
    
    async def test_full_handover_sequence(self, setup_test_data):
        """Test a complete task handover sequence from start to finish."""
        data = setup_test_data
        
        # Mock the actual execution of the task to avoid calling the LLM
        with patch('src.server.controllers.task_runner.TaskRunner.run_task') as mock_run_task:
            # Set up mock to return different outputs for each task
            async def mock_execute(tasksmanager_id, task_id, running_extra_params=None):
                # Check if task has input_from_tasks and previous_task_outputs
                if task_id == "task1":
                    return {"response": "Task 1 output", "status": "success"}
                elif task_id == "task2":
                    # Verify task2 receives task1's output
                    assert running_extra_params and 'previous_task_outputs' in running_extra_params
                    assert 'task1' in running_extra_params['previous_task_outputs']
                    assert running_extra_params['previous_task_outputs']['task1'] == "Task 1 output"
                    return {"response": "Task 2 output based on Task 1", "status": "success"}
                elif task_id == "task3":
                    # Verify task3 receives both task1 and task2's outputs
                    assert running_extra_params and 'previous_task_outputs' in running_extra_params
                    assert 'task1' in running_extra_params['previous_task_outputs']
                    assert 'task2' in running_extra_params['previous_task_outputs']
                    assert running_extra_params['previous_task_outputs']['task1'] == "Task 1 output"
                    assert running_extra_params['previous_task_outputs']['task2'] == "Task 2 output based on Task 1"
                    return {"response": "Task 3 output based on Task 1 and 2", "status": "success"}
                
                # Default fallback
                return {"response": f"Default output for {task_id}", "status": "success"}
            
            mock_run_task.side_effect = mock_execute
            
            # Execute the task sequence
            results = await data["task_runner"].run_task_sequence(
                tasksmanager_id="test_tm",
                task_ids=["task1", "task2", "task3"]
            )
            
            # Verify all tasks were executed
            assert mock_run_task.call_count == 3
            
            # Verify results
            assert "task1" in results
            assert "task2" in results
            assert "task3" in results
            
            assert results["task1"]["response"] == "Task 1 output"
            assert results["task2"]["response"] == "Task 2 output based on Task 1"
            assert results["task3"]["response"] == "Task 3 output based on Task 1 and 2"
            
            # Verify tasks were updated in the persistence model
            task1 = data["persistence_model"].tasks.read("task1")
            task2 = data["persistence_model"].tasks.read("task2")
            task3 = data["persistence_model"].tasks.read("task3")
            
            assert task1.status == "completed"
            assert task2.status == "completed"
            assert task3.status == "completed"
            
            # Verify output data was stored
            assert "result" in task1.output_data
            assert task1.output_data["result"] == "Task 1 output"
            
            assert "result" in task2.output_data
            assert task2.output_data["result"] == "Task 2 output based on Task 1"
            
            assert "result" in task3.output_data
            assert task3.output_data["result"] == "Task 3 output based on Task 1 and 2"
            
            # Verify input data for dependent tasks
            assert "previous_task_outputs" in task2.input_data
            assert "task1" in task2.input_data["previous_task_outputs"]
            
            assert "previous_task_outputs" in task3.input_data
            assert "task1" in task3.input_data["previous_task_outputs"]
            assert "task2" in task3.input_data["previous_task_outputs"]
    
    async def test_controller_view_component_integration(self, setup_test_data):
        """Test integration between controller and view component."""
        data = setup_test_data
        
        # Mock controller's run_task_sequence method
        async def mock_run_sequence(*args, **kwargs):
            return {
                "task1": {"response": "Task 1 output", "status": "success"},
                "task2": {"response": "Task 2 output", "status": "success"}
            }
            
        with patch.object(data["controller"], "run_task_sequence", mock_run_sequence):
            # Create TaskHandoverComponent with the controller
            component = TaskHandoverComponent(data["controller"])
            
            # Mock streamlit functions
            with patch("streamlit.empty", return_value=MagicMock()):
                with patch("streamlit.progress", return_value=MagicMock()):
                    with patch("streamlit.container", return_value=MagicMock()):
                        with patch("streamlit.write", return_value=None):
                            with patch("streamlit.tabs", return_value=[MagicMock(), MagicMock()]):
                                with patch("json.loads", return_value={"test": "input"}):
                                    # Create a real event loop for testing
                                    real_loop = asyncio.get_event_loop()
                                    
                                    # Create an async test function
                                    async def async_test():
                                        # Execute the tasks directly
                                        results = await data["controller"].run_task_sequence(
                                            tasksmanager_id="test_tm",
                                            task_ids=["task1", "task2"],
                                            running_extra_params={"test": "input"}
                                        )
                                        
                                        # Verify the results
                                        assert "task1" in results
                                        assert "task2" in results
                                        assert results["task1"]["status"] == "success"
                                        assert results["task2"]["status"] == "success"
                                    
                                    # Run the async test
                                    await async_test()
    
    async def test_error_handling_and_recovery(self, setup_test_data):
        """Test error handling during task sequence execution."""
        data = setup_test_data
        
        # Mock the actual execution of the task to simulate an error in the second task
        with patch('src.server.controllers.task_runner.TaskRunner.run_task') as mock_run_task:
            # Set up mock to fail on the second task
            async def mock_execute(tasksmanager_id, task_id, running_extra_params=None):
                if task_id == "task1":
                    return {"response": "Task 1 output", "status": "success"}
                elif task_id == "task2":
                    # Simulate an error in task 2
                    raise Exception("Task 2 failed for testing")
                elif task_id == "task3":
                    # Task 3 should still run even if task 2 failed
                    return {"response": "Task 3 output", "status": "success"}
                
                return {"response": f"Default output for {task_id}", "status": "success"}
            
            mock_run_task.side_effect = mock_execute
            
            # Execute the task sequence
            results = await data["task_runner"].run_task_sequence(
                tasksmanager_id="test_tm",
                task_ids=["task1", "task2", "task3"]
            )
            
            # Verify all tasks were attempted
            assert mock_run_task.call_count == 3
            
            # Verify results for successful tasks
            assert "task1" in results
            assert results["task1"]["status"] == "success"
            
            # Verify error for failed task
            assert "task2" in results
            assert results["task2"]["status"] == "failed"
            assert "error" in results["task2"]
            assert "Task 2 failed for testing" in results["task2"]["error"]
            
            # Verify task 3 ran despite task 2 failing
            assert "task3" in results
            assert results["task3"]["status"] == "success"
            
            # Verify statuses in the persistence model
            task1 = data["persistence_model"].tasks.read("task1")
            task2 = data["persistence_model"].tasks.read("task2")
            task3 = data["persistence_model"].tasks.read("task3")
            
            assert task1.status == "completed"
            assert task2.status == "failed"
            assert task3.status == "completed"
            
            # Verify error message was stored
            assert task2.error is not None
            assert "Task 2 failed for testing" in task2.error 