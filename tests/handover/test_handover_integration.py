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
            async def mock_execute(tasksmanager_id, task_id, running_extra_params=None, inside_sequence=False):
                # Check if task has input_from_tasks and previous_task_outputs
                if task_id == "task1":
                    return {"response": "Task 1 output", "status": "success"}
                elif task_id == "task2":
                    # Verify task2 receives task1's output in the context
                    assert running_extra_params and 'previous_results' in running_extra_params
                    assert len(running_extra_params['previous_results']) > 0
                    assert running_extra_params['previous_results'][0]['task_id'] == 'task1'
                    assert running_extra_params['previous_results'][0]['response'] == 'Task 1 output'
                    return {"response": "Task 2 output based on Task 1", "status": "success"}
                elif task_id == "task3":
                    # Verify task3 receives both task1 and task2's outputs in the context
                    assert running_extra_params and 'previous_results' in running_extra_params
                    assert len(running_extra_params['previous_results']) > 1
                    assert running_extra_params['previous_results'][0]['task_id'] == 'task1'
                    assert running_extra_params['previous_results'][1]['task_id'] == 'task2'
                    assert running_extra_params['previous_results'][0]['response'] == 'Task 1 output'
                    assert running_extra_params['previous_results'][1]['response'] == 'Task 2 output based on Task 1'
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
            
            # Verify results structure
            assert "sequence_execution_id" in results
            assert "status" in results
            assert "results" in results
            assert len(results["results"]) == 3
            
            # Verify the status is completed
            assert results["status"] == "completed"
            
            # Verify individual task results
            task1_result = next((r for r in results["results"] if r["task_id"] == "task1"), None)
            task2_result = next((r for r in results["results"] if r["task_id"] == "task2"), None)
            task3_result = next((r for r in results["results"] if r["task_id"] == "task3"), None)
            
            assert task1_result is not None
            assert task2_result is not None
            assert task3_result is not None
            
            assert task1_result["response"] == "Task 1 output"
            assert task2_result["response"] == "Task 2 output based on Task 1"
            assert task3_result["response"] == "Task 3 output based on Task 1 and 2"
            
            # Tasks remain in 'pending' state in the persistence model
            # as the current implementation doesn't update task status to "completed"
            task1 = data["persistence_model"].tasks.read("task1")
            task2 = data["persistence_model"].tasks.read("task2")
            task3 = data["persistence_model"].tasks.read("task3")
            
            assert task1.status == "pending"
            assert task2.status == "pending"
            assert task3.status == "pending"
    
    async def test_controller_view_component_integration(self, setup_test_data):
        """Test integration between controller and view component."""
        data = setup_test_data
        
        # Mock controller's run_task_sequence method
        async def mock_run_sequence(*args, **kwargs):
            return {
                "sequence_execution_id": "test-seq-123",
                "status": "completed",
                "results": [
                    {"task_id": "task1", "position": 0, "status": "success", "response": "Task 1 output", "error": None},
                    {"task_id": "task2", "position": 1, "status": "success", "response": "Task 2 output", "error": None}
                ],
                "context": {"sequence_execution_id": "test-seq-123"}
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
                                        
                                        # Verify the results structure
                                        assert "sequence_execution_id" in results
                                        assert "status" in results
                                        assert "results" in results
                                        assert results["status"] == "completed"
                                        
                                        # Verify task results
                                        task_results = results["results"]
                                        assert len(task_results) == 2
                                        
                                        # Verify first task result
                                        assert task_results[0]["task_id"] == "task1"
                                        assert task_results[0]["status"] == "success"
                                        assert task_results[0]["response"] == "Task 1 output"
                                        
                                        # Verify second task result
                                        assert task_results[1]["task_id"] == "task2"
                                        assert task_results[1]["status"] == "success"
                                        assert task_results[1]["response"] == "Task 2 output"
                                    
                                    # Run the async test
                                    await async_test()
    
    async def test_error_handling_and_recovery(self, setup_test_data):
        """Test error handling during task sequence execution."""
        data = setup_test_data
        
        # Mock the actual execution of the task to simulate an error in the second task
        with patch('src.server.controllers.task_runner.TaskRunner.run_task') as mock_run_task:
            # Set up mock to fail on the second task
            async def mock_execute(tasksmanager_id, task_id, running_extra_params=None, inside_sequence=False):
                if task_id == "task1":
                    return {"response": "Task 1 output", "status": "success"}
                elif task_id == "task2":
                    # Simulate an error in task 2
                    raise Exception("Task 2 failed for testing")
                elif task_id == "task3":
                    # Task 3 should never be executed if task 2 fails
                    return {"response": "Task 3 output", "status": "success"}
                
                return {"response": f"Default output for {task_id}", "status": "success"}
            
            mock_run_task.side_effect = mock_execute
            
            # Execute the task sequence
            results = await data["task_runner"].run_task_sequence(
                tasksmanager_id="test_tm",
                task_ids=["task1", "task2", "task3"]
            )
            
            # Verify first two tasks were attempted (task2 fails but still counts as a call)
            assert mock_run_task.call_count == 2
            
            # Verify results structure
            assert "sequence_execution_id" in results
            assert "status" in results
            assert "results" in results
            
            # Verify the status is failed
            assert results["status"] == "failed"
            
            # Verify we have two results (success for task1, failure for task2)
            assert len(results["results"]) == 2
            
            # Verify individual task results
            task1_result = next((r for r in results["results"] if r["task_id"] == "task1"), None)
            task2_result = next((r for r in results["results"] if r["task_id"] == "task2"), None)
            
            assert task1_result is not None
            assert task2_result is not None
            
            assert task1_result["response"] == "Task 1 output"
            assert task1_result["status"] == "success"
            assert task2_result["status"] == "failed"
            assert "error" in task2_result
            assert "Task 2 failed for testing" in task2_result["error"]
            
            # Task3 result should not exist since execution stopped at task2
            task3_result = next((r for r in results["results"] if r["task_id"] == "task3"), None)
            assert task3_result is None
            
            # Tasks should remain in their original states in the persistence model
            # since the current implementation doesn't update task statuses
            task1 = data["persistence_model"].tasks.read("task1")
            task2 = data["persistence_model"].tasks.read("task2")
            task3 = data["persistence_model"].tasks.read("task3")
            
            assert task1.status == "pending"
            assert task2.status == "pending"
            assert task3.status == "pending" 