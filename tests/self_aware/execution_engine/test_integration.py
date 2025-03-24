import pytest
from datetime import datetime, timedelta
import logging
import uuid

from src.server.execution_engine.execution_engine import ExecutionEngine
from src.server.execution_engine.task_selector import Task, TaskStatus, TaskPriority, TaskDependency, DependencyType
from src.server.execution_engine.context_manager import ContextType, ContextManager
from src.server.execution_engine.resource_manager import ResourceManager


@pytest.fixture
def setup_logging():
    """Set up logging for the tests."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


@pytest.fixture
def execution_engine():
    """Create an ExecutionEngine instance for testing."""
    context_manager = ContextManager()
    resource_manager = ResourceManager()
    return ExecutionEngine(context_manager=context_manager, resource_manager=resource_manager)


class TestExecutionEngineIntegration:
    """Integration tests for the ExecutionEngine components."""

    def test_task_lifecycle(self, execution_engine, setup_logging):
        """Test complete task lifecycle from creation to completion."""
        # Create a task
        task_id = execution_engine.create_task(
            name="Integration Test Task",
            description="A task for testing the complete lifecycle",
            priority=TaskPriority.MEDIUM,
            estimated_duration=5.0,
            estimated_resources={"cpu": 1.0, "memory": 1024},
            context_requirements=["input_data"]
        )
        
        # Set required context
        execution_engine.context_manager.set_context(
            "input_data", {"value": 42}, ContextType.GLOBAL
        )
        
        # Check task is ready
        task = execution_engine.task_selector.tasks[task_id]
        assert task.status == TaskStatus.READY
        
        # Execute the task
        result = execution_engine.execute_task(task_id)
        
        # Check task completed successfully
        assert result is not None
        assert result["status"] == "complete"
        assert task.status == TaskStatus.COMPLETED
        
        # Check execution history was updated
        assert len(execution_engine.execution_history) == 1
        assert execution_engine.execution_history[0]["task_id"] == task_id

    def test_dependency_resolution(self, execution_engine, setup_logging):
        """Test resolution of task dependencies."""
        # Create a chain of dependent tasks
        task1_id = execution_engine.create_task(
            name="Task 1",
            description="First task in chain",
            priority=TaskPriority.HIGH
        )
        
        task2_id = execution_engine.create_task(
            name="Task 2",
            description="Second task in chain",
            priority=TaskPriority.MEDIUM,
            dependencies=[TaskDependency(task1_id, "hard", "Depends on Task 1")]
        )
        
        task3_id = execution_engine.create_task(
            name="Task 3",
            description="Third task in chain",
            priority=TaskPriority.LOW,
            dependencies=[TaskDependency(task2_id, "hard", "Depends on Task 2")]
        )
        
        # Check initial statuses
        assert execution_engine.task_selector.tasks[task1_id].status == TaskStatus.READY
        assert execution_engine.task_selector.tasks[task2_id].status == TaskStatus.BLOCKED
        assert execution_engine.task_selector.tasks[task3_id].status == TaskStatus.BLOCKED
        
        # Select next task - should be task1
        next_task = execution_engine.select_next_task()
        assert next_task.id == task1_id
        
        # Execute task1
        execution_engine.execute_task(task1_id)
        
        # Check task2 is now ready
        assert execution_engine.task_selector.tasks[task2_id].status == TaskStatus.READY
        assert execution_engine.task_selector.tasks[task3_id].status == TaskStatus.BLOCKED
        
        # Select next task - should be task2
        next_task = execution_engine.select_next_task()
        assert next_task.id == task2_id
        
        # Execute task2
        execution_engine.execute_task(task2_id)
        
        # Check task3 is now ready
        assert execution_engine.task_selector.tasks[task3_id].status == TaskStatus.READY
        
        # Select next task - should be task3
        next_task = execution_engine.select_next_task()
        assert next_task.id == task3_id
        
        # Execute task3
        execution_engine.execute_task(task3_id)
        
        # All tasks should be completed
        assert execution_engine.task_selector.tasks[task1_id].status == TaskStatus.COMPLETED
        assert execution_engine.task_selector.tasks[task2_id].status == TaskStatus.COMPLETED
        assert execution_engine.task_selector.tasks[task3_id].status == TaskStatus.COMPLETED
        
        # Execution history should have 3 entries
        assert len(execution_engine.execution_history) == 3

    def test_context_propagation(self, execution_engine):
        # Add propagation rules
        execution_engine.context_propagator.add_rule("raw_data", "processed_data")
        execution_engine.context_propagator.add_rule("processed_data", "final_result")
        
        # Create chain of data processing tasks
        collector_task_id = execution_engine.create_task(
            name="Data Collector",
            description="Task that collects raw data",
            priority=TaskPriority.HIGH,
            context_requirements=["raw_data"]
        )
        
        processor_task_id = execution_engine.create_task(
            name="Data Processor",
            description="Task that processes data",
            priority=TaskPriority.MEDIUM,
            dependencies=[TaskDependency(collector_task_id, DependencyType.REQUIRED)],
            context_requirements=["raw_data", "processed_data"]
        )
        
        result_task_id = execution_engine.create_task(
            name="Result Generator",
            description="Task that generates final result",
            priority=TaskPriority.LOW,
            dependencies=[TaskDependency(processor_task_id, DependencyType.REQUIRED)],
            context_requirements=["processed_data"]
        )
        
        # Set initial context
        execution_engine.context_manager.set_context("raw_data", {"value": 5})
        
        # Execute first task (collector)
        result = execution_engine.execute_task(collector_task_id)
        assert result["status"] == "complete"
        
        # Check that processed_data was propagated from either task_output or direct assignment
        task_output = execution_engine.context_manager.get_context("task_output")
        assert task_output is not None, "Task output was not created"
        assert "processed_data" in task_output, "Processed data was not in task_output"
        
        # Execute second task (processor)
        result = execution_engine.execute_task(processor_task_id)
        assert result["status"] == "complete"
        
        # Check that final_result is available after third task
        result = execution_engine.execute_task(result_task_id)
        assert result["status"] == "complete"
        
        final_result = execution_engine.context_manager.get_context("final_result")
        assert final_result is not None, "Final result was not propagated correctly"

    def test_context_validation(self, execution_engine, setup_logging):
        """Test context validation in the execution engine."""
        # Set up a validator for a number range
        execution_engine.context_validator.add_range_validator("number_key", 1, 100)
        
        # Create a task with validation
        task_id = execution_engine.create_task(
            name="Validation Task",
            description="Task with validated context",
            priority=TaskPriority.MEDIUM,
            context_requirements=["number_key", "string_key"]
        )
        
        # Set valid context
        execution_engine.context_manager.set_context("number_key", 42, ContextType.GLOBAL)
        execution_engine.context_manager.set_context("string_key", "valid string", ContextType.GLOBAL)
        
        # Execute the task
        result = execution_engine.execute_task(task_id)
        
        # Check task completed successfully
        assert result is not None
        assert result["status"] == "complete"
        
        # Create a task with validation that will fail
        invalid_task_id = execution_engine.create_task(
            name="Invalid Task",
            description="Task with invalid context",
            priority=TaskPriority.MEDIUM,
            context_requirements=["number_key"]
        )
        
        # Set invalid context with skip_validation=True to bypass immediate validation
        execution_engine.context_manager.set_context("number_key", 200, ContextType.GLOBAL, skip_validation=True)
        
        # Execute task - should fail validation
        result = execution_engine.execute_task(invalid_task_id)
        
        # Check task failed
        assert "error" in result
        assert execution_engine.task_selector.tasks[invalid_task_id].status == TaskStatus.FAILED

    def test_resource_management(self, execution_engine, setup_logging):
        """Test resource allocation and management."""
        # Set resource limits
        execution_engine.resource_manager.set_resource_limits({
            "cpu": 4.0,
            "memory": 8192
        })
        
        # Create tasks with resource requirements
        task1_id = execution_engine.create_task(
            name="Resource Task 1",
            description="Task with high resource usage",
            priority=TaskPriority.HIGH,
            estimated_resources={"cpu": 3.0, "memory": 6144}
        )
        
        task2_id = execution_engine.create_task(
            name="Resource Task 2",
            description="Task with lower resource usage",
            priority=TaskPriority.MEDIUM,
            estimated_resources={"cpu": 2.0, "memory": 4096}
        )
        
        # Manually allocate resources for first task
        execution_engine.resource_manager.allocate_resources(task1_id, {"cpu": 3.0, "memory": 6144})
        
        # Check resource utilization
        utilization = execution_engine.resource_manager.get_resource_utilization()
        assert utilization["cpu"] > 0  # Resources should be allocated
        assert utilization["memory"] > 0
        
        # Manually allocate resources for second task
        execution_engine.resource_manager.allocate_resources(task2_id, {"cpu": 1.0, "memory": 2048})
        
        # Check resource utilization after both tasks
        utilization = execution_engine.resource_manager.get_resource_utilization()
        assert utilization["cpu"] > 0
        assert utilization["memory"] > 0
        
        # All resources should be freed after tasks complete
        execution_engine.resource_manager.free_resources(task1_id)
        execution_engine.resource_manager.free_resources(task2_id)
        
        utilization = execution_engine.resource_manager.get_resource_utilization()
        assert utilization["cpu"] == 0
        assert utilization["memory"] == 0

    def test_priority_based_selection(self, execution_engine, setup_logging):
        """Test task selection based on calculated priorities."""
        # Create multiple tasks with different priorities and wait times
        old_task_id = execution_engine.create_task(
            name="Old Task",
            description="Task created a while ago",
            priority=TaskPriority.LOW,
            created_at=datetime.now() - timedelta(hours=5)
        )
        
        high_priority_id = execution_engine.create_task(
            name="High Priority",
            description="Task with high priority",
            priority=TaskPriority.HIGH
        )
        
        tagged_task_id = execution_engine.create_task(
            name="Tagged Task",
            description="Task with priority tag",
            priority=TaskPriority.MEDIUM,
            tags=["critical"]
        )
        
        # Set tag priorities
        execution_engine.priority_calculator.set_tag_priorities({
            "critical": 50
        })
        
        # Find next task to execute
        next_task = execution_engine.select_next_task()
        
        # Should select high priority task
        assert next_task.id == high_priority_id
        
        # Execute the high priority task
        execution_engine.execute_task(high_priority_id)
        
        # Next task should be tagged task due to tag priority
        next_task = execution_engine.select_next_task()
        assert next_task.id == tagged_task_id
        
        # Execute the tagged task
        execution_engine.execute_task(tagged_task_id)
        
        # Last task should be old task
        next_task = execution_engine.select_next_task()
        assert next_task.id == old_task_id

    def test_execution_engine_fault_tolerance(self, execution_engine, setup_logging):
        """Test fault tolerance of the execution engine."""
        # Create a task
        task_id = execution_engine.create_task(
            name="Failing Task",
            description="A task that will fail",
            priority=TaskPriority.MEDIUM
        )
        
        # Monkey patch the _simulate_task_execution method to raise an exception
        original_method = execution_engine._simulate_task_execution
        
        def failing_execution(*args, **kwargs):
            raise Exception("Simulated task failure")
        
        execution_engine._simulate_task_execution = failing_execution
        
        try:
            # Execute the task
            result = execution_engine.execute_task(task_id)
            
            # Check failure was handled gracefully
            assert "error" in result
            assert "Simulated task failure" in result["error"]
            assert execution_engine.task_selector.tasks[task_id].status == TaskStatus.FAILED
            
            # Check execution history records failure
            assert len(execution_engine.execution_history) == 1
            assert execution_engine.execution_history[0]["status"] == "failure"
            
            # Check system can continue operating
            task2_id = execution_engine.create_task(
                name="Recovery Task",
                description="A task after failure",
                priority=TaskPriority.MEDIUM
            )
            
            # Restore original method
            execution_engine._simulate_task_execution = original_method
            
            # Execute second task
            result = execution_engine.execute_task(task2_id)
            
            # Check second task completes successfully
            assert result is not None
            assert result["status"] == "complete"
            assert execution_engine.task_selector.tasks[task2_id].status == TaskStatus.COMPLETED
        finally:
            # Always restore original method
            execution_engine._simulate_task_execution = original_method

    def test_automatic_execution_sequence(self, execution_engine, setup_logging):
        """Test automatic execution of multiple tasks in sequence."""
        # Create a chain of tasks
        for i in range(5):
            execution_engine.create_task(
                name=f"Auto Task {i+1}",
                description=f"Automatically executed task {i+1}",
                priority=TaskPriority.MEDIUM,
                estimated_duration=1.0
            )
        
        # Execute all tasks
        for _ in range(5):
            result = execution_engine.execute_next_task()
            assert result is not None
            assert result["status"] == "complete"
        
        # Check all tasks are completed
        task_counts = execution_engine.get_execution_state()["task_counts"]
        assert task_counts["completed"] == 5
        assert task_counts["pending"] == 0
        assert task_counts["ready"] == 0
        
        # Check execution history has 5 entries
        assert len(execution_engine.execution_history) == 5

    def test_context_lifecycle(self, execution_engine):
        """
        Test the complete lifecycle of context through creation, modification, and cleanup
        """
        # Create tasks that will create, modify, and clean up context
        task1_id = execution_engine.create_task(
            name="Context Creator",
            description="Creates initial context value",
            context_requirements={},
            priority=TaskPriority.HIGH,
        )
        
        task2_id = execution_engine.create_task(
            name="Context Modifier",
            description="Modifies the created context value",
            context_requirements={"task_output.created_value": "number"},
            dependencies=[TaskDependency(task1_id, DependencyType.REQUIRED)],
            priority=TaskPriority.MEDIUM,
        )
        
        task3_id = execution_engine.create_task(
            name="Context Cleaner",
            description="Finalizes the context",
            context_requirements={"task_output.modified_value": "number"},
            dependencies=[TaskDependency(task2_id, DependencyType.REQUIRED)],
            priority=TaskPriority.LOW,
        )
        
        # Add propagation rules
        execution_engine.context_propagator.add_rule(
            "task_output.created_value", "task_output.created_value"
        )
        execution_engine.context_propagator.add_rule(
            "task_output.created_value", "task_output.modified_value"
        )
        
        # Mock the task execution function
        def task1_output(task_id, prepared_context):
            return {
                "status": "complete",
                "task_id": task_id,
                "result_" + task_id: "success",
                "task_output": {"created_value": 100}
            }
        
        execution_engine._simulate_task_execution = task1_output
        
        # Execute first task
        execution_engine.execute_task(task1_id)
        
        # Verify that context was created
        task_output = execution_engine.context_manager.get_context("task_output")
        assert task_output is not None, "task_output context not found"
        assert "created_value" in task_output["task_output"], "created_value missing from task_output"
        assert task_output["task_output"]["created_value"] == 100, "created_value not correctly set"
        
        # Mock the second task execution
        def task2_output(task_id, prepared_context):
            return {
                "status": "complete",
                "task_id": task_id,
                "result_" + task_id: "success",
                "task_output": {
                    "created_value": 100,
                    "modified_value": 200
                }
            }
        
        execution_engine._simulate_task_execution = task2_output
        
        # Execute second task
        execution_engine.execute_task(task2_id)
        
        # Verify that context was modified
        task_output = execution_engine.context_manager.get_context("task_output")
        assert task_output is not None, "task_output context not found after task2"
        assert "modified_value" in task_output["task_output"], "modified_value missing from task_output"
        assert task_output["task_output"]["modified_value"] == 200, "modified_value not correctly set"
        
        # Mock the third task execution
        def task3_output(task_id, prepared_context):
            return {
                "status": "complete", 
                "task_id": task_id,
                "result_" + task_id: "success",
                "task_output": {
                    "created_value": 100,
                    "modified_value": 200,
                    "final_value": "cleaned"
                }
            }
        
        execution_engine._simulate_task_execution = task3_output
        
        # Execute third task
        execution_engine.execute_task(task3_id)
        
        # Verify that context was finalized
        task_output = execution_engine.context_manager.get_context("task_output")
        assert task_output is not None, "task_output context not found after task3"
        assert "final_value" in task_output["task_output"], "final_value missing from task_output"
        assert task_output["task_output"]["final_value"] == "cleaned", "final_value not correctly set"
        
        # Reset the mock for other tests
        execution_engine._simulate_task_execution = None 