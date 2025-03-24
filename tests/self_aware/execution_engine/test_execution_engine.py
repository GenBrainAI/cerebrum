import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from src.server.execution_engine.execution_engine import ExecutionEngine
from src.server.execution_engine.task_selector import Task, TaskStatus, TaskPriority, TaskDependency
from src.server.execution_engine.context_manager import ContextType


@pytest.fixture
def execution_engine():
    """Create an ExecutionEngine instance with mocked dependencies."""
    return ExecutionEngine()


@pytest.fixture
def sample_task():
    """Create a sample task for testing."""
    return Task(
        id="task1",
        name="Test Task",
        description="A test task",
        priority=TaskPriority.MEDIUM,
        status=TaskStatus.PENDING,
        dependencies=[],
        estimated_duration=10.0,
        estimated_resources={"cpu": 1.0, "memory": 512},
        context_requirements=["input_data"],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        tags=["test"],
        metadata={}
    )


class TestExecutionEngine:
    """Tests for the ExecutionEngine class."""

    def test_initialization(self, execution_engine):
        """Test that ExecutionEngine initializes its components correctly."""
        assert execution_engine.context_manager is not None
        assert execution_engine.task_selector is not None
        assert execution_engine.context_validator is not None
        assert execution_engine.context_optimizer is not None
        assert execution_engine.context_propagator is not None
        assert execution_engine.dependency_resolver is not None
        assert execution_engine.priority_calculator is not None
        assert execution_engine.current_task_id is None
        assert isinstance(execution_engine.execution_history, list)

    def test_register_task(self, execution_engine, sample_task):
        """Test registering a task with the execution engine."""
        task_id = execution_engine.register_task(sample_task)
        assert task_id == sample_task.id
        assert task_id in execution_engine.task_selector.tasks
        
        # Task with no dependencies should be ready
        assert execution_engine.task_selector.tasks[task_id].status == TaskStatus.READY

    def test_create_task(self, execution_engine):
        """Test creating a new task through the execution engine."""
        task_id = execution_engine.create_task(
            name="Created Task",
            description="A task created through the execution engine",
            priority=TaskPriority.HIGH,
            estimated_duration=5.0,
            estimated_resources={"cpu": 2.0, "memory": 1024},
            context_requirements=["config"],
            tags=["created", "test"]
        )
        
        # Task should be registered
        assert task_id in execution_engine.task_selector.tasks
        
        # Check task properties
        task = execution_engine.task_selector.tasks[task_id]
        assert task.name == "Created Task"
        assert task.description == "A task created through the execution engine"
        assert task.priority == TaskPriority.HIGH
        assert task.status == TaskStatus.READY  # No dependencies, so should be ready
        assert task.estimated_duration == 5.0
        assert task.estimated_resources == {"cpu": 2.0, "memory": 1024}
        assert task.context_requirements == ["config"]
        assert set(task.tags) == {"created", "test"}

    def test_select_next_task(self, execution_engine):
        """Test selecting the next task to execute."""
        # Create two tasks with different priorities
        high_priority_id = execution_engine.create_task(
            name="High Priority",
            description="A high priority task",
            priority=TaskPriority.HIGH,
            estimated_duration=5.0
        )
        
        low_priority_id = execution_engine.create_task(
            name="Low Priority",
            description="A low priority task",
            priority=TaskPriority.LOW,
            estimated_duration=5.0
        )
        
        # Select next task - should be the high priority one
        next_task = execution_engine.select_next_task()
        assert next_task is not None
        assert next_task.id == high_priority_id
        assert next_task.priority == TaskPriority.HIGH

    def test_execute_task(self, execution_engine):
        """Test executing a task."""
        # Create a task
        task_id = execution_engine.create_task(
            name="Task to Execute",
            description="A task to be executed",
            priority=TaskPriority.MEDIUM,
            estimated_duration=5.0,
            context_requirements=[]
        )
        
        # Execute the task
        result = execution_engine.execute_task(task_id)
        
        # Check result
        assert result is not None
        assert "result_" + task_id in result
        assert result["status"] == "complete"
        
        # Task status should be updated to COMPLETED
        assert execution_engine.task_selector.tasks[task_id].status == TaskStatus.COMPLETED
        
        # Execution history should be updated
        assert len(execution_engine.execution_history) == 1
        assert execution_engine.execution_history[0]["task_id"] == task_id
        assert execution_engine.execution_history[0]["status"] == "success"

    def test_execute_task_with_context(self, execution_engine):
        """Test executing a task with context requirements."""
        # Create a task that requires context
        task_id = execution_engine.create_task(
            name="Context Task",
            description="A task with context requirements",
            priority=TaskPriority.MEDIUM,
            estimated_duration=5.0,
            context_requirements=["input_data"]
        )
        
        # Set the required context
        execution_engine.context_manager.set_context(
            "input_data", {"value": 42}, ContextType.GLOBAL
        )
        
        # Execute the task
        result = execution_engine.execute_task(task_id)
        
        # Check execution was successful
        assert result is not None
        assert execution_engine.task_selector.tasks[task_id].status == TaskStatus.COMPLETED

    def test_execute_task_with_dependencies(self, execution_engine):
        """Test executing tasks with dependencies."""
        # Create two dependent tasks
        task1_id = execution_engine.create_task(
            name="Task 1",
            description="First task",
            priority=TaskPriority.HIGH,
            estimated_duration=5.0
        )
        
        task2_id = execution_engine.create_task(
            name="Task 2",
            description="Second task, depends on first",
            priority=TaskPriority.MEDIUM,
            dependencies=[TaskDependency(task1_id, "hard", "")],
            estimated_duration=10.0
        )
        
        # Task 2 should be blocked
        assert execution_engine.task_selector.tasks[task2_id].status == TaskStatus.BLOCKED
        
        # Execute task 1
        execution_engine.execute_task(task1_id)
        
        # Task 2 should now be ready
        assert execution_engine.task_selector.tasks[task2_id].status == TaskStatus.READY
        
        # Execute task 2
        execution_engine.execute_task(task2_id)
        
        # Both tasks should be completed
        assert execution_engine.task_selector.tasks[task1_id].status == TaskStatus.COMPLETED
        assert execution_engine.task_selector.tasks[task2_id].status == TaskStatus.COMPLETED

    def test_execute_next_task(self, execution_engine):
        """Test executing the next available task."""
        # Create a task
        execution_engine.create_task(
            name="Next Task",
            description="A task to be executed next",
            priority=TaskPriority.MEDIUM,
            estimated_duration=5.0
        )
        
        # Execute next task
        result = execution_engine.execute_next_task()
        
        # Check execution was successful
        assert result is not None
        assert result["status"] == "complete"
        assert len(execution_engine.execution_history) == 1

    def test_get_execution_state(self, execution_engine):
        """Test getting the execution state."""
        # Create some tasks with different statuses
        task1_id = execution_engine.create_task(
            name="Ready Task",
            description="A ready task",
            priority=TaskPriority.HIGH
        )
        
        task2_id = execution_engine.create_task(
            name="Blocked Task",
            description="A blocked task",
            priority=TaskPriority.MEDIUM,
            dependencies=[TaskDependency(task1_id, "hard", "")]
        )
        
        execution_engine.task_selector.update_task_status(task1_id, TaskStatus.IN_PROGRESS)
        
        # Get execution state
        state = execution_engine.get_execution_state()
        
        # Check state structure
        assert "task_counts" in state
        assert "current_task" in state
        assert "context_stats" in state
        assert "dependency_analysis" in state
        
        # Check task counts
        assert state["task_counts"]["total"] == 2
        assert state["task_counts"]["in_progress"] == 1
        assert state["task_counts"]["blocked"] == 1
        
        # Check current task
        assert state["current_task"] is None  # We haven't set this
        
        # Check context stats
        assert "global_keys" in state["context_stats"]
        assert "session_keys" in state["context_stats"]
        assert "task_keys" in state["context_stats"]
        assert "temporary_keys" in state["context_stats"]
        
        # Check dependency analysis
        assert "total_tasks" in state["dependency_analysis"]
        assert state["dependency_analysis"]["total_tasks"] == 2

    def test_context_integration(self, execution_engine):
        """Test integration between task execution and context management."""
        # Add validator for test
        execution_engine.context_validator.add_number_validator("number_key")
        
        # Add propagation rule
        execution_engine.context_propagator.add_rule(
            "input_data", "processed_data"
        )
        
        # Set context data
        execution_engine.context_manager.set_context("number_key", 42)
        execution_engine.context_manager.set_context("input_data", {"value": 100})
        
        # Create a task that processes data
        task_id = execution_engine.create_task(
            name="Processing Task",
            description="A task that processes data",
            priority=TaskPriority.MEDIUM,
            context_requirements=["processed_data"]
        )
        
        # Execute the task
        result = execution_engine.execute_task(task_id)
        assert result["status"] == "complete"
        
        # Check task status was updated
        assert execution_engine.task_selector.tasks[task_id].status == TaskStatus.COMPLETED
        
        # Check that processed data was propagated from the task output
        task_output = execution_engine.context_manager.get_context("task_output")
        assert task_output is not None, "Task output was not created"
        assert "processed_data" in task_output, "Processed data was not in task_output"
        assert task_output["processed_data"] is not None, "Processed data was null in task_output"
        assert task_output["processed_data"].get("value") is not None, "Processed data value was not set"

    @patch("src.server.execution_engine.execution_engine.ExecutionEngine._simulate_task_execution")
    def test_task_execution_failure(self, mock_simulate, execution_engine):
        """Test handling task execution failures."""
        # Make task execution fail
        mock_simulate.side_effect = Exception("Task execution failed")
        
        # Create a task
        task_id = execution_engine.create_task(
            name="Failing Task",
            description="A task that will fail",
            priority=TaskPriority.MEDIUM
        )
        
        # Execute the task
        result = execution_engine.execute_task(task_id)
        
        # Check failure was handled
        assert "error" in result
        assert "Task execution failed" in result["error"]
        
        # Task status should be FAILED
        assert execution_engine.task_selector.tasks[task_id].status == TaskStatus.FAILED
        
        # Execution history should reflect failure
        assert execution_engine.execution_history[0]["status"] == "failure" 