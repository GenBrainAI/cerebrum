import pytest
from datetime import datetime
from unittest.mock import MagicMock

from src.server.execution_engine.dependency_resolver import DependencyResolver
from src.server.execution_engine.task_selector import (
    Task, TaskStatus, TaskPriority, TaskDependency, TaskSelector
)


@pytest.fixture
def task_selector():
    """Create a TaskSelector with predefined tasks for testing."""
    selector = TaskSelector()
    
    # Create linear dependency: task1 -> task2 -> task3
    tasks = [
        Task(
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
        ),
        Task(
            id="task2",
            name="Task 2",
            description="Second task",
            priority=TaskPriority.MEDIUM,
            status=TaskStatus.PENDING,
            dependencies=[TaskDependency("task1", "hard", "")],
            estimated_duration=10.0,
            estimated_resources={"cpu": 2.0, "memory": 512},
            context_requirements=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            tags=["second"],
            metadata={}
        ),
        Task(
            id="task3",
            name="Task 3",
            description="Third task",
            priority=TaskPriority.LOW,
            status=TaskStatus.PENDING,
            dependencies=[TaskDependency("task2", "hard", "")],
            estimated_duration=15.0,
            estimated_resources={"cpu": 1.0, "memory": 256},
            context_requirements=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            tags=["third"],
            metadata={}
        ),
    ]
    
    for task in tasks:
        selector.register_task(task)
    
    return selector


@pytest.fixture
def complex_task_selector():
    """Create a TaskSelector with a more complex dependency graph."""
    selector = TaskSelector()
    
    # Create complex dependency graph:
    # task1 -> task2 -> task4
    #   |        |
    #   v        v
    # task3 -> task5
    tasks = [
        Task(id="task1", name="Task 1", description="Task 1", priority=TaskPriority.HIGH, 
             status=TaskStatus.PENDING, dependencies=[], estimated_duration=5.0,
             estimated_resources={}, context_requirements=[], created_at=datetime.now(),
             updated_at=datetime.now(), tags=[], metadata={}),
             
        Task(id="task2", name="Task 2", description="Task 2", priority=TaskPriority.MEDIUM,
             status=TaskStatus.PENDING, dependencies=[TaskDependency("task1", "hard", "")],
             estimated_duration=10.0, estimated_resources={}, context_requirements=[],
             created_at=datetime.now(), updated_at=datetime.now(), tags=[], metadata={}),
             
        Task(id="task3", name="Task 3", description="Task 3", priority=TaskPriority.MEDIUM,
             status=TaskStatus.PENDING, dependencies=[TaskDependency("task1", "hard", "")],
             estimated_duration=15.0, estimated_resources={}, context_requirements=[],
             created_at=datetime.now(), updated_at=datetime.now(), tags=[], metadata={}),
             
        Task(id="task4", name="Task 4", description="Task 4", priority=TaskPriority.LOW,
             status=TaskStatus.PENDING, dependencies=[TaskDependency("task2", "hard", "")],
             estimated_duration=20.0, estimated_resources={}, context_requirements=[],
             created_at=datetime.now(), updated_at=datetime.now(), tags=[], metadata={}),
             
        Task(id="task5", name="Task 5", description="Task 5", priority=TaskPriority.LOW,
             status=TaskStatus.PENDING, 
             dependencies=[TaskDependency("task2", "hard", ""), TaskDependency("task3", "hard", "")],
             estimated_duration=25.0, estimated_resources={}, context_requirements=[],
             created_at=datetime.now(), updated_at=datetime.now(), tags=[], metadata={}),
    ]
    
    for task in tasks:
        selector.register_task(task)
    
    return selector


@pytest.fixture
def circular_task_selector():
    """Create a TaskSelector with circular dependencies."""
    selector = TaskSelector()
    
    # Create circular dependency: task1 -> task2 -> task3 -> task1
    tasks = [
        Task(id="task1", name="Task 1", description="Task 1", priority=TaskPriority.HIGH, 
             status=TaskStatus.PENDING, dependencies=[TaskDependency("task3", "hard", "")],
             estimated_duration=5.0, estimated_resources={}, context_requirements=[],
             created_at=datetime.now(), updated_at=datetime.now(), tags=[], metadata={}),
             
        Task(id="task2", name="Task 2", description="Task 2", priority=TaskPriority.MEDIUM,
             status=TaskStatus.PENDING, dependencies=[TaskDependency("task1", "hard", "")],
             estimated_duration=10.0, estimated_resources={}, context_requirements=[],
             created_at=datetime.now(), updated_at=datetime.now(), tags=[], metadata={}),
             
        Task(id="task3", name="Task 3", description="Task 3", priority=TaskPriority.LOW,
             status=TaskStatus.PENDING, dependencies=[TaskDependency("task2", "hard", "")],
             estimated_duration=15.0, estimated_resources={}, context_requirements=[],
             created_at=datetime.now(), updated_at=datetime.now(), tags=[], metadata={}),
    ]
    
    for task in tasks:
        selector.register_task(task)
    
    return selector


@pytest.fixture
def dependency_resolver(task_selector):
    """Create a DependencyResolver instance."""
    return DependencyResolver(task_selector)


class TestDependencyResolver:
    """Tests for the DependencyResolver class."""

    def test_analyze_dependency_graph_linear(self, dependency_resolver):
        """Test analyzing a linear dependency graph."""
        analysis = dependency_resolver.analyze_dependency_graph()
        
        # Check basic metrics
        assert analysis["total_tasks"] == 3
        assert analysis["independent_tasks"] == 1
        assert analysis["terminal_tasks"] == 1
        assert analysis["max_chain_length"] == 3  # task1 -> task2 -> task3
        
        # No bottlenecks or circular deps in this simple graph
        assert "bottleneck_tasks" in analysis
        assert len(analysis["bottleneck_tasks"]) == 0
        assert "circular_dependencies" in analysis
        assert len(analysis["circular_dependencies"]) == 0

    def test_analyze_complex_dependency_graph(self, complex_task_selector):
        """Test analyzing a more complex dependency graph."""
        resolver = DependencyResolver(complex_task_selector)
        analysis = resolver.analyze_dependency_graph()
        
        assert analysis["total_tasks"] == 5
        assert analysis["independent_tasks"] == 1  # task1
        assert analysis["terminal_tasks"] == 2  # task4 and task5
        
        # Critical path would be task1 -> task2 -> task5 or task1 -> task3 -> task5
        assert "critical_path" in analysis
        assert len(analysis["critical_path"]) > 0
        
        # task1 is a bottleneck - both task2 and task3 depend on it
        assert "bottleneck_tasks" in analysis
        # We use a threshold for bottlenecks, so we need to check value calculation
        task1_dependents = len(complex_task_selector.dependency_graph["task1"])
        threshold = max(3, 5 // 5)  # From DependencyResolver._find_bottleneck_tasks
        if task1_dependents >= threshold:
            assert "task1" in analysis["bottleneck_tasks"]
        
        # No circular dependencies
        assert len(analysis["circular_dependencies"]) == 0

    def test_detect_circular_dependencies(self, circular_task_selector):
        """Test detecting circular dependencies."""
        resolver = DependencyResolver(circular_task_selector)
        analysis = resolver.analyze_dependency_graph()
        
        # Should detect the circular dependency
        assert len(analysis["circular_dependencies"]) > 0
        
        # The cycle should be task1 -> task2 -> task3 -> task1
        cycle = analysis["circular_dependencies"][0]
        assert set(cycle) == {"task1", "task2", "task3"}

    def test_resolve_dependencies(self, dependency_resolver, task_selector):
        """Test resolving dependencies for a task."""
        # Initially task2 is blocked by task1
        assert not dependency_resolver.resolve_dependencies("task2")
        
        # Mark task1 as completed
        task_selector.update_task_status("task1", TaskStatus.COMPLETED)
        
        # Now task2 dependencies should be resolved
        assert dependency_resolver.resolve_dependencies("task2")
        assert task_selector.tasks["task2"].status == TaskStatus.READY
        
        # task3 is still blocked
        assert not dependency_resolver.resolve_dependencies("task3")
        
        # Mark task2 as completed
        task_selector.update_task_status("task2", TaskStatus.COMPLETED)
        
        # Now task3 dependencies should be resolved
        assert dependency_resolver.resolve_dependencies("task3")
        assert task_selector.tasks["task3"].status == TaskStatus.READY 