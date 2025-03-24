import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from src.server.execution_engine.priority_calculator import PriorityCalculator
from src.server.execution_engine.task_selector import TaskStatus, TaskPriority, TaskDependency

# MockTask to avoid Task initialization issues
class MockTask:
    def __init__(self, id, name, description, priority, status, dependencies, 
                 estimated_duration, created_at, tags=None, 
                 estimated_resources=None, context_requirements=None, 
                 updated_at=None, metadata=None):
        self.id = id
        self.name = name
        self.description = description
        self.priority = priority
        self.status = status
        self.dependencies = dependencies
        self.estimated_duration = estimated_duration
        self.created_at = created_at
        self.updated_at = updated_at or created_at
        self.tags = tags or []
        self.estimated_resources = estimated_resources or {}
        self.context_requirements = context_requirements or []
        self.metadata = metadata or {}


@pytest.fixture
def task_selector():
    """Create a mocked TaskSelector instance."""
    mock_task_selector = MagicMock()
    
    # Create test tasks with dependencies
    task1 = MockTask(
        id="task1",
        name="High Priority Task",
        description="A high priority task",
        priority=TaskPriority.HIGH,
        status=TaskStatus.READY,
        dependencies=[],
        estimated_duration=5.0,
        created_at=datetime.now() - timedelta(hours=2),
        tags=["critical"]
    )
    
    task2 = MockTask(
        id="task2",
        name="Medium Priority Task",
        description="A medium priority task",
        priority=TaskPriority.MEDIUM,
        status=TaskStatus.READY,
        dependencies=[TaskDependency(task_id="task1", type="hard", condition="")],
        estimated_duration=10.0,
        created_at=datetime.now() - timedelta(hours=1),
        tags=["maintenance"]
    )
    
    task3 = MockTask(
        id="task3",
        name="Low Priority Task",
        description="A low priority task",
        priority=TaskPriority.LOW,
        status=TaskStatus.READY,
        dependencies=[TaskDependency(task_id="task2", type="hard", condition="")],
        estimated_duration=3.0,
        created_at=datetime.now() - timedelta(minutes=30),
        tags=["optional"]
    )
    
    # Configure mock
    mock_task_selector.tasks = {
        "task1": task1,
        "task2": task2,
        "task3": task3
    }
    
    # Setup dependency graph
    mock_task_selector.dependency_graph = {
        "task1": {"task2"},
        "task2": {"task3"},
        "task3": set()
    }
    
    return mock_task_selector


@pytest.fixture
def context_manager():
    """Create a mocked ContextManager instance."""
    mock_context_manager = MagicMock()
    mock_context_manager.get_context.return_value = "test_value"
    mock_context_manager.task_selector = MagicMock()
    return mock_context_manager


@pytest.fixture
def resource_manager():
    """Create a mocked ResourceManager instance."""
    mock_resource_manager = MagicMock()
    mock_resource_manager.get_available_resources.return_value = {
        "cpu": 8.0,
        "memory": 16384,
        "disk": 1024000
    }
    return mock_resource_manager


@pytest.fixture
def priority_calculator():
    """Create a PriorityCalculator instance for testing."""
    return PriorityCalculator()


class TestPriorityCalculator:
    """Test suite for PriorityCalculator."""
    
    def test_initialization(self, priority_calculator):
        """Test that the calculator initializes correctly."""
        assert priority_calculator.weights["base_priority"] == 1.0
        assert priority_calculator.weights["urgency"] == 0.8
        assert priority_calculator.weights["dependency_impact"] == 0.7
        assert priority_calculator.weights["resource_availability"] == 0.6
        assert priority_calculator.weights["context_relevance"] == 0.5
        assert isinstance(priority_calculator.tag_priorities, dict)
        assert isinstance(priority_calculator.custom_priority_functions, list)

    def test_calculate_base_priority(self, priority_calculator):
        """Test calculating base priority from task priority enum."""
        # Test for HIGH priority
        assert priority_calculator._normalize_base_priority(TaskPriority.HIGH) == 0.75
        
        # Test for MEDIUM priority
        assert priority_calculator._normalize_base_priority(TaskPriority.MEDIUM) == 0.5
        
        # Test for LOW priority
        assert priority_calculator._normalize_base_priority(TaskPriority.LOW) == 0.25

    def test_calculate_waiting_time_factor(self, priority_calculator):
        """Test calculating waiting time factor based on creation time."""
        # Create tasks with different creation times
        now = datetime.now()
        
        # Task created 5 hours ago
        old_task = MockTask(
            id="old_task",
            name="Old Task",
            description="Old Task",
            priority=TaskPriority.HIGH,
            status=TaskStatus.READY,
            dependencies=[],
            estimated_duration=5.0,
            created_at=now - timedelta(hours=5),
            tags=["critical"]
        )
        
        # Task created 1 hour ago
        recent_task = MockTask(
            id="recent_task",
            name="Recent Task",
            description="Recent Task",
            priority=TaskPriority.HIGH,
            status=TaskStatus.READY,
            dependencies=[],
            estimated_duration=5.0,
            created_at=now - timedelta(hours=1),
            tags=["critical"]
        )
        
        # Task just created
        new_task = MockTask(
            id="new_task",
            name="New Task",
            description="New Task",
            priority=TaskPriority.HIGH,
            status=TaskStatus.READY,
            dependencies=[],
            estimated_duration=5.0,
            created_at=now,
            tags=["critical"]
        )
        
        # Calculate waiting time factors
        old_factor = priority_calculator._calculate_waiting_time_factor(old_task)
        recent_factor = priority_calculator._calculate_waiting_time_factor(recent_task)
        new_factor = priority_calculator._calculate_waiting_time_factor(new_task)
        
        # Older tasks should have higher waiting time factors
        assert old_factor > recent_factor > new_factor
        assert new_factor >= 0  # New task should have minimal waiting time factor

    def test_calculate_dependency_factor(self, priority_calculator, task_selector):
        """Test calculating dependency factor."""
        # Create task with dependencies
        dependent_task = MockTask(
            id="dependent_task",
            name="Dependent Task",
            description="Dependent Task",
            priority=TaskPriority.HIGH,
            status=TaskStatus.BLOCKED,
            dependencies=[
                TaskDependency(task_id="task1", type="hard", condition=""),
                TaskDependency(task_id="task2", type="soft", condition="")
            ],
            estimated_duration=5.0,
            created_at=datetime.now() - timedelta(hours=1),
            tags=["critical"]
        )
        
        # Add to task selector's dependency graph
        task_selector.dependency_graph["dependent_task"] = set()
        
        # Calculate dependency factor
        factor = priority_calculator._calculate_dependency_impact(dependent_task, task_selector)
        
        # Factor should be based on the number of tasks dependent on this one
        assert factor >= 0
        
        # Task with no dependencies
        no_dep_task = MockTask(
            id="no_dep_task",
            name="No Dependencies",
            description="No Dependencies",
            priority=TaskPriority.HIGH,
            status=TaskStatus.READY,
            dependencies=[],
            estimated_duration=5.0,
            created_at=datetime.now(),
            tags=["critical"]
        )
        
        # Add a task depending on no_dep_task
        task_selector.dependency_graph["no_dep_task"] = {"dependent_task"}
        factor = priority_calculator._calculate_dependency_impact(no_dep_task, task_selector)
        
        # Factor should be non-zero when tasks depend on it
        assert factor > 0

    def test_calculate_tag_priority_factor(self, priority_calculator):
        """Test calculating priority factor based on tags."""
        # Set up tag priorities
        priority_calculator.set_tag_priorities({
            "critical": 0.5,
            "important": 0.3,
            "normal": 0.0,
            "background": -0.2
        })
        
        # Create tasks with different tags
        critical_task = MockTask(
            id="critical_task",
            name="Critical Task",
            description="Critical Task",
            priority=TaskPriority.HIGH,
            status=TaskStatus.READY,
            dependencies=[],
            estimated_duration=5.0,
            created_at=datetime.now() - timedelta(hours=2),
            tags=["critical", "normal"]
        )
        
        important_task = MockTask(
            id="important_task",
            name="Important Task",
            description="Important Task",
            priority=TaskPriority.HIGH,
            status=TaskStatus.READY,
            dependencies=[],
            estimated_duration=5.0,
            created_at=datetime.now() - timedelta(hours=2),
            tags=["important"]
        )
        
        normal_task = MockTask(
            id="normal_task",
            name="Normal Task",
            description="Normal Task",
            priority=TaskPriority.MEDIUM,
            status=TaskStatus.READY,
            dependencies=[],
            estimated_duration=10.0,
            created_at=datetime.now() - timedelta(hours=1),
            tags=["normal"]
        )
        
        background_task = MockTask(
            id="background_task",
            name="Background Task",
            description="Background Task",
            priority=TaskPriority.LOW,
            status=TaskStatus.READY,
            dependencies=[],
            estimated_duration=15.0,
            created_at=datetime.now(),
            tags=["background", "normal"]
        )
        
        no_tag_task = MockTask(
            id="no_tag_task",
            name="No Tags Task",
            description="No Tags Task",
            priority=TaskPriority.HIGH,
            status=TaskStatus.READY,
            dependencies=[],
            estimated_duration=5.0,
            created_at=datetime.now() - timedelta(hours=2),
            tags=[]
        )
        
        # Calculate tag priority factors
        critical_factor = priority_calculator._calculate_tag_priority_factor(critical_task)
        important_factor = priority_calculator._calculate_tag_priority_factor(important_task)
        normal_factor = priority_calculator._calculate_tag_priority_factor(normal_task)
        background_factor = priority_calculator._calculate_tag_priority_factor(background_task)
        no_tag_factor = priority_calculator._calculate_tag_priority_factor(no_tag_task)
        
        # Verify factors reflect tag priorities
        assert critical_factor == 0.5  # Uses highest priority tag
        assert important_factor == 0.3
        assert normal_factor == 0.0
        assert background_factor == -0.2  # Uses lowest priority tag
        assert no_tag_factor == 0.0  # No tags = 0 boost

    def test_calculate_task_priority(self, priority_calculator, context_manager, resource_manager, task_selector):
        """Test calculating overall task priority."""
        # Create a task with metadata
        task = MockTask(
            id="test_task",
            name="Test Task",
            description="A test task",
            priority=TaskPriority.HIGH,
            status=TaskStatus.READY,
            dependencies=[],
            estimated_duration=5.0,
            created_at=datetime.now() - timedelta(hours=1),
            tags=["critical"],
            estimated_resources={"cpu": 2.0, "memory": 4096},
            context_requirements=["data_source", "configuration"],
            metadata={"deadline": datetime.now() + timedelta(hours=2)}
        )
        
        # Calculate priority
        priority = priority_calculator.calculate_effective_priority(task, context_manager, resource_manager)
        
        # Should return a numerical value
        assert isinstance(priority, float)
        assert priority > 0

    def test_calculate_all_priorities(self, priority_calculator, context_manager, resource_manager, task_selector):
        """Test calculating priorities for all tasks."""
        # Calculate all priorities
        all_priorities = priority_calculator.calculate_all_priorities(
            task_selector.tasks.values(),
            context_manager,
            resource_manager
        )
        
        # Should return a dictionary mapping task IDs to priorities
        assert isinstance(all_priorities, dict)
        assert len(all_priorities) == len(task_selector.tasks)
        assert all(isinstance(p, float) for p in all_priorities.values())

    def test_set_priority_factors(self, priority_calculator):
        """Test setting custom priority factors."""
        # Original weights
        original_weights = priority_calculator.weights.copy()
        
        # Set new weights
        new_weights = {
            "base_priority": 0.5,
            "urgency": 1.0,
            "custom_factor": 0.8
        }
        priority_calculator.set_priority_factors(new_weights)
        
        # Verify weights were updated
        assert priority_calculator.weights["base_priority"] == 0.5
        assert priority_calculator.weights["urgency"] == 1.0
        assert priority_calculator.weights["custom_factor"] == 0.8
        
        # Verify other weights remained unchanged
        assert priority_calculator.weights["dependency_impact"] == original_weights["dependency_impact"]

    def test_set_tag_priorities(self, priority_calculator):
        """Test setting tag-based priority boosts."""
        # Set tag priorities
        tag_priorities = {
            "critical": 0.9,
            "important": 0.6,
            "normal": 0.3,
            "low": 0.1
        }
        priority_calculator.set_tag_priorities(tag_priorities)
        
        # Verify priorities were set
        assert priority_calculator.tag_priorities == tag_priorities
        
        # Test with a task that has a critical tag
        task = MockTask(
            id="critical_task",
            name="Critical Task",
            description="A critical task",
            priority=TaskPriority.MEDIUM,
            status=TaskStatus.READY,
            dependencies=[],
            estimated_duration=5.0,
            created_at=datetime.now(),
            tags=["critical"]
        )
        
        # Calculate tag factor
        factor = priority_calculator._calculate_tag_priority_factor(task)
        assert factor == 0.9  # Should match the priority boost for "critical"

    def test_get_task_priority_score(self, priority_calculator):
        """Test getting base priority score for a task."""
        # Create tasks with different priorities
        high_task = MockTask(
            id="high_task",
            name="High Priority Task",
            description="A high priority task",
            priority=TaskPriority.HIGH,
            status=TaskStatus.READY,
            dependencies=[],
            estimated_duration=5.0,
            created_at=datetime.now(),
            tags=[]
        )
        
        medium_task = MockTask(
            id="medium_task",
            name="Medium Priority Task",
            description="A medium priority task",
            priority=TaskPriority.MEDIUM,
            status=TaskStatus.READY,
            dependencies=[],
            estimated_duration=5.0,
            created_at=datetime.now(),
            tags=[]
        )
        
        low_task = MockTask(
            id="low_task",
            name="Low Priority Task",
            description="A low priority task",
            priority=TaskPriority.LOW,
            status=TaskStatus.READY,
            dependencies=[],
            estimated_duration=5.0,
            created_at=datetime.now(),
            tags=[]
        )
        
        # Get priority scores
        high_score = priority_calculator.get_task_priority_score(high_task)
        medium_score = priority_calculator.get_task_priority_score(medium_task)
        low_score = priority_calculator.get_task_priority_score(low_task)
        
        # Verify scores match expected values
        assert high_score > medium_score > low_score
        assert high_score == 0.75  # HIGH priority normalized is 75/100 = 0.75
        assert medium_score == 0.5  # MEDIUM priority normalized is 50/100 = 0.5
        assert low_score == 0.25  # LOW priority normalized is 25/100 = 0.25

    def test_clear_priorities(self, priority_calculator):
        """Test clearing all priority settings."""
        # Set custom values
        priority_calculator.set_priority_factors({"base_priority": 0.1, "custom": 2.0})
        priority_calculator.set_tag_priorities({"test": 0.5})
        
        # Clear priorities
        priority_calculator.clear_priorities()
        
        # Verify defaults were restored
        assert priority_calculator.weights["base_priority"] == 1.0
        assert priority_calculator.weights["urgency"] == 0.8
        assert priority_calculator.weights["dependency_impact"] == 0.7
        assert priority_calculator.weights["resource_availability"] == 0.6
        assert priority_calculator.weights["context_relevance"] == 0.5
        assert "custom" not in priority_calculator.weights
        assert len(priority_calculator.tag_priorities) == 0
        assert len(priority_calculator.custom_priority_functions) == 0

    def test_custom_priority_function(self, priority_calculator):
        """Test adding custom priority calculation function."""
        # Create a task
        task = MockTask(
            id="test_task",
            name="Test Task",
            description="A test task",
            priority=TaskPriority.MEDIUM,
            status=TaskStatus.READY,
            dependencies=[],
            estimated_duration=5.0,
            created_at=datetime.now(),
            tags=[],
            metadata={"custom_value": 42}
        )
        
        # Define custom function
        def custom_factor(t):
            return t.metadata.get("custom_value", 0) / 100.0
        
        # Add custom function
        priority_calculator.add_custom_priority_function(custom_factor)
        
        # Calculate priority
        priority = priority_calculator.calculate_effective_priority(task)
        
        # Create identical task without the custom metadata
        task2 = MockTask(
            id="test_task2",
            name="Test Task 2",
            description="A test task",
            priority=TaskPriority.MEDIUM,
            status=TaskStatus.READY,
            dependencies=[],
            estimated_duration=5.0,
            created_at=datetime.now(),
            tags=[],
            metadata={}
        )
        
        # Calculate priority for second task
        priority2 = priority_calculator.calculate_effective_priority(task2)
        
        # First task should have higher priority due to custom factor
        assert priority > priority2 