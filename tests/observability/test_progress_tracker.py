import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
import json
import os
import tempfile
from datetime import datetime, timedelta

from src.server.observability.progress_tracker import (
    ProgressTracker, 
    ProgressState, 
    ProgressMetric, 
    TrackingLevel
)

@pytest.fixture
def progress_tracker():
    """Create a ProgressTracker instance for testing."""
    return ProgressTracker(config={
        "tracking_level": TrackingLevel.STANDARD,
        "snapshot_interval": 0.1,  # Fast for testing
        "visualization_enabled": True,
        "notification_thresholds": {
            "stalled_minutes": 0.1,  # Fast for testing
            "completion_percentage": 90,
            "failure_count": 3
        }
    })

@pytest.fixture
def sample_metrics():
    """Create sample metrics for testing."""
    return {
        "tasks_completed": ProgressMetric(
            name="Tasks Completed",
            description="Number of tasks completed",
            current_value=5,
            target_value=10,
            unit="tasks"
        ),
        "time_spent": ProgressMetric(
            name="Time Spent",
            description="Time spent on the item",
            current_value=120,
            target_value=300,
            unit="minutes"
        )
    }

class TestProgressTracker:
    """Test suite for ProgressTracker."""
    
    @pytest.mark.asyncio
    async def test_register_item(self, progress_tracker, sample_metrics):
        """Test item registration."""
        item = await progress_tracker.register_item(
            item_id="test_item",
            item_type="task",
            name="Test Item",
            description="A test item",
            expected_duration=3600,
            metrics=sample_metrics
        )
        
        assert item["id"] == "test_item"
        assert item["name"] == "Test Item"
        assert item["state"] == ProgressState.NOT_STARTED
        assert item["completion_percentage"] == 0.0
        assert "tasks_completed" in item["metrics"]
        assert len(item["snapshots"]) == 1
    
    @pytest.mark.asyncio
    async def test_update_progress(self, progress_tracker):
        """Test progress updates."""
        # Register item
        await progress_tracker.register_item(
            item_id="test_item",
            item_type="task",
            name="Test Item",
            description="A test item"
        )
        
        # Update progress
        updated = await progress_tracker.update_progress(
            item_id="test_item",
            state=ProgressState.IN_PROGRESS,
            completion_percentage=50.0,
            message="Making progress"
        )
        
        assert updated["state"] == ProgressState.IN_PROGRESS
        assert updated["completion_percentage"] == 50.0
        assert updated["start_time"] is not None
        assert len(updated["snapshots"]) == 2
        
        # Update to completion
        completed = await progress_tracker.update_progress(
            item_id="test_item",
            state=ProgressState.COMPLETED,
            completion_percentage=100.0,
            message="Task completed"
        )
        
        assert completed["state"] == ProgressState.COMPLETED
        assert completed["completion_percentage"] == 100.0
        assert completed["end_time"] is not None
    
    @pytest.mark.asyncio
    async def test_parent_child_relationship(self, progress_tracker):
        """Test parent-child progress propagation."""
        # Register parent
        await progress_tracker.register_item(
            item_id="parent_item",
            item_type="project",
            name="Parent Item",
            description="A parent item"
        )
        
        # Register child
        await progress_tracker.register_item(
            item_id="child_item",
            item_type="task",
            name="Child Item",
            description="A child item",
            parent_id="parent_item"
        )
        
        # Update child progress
        await progress_tracker.update_progress(
            item_id="child_item",
            state=ProgressState.IN_PROGRESS,
            completion_percentage=50.0
        )
        
        # Check parent progress
        parent = progress_tracker.tracked_items["parent_item"]
        assert parent["completion_percentage"] == 50.0
        
        # Complete child
        await progress_tracker.update_progress(
            item_id="child_item",
            state=ProgressState.COMPLETED,
            completion_percentage=100.0
        )
        
        # Check parent state
        parent = progress_tracker.tracked_items["parent_item"]
        assert parent["completion_percentage"] == 100.0
        assert parent["state"] == ProgressState.COMPLETED
    
    @pytest.mark.asyncio
    async def test_notifications(self, progress_tracker):
        """Test notification generation."""
        # Register item
        await progress_tracker.register_item(
            item_id="test_item",
            item_type="task",
            name="Test Item",
            description="A test item"
        )
        
        # Create notification
        notification = await progress_tracker._create_notification(
            item_id="test_item",
            notification_type="test",
            message="Test notification"
        )
        
        assert notification["item_id"] == "test_item"
        assert notification["type"] == "test"
        assert notification["message"] == "Test notification"
        assert not notification["acknowledged"]
        
        # Get notifications
        notifications = await progress_tracker.get_notifications()
        assert len(notifications) == 1
        
        # Acknowledge notification
        acknowledged = await progress_tracker.acknowledge_notification(
            notification["id"]
        )
        
        assert acknowledged["acknowledged"]
        assert "acknowledgment_time" in acknowledged
        
        # Check filtered notifications
        filtered = await progress_tracker.get_notifications(acknowledged=False)
        assert len(filtered) == 0
    
    @pytest.mark.asyncio
    async def test_progress_report(self, progress_tracker):
        """Test progress reporting."""
        # Register items
        await progress_tracker.register_item(
            item_id="parent_item",
            item_type="project",
            name="Parent Item",
            description="A parent item"
        )
        
        await progress_tracker.register_item(
            item_id="child_item1",
            item_type="task",
            name="Child Item 1",
            description="A child item",
            parent_id="parent_item"
        )
        
        await progress_tracker.register_item(
            item_id="child_item2",
            item_type="task",
            name="Child Item 2",
            description="Another child item",
            parent_id="parent_item"
        )
        
        # Update progress
        await progress_tracker.update_progress(
            item_id="child_item1",
            state=ProgressState.COMPLETED,
            completion_percentage=100.0
        )
        
        await progress_tracker.update_progress(
            item_id="child_item2",
            state=ProgressState.IN_PROGRESS,
            completion_percentage=50.0
        )
        
        # Get item report
        report = await progress_tracker.get_progress_report(
            item_id="parent_item",
            include_children=True
        )
        
        assert report["id"] == "parent_item"
        assert report["completion_percentage"] == 75.0  # Average of children
        assert len(report["children"]) == 2
        
        # Get system report
        system_report = await progress_tracker.get_progress_report()
        
        assert "summary" in system_report
        assert system_report["summary"]["total_items"] == 3
        assert system_report["summary"]["completed_items"] == 1
        assert system_report["summary"]["in_progress_items"] == 2
        assert system_report["summary"]["overall_completion"] == 75.0
    
    @pytest.mark.asyncio
    async def test_save_load_data(self, progress_tracker, sample_metrics, tmpdir):
        """Test saving and loading tracking data."""
        # Register items
        await progress_tracker.register_item(
            item_id="test_item",
            item_type="task",
            name="Test Item",
            description="A test item",
            metrics=sample_metrics
        )
        
        # Update progress
        await progress_tracker.update_progress(
            item_id="test_item",
            state=ProgressState.IN_PROGRESS,
            completion_percentage=50.0
        )
        
        # Create notification
        await progress_tracker._create_notification(
            item_id="test_item",
            notification_type="test",
            message="Test notification"
        )
        
        # Save data
        file_path = os.path.join(tmpdir, "tracking_data.json")
        await progress_tracker.save_tracking_data(file_path)
        
        # Create new tracker
        new_tracker = ProgressTracker()
        
        # Load data
        await new_tracker.load_tracking_data(file_path)
        
        # Verify loaded data
        assert "test_item" in new_tracker.tracked_items
        assert new_tracker.tracked_items["test_item"]["name"] == "Test Item"
        assert new_tracker.tracked_items["test_item"]["completion_percentage"] == 50.0
        assert len(new_tracker.notifications) == 2 