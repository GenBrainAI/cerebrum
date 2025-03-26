import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from src.server.execution_engine.execution_engine import ExecutionEngine
from src.server.execution_engine.task_selector import Task, TaskStatus, TaskPriority, TaskDependency
from src.server.execution_engine.context_manager import ContextType, ContextManager
from src.server.execution_engine.parallel_execution_controller import ExecutionMode, ExecutionResult


@pytest.fixture
def context_manager():
    """Create a ContextManager instance."""
    return ContextManager()


@pytest.fixture
def execution_engine(context_manager):
    """Create an ExecutionEngine instance with mocked dependencies."""
    engine = ExecutionEngine(context_manager=context_manager)
    # Mock the _simulate_task_execution method to avoid actual execution
    engine._simulate_task_execution = MagicMock(return_value={
        "status": "complete",
        "result": "Simulated execution"
    })
    return engine


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
        assert execution_engine.task_selector is not None
        assert execution_engine.context_manager is not None
        assert execution_engine.resource_manager is not None
        assert execution_engine.parallel_controller is not None
        assert execution_engine.async_controller is not None
        assert execution_engine.execution_tracker is not None

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
        
        # Mock the execution result
        execution_engine._simulate_task_execution.return_value = {
            "result_" + task_id: "Simulated execution",
            "status": "complete"
        }
        
        # Execute the task
        result = execution_engine.execute_task(task_id)
        
        # Check result
        assert result is not None
        assert "result_" + task_id in result
        assert result["status"] == "complete"
        
        # Task status should be updated to COMPLETED
        assert execution_engine.task_selector.tasks[task_id].status == TaskStatus.COMPLETED

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
        
        # Mock the execution result
        execution_engine._simulate_task_execution.return_value = {
            "result_" + task_id: "Simulated execution with context",
            "status": "complete"
        }
        
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
        
        # Mock execution results
        execution_engine._simulate_task_execution.side_effect = [
            {"result_" + task1_id: "Task 1 execution", "status": "complete"},
            {"result_" + task2_id: "Task 2 execution", "status": "complete"}
        ]
        
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
        task_id = execution_engine.create_task(
            name="Next Task",
            description="A task to be executed next",
            priority=TaskPriority.MEDIUM,
            estimated_duration=5.0
        )
        
        # Mock the execution result
        execution_engine._simulate_task_execution.return_value = {
            "result_" + task_id: "Simulated next task execution",
            "status": "complete"
        }
        
        # Execute next task
        result = execution_engine.execute_next_task()
        
        # Check execution was successful
        assert result is not None
        assert result["status"] == "complete"

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

    @patch("src.server.execution_engine.execution_engine.ExecutionEngine._simulate_task_execution")
    def test_task_execution_failure(self, mock_simulate, execution_engine):
        """Test handling task execution failures."""
        # Create a task
        task_id = execution_engine.create_task(
            name="Failing Task",
            description="A task that will fail",
            priority=TaskPriority.MEDIUM
        )
        
        # Make task execution fail
        execution_engine._simulate_task_execution = mock_simulate  # Replace the fixture's mock with our test mock
        mock_simulate.side_effect = Exception("Task execution failed")
        
        # Execute the task
        result = execution_engine.execute_task(task_id)
        
        # Check failure was handled
        assert "error" in result
        assert "Task execution failed" in result["error"]
        
        # Task status should be FAILED
        assert execution_engine.task_selector.tasks[task_id].status == TaskStatus.FAILED 