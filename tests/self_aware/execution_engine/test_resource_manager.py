import pytest
from unittest.mock import MagicMock
from datetime import datetime

from src.server.execution_engine.resource_manager import ResourceManager, ResourceAllocationError, MockTask
from src.server.execution_engine.task_selector import TaskStatus, TaskPriority


@pytest.fixture
def resource_manager():
    """Create a ResourceManager instance with default limits."""
    return ResourceManager({
        "cpu": 8.0,
        "memory": 16384,  # MB
        "gpu": 1.0,
        "network": 100.0  # MB/s
    })


@pytest.fixture
def sample_task():
    """Create a sample task with resource requirements."""
    return MockTask(
        id="task1",
        name="Resource Test Task",
        description="A task for testing resource allocation",
        priority=TaskPriority.MEDIUM,
        status=TaskStatus.READY,
        dependencies=[],
        estimated_duration=10.0,
        estimated_resources={"cpu": 2.0, "memory": 4096},
        context_requirements=["input_data"],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        tags=["test"],
        metadata={}
    )


class TestResourceManager:
    """Tests for the ResourceManager class."""

    def test_initialization(self, resource_manager):
        """Test that ResourceManager initializes correctly with resource limits."""
        assert resource_manager.limits == {
            "cpu": 8.0,
            "memory": 16384,
            "gpu": 1.0,
            "network": 100.0
        }
        assert resource_manager.used == {
            "cpu": 0.0,
            "memory": 0,
            "gpu": 0.0,
            "network": 0.0
        }
        assert isinstance(resource_manager.task_allocations, dict)
        assert len(resource_manager.task_allocations) == 0

    def test_check_resources_available(self, resource_manager):
        """Test checking if resources are available."""
        # Resources should be available initially
        assert resource_manager.check_resources_available({"cpu": 4.0, "memory": 8192})
        
        # Allocate some resources
        resource_manager.used["cpu"] = 6.0
        resource_manager.used["memory"] = 12000
        
        # These resources should still be available
        assert resource_manager.check_resources_available({"cpu": 2.0, "memory": 4000})
        
        # These resources should not be available
        assert not resource_manager.check_resources_available({"cpu": 3.0, "memory": 5000})

    def test_allocate_resources(self, resource_manager, sample_task):
        """Test allocating resources for a task."""
        # Allocate resources for the task
        resource_manager.allocate_resources(sample_task.id, sample_task.estimated_resources)
        
        # Check resources were allocated
        assert resource_manager.used["cpu"] == 2.0
        assert resource_manager.used["memory"] == 4096
        assert sample_task.id in resource_manager.task_allocations
        assert resource_manager.task_allocations[sample_task.id] == {
            "cpu": 2.0,
            "memory": 4096
        }

    def test_allocate_resources_over_limit(self, resource_manager):
        """Test attempting to allocate resources over the limit."""
        # First allocation should succeed
        resource_manager.allocate_resources("task1", {"cpu": 6.0, "memory": 10000})
        
        # Second allocation should fail
        with pytest.raises(ResourceAllocationError):
            resource_manager.allocate_resources("task2", {"cpu": 3.0, "memory": 7000})

    def test_free_resources(self, resource_manager, sample_task):
        """Test freeing resources after a task completes."""
        # Allocate resources
        resource_manager.allocate_resources(sample_task.id, sample_task.estimated_resources)
        
        # Free resources
        resource_manager.free_resources(sample_task.id)
        
        # Check resources were freed
        assert resource_manager.used["cpu"] == 0.0
        assert resource_manager.used["memory"] == 0
        assert sample_task.id not in resource_manager.task_allocations

    def test_free_nonexistent_task(self, resource_manager):
        """Test freeing resources for a task that doesn't exist."""
        # Should not raise an error
        resource_manager.free_resources("nonexistent_task")
        
        # Resources should remain at zero
        assert resource_manager.used["cpu"] == 0.0
        assert resource_manager.used["memory"] == 0

    def test_get_available_resources(self, resource_manager):
        """Test getting available resources."""
        # Initially all resources are available
        available = resource_manager.get_available_resources()
        assert available == {
            "cpu": 8.0,
            "memory": 16384,
            "gpu": 1.0,
            "network": 100.0
        }
        
        # Allocate some resources
        resource_manager.allocate_resources("task1", {"cpu": 3.0, "memory": 6000})
        
        # Check available resources
        available = resource_manager.get_available_resources()
        assert available == {
            "cpu": 5.0,
            "memory": 10384,
            "gpu": 1.0,
            "network": 100.0
        }

    def test_get_resource_utilization(self, resource_manager):
        """Test getting resource utilization percentages."""
        # Initially utilization is 0%
        utilization = resource_manager.get_resource_utilization()
        assert utilization == {
            "cpu": 0.0,
            "memory": 0.0,
            "gpu": 0.0,
            "network": 0.0
        }
        
        # Allocate some resources
        resource_manager.allocate_resources("task1", {"cpu": 4.0, "memory": 8192})
        
        # Check utilization
        utilization = resource_manager.get_resource_utilization()
        assert utilization == {
            "cpu": 50.0,  # 4.0 / 8.0 * 100
            "memory": 50.0,  # 8192 / 16384 * 100
            "gpu": 0.0,
            "network": 0.0
        }

    def test_set_resource_limits(self, resource_manager):
        """Test setting new resource limits."""
        # Set new limits
        resource_manager.set_resource_limits({
            "cpu": 16.0,
            "memory": 32768,
            "gpu": 2.0
        })
        
        # Check limits were updated
        assert resource_manager.limits == {
            "cpu": 16.0,
            "memory": 32768,
            "gpu": 2.0,
            "network": 100.0  # This should remain unchanged
        }

    def test_set_resource_limits_below_used(self, resource_manager):
        """Test setting resource limits below currently used resources."""
        # Allocate some resources
        resource_manager.allocate_resources("task1", {"cpu": 6.0, "memory": 12000})
        
        # Try to set limits below what's being used
        with pytest.raises(ValueError):
            resource_manager.set_resource_limits({"cpu": 4.0})

    def test_can_allocate_partial_resources(self, resource_manager):
        """Test checking if partial resources can be allocated."""
        # Request resources
        requested = {"cpu": 10.0, "memory": 8192}
        
        # Check if we can allocate - should be partial (only memory)
        result = resource_manager.can_allocate_partial_resources(requested)
        assert result == {
            "can_allocate_all": False,
            "can_allocate_partial": True,
            "allocatable_resources": {"memory": 8192}
        }
        
        # Allocate all CPU resources
        resource_manager.allocate_resources("task1", {"cpu": 8.0})
        
        # Now check again - should not be able to allocate any
        result = resource_manager.can_allocate_partial_resources(requested)
        assert result == {
            "can_allocate_all": False,
            "can_allocate_partial": False,
            "allocatable_resources": {}
        }

    def test_monitor_resources(self, resource_manager):
        """Test resource monitoring."""
        # Create mock task selector
        task_selector = MagicMock()
        task_selector.get_tasks_by_status.return_value = {
            "task1": MockTask(
                id="task1",
                name="Task 1",
                description="Task 1",
                priority=TaskPriority.MEDIUM,
                status=TaskStatus.IN_PROGRESS,
                dependencies=[],
                estimated_resources={"cpu": 2.0, "memory": 4096},
                estimated_duration=5.0,
                context_requirements=[],
                created_at=datetime.now(),
                updated_at=datetime.now(),
                metadata={},
                tags=[]
            ),
            "task2": MockTask(
                id="task2",
                name="Task 2",
                description="Task 2",
                priority=TaskPriority.MEDIUM,
                status=TaskStatus.IN_PROGRESS,
                dependencies=[],
                estimated_resources={"cpu": 3.0, "memory": 6144},
                estimated_duration=5.0,
                context_requirements=[],
                created_at=datetime.now(),
                updated_at=datetime.now(),
                metadata={},
                tags=[]
            )
        }
        
        # Monitor resources for running tasks
        resource_manager.monitor_resources(task_selector)
        
        # Check that resources were allocated for both tasks
        assert resource_manager.used["cpu"] == 5.0
        assert resource_manager.used["memory"] == 10240
        assert len(resource_manager.task_allocations) == 2
        assert "task1" in resource_manager.task_allocations
        assert "task2" in resource_manager.task_allocations

    def test_resource_reservation(self, resource_manager):
        """Test reserving resources for future allocation."""
        # Reserve some resources
        reservation_id = resource_manager.reserve_resources({"cpu": 2.0, "memory": 4096})
        
        # Check reservation
        assert reservation_id in resource_manager.task_allocations
        assert resource_manager.used["cpu"] == 2.0
        assert resource_manager.used["memory"] == 4096
        
        # Try to allocate more than what's available after reservation
        with pytest.raises(ResourceAllocationError):
            resource_manager.allocate_resources("task1", {"cpu": 7.0, "memory": 13000})
        
        # Cancel reservation
        resource_manager.cancel_reservation(reservation_id)
        
        # Check resources were freed
        assert resource_manager.used["cpu"] == 0.0
        assert resource_manager.used["memory"] == 0
        assert reservation_id not in resource_manager.task_allocations 