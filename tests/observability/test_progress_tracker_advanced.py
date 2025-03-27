import pytest
import asyncio
import tempfile
import os
import json
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta

from src.server.observability.progress_tracker import (
    ProgressTracker, 
    ProgressState, 
    ProgressMetric, 
    TrackingLevel,
    ProgressSnapshot
)

@pytest.fixture
def progress_tracker():
    """Create a ProgressTracker instance with test configuration."""
    return ProgressTracker(config={
        "tracking_level": TrackingLevel.DETAILED,
        "snapshot_interval": 0.1,  # Fast for testing
        "visualization_enabled": True,
        "notification_thresholds": {
            "stalled_minutes": 0.1,  # Fast for testing
            "completion_percentage": 90,
            "failure_count": 3
        }
    })

@pytest.fixture
def complex_task_hierarchy():
    """Create a complex task hierarchy for testing advanced tracking features."""
    return [
        {
            "id": "project",
            "name": "Main Project",
            "type": "project",
            "children": [
                {
                    "id": "phase1",
                    "name": "Planning Phase",
                    "type": "phase",
                    "children": [
                        {
                            "id": "task1",
                            "name": "Requirements Gathering",
                            "type": "task"
                        },
                        {
                            "id": "task2",
                            "name": "Architecture Design",
                            "type": "task"
                        }
                    ]
                },
                {
                    "id": "phase2",
                    "name": "Implementation Phase",
                    "type": "phase",
                    "children": [
                        {
                            "id": "task3",
                            "name": "Development Task",
                            "type": "task",
                            "children": [
                                {
                                    "id": "subtask1",
                                    "name": "Backend Development",
                                    "type": "subtask"
                                },
                                {
                                    "id": "subtask2",
                                    "name": "Frontend Development",
                                    "type": "subtask"
                                }
                            ]
                        },
                        {
                            "id": "task4",
                            "name": "Testing Task",
                            "type": "task"
                        }
                    ]
                },
                {
                    "id": "milestone1",
                    "name": "Alpha Release",
                    "type": "milestone"
                }
            ]
        }
    ]

class TestProgressTrackerAdvanced:
    """Advanced test cases for ProgressTracker."""
    
    @pytest.mark.asyncio
    async def test_deep_hierarchical_tracking(self, progress_tracker, complex_task_hierarchy):
        """Test tracking with a deep hierarchy of tasks."""
        # Helper function to register items recursively
        async def register_hierarchy(items, parent_id=None):
            for item in items:
                await progress_tracker.register_item(
                    item_id=item["id"],
                    item_type=item["type"],
                    name=item["name"],
                    description=f"Description for {item['name']}",
                    parent_id=parent_id
                )
                
                if "children" in item:
                    await register_hierarchy(item["children"], item["id"])
        
        # Register the hierarchy
        await register_hierarchy(complex_task_hierarchy)
        
        # Update progress for leaf nodes
        await progress_tracker.update_progress(
            item_id="task1",
            state=ProgressState.COMPLETED,
            completion_percentage=100.0
        )
        
        await progress_tracker.update_progress(
            item_id="task2",
            state=ProgressState.COMPLETED,
            completion_percentage=100.0
        )
        
        await progress_tracker.update_progress(
            item_id="subtask1",
            state=ProgressState.COMPLETED,
            completion_percentage=100.0
        )
        
        await progress_tracker.update_progress(
            item_id="subtask2",
            state=ProgressState.IN_PROGRESS,
            completion_percentage=50.0
        )
        
        await progress_tracker.update_progress(
            item_id="task4",
            state=ProgressState.NOT_STARTED,
            completion_percentage=0.0
        )
        
        # Check intermediate node progress
        task3 = progress_tracker.tracked_items["task3"]
        assert task3["completion_percentage"] == 75.0  # Average of subtask1 (100%) and subtask2 (50%)
        
        # Check phase progress
        phase1 = progress_tracker.tracked_items["phase1"]
        assert phase1["completion_percentage"] == 100.0  # Both tasks completed
        assert phase1["state"] == ProgressState.COMPLETED
        
        phase2 = progress_tracker.tracked_items["phase2"]
        assert phase2["completion_percentage"] == 37.5  # (75% + 0%) / 2
        assert phase2["state"] == ProgressState.IN_PROGRESS
        
        # Check project progress
        project = progress_tracker.tracked_items["project"]
        # (100% + 37.5% + 0%) / 3 = 45.83%
        assert abs(project["completion_percentage"] - 45.83) < 0.1
        assert project["state"] == ProgressState.IN_PROGRESS
        
        # Complete the milestone
        await progress_tracker.update_progress(
            item_id="milestone1",
            state=ProgressState.COMPLETED,
            completion_percentage=100.0
        )
        
        # Project progress should now include the milestone
        project = progress_tracker.tracked_items["project"]
        # (100% + 37.5% + 100%) / 3 = 79.16%
        assert abs(project["completion_percentage"] - 79.16) < 0.1
    
    @pytest.mark.asyncio
    async def test_stalled_progress_detection(self, progress_tracker):
        """Test detection of stalled progress."""
        # Register a task
        await progress_tracker.register_item(
            item_id="stalled_task",
            item_type="task",
            name="Stalled Task",
            description="A task that will stall"
        )
        
        # Start the task
        await progress_tracker.update_progress(
            item_id="stalled_task",
            state=ProgressState.IN_PROGRESS,
            completion_percentage=20.0
        )
        
        # Mock the last update time to be old enough to trigger stalled detection
        stalled_time = datetime.now() - timedelta(minutes=1)
        progress_tracker.tracked_items["stalled_task"]["latest_update"] = stalled_time.isoformat()
        
        # Manually trigger stalled check
        await progress_tracker._check_stalled_progress("stalled_task")
        
        # Check if notification was created
        notifications = await progress_tracker.get_notifications()
        assert len(notifications) > 0
        
        # Find stalled notification by notification type
        stalled_notification = next(
            (n for n in notifications if n["type"] == "stalled_progress"), None
        )
        assert stalled_notification is not None
        assert stalled_notification["item_id"] == "stalled_task"
        assert "has stalled for" in stalled_notification["message"].lower()
        # Verify notification has the expected format
        expected_minutes = progress_tracker.config["notification_thresholds"]["stalled_minutes"]
        assert f"has stalled for {expected_minutes} minutes" in stalled_notification["message"].lower()
    
    @pytest.mark.asyncio
    async def test_snapshot_history(self, progress_tracker):
        """Test the history of progress snapshots."""
        # Register a task
        await progress_tracker.register_item(
            item_id="history_task",
            item_type="task",
            name="History Task",
            description="A task with history"
        )
        
        # Start the task
        await progress_tracker.update_progress(
            item_id="history_task",
            state=ProgressState.IN_PROGRESS,
            completion_percentage=25.0,
            message="Started work"
        )
        
        # Take a short break to ensure snapshots have different timestamps
        await asyncio.sleep(0.05)
        
        # Update again
        await progress_tracker.update_progress(
            item_id="history_task",
            state=ProgressState.IN_PROGRESS,
            completion_percentage=50.0,
            message="Half complete"
        )
        
        # Take another short break
        await asyncio.sleep(0.05)
        
        # Update again
        await progress_tracker.update_progress(
            item_id="history_task",
            state=ProgressState.IN_PROGRESS,
            completion_percentage=75.0,
            message="Almost done"
        )
        
        # Take another short break
        await asyncio.sleep(0.05)
        
        # Complete the task
        await progress_tracker.update_progress(
            item_id="history_task",
            state=ProgressState.COMPLETED,
            completion_percentage=100.0,
            message="Finished"
        )
        
        # Get task with snapshots
        task_report = await progress_tracker.get_progress_report(
            item_id="history_task",
            include_snapshots=True
        )
        
        # Check snapshots
        assert len(task_report["snapshots"]) >= 5  # Initial + 4 updates
        
        # Check progress over time
        completion_values = [s["completion_percentage"] for s in task_report["snapshots"]]
        assert completion_values[0] == 0.0  # Initial state
        assert completion_values[-1] == 100.0  # Final state
        
        # Check messages
        assert any(s["message"] == "Started work" for s in task_report["snapshots"])
        assert any(s["message"] == "Half complete" for s in task_report["snapshots"])
        assert any(s["message"] == "Almost done" for s in task_report["snapshots"])
        assert any(s["message"] == "Finished" for s in task_report["snapshots"])
        
        # Check timestamps are in order
        timestamps = [s["timestamp"] for s in task_report["snapshots"]]
        for i in range(1, len(timestamps)):
            assert timestamps[i] >= timestamps[i-1]
    
    @pytest.mark.asyncio
    async def test_failure_and_retry(self, progress_tracker):
        """Test handling task failure and retry."""
        # Register a task
        await progress_tracker.register_item(
            item_id="failing_task",
            item_type="task",
            name="Failing Task",
            description="A task that fails and is retried"
        )
        
        # Start the task
        await progress_tracker.update_progress(
            item_id="failing_task",
            state=ProgressState.IN_PROGRESS,
            completion_percentage=30.0
        )
        
        # Task fails
        await progress_tracker.update_progress(
            item_id="failing_task",
            state=ProgressState.FAILED,
            completion_percentage=30.0,
            message="Task failed due to network error"
        )
        
        # Check failed state
        task = progress_tracker.tracked_items["failing_task"]
        assert task["state"] == ProgressState.FAILED
        assert task["completion_percentage"] == 30.0
        
        # Get notifications
        notifications = await progress_tracker.get_notifications()
        assert len(notifications) > 0
        
        failure_notification = next(
            (n for n in notifications if "failed" in n["message"].lower()), None
        )
        assert failure_notification is not None
        
        # Retry the task
        await progress_tracker.update_progress(
            item_id="failing_task",
            state=ProgressState.IN_PROGRESS,
            completion_percentage=30.0,
            message="Retrying task"
        )
        
        # Complete the task
        await progress_tracker.update_progress(
            item_id="failing_task",
            state=ProgressState.COMPLETED,
            completion_percentage=100.0,
            message="Task completed successfully on retry"
        )
        
        # Check completion
        task = progress_tracker.tracked_items["failing_task"]
        assert task["state"] == ProgressState.COMPLETED
        assert task["completion_percentage"] == 100.0
        
        # Get task history with snapshots
        task_report = await progress_tracker.get_progress_report(
            item_id="failing_task",
            include_snapshots=True
        )
        
        # Verify failure and recovery in history
        states = [s["state"] for s in task_report["snapshots"]]
        assert ProgressState.FAILED in states
        assert states[-1] == ProgressState.COMPLETED
    
    @pytest.mark.asyncio
    async def test_complex_metrics_tracking(self, progress_tracker):
        """Test tracking complex metrics with a task."""
        # Define complex metrics
        metrics = {
            "accuracy": ProgressMetric(
                name="Model Accuracy",
                description="Current model accuracy",
                current_value=0.0,
                target_value=0.95,
                unit="accuracy"
            ),
            "data_processed": ProgressMetric(
                name="Data Processed",
                description="Amount of data processed",
                current_value=0,
                target_value=1000,
                unit="MB"
            ),
            "errors": ProgressMetric(
                name="Error Count",
                description="Number of errors encountered",
                current_value=0,
                target_value=0,  # Lower is better
                unit="errors"
            )
        }
        
        # Register a task with metrics
        await progress_tracker.register_item(
            item_id="metrics_task",
            item_type="task",
            name="Metrics Task",
            description="A task with complex metrics",
            metrics=metrics
        )
        
        # Update with initial progress
        await progress_tracker.update_progress(
            item_id="metrics_task",
            state=ProgressState.IN_PROGRESS,
            completion_percentage=0,
            metrics_updates={
                "accuracy": 0.1,
                "data_processed": 100,
                "errors": 5
            }
        )
        
        # Check metrics
        task = progress_tracker.tracked_items["metrics_task"]
        assert task["metrics"]["accuracy"].current_value == 0.1
        assert task["metrics"]["data_processed"].current_value == 100
        assert task["metrics"]["errors"].current_value == 5
        
        # Calculate percentages
        assert task["metrics"]["accuracy"].percentage == (0.1 / 0.95) * 100
        assert task["metrics"]["data_processed"].percentage == 10.0  # (100 / 1000) * 100
        
        # Update with more progress
        await progress_tracker.update_progress(
            item_id="metrics_task",
            metrics_updates={
                "accuracy": 0.5,
                "data_processed": 500,
                "errors": 2  # Errors decreased
            }
        )
        
        # Check updated metrics
        task = progress_tracker.tracked_items["metrics_task"]
        assert task["metrics"]["accuracy"].current_value == 0.5
        assert task["metrics"]["data_processed"].current_value == 500
        assert task["metrics"]["errors"].current_value == 2
        
        # Complete with final metrics
        await progress_tracker.update_progress(
            item_id="metrics_task",
            state=ProgressState.COMPLETED,
            completion_percentage=100,
            metrics_updates={
                "accuracy": 0.97,  # Exceeded target
                "data_processed": 1000,
                "errors": 0
            }
        )
        
        # Check final metrics
        task = progress_tracker.tracked_items["metrics_task"]
        assert task["metrics"]["accuracy"].current_value == 0.97
        assert task["metrics"]["accuracy"].percentage == 100.0  # Capped at 100%
        assert task["metrics"]["data_processed"].current_value == 1000
        assert task["metrics"]["data_processed"].percentage == 100.0
        assert task["metrics"]["errors"].current_value == 0
    
    @pytest.mark.asyncio
    async def test_wait_state_handling(self, progress_tracker):
        """Test handling of the WAITING state for tasks."""
        # Register a task
        await progress_tracker.register_item(
            item_id="waiting_task",
            item_type="task",
            name="Waiting Task",
            description="A task that enters a waiting state"
        )
        
        # Start the task
        await progress_tracker.update_progress(
            item_id="waiting_task",
            state=ProgressState.IN_PROGRESS,
            completion_percentage=40.0
        )
        
        # Task enters waiting state
        await progress_tracker.update_progress(
            item_id="waiting_task",
            state=ProgressState.WAITING,
            completion_percentage=40.0,
            message="Waiting for external service"
        )
        
        # Check waiting state
        task = progress_tracker.tracked_items["waiting_task"]
        assert task["state"] == ProgressState.WAITING
        assert task["completion_percentage"] == 40.0
        
        # Register a dependent task
        await progress_tracker.register_item(
            item_id="dependent_task",
            item_type="task",
            name="Dependent Task",
            description="A task that depends on the waiting task",
            parent_id="waiting_task"
        )
        
        # Start and complete dependent task
        await progress_tracker.update_progress(
            item_id="dependent_task",
            state=ProgressState.IN_PROGRESS,
            completion_percentage=50.0
        )
        
        await progress_tracker.update_progress(
            item_id="dependent_task",
            state=ProgressState.COMPLETED,
            completion_percentage=100.0
        )
        
        # Continue with the waiting task
        await progress_tracker.update_progress(
            item_id="waiting_task",
            state=ProgressState.IN_PROGRESS,
            completion_percentage=60.0,
            message="External service responded, continuing"
        )
        
        # Complete the task
        await progress_tracker.update_progress(
            item_id="waiting_task",
            state=ProgressState.COMPLETED,
            completion_percentage=100.0
        )
        
        # Verify history shows waiting state
        task_report = await progress_tracker.get_progress_report(
            item_id="waiting_task",
            include_snapshots=True,
            include_children=True
        )
        
        # Check state transitions
        states = [s["state"] for s in task_report["snapshots"]]
        assert ProgressState.WAITING in states
        assert states[-1] == ProgressState.COMPLETED
        
        # Check children were included
        assert "children" in task_report
        assert len(task_report["children"]) == 1
        assert task_report["children"][0]["id"] == "dependent_task"
    
    @pytest.mark.asyncio
    async def test_milestone_visualization(self, progress_tracker):
        """Test milestone status visualization."""
        # Register a project with milestones
        await progress_tracker.register_item(
            item_id="milestone_project",
            item_type="project",
            name="Milestone Project",
            description="A project with milestones"
        )
        
        # Register milestones
        milestones = [
            {"id": "m1", "name": "Requirements Complete", "expected_date": "2023-01-15"},
            {"id": "m2", "name": "Design Complete", "expected_date": "2023-02-01"},
            {"id": "m3", "name": "Alpha Release", "expected_date": "2023-03-15"},
            {"id": "m4", "name": "Beta Release", "expected_date": "2023-04-01"},
            {"id": "m5", "name": "Final Release", "expected_date": "2023-05-15"}
        ]
        
        for m in milestones:
            await progress_tracker.register_item(
                item_id=m["id"],
                item_type="milestone",
                name=m["name"],
                description=f"Milestone: {m['name']}",
                parent_id="milestone_project",
                expected_duration=None,
                metrics=None
            )
            
            # Store expected date in the data field
            progress_tracker.tracked_items[m["id"]]["data"] = {
                "expected_date": m["expected_date"]
            }
        
        # Complete some milestones
        await progress_tracker.update_progress(
            item_id="m1",
            state=ProgressState.COMPLETED,
            completion_percentage=100.0
        )
        
        await progress_tracker.update_progress(
            item_id="m2",
            state=ProgressState.COMPLETED,
            completion_percentage=100.0
        )
        
        await progress_tracker.update_progress(
            item_id="m3",
            state=ProgressState.IN_PROGRESS,
            completion_percentage=75.0
        )
        
        # Create milestone visualization
        with patch('src.server.observability.progress_tracker.ProgressTracker._generate_milestone_image', 
                  return_value="data:image/png;base64,test_milestone_data"):
            vis = await progress_tracker.create_visualization(
                item_id="milestone_project",
                visualization_type="milestone_status"
            )
            
            assert vis["type"] == "milestone_status"
            assert "image" in vis
            assert vis["image"].startswith("data:image/png;base64,")
            
            # Check visualization data
            assert "milestones" in vis["data"]
            assert len(vis["data"]["milestones"]) == 5
            assert vis["data"]["milestones"][0]["state"] == ProgressState.COMPLETED.value
            assert vis["data"]["milestones"][1]["state"] == ProgressState.COMPLETED.value
            assert vis["data"]["milestones"][2]["state"] == ProgressState.IN_PROGRESS.value
            assert vis["data"]["milestones"][3]["state"] == ProgressState.NOT_STARTED.value
    
    @pytest.mark.asyncio
    async def test_dependency_visualization(self, progress_tracker):
        """Test dependency network visualization."""
        # Create a network of tasks with dependencies
        tasks = [
            {"id": "t1", "name": "Task 1", "depends_on": []},
            {"id": "t2", "name": "Task 2", "depends_on": ["t1"]},
            {"id": "t3", "name": "Task 3", "depends_on": ["t1"]},
            {"id": "t4", "name": "Task 4", "depends_on": ["t2", "t3"]},
            {"id": "t5", "name": "Task 5", "depends_on": ["t3"]},
            {"id": "t6", "name": "Task 6", "depends_on": ["t4", "t5"]}
        ]
        
        # Register tasks
        for task in tasks:
            await progress_tracker.register_item(
                item_id=task["id"],
                item_type="task",
                name=task["name"],
                description=f"Description for {task['name']}"
            )
            
            # Store dependencies in the data field
            progress_tracker.tracked_items[task["id"]]["data"] = {
                "dependencies": task["depends_on"]
            }
        
        # Set progress on some tasks
        await progress_tracker.update_progress(
            item_id="t1",
            state=ProgressState.COMPLETED,
            completion_percentage=100.0
        )
        
        await progress_tracker.update_progress(
            item_id="t2",
            state=ProgressState.IN_PROGRESS,
            completion_percentage=50.0
        )
        
        await progress_tracker.update_progress(
            item_id="t3",
            state=ProgressState.COMPLETED,
            completion_percentage=100.0
        )
        
        # Create dependency visualization
        with patch('src.server.observability.progress_tracker.ProgressTracker._generate_network_image', 
                  return_value="data:image/png;base64,test_network_data"):
            vis = await progress_tracker.create_visualization(
                visualization_type="dependency_network",
                options={"include_all_tasks": True}
            )
            
            assert vis["type"] == "dependency_network"
            assert "image" in vis
            assert vis["image"].startswith("data:image/png;base64,")
            
            # Check network data
            assert "nodes" in vis["data"]
            assert "edges" in vis["data"]
            assert len(vis["data"]["nodes"]) == 6
            
            # Check that dependencies were converted to edges
            edge_count = 0
            for task in tasks:
                edge_count += len(task["depends_on"])
            
            assert len(vis["data"]["edges"]) == edge_count
            
            # Check state representation
            nodes = {node["id"]: node for node in vis["data"]["nodes"]}
            assert nodes["t1"]["state"] == ProgressState.COMPLETED.value
            assert nodes["t2"]["state"] == ProgressState.IN_PROGRESS.value
            assert nodes["t3"]["state"] == ProgressState.COMPLETED.value
            assert nodes["t4"]["state"] == ProgressState.NOT_STARTED.value 