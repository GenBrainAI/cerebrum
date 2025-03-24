import pytest
from datetime import datetime
from unittest.mock import MagicMock

from src.server.execution_engine.task_selector import (
    TaskSelector, Task, TaskStatus, TaskPriority, TaskDependency
)


@pytest.fixture
def task_selector():
    """Create a TaskSelector instance with mocked dependencies."""
    context_manager = MagicMock()
    resource_manager = MagicMock()
    return TaskSelector(context_manager, resource_manager)


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


@pytest.fixture
def dependent_tasks():
    """Create a set of dependent tasks for testing."""
    task1 = Task(
        id="task1",
        name="Task 1",
        description="First task",
        priority=TaskPriority.HIGH,
        status=TaskStatus.PENDING,
        dependencies=[],
        estimated_duration=5.0,
        estimated_resources={"cpu": 1.0, "memory": 256},
        context_requirements=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        tags=["first"],
        metadata={}
    )
    
    task2 = Task(
        id="task2",
        name="Task 2",
        description="Second task that depends on first",
        priority=TaskPriority.MEDIUM,
        status=TaskStatus.PENDING,
        dependencies=[TaskDependency("task1", "hard", "")],
        estimated_duration=10.0,
        estimated_resources={"cpu": 2.0, "memory": 512},
        context_requirements=["task1_output"],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        tags=["second"],
        metadata={}
    )
    
    task3 = Task(
        id="task3",
        name="Task 3",
        description="Third task that depends on second",
        priority=TaskPriority.LOW,
        status=TaskStatus.PENDING,
        dependencies=[TaskDependency("task2", "hard", "")],
        estimated_duration=15.0,
        estimated_resources={"cpu": 1.0, "memory": 256},
        context_requirements=["task2_output"],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        tags=["third"],
        metadata={}
    )
    
    return [task1, task2, task3]


class TestTaskSelector:
    """Tests for the TaskSelector class."""

    def test_register_task(self, task_selector, sample_task):
        """Test registering a task."""
        task_id = task_selector.register_task(sample_task)
        assert task_id == sample_task.id
        assert task_id in task_selector.tasks
        assert task_id in task_selector.dependency_graph
        assert task_selector.tasks[task_id].status == TaskStatus.READY  # No dependencies, should be ready

    def test_register_dependent_tasks(self, task_selector, dependent_tasks):
        """Test registering tasks with dependencies."""
        for task in dependent_tasks:
            task_selector.register_task(task)
        
        # First task should be ready (no dependencies)
        assert task_selector.tasks["task1"].status == TaskStatus.READY
        
        # Second and third should be blocked
        assert task_selector.tasks["task2"].status == TaskStatus.BLOCKED
        assert task_selector.tasks["task3"].status == TaskStatus.BLOCKED
        
        # Check dependency graph
        assert "task2" in task_selector.dependency_graph["task1"]
        assert "task3" in task_selector.dependency_graph["task2"]

    def test_update_task_status(self, task_selector, dependent_tasks):
        """Test updating task status and dependency propagation."""
        for task in dependent_tasks:
            task_selector.register_task(task)
        
        # Complete the first task
        task_selector.update_task_status("task1", TaskStatus.COMPLETED)
        
        # Second task should now be ready
        assert task_selector.tasks["task2"].status == TaskStatus.READY
        
        # Third task should still be blocked
        assert task_selector.tasks["task3"].status == TaskStatus.BLOCKED
        
        # Complete the second task
        task_selector.update_task_status("task2", TaskStatus.COMPLETED)
        
        # Third task should now be ready
        assert task_selector.tasks["task3"].status == TaskStatus.READY

    def test_select_next_task_priority(self, task_selector, dependent_tasks):
        """Test selecting task by priority."""
        # Modify tasks to all be ready
        for task in dependent_tasks:
            task.dependencies = []
            task.status = TaskStatus.READY
            task_selector.register_task(task)
        
        # Default strategy is priority_first
        next_task = task_selector.select_next_task()
        assert next_task.id == "task1"  # Highest priority
        
        # Change priorities
        task_selector.tasks["task3"].priority = TaskPriority.CRITICAL
        next_task = task_selector.select_next_task()
        assert next_task.id == "task3"  # Now highest priority

    def test_selection_strategies(self, task_selector, dependent_tasks):
        """Test different task selection strategies."""
        # Modify tasks to all be ready with different durations
        for task in dependent_tasks:
            task.dependencies = []
            task.status = TaskStatus.READY
            task_selector.register_task(task)
        
        # Test shortest_first strategy
        task_selector.set_selection_strategy("shortest_first")
        next_task = task_selector.select_next_task()
        assert next_task.id == "task1"  # Shortest duration
        
        # Test dependency_chain strategy
        task_selector.set_selection_strategy("dependency_chain")
        # We need to set up dependencies again for this test
        task_selector.dependency_graph = {
            "task1": {"task2"},
            "task2": {"task3"},
            "task3": set()
        }
        next_task = task_selector.select_next_task()
        assert next_task.id == "task1"  # Unblocks longest chain
        
        # Reset to default strategy
        task_selector.set_selection_strategy("priority_first")

    def test_get_tasks_by_status(self, task_selector, dependent_tasks):
        """Test getting tasks by status."""
        for task in dependent_tasks:
            task_selector.register_task(task)
        
        # Only task1 should be ready
        ready_tasks = task_selector.get_tasks_by_status(TaskStatus.READY)
        assert len(ready_tasks) == 1
        assert ready_tasks[0].id == "task1"
        
        # Two tasks should be blocked
        blocked_tasks = task_selector.get_tasks_by_status(TaskStatus.BLOCKED)
        assert len(blocked_tasks) == 2
        assert set(t.id for t in blocked_tasks) == {"task2", "task3"}

    def test_get_blocked_task_reasons(self, task_selector, dependent_tasks):
        """Test getting reasons why a task is blocked."""
        for task in dependent_tasks:
            task_selector.register_task(task)
        
        # Check reasons for task2 being blocked
        reasons = task_selector.get_blocked_task_reasons("task2")
        assert len(reasons) == 1
        assert "Task 1" in reasons[0]  # Should mention the dependency name
        
        # Complete task1
        task_selector.update_task_status("task1", TaskStatus.COMPLETED)
        
        # Task2 should no longer be blocked
        assert task_selector.tasks["task2"].status == TaskStatus.READY
        assert len(task_selector.get_blocked_task_reasons("task2")) == 0 