"""
Progress Tracker component for the Self-Aware System.

This module provides functionality for tracking progress of various system tasks,
projects, and milestones, with support for hierarchical tracking, metrics,
visualizations, and notifications.
"""

import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Union, Set
import base64
from io import BytesIO

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import networkx as nx

logger = logging.getLogger(__name__)


class TrackingLevel(str, Enum):
    """Level of detail for tracking progress."""
    BASIC = "basic"
    STANDARD = "standard"
    DETAILED = "detailed"


class ItemType(str, Enum):
    """Types of items that can be tracked."""
    TASK = "task"
    PROJECT = "project"
    MILESTONE = "milestone"
    FEATURE = "feature"
    BUG = "bug"
    ISSUE = "issue"


class ProgressState(str, Enum):
    """Possible states for a tracked item."""
    NOT_STARTED = "not_started"
    WAITING = "waiting"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


# Alias for backward compatibility with tests
ItemState = ProgressState


class ProgressMetric:
    """A metric for tracking progress."""
    
    def __init__(self, name: str, description: str = "", current_value: Any = 0,
                 target_value: Any = 100, unit: str = "", timestamp: Optional[str] = None):
        """Initialize a progress metric."""
        self.name = name
        self.description = description
        self.current_value = current_value
        self.target_value = target_value
        self.unit = unit
        self.timestamp = timestamp or datetime.now().isoformat()
    
    @property
    def percentage(self) -> float:
        """Calculate the percentage of completion based on current and target values."""
        if self.target_value == 0:
            return 100.0 if self.current_value == 0 else 0.0
        
        try:
            # Try to calculate percentage based on numerical values
            percentage = (float(self.current_value) / float(self.target_value)) * 100.0
            return min(100.0, percentage)  # Cap at 100%
        except (TypeError, ValueError):
            # If values are not numeric, return 0
            return 0.0


class ProgressSnapshot:
    """A snapshot of progress at a point in time."""
    
    def __init__(self, timestamp: str, state: ProgressState,
                completion_percentage: float, metrics: Dict[str, ProgressMetric] = None,
                message: Optional[str] = None):
        """Initialize a progress snapshot."""
        self.timestamp = timestamp
        self.state = state
        self.completion_percentage = completion_percentage
        self.metrics = metrics or {}
        self.message = message


class ProgressTracker:
    """
    Tracks progress of system tasks, projects, and milestones.
    
    Features:
    - Hierarchical tracking (projects, tasks, subtasks)
    - Progress state management
    - Metric tracking
    - Notification generation
    - Snapshot history
    - Progress visualization
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Progress Tracker.
        
        Args:
            config: Configuration for the tracker
                - tracking_level: Level of detail for tracking
                - snapshot_interval: Interval in seconds for automatic snapshots
                - storage_path: Path to store persistent data
                - visualization_enabled: Whether to enable visualization generation
                - notification_thresholds: Thresholds for generating notifications
        """
        self.config = config or {
            "tracking_level": "standard",  # basic, standard, detailed
            "snapshot_interval": 60,  # seconds
            "storage_path": "persistent_state/progress",
            "visualization_enabled": True,
            "notification_thresholds": {
                "stalled_minutes": 15,
                "completion_percentage": 75.0,
                "failure_count": 3
            }
        }
        
        # Create storage directory if it doesn't exist
        if "storage_path" in self.config:
            os.makedirs(self.config["storage_path"], exist_ok=True)
        
        # Initialize data structures
        self.tracked_items: Dict[str, Dict[str, Any]] = {}
        self.notifications: List[Dict[str, Any]] = []
        self.snapshot_tasks: Dict[str, asyncio.Task] = {}
    
    async def initialize(self):
        """Initialize the Progress Tracker."""
        logger.info("Initializing Progress Tracker")
        
        # Load any existing data
        if "storage_path" in self.config:
            data_file = os.path.join(self.config["storage_path"], "tracking_data.json")
            if os.path.exists(data_file):
                await self.load_tracking_data(data_file)
    
    async def cleanup(self):
        """Cancel all active snapshot tasks and cleanup resources."""
        for task_id, task in list(self.snapshot_tasks.items()):
            if not task.done() and not task.cancelled():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logger.info(f"Snapshot task for item {task_id} cancelled")
                except Exception as e:
                    logger.error(f"Error cleaning up snapshot task for item {task_id}: {e}")
            
            # Remove task from dictionary
            self.snapshot_tasks.pop(task_id, None)
        
        logger.info("Progress Tracker cleanup completed")
    
    async def register_item(self, item_id: str, item_type: str, name: str,
                           description: str, parent_id: Optional[str] = None,
                           expected_duration: Optional[float] = None,
                           depends_on: Optional[List[str]] = None,
                           metrics: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Register an item for tracking."""
        logger.info(f"Registering item: {item_id} ({item_type})")
        
        if item_id in self.tracked_items:
            raise ValueError(f"Item {item_id} already registered")
        
        # Validate parent_id if provided
        if parent_id and parent_id not in self.tracked_items:
            raise ValueError(f"Parent item {parent_id} not registered")
        
        # Convert metrics to ProgressMetric objects if they are not already
        processed_metrics = {}
        if metrics:
            for metric_name, metric_value in metrics.items():
                if isinstance(metric_value, ProgressMetric):
                    processed_metrics[metric_name] = metric_value
                else:
                    # If it's a simple value or dict, convert to ProgressMetric
                    if isinstance(metric_value, dict):
                        processed_metrics[metric_name] = ProgressMetric(
                            name=metric_value.get('name', metric_name),
                            description=metric_value.get('description', ''),
                            current_value=metric_value.get('current_value', 0),
                            target_value=metric_value.get('target_value', 100),
                            unit=metric_value.get('unit', '')
                        )
                    else:
                        # Simple value
                        processed_metrics[metric_name] = ProgressMetric(
                            name=metric_name,
                            description='',
                            current_value=metric_value,
                            target_value=100,
                            unit=''
                        )
        
        # Create item
        item = {
            "id": item_id,
            "type": item_type,
            "name": name,
            "description": description,
            "parent_id": parent_id,
            "expected_duration": expected_duration,
            "depends_on": depends_on or [],
            "state": ProgressState.NOT_STARTED,
            "completion_percentage": 0.0,
            "metrics": processed_metrics,
            "registration_time": datetime.now().isoformat(),
            "start_time": None,
            "end_time": None,
            "latest_update": datetime.now().isoformat(),
            "snapshots": [],
            "children": []
        }
        
        # Store item
        self.tracked_items[item_id] = item
        
        # Update parent item
        if parent_id:
            parent_item = self.tracked_items[parent_id]
            parent_item["children"].append(item_id)
        
        # Start snapshot task if configured
        if self.config.get("snapshot_interval", 0) > 0:
            await self._start_snapshot_task(item_id)
        
        return item
    
    async def update_progress(self, item_id: str, state: Optional[Union[ProgressState, str]] = None,
                            completion_percentage: Optional[float] = None,
                            message: Optional[str] = None,
                            metrics_updates: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Update progress for a tracked item."""
        logger.info(f"Updating progress for item: {item_id}")
        
        if item_id not in self.tracked_items:
            raise ValueError(f"Item {item_id} not registered for tracking")
        
        item = self.tracked_items[item_id]
        now = datetime.now().isoformat()
        
        # Update state if provided
        if state:
            old_state = item["state"]
            # Convert string to enum if needed
            if isinstance(state, str):
                try:
                    state = ProgressState(state)
                except ValueError:
                    logger.warning(f"Invalid state value: {state}, using NOT_STARTED")
                    state = ProgressState.NOT_STARTED
            
            item["state"] = state
            
            # Handle state transitions
            if state == ProgressState.IN_PROGRESS and not item["start_time"]:
                item["start_time"] = now
            elif state in [ProgressState.COMPLETED, ProgressState.FAILED, ProgressState.CANCELED]:
                item["end_time"] = now
            
            # Check for notifications on state change
            if old_state != state:
                await self._check_state_notification(item_id, old_state, state)
        
        # Update completion percentage if provided
        if completion_percentage is not None:
            old_percentage = item["completion_percentage"]
            item["completion_percentage"] = min(100.0, max(0.0, completion_percentage))
            
            # Check for notifications on significant progress
            if (item["completion_percentage"] >= self.config["notification_thresholds"]["completion_percentage"] and
                old_percentage < self.config["notification_thresholds"]["completion_percentage"]):
                await self._create_notification(
                    item_id=item_id,
                    notification_type="completion_threshold",
                    message=f"Item {item['name']} is {item['completion_percentage']}% complete"
                )
        
        # Update metrics if provided
        if metrics_updates:
            for metric_name, metric_value in metrics_updates.items():
                if metric_name in item["metrics"]:
                    item["metrics"][metric_name].current_value = metric_value
                    item["metrics"][metric_name].timestamp = now
                else:
                    # Create a new ProgressMetric for metrics that don't exist yet
                    logger.warning(f"Metric {metric_name} not registered for item {item_id}")
                    item["metrics"][metric_name] = ProgressMetric(
                        name=metric_name,
                        description=f"Dynamically added metric {metric_name}",
                        current_value=metric_value,
                        target_value=100 if isinstance(metric_value, (int, float)) else metric_value,
                        unit="",
                        timestamp=now
                    )
        
        # Update timestamp
        item["latest_update"] = now
        
        # Create a new snapshot
        await self._create_snapshot(item_id, message)
        
        # Propagate updates to parent items
        if item["parent_id"]:
            await self._update_parent_progress(item["parent_id"])
        
        # Update dependent items if this is a completion state
        if state in [ProgressState.COMPLETED, ProgressState.FAILED, ProgressState.CANCELED]:
            await self._update_dependent_items(item_id, state)
        
        return item
    
    async def get_progress_report(self, item_id: Optional[str] = None, 
                                 include_children: bool = False,
                                 include_snapshots: bool = False) -> Dict[str, Any]:
        """
        Get a progress report for a specific item or the entire system.
        
        Args:
            item_id: ID of the item to get report for, or None for system-wide report
            include_children: Whether to include children items in the report
            include_snapshots: Whether to include snapshots history in the report
            
        Returns:
            Progress report dictionary
        """
        if item_id:
            if item_id not in self.tracked_items:
                raise ValueError(f"Item {item_id} not found in tracked items")
            
            # Get basic item report
            item = self.tracked_items[item_id]
            report = {
                "id": item["id"],
                "type": item["type"],
                "name": item["name"],
                "state": item["state"],
                "completion_percentage": item["completion_percentage"],
                "registration_time": item["registration_time"],
                "start_time": item["start_time"],
                "end_time": item["end_time"],
                "latest_update": item["latest_update"]
            }
            
            # Add metrics if present
            if item["metrics"]:
                report["metrics"] = {
                    name: {
                        "current_value": metric.current_value,
                        "target_value": metric.target_value,
                        "unit": metric.unit
                    } for name, metric in item["metrics"].items()
                }
            
            # Add snapshots if requested
            if include_snapshots and item["snapshots"]:
                # Convert ProgressSnapshot objects to dictionaries
                report["snapshots"] = []
                for snapshot in item["snapshots"]:
                    if isinstance(snapshot, ProgressSnapshot):
                        # Convert metrics to dict
                        metrics_dict = {}
                        for metric_name, metric in snapshot.metrics.items():
                            if isinstance(metric, ProgressMetric):
                                metrics_dict[metric_name] = {
                                    "current_value": metric.current_value, 
                                    "target_value": metric.target_value,
                                    "unit": metric.unit
                                }
                            else:
                                metrics_dict[metric_name] = metric

                        # Add snapshot as dict
                        report["snapshots"].append({
                            "timestamp": snapshot.timestamp,
                            "state": snapshot.state.value if isinstance(snapshot.state, Enum) else snapshot.state,
                            "completion_percentage": snapshot.completion_percentage,
                            "metrics": metrics_dict,
                            "message": snapshot.message
                        })
                    else:
                        # Snapshot is already a dict
                        report["snapshots"].append(snapshot)
            
            # Add children if requested
            if include_children and item["children"]:
                report["children"] = []
                for child_id in item["children"]:
                    child_report = await self.get_progress_report(child_id, include_children, include_snapshots)
                    report["children"].append(child_report)
            
            return report
        else:
            # System-wide report
            total_items = len(self.tracked_items)
            completed_items = sum(1 for item in self.tracked_items.values() 
                                 if item["state"] == ProgressState.COMPLETED)
            in_progress_items = sum(1 for item in self.tracked_items.values() 
                                    if item["state"] == ProgressState.IN_PROGRESS)
            failed_items = sum(1 for item in self.tracked_items.values() 
                              if item["state"] == ProgressState.FAILED)
            
            # Calculate overall completion
            overall_completion = self._calculate_overall_completion()
            
            report = {
                "summary": {
                    "total_items": total_items,
                    "completed_items": completed_items,
                    "in_progress_items": in_progress_items,
                    "failed_items": failed_items,
                    "overall_completion": overall_completion
                }
            }
            
            # Add detailed item reports if requested
            if include_children:
                report["items"] = []
                # Only include root items (no parent)
                for item_id, item in self.tracked_items.items():
                    if not item["parent_id"]:
                        item_report = await self.get_progress_report(item_id, include_children, include_snapshots)
                        report["items"].append(item_report)
            
            return report
    
    async def _update_parent_progress(self, parent_id: str):
        """Update progress of a parent item based on its children."""
        if parent_id not in self.tracked_items:
            logger.warning(f"Parent item {parent_id} not found in tracked items")
            return
        
        parent = self.tracked_items[parent_id]
        children = [self.tracked_items[child_id] for child_id in parent["children"]]
        
        if not children:
            logger.warning(f"Parent item {parent_id} has no children")
            return
        
        # Calculate average completion
        total_completion = sum(child["completion_percentage"] for child in children)
        avg_completion = total_completion / len(children)
        
        # Update parent completion
        parent["completion_percentage"] = avg_completion
        
        # Update parent state based on children states
        all_completed = all(child["state"] == ProgressState.COMPLETED for child in children)
        all_failed = all(child["state"] == ProgressState.FAILED for child in children)
        any_in_progress = any(child["state"] == ProgressState.IN_PROGRESS for child in children)
        any_failed = any(child["state"] == ProgressState.FAILED for child in children)
        
        if all_completed:
            parent["state"] = ProgressState.COMPLETED
            parent["end_time"] = datetime.now().isoformat()
        elif all_failed:
            parent["state"] = ProgressState.FAILED
            parent["end_time"] = datetime.now().isoformat()
        elif any_in_progress:
            parent["state"] = ProgressState.IN_PROGRESS
            if not parent["start_time"]:
                parent["start_time"] = datetime.now().isoformat()
        elif any_failed:
            # Some failed, some not
            parent["state"] = ProgressState.IN_PROGRESS
        
        # Update timestamp
        parent["latest_update"] = datetime.now().isoformat()
        
        # Create a snapshot
        await self._create_snapshot(parent_id)
        
        # Propagate update to parent's parent (if any)
        if parent["parent_id"]:
            await self._update_parent_progress(parent["parent_id"])
    
    async def _update_dependent_items(self, item_id: str, state: ProgressState):
        """Update items that depend on this item."""
        item = self.tracked_items[item_id]
        
        # Find all items that depend on this one
        for dep_id, dep_item in self.tracked_items.items():
            if item_id in dep_item.get("depends_on", []):
                # Check if this item is a milestone
                if dep_item["type"] == "milestone":
                    # For milestones, check if all dependencies are complete
                    all_deps_completed = True
                    for dep in dep_item["depends_on"]:
                        if dep not in self.tracked_items:
                            all_deps_completed = False
                            break
                        
                        dep_state = self.tracked_items[dep]["state"]
                        if dep_state != ProgressState.COMPLETED:
                            all_deps_completed = False
                            break
                    
                    # Update milestone state if all dependencies are complete
                    if all_deps_completed:
                        await self.update_progress(
                            item_id=dep_id,
                            state=ProgressState.COMPLETED,
                            completion_percentage=100.0,
                            message="All dependencies completed"
                        )
                else:
                    # For regular items, update to WAITING state if not already started
                    if dep_item["state"] == ProgressState.NOT_STARTED:
                        # Check if all dependencies are complete
                        all_deps_completed = True
                        for dep in dep_item["depends_on"]:
                            if dep not in self.tracked_items:
                                all_deps_completed = False
                                break
                            
                            dep_state = self.tracked_items[dep]["state"]
                            if dep_state != ProgressState.COMPLETED:
                                all_deps_completed = False
                                break
                        
                        # If all dependencies are complete, update to WAITING
                        if all_deps_completed:
                            await self.update_progress(
                                item_id=dep_id,
                                state=ProgressState.WAITING,
                                message="Ready to start (all dependencies completed)"
                            )
    
    async def _create_snapshot(self, item_id: str, message: Optional[str] = None):
        """Create a snapshot for a tracked item."""
        logger.info(f"Creating snapshot for item: {item_id}")
        
        if item_id not in self.tracked_items:
            raise ValueError(f"Item {item_id} not registered for tracking")
        
        item = self.tracked_items[item_id]
        now = datetime.now().isoformat()
        
        # Collect metrics
        metrics = {metric_name: metric for metric_name, metric in item["metrics"].items()}
        
        # Create snapshot
        snapshot = ProgressSnapshot(
            timestamp=now,
            state=item["state"],
            completion_percentage=item["completion_percentage"],
            metrics=metrics,
            message=message
        )
        
        # Store snapshot
        item["snapshots"].append(snapshot)
        
        # Check for notifications on significant progress
        if item["completion_percentage"] >= self.config["notification_thresholds"]["completion_percentage"]:
            await self._create_notification(
                item_id=item_id,
                notification_type="completion_threshold",
                message=f"Item {item['name']} is {item['completion_percentage']}% complete"
            )
        
        # Check for notifications on stalled progress
        if (item["state"] == ProgressState.IN_PROGRESS and 
            item["start_time"] and 
            (datetime.now() - datetime.fromisoformat(item["start_time"])) > 
                timedelta(minutes=self.config["notification_thresholds"]["stalled_minutes"])):
            await self._create_notification(
                item_id=item_id,
                notification_type="stalled_progress",
                message=f"Item {item['name']} has been stalled for {self.config['notification_thresholds']['stalled_minutes']} minutes"
            )
        
        # Check for notifications on failure
        if item["state"] == ProgressState.FAILED:
            await self._create_notification(
                item_id=item_id,
                notification_type="failure",
                message=f"Item {item['name']} has failed"
            )
        
        # Check for notifications on completion
        if item["state"] == ProgressState.COMPLETED:
            await self._create_notification(
                item_id=item_id,
                notification_type="completion",
                message=f"Item {item['name']} has completed"
            )
        
        # Check for notifications on cancellation
        if item["state"] == ProgressState.CANCELED:
            await self._create_notification(
                item_id=item_id,
                notification_type="cancellation",
                message=f"Item {item['name']} has been canceled"
            )
    
    async def _start_snapshot_task(self, item_id: str):
        """Start a background task to create snapshots for a tracked item."""
        logger.info(f"Starting snapshot task for item: {item_id}")
        
        if item_id not in self.tracked_items:
            raise ValueError(f"Item {item_id} not registered for tracking")
        
        # Create snapshot
        await self._create_snapshot(item_id)
        
        # Schedule next snapshot
        if self.config.get("snapshot_interval") > 0:
            self.snapshot_tasks[item_id] = asyncio.create_task(self._schedule_snapshot_task(item_id))
    
    async def _schedule_snapshot_task(self, item_id: str):
        """Schedule a snapshot task for a tracked item."""
        logger.info(f"Scheduling snapshot task for item: {item_id}")
        
        if item_id not in self.tracked_items:
            raise ValueError(f"Item {item_id} not registered for tracking")
        
        # Wait for the next interval
        await asyncio.sleep(self.config["snapshot_interval"])
        
        # Create snapshot
        if item_id in self.tracked_items:  # Check again after sleep
            await self._create_snapshot(item_id)
            
            # Schedule next snapshot if item is still active
            if (item_id in self.tracked_items and 
                self.tracked_items[item_id]["state"] not in 
                [ProgressState.COMPLETED, ProgressState.FAILED, ProgressState.CANCELED]):
                self.snapshot_tasks[item_id] = asyncio.create_task(self._schedule_snapshot_task(item_id))
    
    async def _check_state_notification(self, item_id: str, old_state: ProgressState, new_state: ProgressState):
        """Check for notifications on state change."""
        logger.info(f"Checking state notification for item: {item_id}")
        
        if item_id not in self.tracked_items:
            raise ValueError(f"Item {item_id} not registered for tracking")
        
        item = self.tracked_items[item_id]
        
        # Check for notifications on state change
        if old_state != new_state:
            await self._create_notification(
                item_id=item_id,
                notification_type="state_change",
                message=f"Item {item['name']} state changed from {old_state} to {new_state}"
            )
    
    async def _create_notification(self, item_id: str, notification_type: str, message: str):
        """Create a notification for a tracked item."""
        logger.info(f"Creating notification for item: {item_id}")
        
        if item_id not in self.tracked_items:
            raise ValueError(f"Item {item_id} not registered for tracking")
        
        item = self.tracked_items[item_id]
        
        # Create notification
        notification = {
            "id": f"notif_{len(self.notifications) + 1}",
            "type": notification_type,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "item_id": item_id,
            "acknowledged": False,
            "completion_percentage": item["completion_percentage"],
            "metrics": {}
        }
        
        # Add metrics to notification
        if item["metrics"]:
            for metric_name, metric in item["metrics"].items():
                notification["metrics"][metric_name] = metric.current_value
        
        # Store notification
        self.notifications.append(notification)
        
        # Log notification
        logger.info(f"Notification: {message}")
        
        return notification

    def _calculate_overall_completion(self) -> float:
        """Calculate overall system completion percentage."""
        if not self.tracked_items:
            return 0.0
        
        # Get root items (no parent)
        root_items = [
            item for item in self.tracked_items.values()
            if not item["parent_id"]
        ]
        
        if not root_items:
            # No root items, calculate average of all items
            return sum(item["completion_percentage"] for item in self.tracked_items.values()) / len(self.tracked_items)
        
        # Calculate average of root items
        return sum(item["completion_percentage"] for item in root_items) / len(root_items)

    async def create_visualization(
        self, 
        visualization_type: str, 
        item_id: Optional[str] = None, 
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a visualization for an item or the whole system.
        
        Args:
            visualization_type: Type of visualization to create
            item_id: ID of the item to visualize (or None for system-wide)
            options: Additional options for the visualization
            
        Returns:
            Visualization data dictionary with type, base64-encoded image, and any additional data
        """
        if not self.config.get("visualization_enabled", True):
            return {"error": "Visualization is disabled"}
        
        kwargs = options or {}
        
        if visualization_type == "timeline":
            return await self._create_timeline_visualization(item_id, **kwargs)
        elif visualization_type == "metrics":
            return await self._create_metrics_visualization(item_id, **kwargs)
        elif visualization_type == "dependency_network":
            return await self._create_dependencies_visualization(item_id, **kwargs)
        elif visualization_type == "milestone_status":
            return await self._create_milestone_status_visualization(item_id, **kwargs)
        else:
            return {"error": f"Unknown visualization type: {visualization_type}"}
    
    async def _create_timeline_visualization(self, item_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Create a timeline visualization."""
        if item_id and item_id not in self.tracked_items:
            return {"error": f"Item {item_id} not found in tracked items"}
        
        # Determine items to include in visualization
        if item_id:
            item = self.tracked_items[item_id]
            items = [item]
            
            # Include children if requested
            if kwargs.get("include_children", False):
                for child_id in item["children"]:
                    items.append(self.tracked_items[child_id])
        else:
            # Include all root items and their immediate children
            items = []
            for item_id, item in self.tracked_items.items():
                if not item["parent_id"]:  # Root item
                    items.append(item)
                    if kwargs.get("include_children", False):
                        for child_id in item["children"]:
                            items.append(self.tracked_items[child_id])
        
        # Sort items by start time
        items.sort(key=lambda x: x.get("start_time") or "9999-12-31")
        
        # Create a timeline plot
        plt.figure(figsize=(12, 6))
        
        # Y-axis will be item names
        y_labels = [item["name"] for item in items]
        y_pos = range(len(y_labels))
        
        # Define colors for different states
        colors = {
            ProgressState.NOT_STARTED: "lightgray",
            ProgressState.WAITING: "lightyellow",
            ProgressState.IN_PROGRESS: "lightblue",
            ProgressState.PAUSED: "orange",
            ProgressState.COMPLETED: "lightgreen",
            ProgressState.FAILED: "lightcoral",
            ProgressState.CANCELED: "lightpink"
        }
        
        # Plot each item
        for i, item in enumerate(items):
            start_time = datetime.fromisoformat(item["start_time"]) if item["start_time"] else None
            end_time = datetime.fromisoformat(item["end_time"]) if item["end_time"] else datetime.now()
            
            if start_time:
                plt.barh(
                    y_pos[i], 
                    (end_time - start_time).total_seconds() / 3600,  # Convert to hours
                    left=(start_time - datetime.now()).total_seconds() / 3600,  # Offset from now
                    color=colors.get(item["state"], "gray"),
                    height=0.5,
                    alpha=0.7
                )
                
                # Add completion percentage
                plt.text(
                    (start_time - datetime.now()).total_seconds() / 3600 + 0.1,
                    y_pos[i],
                    f"{item['completion_percentage']:.1f}%",
                    verticalalignment="center"
                )
        
        # Format plot
        plt.yticks(y_pos, y_labels)
        plt.xlabel("Time (hours)")
        plt.title("Progress Timeline")
        plt.grid(True, axis="x")
        
        # Add legend
        legend_elements = [
            plt.Rectangle((0, 0), 1, 1, facecolor=color, label=state.value)
            for state, color in colors.items()
            if any(item["state"] == state for item in items)
        ]
        plt.legend(handles=legend_elements, loc="best")
        
        # Convert to base64
        buffer = BytesIO()
        plt.savefig(buffer, format="png")
        plt.close()
        
        image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        return {
            "type": "timeline",
            "image": f"data:image/png;base64,{image_base64}",
            "items": [{"id": item["id"], "name": item["name"], "state": item["state"]} for item in items]
        }
    
    async def _create_metrics_visualization(self, item_id: str, **kwargs) -> Dict[str, Any]:
        """Create a metrics visualization for an item."""
        if item_id not in self.tracked_items:
            return {"error": f"Item {item_id} not found in tracked items"}
        
        item = self.tracked_items[item_id]
        
        if not item["metrics"]:
            return {"error": f"Item {item_id} has no metrics"}
        
        # Create a metrics plot
        num_metrics = len(item["metrics"])
        plt.figure(figsize=(10, 3 * num_metrics))
        
        # Get snapshot history
        if not item["snapshots"]:
            return {"error": f"Item {item_id} has no snapshots"}
        
        # Extract timestamps
        timestamps = [
            datetime.fromisoformat(snapshot.timestamp)
            for snapshot in item["snapshots"]
        ]
        
        # Plot each metric
        for i, (metric_name, metric) in enumerate(item["metrics"].items()):
            plt.subplot(num_metrics, 1, i + 1)
            
            # Extract metric values from snapshots
            values = []
            for snapshot in item["snapshots"]:
                if metric_name in snapshot.metrics:
                    values.append(snapshot.metrics[metric_name].current_value)
                else:
                    # Use last known value or 0
                    values.append(values[-1] if values else 0)
            
            plt.plot(timestamps, values, marker="o", linestyle="-")
            
            # Add target line if target_value exists
            if hasattr(metric, "target_value") and metric.target_value is not None:
                plt.axhline(y=metric.target_value, color="r", linestyle="--", alpha=0.5)
            
            plt.title(f"{metric_name} ({metric.unit})")
            plt.ylabel(metric.name)
            plt.grid(True)
        
        plt.tight_layout()
        
        # Convert to base64
        buffer = BytesIO()
        plt.savefig(buffer, format="png")
        plt.close()
        
        image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        return {
            "type": "metrics",
            "image": f"data:image/png;base64,{image_base64}",
            "metrics": [{"name": name, "current": metric.current_value, "target": metric.target_value} 
                       for name, metric in item["metrics"].items()]
        }
    
    async def _create_dependencies_visualization(self, item_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Create a dependencies network visualization."""
        # Create a directed graph
        G = nx.DiGraph()
        
        # Determine items to include
        if item_id:
            if item_id not in self.tracked_items:
                return {"error": f"Item {item_id} not found in tracked items"}
            
            # Include the item and its dependencies
            items_to_include = set()
            self._add_item_and_dependencies(item_id, items_to_include)
            
            if kwargs.get("include_dependents", False):
                # Also include items that depend on this item
                dependents = self._find_dependents(item_id)
                items_to_include.update(dependents)
        else:
            # Include all items
            items_to_include = set(self.tracked_items.keys())
        
        # Add nodes and edges
        nodes_data = []
        edges_data = []
        
        for item_id in items_to_include:
            item = self.tracked_items[item_id]
            
            # Add node
            G.add_node(
                item_id, 
                name=item["name"],
                type=item["type"],
                state=item["state"],
                completion=item["completion_percentage"]
            )
            
            # Add node data
            nodes_data.append({
                "id": item_id,
                "name": item["name"],
                "type": item["type"],
                "state": item["state"].value if isinstance(item["state"], Enum) else item["state"],
                "completion_percentage": item["completion_percentage"]
            })
            
            # Get dependencies from the data field (as used in the test) or from depends_on
            dependencies = []
            if "data" in item and "dependencies" in item["data"]:
                dependencies = item["data"]["dependencies"]
            elif "depends_on" in item:
                dependencies = item["depends_on"]
            
            # Add edges for dependencies
            for dep_id in dependencies:
                if dep_id in items_to_include:
                    G.add_edge(dep_id, item_id)
                    edges_data.append({
                        "from": dep_id,
                        "to": item_id
                    })
        
        # Create visualization
        plt.figure(figsize=(12, 8))
        
        # Define node colors based on state
        node_colors = {
            ProgressState.NOT_STARTED: "lightgray",
            ProgressState.WAITING: "lightyellow",
            ProgressState.IN_PROGRESS: "lightblue",
            ProgressState.PAUSED: "orange",
            ProgressState.COMPLETED: "lightgreen",
            ProgressState.FAILED: "lightcoral",
            ProgressState.CANCELED: "lightpink"
        }
        
        # Get colors for each node
        colors = [
            node_colors.get(
                self.tracked_items[node]["state"],
                "gray"
            ) for node in G.nodes
        ]
        
        # Define different node shapes based on type
        node_shapes = {
            "task": "o",      # circle
            "project": "s",   # square
            "milestone": "D"  # diamond
        }
        
        # Position nodes using layout algorithm
        pos = nx.spring_layout(G)
        
        # Draw nodes
        for node_type, shape in node_shapes.items():
            nodes = [n for n in G.nodes if self.tracked_items[n]["type"] == node_type]
            if nodes:
                nx.draw_networkx_nodes(
                    G, pos,
                    nodelist=nodes,
                    node_color=[node_colors.get(self.tracked_items[n]["state"], "gray") for n in nodes],
                    node_shape=shape,
                    node_size=500,
                    alpha=0.8
                )
        
        # Draw edges
        nx.draw_networkx_edges(
            G, pos,
            arrows=True,
            arrowstyle="-|>",
            width=1.5,
            alpha=0.7
        )
        
        # Draw labels
        nx.draw_networkx_labels(
            G, pos,
            labels={n: self.tracked_items[n]["name"] for n in G.nodes},
            font_size=10,
            font_weight="bold"
        )
        
        plt.title("Dependency Network")
        plt.axis("off")
        
        # Convert to base64
        buffer = BytesIO()
        plt.savefig(buffer, format="png")
        plt.close()
        
        image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        return {
            "type": "dependency_network",
            "image": f"data:image/png;base64,{image_base64}",
            "data": {
                "nodes": nodes_data,
                "edges": edges_data
            }
        }
    
    def _add_item_and_dependencies(self, item_id: str, items_set: Set[str]):
        """Helper to add an item and its dependencies to a set recursively."""
        if item_id not in self.tracked_items:
            return
        
        items_set.add(item_id)
        
        # Add dependencies
        for dep_id in self.tracked_items[item_id].get("depends_on", []):
            if dep_id not in items_set and dep_id in self.tracked_items:
                self._add_item_and_dependencies(dep_id, items_set)
    
    def _find_dependents(self, item_id: str) -> Set[str]:
        """Find all items that depend on the given item."""
        dependents = set()
        
        for dep_id, dep_item in self.tracked_items.items():
            if item_id in dep_item.get("depends_on", []):
                dependents.add(dep_id)
                # Also add items that depend on this dependent
                dependents.update(self._find_dependents(dep_id))
        
        return dependents
    
    async def _create_milestone_status_visualization(self, item_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Create a milestone status visualization."""
        # Find all milestones
        if item_id:
            # If item_id is provided, only include milestones related to that item
            milestones = [
                item for item in self.tracked_items.values()
                if item["type"] == "milestone" and item.get("parent_id") == item_id
            ]
        else:
            # Otherwise, include all milestones
            milestones = [
                item for item in self.tracked_items.values()
                if item["type"] == "milestone"
            ]
        
        if not milestones:
            return {"error": "No milestones found"}
        
        # Create milestone data
        milestone_data = []
        for milestone in milestones:
            # Check if all dependencies are complete
            deps_complete = True
            deps_status = {}
            for dep_id in milestone.get("depends_on", []):
                if dep_id not in self.tracked_items:
                    deps_complete = False
                    deps_status[dep_id] = "not_found"
                elif self.tracked_items[dep_id]["state"] != ProgressState.COMPLETED:
                    deps_complete = False
                    deps_status[dep_id] = self.tracked_items[dep_id]["state"]
                else:
                    deps_status[dep_id] = "completed"
            
            milestone_data.append({
                "id": milestone["id"],
                "name": milestone["name"],
                "state": milestone["state"].value if isinstance(milestone["state"], Enum) else milestone["state"],
                "completion_percentage": milestone["completion_percentage"],
                "expected_date": milestone.get("data", {}).get("expected_date"),
                "deps_complete": deps_complete,
                "deps_status": deps_status
            })
        
        # Sort milestones by expected date
        milestone_data.sort(
            key=lambda x: x.get("expected_date") or "9999-12-31"
        )
        
        # Generate image
        plt.figure(figsize=(12, len(milestone_data) * 0.5 + 2))
        
        # Y-axis will be milestone names
        y_labels = [milestone["name"] for milestone in milestone_data]
        y_pos = range(len(y_labels))
        
        # Define colors for different states
        colors = {
            "NOT_STARTED": "lightgray",
            "WAITING": "lightyellow",
            "IN_PROGRESS": "lightblue",
            "PAUSED": "orange",
            "COMPLETED": "lightgreen",
            "FAILED": "lightcoral",
            "CANCELED": "lightpink"
        }
        
        # Plot each milestone
        for i, milestone in enumerate(milestone_data):
            plt.barh(
                y_pos[i],
                milestone["completion_percentage"],
                color=colors.get(milestone["state"], "gray"),
                height=0.5,
                alpha=0.7
            )
            
            # Add completion percentage
            plt.text(
                milestone["completion_percentage"] + 1,
                y_pos[i],
                f"{milestone['completion_percentage']:.1f}%",
                verticalalignment="center"
            )
        
        # Format plot
        plt.yticks(y_pos, y_labels)
        plt.xlabel("Completion Percentage")
        plt.title("Milestone Status")
        plt.xlim(0, 105)  # Add a bit of space for labels
        plt.grid(True)
        
        # Add color legend
        legend_elements = [
            plt.Rectangle((0, 0), 1, 1, color=color, label=state)
            for state, color in colors.items()
        ]
        plt.legend(handles=legend_elements, loc="best")
        
        # Convert to base64
        buffer = BytesIO()
        plt.savefig(buffer, format="png")
        plt.close()
        
        image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        return {
            "type": "milestone_status",
            "image": f"data:image/png;base64,{image_base64}",
            "data": {"milestones": milestone_data}
        }
    
    async def _check_stalled_progress(self, item_id: str) -> None:
        """Check if progress has stalled for too long."""
        item = self.tracked_items[item_id]
        
        # Skip if not in progress
        if item["state"] != ProgressState.IN_PROGRESS:
            return
        
        # Check time since last update
        last_update = datetime.fromisoformat(item["latest_update"])
        now = datetime.now()
        
        stalled_threshold = timedelta(
            minutes=self.config["notification_thresholds"]["stalled_minutes"]
        )
        
        if now - last_update > stalled_threshold:
            await self._create_notification(
                item_id=item_id,
                notification_type="stalled_progress",
                message=f"Item {item['name']} has stalled for {self.config['notification_thresholds']['stalled_minutes']} minutes"
            )
    
    async def get_notifications(self, acknowledged: Optional[bool] = None, item_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get notifications, optionally filtered by acknowledgment status or item.
        
        Args:
            acknowledged: Filter by acknowledgment status (True/False), or None for all
            item_id: Filter by item ID, or None for all items
            
        Returns:
            List of notification dictionaries
        """
        result = []
        
        for notification in self.notifications:
            # Apply acknowledgment filter if provided
            if acknowledged is not None and notification["acknowledged"] != acknowledged:
                continue
                
            # Apply item filter if provided
            if item_id and notification["item_id"] != item_id:
                continue
                
            result.append(notification)
            
        return result
    
    async def acknowledge_notification(self, notification_id: str) -> Dict[str, Any]:
        """
        Acknowledge a notification.
        
        Args:
            notification_id: ID of the notification to acknowledge
            
        Returns:
            The updated notification dictionary
        """
        for notification in self.notifications:
            if notification["id"] == notification_id:
                notification["acknowledged"] = True
                notification["acknowledgment_time"] = datetime.now().isoformat()
                return notification
                
        raise ValueError(f"Notification {notification_id} not found")
    
    async def save_tracking_data(self, file_path: str) -> None:
        """Save tracking data to a file."""
        data = {
            "tracked_items": self.tracked_items,
            "notifications": self.notifications,
            "timestamp": datetime.now().isoformat()
        }
        
        # Convert tracked items for serialization
        for item_id, item in data["tracked_items"].items():
            # Convert Enum values to strings
            if isinstance(item["state"], Enum):
                item["state"] = item["state"].value
                
            # Convert metrics to dictionaries
            metrics_dict = {}
            for metric_name, metric in item["metrics"].items():
                if isinstance(metric, ProgressMetric):
                    metrics_dict[metric_name] = {
                        "name": metric.name,
                        "description": metric.description,
                        "current_value": metric.current_value,
                        "target_value": metric.target_value,
                        "unit": metric.unit,
                        "timestamp": metric.timestamp
                    }
                else:
                    metrics_dict[metric_name] = metric
            item["metrics"] = metrics_dict
            
            # Convert snapshots to dictionaries
            snapshots_list = []
            for snapshot in item["snapshots"]:
                if isinstance(snapshot, ProgressSnapshot):
                    # Convert snapshot metrics to dictionaries
                    snapshot_metrics = {}
                    for s_metric_name, s_metric in snapshot.metrics.items():
                        if isinstance(s_metric, ProgressMetric):
                            snapshot_metrics[s_metric_name] = {
                                "name": s_metric.name,
                                "description": s_metric.description,
                                "current_value": s_metric.current_value,
                                "target_value": s_metric.target_value,
                                "unit": s_metric.unit,
                                "timestamp": s_metric.timestamp
                            }
                        else:
                            snapshot_metrics[s_metric_name] = s_metric
                    
                    snapshots_list.append({
                        "timestamp": snapshot.timestamp,
                        "state": snapshot.state.value if isinstance(snapshot.state, Enum) else snapshot.state,
                        "completion_percentage": snapshot.completion_percentage,
                        "metrics": snapshot_metrics,
                        "message": snapshot.message
                    })
                else:
                    snapshots_list.append(snapshot)
            item["snapshots"] = snapshots_list
        
        # Save to file
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Tracking data saved to {file_path}")
    
    async def load_tracking_data(self, file_path: str) -> None:
        """Load tracking data from a file."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Tracking data file not found: {file_path}")
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Clear existing data
        self.tracked_items.clear()
        self.notifications.clear()
        
        # Load notifications
        self.notifications = data.get("notifications", [])
        
        # Load tracked items
        for item_id, item in data.get("tracked_items", {}).items():
            # Convert state string back to Enum
            if isinstance(item["state"], str):
                try:
                    item["state"] = ProgressState(item["state"])
                except ValueError:
                    logger.warning(f"Invalid state value: {item['state']}, using NOT_STARTED")
                    item["state"] = ProgressState.NOT_STARTED
            
            # Convert metrics back to ProgressMetric objects
            metrics_dict = {}
            for metric_name, metric_data in item["metrics"].items():
                if isinstance(metric_data, dict) and "name" in metric_data:
                    metrics_dict[metric_name] = ProgressMetric(
                        name=metric_data.get("name", metric_name),
                        description=metric_data.get("description", ""),
                        current_value=metric_data.get("current_value", 0),
                        target_value=metric_data.get("target_value", 100),
                        unit=metric_data.get("unit", ""),
                        timestamp=metric_data.get("timestamp", datetime.now().isoformat())
                    )
                else:
                    # Handle legacy format
                    metrics_dict[metric_name] = metric_data
            
            item["metrics"] = metrics_dict
            
            # Convert snapshots back to ProgressSnapshot objects
            snapshots_list = []
            for snapshot_data in item["snapshots"]:
                if isinstance(snapshot_data, dict):
                    # Convert state string back to Enum
                    snapshot_state = snapshot_data.get("state")
                    if isinstance(snapshot_state, str):
                        try:
                            snapshot_state = ProgressState(snapshot_state)
                        except ValueError:
                            logger.warning(f"Invalid snapshot state value: {snapshot_state}, using NOT_STARTED")
                            snapshot_state = ProgressState.NOT_STARTED
                    
                    # Convert snapshot metrics back to ProgressMetric objects
                    snapshot_metrics = {}
                    for s_metric_name, s_metric_data in snapshot_data.get("metrics", {}).items():
                        if isinstance(s_metric_data, dict) and "name" in s_metric_data:
                            snapshot_metrics[s_metric_name] = ProgressMetric(
                                name=s_metric_data.get("name", s_metric_name),
                                description=s_metric_data.get("description", ""),
                                current_value=s_metric_data.get("current_value", 0),
                                target_value=s_metric_data.get("target_value", 100),
                                unit=s_metric_data.get("unit", ""),
                                timestamp=s_metric_data.get("timestamp", snapshot_data.get("timestamp"))
                            )
                        else:
                            snapshot_metrics[s_metric_name] = s_metric_data
                    
                    snapshots_list.append(ProgressSnapshot(
                        timestamp=snapshot_data.get("timestamp"),
                        state=snapshot_state,
                        completion_percentage=snapshot_data.get("completion_percentage", 0.0),
                        metrics=snapshot_metrics,
                        message=snapshot_data.get("message")
                    ))
                else:
                    snapshots_list.append(snapshot_data)
            
            item["snapshots"] = snapshots_list
            
            # Add to tracked items
            self.tracked_items[item_id] = item
        
        logger.info(f"Loaded tracking data from {file_path}: {len(self.tracked_items)} items, {len(self.notifications)} notifications")
    
    async def get_item_status(self, item_id: str) -> Dict[str, Any]:
        """
        Get the current status of a tracked item.
        
        Args:
            item_id: ID of the item to get status for
            
        Returns:
            Dictionary with item status details
        """
        if item_id not in self.tracked_items:
            raise ValueError(f"Item {item_id} not found in tracked items")
        
        item = self.tracked_items[item_id]
        
        # Create status dictionary with basic item details
        status = {
            "id": item["id"],
            "type": item["type"],
            "name": item["name"],
            "description": item["description"],
            "state": item["state"],
            "completion_percentage": item["completion_percentage"],
            "latest_update": item["latest_update"],
            "metrics": {}
        }
        
        # Add start/end time if available
        if item["start_time"]:
            status["start_time"] = item["start_time"]
        
        if item["end_time"]:
            status["end_time"] = item["end_time"]
            
        # Add metrics if available
        if item["metrics"]:
            for metric_name, metric in item["metrics"].items():
                status["metrics"][metric_name] = metric.current_value
                
        # Add dependencies if any
        if item["depends_on"]:
            status["depends_on"] = item["depends_on"]
            
        # Add parent if any
        if item["parent_id"]:
            status["parent_id"] = item["parent_id"]
            
        return status

    async def _generate_milestone_image(self, milestones_data):
        """Generate an image visualization of milestone status.
        
        This method would normally create a timeline or chart visualization of milestones.
        For testing purposes, this is a stub that would be replaced with actual visualization code.
        
        Args:
            milestones_data: Data about milestones to visualize
            
        Returns:
            Base64 encoded image data
        """
        # This is a stub implementation that would be replaced with actual visualization code
        # In a real implementation, this would generate a timeline or chart of milestone status
        
        plt.figure(figsize=(10, 6))
        
        # Example implementation (would be more sophisticated in production)
        names = [m.get("name", f"Milestone {i}") for i, m in enumerate(milestones_data)]
        states = [m.get("state", ProgressState.NOT_STARTED) for m in milestones_data]
        completions = [m.get("completion", 0) for m in milestones_data]
        
        # Create colors based on state
        colors = []
        for state in states:
            if state == ProgressState.COMPLETED:
                colors.append("green")
            elif state == ProgressState.IN_PROGRESS:
                colors.append("blue")
            elif state == ProgressState.FAILED:
                colors.append("red")
            else:
                colors.append("gray")
        
        # Create horizontal bar chart
        plt.barh(names, completions, color=colors)
        plt.xlabel("Completion %")
        plt.title("Milestone Status")
        plt.tight_layout()
        
        # Convert to base64
        buffer = BytesIO()
        plt.savefig(buffer, format="png")
        plt.close()
        
        image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{image_base64}"
    
    async def _generate_network_image(self, network_data):
        """Generate an image visualization of a dependency network.
        
        This method would normally create a network graph visualization.
        For testing purposes, this is a stub that would be replaced with actual visualization code.
        
        Args:
            network_data: Data about network nodes and edges to visualize
            
        Returns:
            Base64 encoded image data
        """
        # This is a stub implementation that would be replaced with actual visualization code
        # In a real implementation, this would generate a network graph of dependencies
        
        # Create a directed graph
        G = nx.DiGraph()
        
        # Add nodes
        for node in network_data.get("nodes", []):
            G.add_node(
                node["id"],
                name=node.get("name", node["id"]),
                state=node.get("state", ProgressState.NOT_STARTED),
                completion=node.get("completion", 0)
            )
        
        # Add edges
        for edge in network_data.get("edges", []):
            G.add_edge(edge["source"], edge["target"])
        
        # Draw the graph
        plt.figure(figsize=(10, 8))
        pos = nx.spring_layout(G)
        
        # Color nodes based on state
        node_colors = []
        for node in G.nodes:
            state = G.nodes[node].get("state")
            if state == ProgressState.COMPLETED:
                node_colors.append("green")
            elif state == ProgressState.IN_PROGRESS:
                node_colors.append("blue")
            elif state == ProgressState.FAILED:
                node_colors.append("red")
            else:
                node_colors.append("gray")
        
        nx.draw(G, pos, with_labels=True, node_color=node_colors, 
                node_size=500, arrows=True, font_size=10)
        plt.title("Dependency Network")
        
        # Convert to base64
        buffer = BytesIO()
        plt.savefig(buffer, format="png")
        plt.close()
        
        image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{image_base64}" 