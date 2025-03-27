I'll provide detailed implementation instructions for Phase 5 Work Units 5.1 (Progress Tracker) and 5.2 (Intervention Interface). I'll include comprehensive code examples, unit tests, and explain the connections to previous phases.

# Phase 5: Observability Layer Implementation

Let's begin with a high-level overview before diving into the specifics of each work unit.

## Overview of Phase 5 - Observability Layer

The Observability Layer provides visibility into the system's operation, enabling human oversight and intervention. This layer builds upon the previous phases:

- **Phase 1 (Core Intelligence)**: Provides the fundamental AI capabilities
- **Phase 2 (Planning Engine)**: Enables goal-driven planning
- **Phase 3 (Execution Engine)**: Manages task execution and coordination
- **Phase 4 (Self-Modification Engine)**: Enables the system to modify itself

The Observability Layer serves as a critical interface between the autonomous system and human supervisors. It makes the system's internal state, progress, and decision-making transparent, while providing controlled intervention points.

Now let's implement Work Units 5.1 and 5.2.

## Work Unit 5.1: Progress Tracker

The Progress Tracker monitors and visualizes system progress across different levels, from individual tasks to overall goals. It connects with the Execution Engine (Phase 3) to track task execution and the Planning Engine (Phase 2) to monitor goal progress.

```python
from typing import Dict, List, Optional, Any, Union, Callable
import logging
from enum import Enum
from dataclasses import dataclass, field
import json
from datetime import datetime, timedelta
import asyncio
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
import networkx as nx
from io import BytesIO
import base64

logger = logging.getLogger(__name__)

class TrackingLevel(Enum):
    """Tracking detail level."""
    MINIMAL = "minimal"  # Basic task completion
    STANDARD = "standard"  # Progress, status, timing
    DETAILED = "detailed"  # Full context, metrics, dependencies
    DIAGNOSTIC = "diagnostic"  # Debug-level information

class ProgressState(Enum):
    """States for progress tracking."""
    NOT_STARTED = "not_started"
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"

@dataclass
class ProgressMetric:
    """A metric for measuring progress."""
    name: str
    description: str
    current_value: float
    target_value: float
    unit: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def percentage(self) -> float:
        """Calculate percentage completion."""
        if self.target_value == 0:
            return 100.0 if self.current_value == 0 else 0.0
        return min(100.0, (self.current_value / self.target_value) * 100.0)

@dataclass
class ProgressSnapshot:
    """A point-in-time snapshot of progress."""
    timestamp: str
    state: ProgressState
    completion_percentage: float
    metrics: Dict[str, ProgressMetric]
    message: Optional[str] = None

class ProgressTracker:
    """Tracks and visualizes system progress across different levels."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize with optional configuration."""
        self.config = config or {
            "tracking_level": TrackingLevel.STANDARD,
            "snapshot_interval": 60,  # seconds
            "visualization_enabled": True,
            "data_retention_days": 30,
            "notification_thresholds": {
                "stalled_minutes": 30,
                "completion_percentage": 90,
                "failure_count": 3
            }
        }
        
        self.tracked_items: Dict[str, Dict[str, Any]] = {}
        self.visualization_handlers: Dict[str, Callable] = self._register_visualization_handlers()
        self.notifications: List[Dict[str, Any]] = []
        self.snapshot_tasks: Dict[str, asyncio.Task] = {}
    
    def _register_visualization_handlers(self) -> Dict[str, Callable]:
        """Register handlers for different visualization types."""
        return {
            "progress_timeline": self._visualize_progress_timeline,
            "milestone_status": self._visualize_milestone_status,
            "dependency_network": self._visualize_dependency_network,
            "resource_utilization": self._visualize_resource_utilization,
            "completion_forecast": self._visualize_completion_forecast
        }
    
    async def register_item(self, 
                           item_id: str,
                           item_type: str,
                           name: str,
                           description: str,
                           parent_id: Optional[str] = None,
                           expected_duration: Optional[int] = None,
                           metrics: Optional[Dict[str, ProgressMetric]] = None) -> Dict[str, Any]:
        """Register an item to be tracked."""
        logger.info(f"Registering tracking item: {name} ({item_id})")
        
        if item_id in self.tracked_items:
            logger.warning(f"Item {item_id} already being tracked, updating instead")
        
        # Create tracking record
        now = datetime.now().isoformat()
        item_data = {
            "id": item_id,
            "type": item_type,
            "name": name,
            "description": description,
            "parent_id": parent_id,
            "state": ProgressState.NOT_STARTED,
            "expected_duration": expected_duration,  # in seconds
            "start_time": None,
            "end_time": None,
            "completion_percentage": 0.0,
            "children": [],
            "metrics": metrics or {},
            "snapshots": [],
            "latest_update": now,
            "created_at": now
        }
        
        # Link to parent if specified
        if parent_id:
            if parent_id in self.tracked_items:
                self.tracked_items[parent_id]["children"].append(item_id)
            else:
                logger.warning(f"Parent item {parent_id} not found, creating orphaned item")
        
        # Store item
        self.tracked_items[item_id] = item_data
        
        # Create initial snapshot
        await self._create_snapshot(item_id)
        
        # Start background snapshot task if needed
        if self.config.get("snapshot_interval") > 0:
            await self._start_snapshot_task(item_id)
        
        return self.tracked_items[item_id]
    
    async def update_progress(self,
                            item_id: str,
                            state: Optional[ProgressState] = None,
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
                    item_id,
                    "completion_threshold",
                    f"Item {item['name']} is {item['completion_percentage']}% complete"
                )
        
        # Update metrics if provided
        if metrics_updates:
            for metric_name, metric_value in metrics_updates.items():
                if metric_name in item["metrics"]:
                    item["metrics"][metric_name].current_value = metric_value
                    item["metrics"][metric_name].timestamp = now
                else:
                    logger.warning(f"Metric {metric_name} not registered for item {item_id}")
        
        # Update timestamp
        item["latest_update"] = now
        
        # Create a new snapshot
        await self._create_snapshot(item_id, message)
        
        # Propagate updates to parent items
        if item["parent_id"]:
            await self._update_parent_progress(item["parent_id"])
        
        return item
    
    async def get_progress_report(self,
                                item_id: Optional[str] = None,
                                include_children: bool = True,
                                include_snapshots: bool = False) -> Dict[str, Any]:
        """Get a progress report for an item or the entire system."""
        if item_id:
            if item_id not in self.tracked_items:
                raise ValueError(f"Item {item_id} not registered for tracking")
            
            item = self.tracked_items[item_id]
            report = self._create_item_report(item, include_snapshots)
            
            if include_children:
                report["children"] = [
                    self._create_item_report(self.tracked_items[child_id], include_snapshots)
                    for child_id in item["children"]
                    if child_id in self.tracked_items
                ]
            
            return report
        else:
            # Generate whole system report
            root_items = [
                item for item in self.tracked_items.values()
                if not item["parent_id"]
            ]
            
            summary = {
                "total_items": len(self.tracked_items),
                "completed_items": sum(1 for item in self.tracked_items.values() 
                                     if item["state"] == ProgressState.COMPLETED),
                "failed_items": sum(1 for item in self.tracked_items.values() 
                                  if item["state"] == ProgressState.FAILED),
                "in_progress_items": sum(1 for item in self.tracked_items.values() 
                                       if item["state"] == ProgressState.IN_PROGRESS),
                "overall_completion": self._calculate_overall_completion(),
                "timestamp": datetime.now().isoformat()
            }
            
            return {
                "summary": summary,
                "root_items": [
                    self._create_item_report(item, include_snapshots, include_children)
                    for item in root_items
                ]
            }
    
    def _create_item_report(self, 
                          item: Dict[str, Any], 
                          include_snapshots: bool = False,
                          include_children: bool = False) -> Dict[str, Any]:
        """Create a report for a single item."""
        report = {
            "id": item["id"],
            "name": item["name"],
            "type": item["type"],
            "state": item["state"],
            "completion_percentage": item["completion_percentage"],
            "start_time": item["start_time"],
            "end_time": item["end_time"],
            "latest_update": item["latest_update"],
            "metrics": {
                name: {
                    "current_value": metric.current_value,
                    "target_value": metric.target_value,
                    "percentage": metric.percentage,
                    "unit": metric.unit
                }
                for name, metric in item["metrics"].items()
            }
        }
        
        if include_snapshots:
            report["snapshots"] = item["snapshots"]
        
        if include_children:
            report["children"] = [
                self._create_item_report(self.tracked_items[child_id], include_snapshots)
                for child_id in item["children"]
                if child_id in self.tracked_items
            ]
        
        return report
    
    async def create_visualization(self,
                                 item_id: Optional[str] = None,
                                 visualization_type: str = "progress_timeline",
                                 options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a visualization of progress data."""
        if visualization_type not in self.visualization_handlers:
            raise ValueError(f"Unsupported visualization type: {visualization_type}")
        
        options = options or {}
        
        # Set default item scope if not specified
        if not item_id and "items" not in options:
            options["items"] = list(self.tracked_items.keys())
        elif item_id:
            if item_id not in self.tracked_items:
                raise ValueError(f"Item {item_id} not registered for tracking")
            options["items"] = [item_id]
        
        # Create visualization
        return await self.visualization_handlers[visualization_type](options)
    
    async def _visualize_progress_timeline(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """Visualize progress over time."""
        item_ids = options.get("items", [])
        start_date = options.get("start_date")
        end_date = options.get("end_date")
        
        # Collect data
        timeline_data = []
        for item_id in item_ids:
            if item_id not in self.tracked_items:
                continue
                
            item = self.tracked_items[item_id]
            
            # Filter snapshots by date if specified
            snapshots = item["snapshots"]
            if start_date:
                snapshots = [s for s in snapshots if s["timestamp"] >= start_date]
            if end_date:
                snapshots = [s for s in snapshots if s["timestamp"] <= end_date]
            
            # Create data points
            for snapshot in snapshots:
                timeline_data.append({
                    "item_id": item_id,
                    "name": item["name"],
                    "timestamp": snapshot["timestamp"],
                    "completion_percentage": snapshot["completion_percentage"],
                    "state": snapshot["state"].value
                })
        
        # Create visualization
        if not timeline_data:
            return {"error": "No data available for visualization"}
        
        # Convert to DataFrame for easier plotting
        df = pd.DataFrame(timeline_data)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp")
        
        # Create plot
        plt.figure(figsize=(12, 6))
        
        for item_id in df["item_id"].unique():
            item_df = df[df["item_id"] == item_id]
            plt.plot(
                item_df["timestamp"], 
                item_df["completion_percentage"],
                label=item_df["name"].iloc[0]
            )
        
        plt.title("Progress Timeline")
        plt.xlabel("Time")
        plt.ylabel("Completion (%)")
        plt.legend()
        plt.grid(True)
        
        # Convert to base64
        buffer = BytesIO()
        plt.savefig(buffer, format="png")
        plt.close()
        
        image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        return {
            "type": "progress_timeline",
            "image": f"data:image/png;base64,{image_base64}",
            "data": timeline_data
        }
    
    async def _visualize_milestone_status(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """Visualize milestone status."""
        item_ids = options.get("items", [])
        
        # Collect milestone data
        milestone_data = []
        for item_id in item_ids:
            if item_id not in self.tracked_items:
                continue
                
            item = self.tracked_items[item_id]
            
            # Only include milestones (can be configured by item type)
            if item["type"] == "milestone":
                milestone_data.append({
                    "name": item["name"],
                    "state": item["state"].value,
                    "completion": item["completion_percentage"],
                    "deadline": item.get("deadline")
                })
        
        if not milestone_data:
            return {"error": "No milestones available for visualization"}
        
        # Create visualization
        plt.figure(figsize=(10, 6))
        
        df = pd.DataFrame(milestone_data)
        df = df.sort_values("completion")
        
        # Color-code by state
        colors = {
            "not_started": "gray",
            "planning": "blue",
            "in_progress": "orange",
            "waiting": "yellow",
            "completed": "green",
            "failed": "red",
            "canceled": "black"
        }
        
        bar_colors = [colors.get(state, "gray") for state in df["state"]]
        
        plt.barh(df["name"], df["completion"], color=bar_colors)
        plt.title("Milestone Status")
        plt.xlabel("Completion (%)")
        plt.xlim(0, 100)
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
            "data": milestone_data
        }
    
    async def _visualize_dependency_network(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """Visualize item dependencies as a network."""
        item_ids = options.get("items", [])
        include_all_descendants = options.get("include_all_descendants", True)
        
        # Build dependency graph
        G = nx.DiGraph()
        
        # Add all specified items and their descendants
        items_to_include = set(item_ids)
        if include_all_descendants:
            for item_id in list(items_to_include):
                self._add_descendants_recursive(item_id, items_to_include)
        
        # Add nodes and edges
        for item_id in items_to_include:
            if item_id not in self.tracked_items:
                continue
                
            item = self.tracked_items[item_id]
            
            # Add node
            G.add_node(
                item_id,
                name=item["name"],
                state=item["state"].value,
                completion=item["completion_percentage"]
            )
            
            # Add edges for parent-child relationships
            parent_id = item["parent_id"]
            if parent_id and parent_id in items_to_include:
                G.add_edge(parent_id, item_id, type="parent-child")
        
        if not G.nodes:
            return {"error": "No items available for network visualization"}
        
        # Create visualization
        plt.figure(figsize=(12, 10))
        
        # Define node colors based on state
        node_colors = {
            "not_started": "lightgray",
            "planning": "lightblue",
            "in_progress": "orange",
            "waiting": "yellow",
            "completed": "lightgreen",
            "failed": "lightcoral",
            "canceled": "black"
        }
        
        # Create position layout
        pos = nx.spring_layout(G)
        
        # Draw nodes with color based on state
        for state, color in node_colors.items():
            nodes = [
                node for node in G.nodes
                if G.nodes[node].get("state") == state
            ]
            if nodes:
                nx.draw_networkx_nodes(
                    G, pos,
                    nodelist=nodes,
                    node_color=color,
                    node_size=500
                )
        
        # Draw edges
        nx.draw_networkx_edges(G, pos, arrows=True)
        
        # Draw labels
        labels = {node: G.nodes[node]["name"] for node in G.nodes}
        nx.draw_networkx_labels(G, pos, labels=labels)
        
        plt.title("Dependency Network")
        plt.axis("off")
        
        # Add color legend
        legend_elements = [
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=color, 
                      markersize=10, label=state)
            for state, color in node_colors.items()
        ]
        plt.legend(handles=legend_elements, loc="best")
        
        # Convert to base64
        buffer = BytesIO()
        plt.savefig(buffer, format="png")
        plt.close()
        
        image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        # Prepare return data
        node_data = [
            {
                "id": node,
                "name": G.nodes[node]["name"],
                "state": G.nodes[node]["state"],
                "completion": G.nodes[node]["completion"]
            }
            for node in G.nodes
        ]
        
        edge_data = [
            {
                "source": source,
                "target": target,
                "type": G.edges[source, target]["type"]
            }
            for source, target in G.edges
        ]
        
        return {
            "type": "dependency_network",
            "image": f"data:image/png;base64,{image_base64}",
            "data": {
                "nodes": node_data,
                "edges": edge_data
            }
        }
    
    def _add_descendants_recursive(self, item_id: str, result_set: set) -> None:
        """Add item's descendants to the result set recursively."""
        if item_id not in self.tracked_items:
            return
            
        item = self.tracked_items[item_id]
        for child_id in item["children"]:
            result_set.add(child_id)
            self._add_descendants_recursive(child_id, result_set)
    
    async def _visualize_resource_utilization(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """Visualize resource utilization."""
        # Implementation for resource visualization
        # This would typically collect resource usage data from different components
        return {"type": "resource_utilization", "message": "Not implemented"}
    
    async def _visualize_completion_forecast(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """Visualize completion forecast based on current progress."""
        # Implementation for completion forecast
        # This would use historical data to predict completion times
        return {"type": "completion_forecast", "message": "Not implemented"}
    
    async def _create_snapshot(self, 
                             item_id: str,
                             message: Optional[str] = None) -> None:
        """Create a progress snapshot for an item."""
        item = self.tracked_items[item_id]
        
        snapshot = ProgressSnapshot(
            timestamp=datetime.now().isoformat(),
            state=item["state"],
            completion_percentage=item["completion_percentage"],
            metrics={name: metric for name, metric in item["metrics"].items()},
            message=message
        )
        
        # Convert to dictionary for storage
        snapshot_dict = {
            "timestamp": snapshot.timestamp,
            "state": snapshot.state,
            "completion_percentage": snapshot.completion_percentage,
            "metrics": {
                name: {
                    "current_value": metric.current_value,
                    "target_value": metric.target_value,
                    "unit": metric.unit
                }
                for name, metric in snapshot.metrics.items()
            }
        }
        
        if message:
            snapshot_dict["message"] = message
        
        # Add to snapshots list
        item["snapshots"].append(snapshot_dict)
        
        # Limit number of snapshots if needed
        max_snapshots = self.config.get("max_snapshots_per_item", 100)
        if len(item["snapshots"]) > max_snapshots:
            item["snapshots"] = item["snapshots"][-max_snapshots:]
    
    async def _start_snapshot_task(self, item_id: str) -> None:
        """Start background task for periodic snapshots."""
        if item_id in self.snapshot_tasks and not self.snapshot_tasks[item_id].done():
            # Task already running
            return
        
        # Create new snapshot task
        task = asyncio.create_task(self._snapshot_loop(item_id))
        self.snapshot_tasks[item_id] = task
    
    async def _snapshot_loop(self, item_id: str) -> None:
        """Background loop for creating periodic snapshots."""
        interval = self.config["snapshot_interval"]
        
        try:
            while item_id in self.tracked_items:
                # Sleep first to avoid duplicate snapshots
                await asyncio.sleep(interval)
                
                if item_id not in self.tracked_items:
                    break
                    
                item = self.tracked_items[item_id]
                
                # Skip if item is in a terminal state
                if item["state"] in [
                    ProgressState.COMPLETED,
                    ProgressState.FAILED,
                    ProgressState.CANCELED
                ]:
                    break
                
                # Create snapshot
                await self._create_snapshot(item_id)
                
                # Check for stalled progress
                await self._check_stalled_progress(item_id)
                
        except asyncio.CancelledError:
            logger.info(f"Snapshot task for item {item_id} canceled")
        except Exception as e:
            logger.error(f"Error in snapshot task for item {item_id}: {str(e)}")
    
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
                item_id,
                "stalled_progress",
                f"Item {item['name']} has stalled for {self.config['notification_thresholds']['stalled_minutes']} minutes"
            )
    
    async def _update_parent_progress(self, parent_id: str) -> None:
        """Update parent item progress based on children."""
        if parent_id not in self.tracked_items:
            return
        
        parent = self.tracked_items[parent_id]
        child_ids = parent["children"]
        
        if not child_ids:
            return
        
        # Calculate aggregate progress
        total_children = len(child_ids)
        completed_children = 0
        total_percentage = 0.0
        
        for child_id in child_ids:
            if child_id not in self.tracked_items:
                continue
                
            child = self.tracked_items[child_id]
            total_percentage += child["completion_percentage"]
            
            if child["state"] == ProgressState.COMPLETED:
                completed_children += 1
        
        # Update parent completion percentage
        average_percentage = total_percentage / total_children if total_children > 0 else 0
        
        await self.update_progress(
            parent_id,
            completion_percentage=average_percentage
        )
        
        # Update parent state if all children complete
        if completed_children == total_children and total_children > 0:
            await self.update_progress(
                parent_id,
                state=ProgressState.COMPLETED
            )
    
    async def _check_state_notification(self, 
                                      item_id: str,
                                      old_state: ProgressState,
                                      new_state: ProgressState) -> None:
        """Check if a state change should trigger a notification."""
        item = self.tracked_items[item_id]
        
        # Notify on completion
        if new_state == ProgressState.COMPLETED:
            await self._create_notification(
                item_id,
                "state_change",
                f"Item {item['name']} has been completed"
            )
        
        # Notify on failure
        elif new_state == ProgressState.FAILED:
            await self._create_notification(
                item_id,
                "state_change",
                f"Item {item['name']} has failed"
            )
    
    async def _create_notification(self, 
                                 item_id: str,
                                 notification_type: str,
                                 message: str) -> Dict[str, Any]:
        """Create a notification for an item."""
        notification = {
            "id": f"notif_{len(self.notifications) + 1}",
            "item_id": item_id,
            "type": notification_type,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "acknowledged": False
        }
        
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
    
    async def save_tracking_data(self, file_path: str) -> None:
        """Save tracking data to a file."""
        data = {
            "tracked_items": self.tracked_items,
            "notifications": self.notifications,
            "timestamp": datetime.now().isoformat()
        }
        
CCCCC

Let me continue with the implementation of the Progress Tracker and then move on to the Intervention Interface.

```python
# Continuing ProgressTracker class implementation

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
            
            # Add to tracked items
            self.tracked_items[item_id] = item
        
        logger.info(f"Loaded tracking data from {file_path}: {len(self.tracked_items)} items, {len(self.notifications)} notifications")
    
    async def get_notifications(self, 
                              include_acknowledged: bool = False,
                              item_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get notifications, optionally filtered by acknowledgment status or item."""
        filtered_notifications = self.notifications
        
        if not include_acknowledged:
            filtered_notifications = [n for n in filtered_notifications if not n.get("acknowledged")]
            
        if item_id:
            filtered_notifications = [n for n in filtered_notifications if n.get("item_id") == item_id]
            
        return filtered_notifications
    
    async def acknowledge_notification(self, notification_id: str) -> Dict[str, Any]:
        """Acknowledge a notification."""
        for notification in self.notifications:
            if notification["id"] == notification_id:
                notification["acknowledged"] = True
                notification["acknowledged_at"] = datetime.now().isoformat()
                return notification
                
        raise ValueError(f"Notification {notification_id} not found")
```

Now let's implement the unit tests for the Progress Tracker:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
import json
import os
import tempfile
from datetime import datetime, timedelta

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
        assert "acknowledged_at" in acknowledged
        
        # Check filtered notifications
        filtered = await progress_tracker.get_notifications(include_acknowledged=False)
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
        assert system_report["summary"]["in_progress_items"] == 1
        assert system_report["summary"]["overall_completion"] == 75.0
    
    @pytest.mark.asyncio
    async def test_visualization(self, progress_tracker):
        """Test visualization creation."""
        # Register item
        await progress_tracker.register_item(
            item_id="test_item",
            item_type="task",
            name="Test Item",
            description="A test item"
        )
        
        # Update progress a few times
        for i in range(1, 6):
            await progress_tracker.update_progress(
                item_id="test_item",
                completion_percentage=i * 20.0
            )
            await asyncio.sleep(0.1)  # Small delay for different timestamps
        
        # Create timeline visualization
        vis = await progress_tracker.create_visualization(
            item_id="test_item",
            visualization_type="progress_timeline"
        )
        
        assert vis["type"] == "progress_timeline"
        assert "image" in vis
        assert "data" in vis
        assert len(vis["data"]) >= 5
    
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
        assert len(new_tracker.notifications) == 1
```

Now, let's implement the `InterventionInterface`, which is Work Unit 5.2:

```python
from typing import Dict, List, Optional, Any, Union, Callable
import logging
from enum import Enum
from dataclasses import dataclass, field
import asyncio
import json
from datetime import datetime
import os
from pathlib import Path
import hashlib
import base64

logger = logging.getLogger(__name__)

class InterventionLevel(Enum):
    """Levels of intervention."""
    INFORMATION = "information"  # Just inform, no action needed
    SUGGESTION = "suggestion"    # Suggest action, but system can proceed
    WARNING = "warning"          # Potential issue, human should check
    CRITICAL = "critical"        # Serious issue, requires human decision
    EMERGENCY = "emergency"      # System-threatening issue, must stop

class InterventionStatus(Enum):
    """Status of an intervention request."""
    PENDING = "pending"      # Awaiting response
    APPROVED = "approved"    # Action approved
    REJECTED = "rejected"    # Action rejected
    MODIFIED = "modified"    # Action approved with modifications
    ESCALATED = "escalated"  # Escalated to higher authority
    TIMEOUT = "timeout"      # No response within time limit
    CLOSED = "closed"        # Intervention closed without action

class ResponseAction(Enum):
    """Possible actions that can be taken in response to an intervention."""
    CONTINUE = "continue"    # Continue with planned action
    MODIFY = "modify"        # Continue with modifications
    CANCEL = "cancel"        # Cancel the planned action
    RESTART = "restart"      # Restart the process
    ESCALATE = "escalate"    # Escalate to higher authority
    PAUSE = "pause"          # Pause for further analysis

@dataclass
class InterventionContext:
    """Context information for an intervention."""
    component: str
    operation: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    related_items: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    system_state: Dict[str, Any] = field(default_factory=dict)
    decision_factors: Dict[str, Any] = field(default_factory=dict)

@dataclass
class InterventionRequest:
    """A request for human intervention."""
    title: str
    description: str
    level: InterventionLevel
    context: InterventionContext
    options: List[ResponseAction]
    timeout: Optional[int] = None  # Timeout in seconds
    required_role: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "title": self.title,
            "description": self.description,
            "level": self.level.value if isinstance(self.level, Enum) else self.level,
            "context": {
                "component": self.context.component,
                "operation": self.context.operation,
                "timestamp": self.context.timestamp,
                "related_items": self.context.related_items,
                "metrics": self.context.metrics,
                "system_state": self.context.system_state,
                "decision_factors": self.context.decision_factors
            },
            "options": [opt.value if isinstance(opt, Enum) else opt for opt in self.options],
            "timeout": self.timeout,
            "required_role": self.required_role
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InterventionRequest':
        """Create from dictionary."""
        context_data = data.get("context", {})
        
        context = InterventionContext(
            component=context_data.get("component", "unknown"),
            operation=context_data.get("operation", "unknown"),
            timestamp=context_data.get("timestamp", datetime.now().isoformat()),
            related_items=context_data.get("related_items", []),
            metrics=context_data.get("metrics", {}),
            system_state=context_data.get("system_state", {}),
            decision_factors=context_data.get("decision_factors", {})
        )
        
        options = [
            ResponseAction(opt) if isinstance(opt, str) else opt
            for opt in data.get("options", [])
        ]
        
        level_val = data.get("level", "information")
        level = InterventionLevel(level_val) if isinstance(level_val, str) else level_val
        
        return cls(
            title=data.get("title", "Untitled Intervention"),
            description=data.get("description", ""),
            level=level,
            context=context,
            options=options,
            timeout=data.get("timeout"),
            required_role=data.get("required_role")
        )

@dataclass
class InterventionResponse:
    """A response to an intervention request."""
    action: ResponseAction
    notes: Optional[str] = None
    modifications: Optional[Dict[str, Any]] = None
    responder: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "action": self.action.value if isinstance(self.action, Enum) else self.action,
            "notes": self.notes,
            "modifications": self.modifications,
            "responder": self.responder,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InterventionResponse':
        """Create from dictionary."""
        action_val = data.get("action", "continue")
        action = ResponseAction(action_val) if isinstance(action_val, str) else action_val
        
        return cls(
            action=action,
            notes=data.get("notes"),
            modifications=data.get("modifications"),
            responder=data.get("responder"),
            timestamp=data.get("timestamp", datetime.now().isoformat())
        )

class InterventionInterface:
    """Interface for human intervention in system operations."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize with optional configuration."""
        self.config = config or {
            "auto_approve_level": InterventionLevel.INFORMATION,
            "default_timeout": 3600,  # 1 hour
            "notification_channels": ["console"],
            "storage_path": "data/interventions",
            "require_authentication": True,
            "allowed_roles": ["operator", "supervisor", "admin"]
        }
        
        self.interventions: Dict[str, Dict[str, Any]] = {}
        self.response_callbacks: Dict[str, List[Callable]] = {}
        self.notification_handlers: Dict[str, Callable] = self._register_notification_handlers()
        
    def _register_notification_handlers(self) -> Dict[str, Callable]:
        """Register handlers for different notification channels."""
        return {
            "console": self._notify_console,
            "email": self._notify_email,
            "slack": self._notify_slack,
            "webhook": self._notify_webhook
        }
    
    async def request_intervention(self, 
                                 request: InterventionRequest) -> Dict[str, Any]:
        """Request human intervention."""
        logger.info(f"Intervention requested: {request.title}")
        
        # Generate unique ID
        intervention_id = self._generate_intervention_id(request)
        
        # Check for auto-approval
        auto_approve = (request.level == InterventionLevel.INFORMATION and 
                       self.config.get("auto_approve_level") == InterventionLevel.INFORMATION)
        
        # Create intervention record
        intervention = {
            "id": intervention_id,
            "request": request.to_dict(),
            "status": InterventionStatus.APPROVED.value if auto_approve else InterventionStatus.PENDING.value,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "response": None,
            "timeout_task": None
        }
        
        # Store intervention
        self.interventions[intervention_id] = intervention
        
        # Save to storage
        await self._save_intervention(intervention_id)
        
        # Auto-respond if appropriate
        if auto_approve:
            response = InterventionResponse(
                action=ResponseAction.CONTINUE,
                notes="Auto-approved informational intervention",
                responder="system"
            )
            
            intervention["response"] = response.to_dict()
            intervention["status"] = InterventionStatus.APPROVED.value
            intervention["updated_at"] = datetime.now().isoformat()
            
            # Save updated intervention
            await self._save_intervention(intervention_id)
            
            return {
                "intervention_id": intervention_id,
                "status": intervention["status"],
                "auto_approved": True,
                "response": intervention["response"]
            }
        
        # Start timeout task if timeout specified
        timeout = request.timeout or self.config.get("default_timeout")
        if timeout:
            timeout_task = asyncio.create_task(
                self._handle_timeout(intervention_id, timeout)
            )
            intervention["timeout_task"] = timeout_task
        
        # Send notifications
        await self._send_notifications(intervention_id)
        
        return {
            "intervention_id": intervention_id,
            "status": intervention["status"],
            "auto_approved": False,
            "expiration": (datetime.now() + timedelta(seconds=timeout)).isoformat() if timeout else None
        }
    
    async def respond_to_intervention(self,
                                    intervention_id: str,
                                    response: InterventionResponse) -> Dict[str, Any]:
        """Respond to an intervention request."""
        logger.info(f"Response received for intervention {intervention_id}")
        
        if intervention_id not in self.interventions:
            raise ValueError(f"Unknown intervention ID: {intervention_id}")
        
        intervention = self.interventions[intervention_id]
        
        # Check if already resolved
        if intervention["status"] not in [
            InterventionStatus.PENDING.value,
            InterventionStatus.ESCALATED.value
        ]:
            raise ValueError(f"Intervention {intervention_id} already resolved with status {intervention['status']}")
        
        # Update intervention
        intervention["response"] = response.to_dict()
        intervention["updated_at"] = datetime.now().isoformat()
        
        # Map action to status
        status_map = {
            ResponseAction.CONTINUE: InterventionStatus.APPROVED,
            ResponseAction.MODIFY: InterventionStatus.MODIFIED,
            ResponseAction.CANCEL: InterventionStatus.REJECTED,
            ResponseAction.RESTART: InterventionStatus.MODIFIED,
            ResponseAction.ESCALATE: InterventionStatus.ESCALATED,
            ResponseAction.PAUSE: InterventionStatus.PENDING
        }
        
        intervention["status"] = status_map.get(
            response.action, 
            InterventionStatus.PENDING
        ).value
        
        # Cancel timeout task if running
        if "timeout_task" in intervention and intervention["timeout_task"]:
            intervention["timeout_task"].cancel()
            intervention["timeout_task"] = None
        
        # Save updated intervention
        await self._save_intervention(intervention_id)
        
        # Execute callbacks
        await self._execute_callbacks(intervention_id, response)
        
        return {
            "intervention_id": intervention_id,
            "status": intervention["status"],
            "response": intervention["response"]
        }
    
    async def get_intervention(self, intervention_id: str) -> Dict[str, Any]:
        """Get details of an intervention."""
        if intervention_id not in self.interventions:
            # Try to load from storage
            try:
                await self._load_intervention(intervention_id)
            except FileNotFoundError:
                raise ValueError(f"Unknown intervention ID: {intervention_id}")
        
        intervention = self.interventions[intervention_id]
        
        # Remove internal fields
        result = {k: v for k, v in intervention.items() if k != "timeout_task"}
        
        return result
    
    async def get_pending_interventions(self, role: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all pending interventions, optionally filtered by required role."""
        result = []
        
        for intervention_id, intervention in self.interventions.items():
            if intervention["status"] != InterventionStatus.PENDING.value:
                continue
                
            if role and intervention["request"].get("required_role") and intervention["request"]["required_role"] != role:
                continue
                
            # Remove internal fields
            filtered = {k: v for k, v in intervention.items() if k != "timeout_task"}
            result.append(filtered)
        
        return result
    
    async def register_callback(self, 
                              intervention_id: str,
                              callback: Callable) -> None:
        """Register a callback for when an intervention receives a response."""
        if intervention_id not in self.response_callbacks:
            self.response_callbacks[intervention_id] = []
            
        self.response_callbacks[intervention_id].append(callback)
    
    async def close_intervention(self, 
                               intervention_id: str,
                               status: InterventionStatus = InterventionStatus.CLOSED,
                               notes: Optional[str] = None) -> Dict[str, Any]:
        """Close an intervention without a formal response."""
        if intervention_id not in self.interventions:
            raise ValueError(f"Unknown intervention ID: {intervention_id}")
        
        intervention = self.interventions[intervention_id]
        
        # Update intervention
        intervention["status"] = status.value if isinstance(status, Enum) else status
        intervention["updated_at"] = datetime.now().isoformat()
        
        if notes:
            if not intervention["response"]:
                intervention["response"] = {
                    "notes": notes,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                intervention["response"]["notes"] = notes
        
        # Cancel timeout task if running
        if "timeout_task" in intervention and intervention["timeout_task"]:
            intervention["timeout_task"].cancel()
            intervention["timeout_task"] = None
        
        # Save updated intervention
        await self._save_intervention(intervention_id)
        
        return {
            "intervention_id": intervention_id,
            "status": intervention["status"],
            "response": intervention["response"]
        }
    
    def _generate_intervention_id(self, request: InterventionRequest) -> str:
        """Generate a unique ID for an intervention request."""
        # Create a hash of key content
        hash_input = f"{request.title}:{request.description}:{datetime.now().isoformat()}"
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()
        
        return f"int_{hash_value[:10]}"
    
    async def _handle_timeout(self, intervention_id: str, timeout: int) -> None:
        """Handle timeout for an intervention."""
        try:
            await asyncio.sleep(timeout)
            
            # Check if intervention still exists and is pending
            if (intervention_id in self.interventions and 
                self.interventions[intervention_id]["status"] == InterventionStatus.PENDING.value):
                
                logger.warning(f"Intervention {intervention_id} timed out after {timeout} seconds")
                
                # Update status
                await self.close_intervention(
                    intervention_id,
                    status=InterventionStatus.TIMEOUT,
                    notes=f"Intervention timed out after {timeout} seconds"
                )
                
        except asyncio.CancelledError:
            # Task was cancelled, likely because a response was received
            pass
        except Exception as e:
            logger.error(f"Error in timeout handler for {intervention_id}: {str(e)}")
    
    async def _send_notifications(self, intervention_id: str) -> None:
        """Send notifications for a new intervention request."""
        intervention = self.interventions[intervention_id]
        channels = self.config.get("notification_channels", ["console"])
        
        for channel in channels:
            if channel in self.notification_handlers:
                try:
                    await self.notification_handlers[channel](intervention)
                except Exception as e:
                    logger.error(f"Error sending {channel} notification: {
CCCCC

Let me continue with the implementation of the Intervention Interface and its unit tests.

```python
# Continuing InterventionInterface class implementation

    async def _send_notifications(self, intervention_id: str) -> None:
        """Send notifications for a new intervention request."""
        intervention = self.interventions[intervention_id]
        channels = self.config.get("notification_channels", ["console"])
        
        for channel in channels:
            if channel in self.notification_handlers:
                try:
                    await self.notification_handlers[channel](intervention)
                except Exception as e:
                    logger.error(f"Error sending {channel} notification: {str(e)}")
    
    async def _execute_callbacks(self, 
                               intervention_id: str,
                               response: InterventionResponse) -> None:
        """Execute registered callbacks for an intervention."""
        if intervention_id not in self.response_callbacks:
            return
            
        for callback in self.response_callbacks[intervention_id]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(intervention_id, response)
                else:
                    callback(intervention_id, response)
            except Exception as e:
                logger.error(f"Error executing callback for {intervention_id}: {str(e)}")
    
    async def _save_intervention(self, intervention_id: str) -> None:
        """Save intervention to storage."""
        if "storage_path" not in self.config:
            logger.warning("No storage path configured, intervention not saved")
            return
            
        storage_path = self.config["storage_path"]
        os.makedirs(storage_path, exist_ok=True)
        
        file_path = os.path.join(storage_path, f"{intervention_id}.json")
        
        # Create a copy without the timeout task
        intervention = self.interventions[intervention_id]
        save_data = {k: v for k, v in intervention.items() if k != "timeout_task"}
        
        with open(file_path, 'w') as f:
            json.dump(save_data, f, indent=2)
            
        logger.debug(f"Intervention {intervention_id} saved to {file_path}")
    
    async def _load_intervention(self, intervention_id: str) -> None:
        """Load intervention from storage."""
        if "storage_path" not in self.config:
            raise FileNotFoundError(f"No storage path configured")
            
        storage_path = self.config["storage_path"]
        file_path = os.path.join(storage_path, f"{intervention_id}.json")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Intervention file not found: {file_path}")
            
        with open(file_path, 'r') as f:
            data = json.load(f)
            
        # Convert status string to enum if needed
        if "status" in data and isinstance(data["status"], str):
            try:
                # Keep as string, will be converted when needed
                pass
            except ValueError:
                logger.warning(f"Invalid status value: {data['status']}")
        
        # Store in interventions dict
        self.interventions[intervention_id] = data
        
        logger.debug(f"Intervention {intervention_id} loaded from {file_path}")
    
    async def _notify_console(self, intervention: Dict[str, Any]) -> None:
        """Send console notification."""
        request = intervention["request"]
        level = request["level"]
        
        message = (
            f"\n{'!' * 40}\n"
            f"INTERVENTION REQUIRED: {request['title']}\n"
            f"Level: {level}\n"
            f"ID: {intervention['id']}\n"
            f"Description: {request['description']}\n"
            f"{'!' * 40}\n"
        )
        
        logger.warning(message)
        print(message)  # Direct console output
    
    async def _notify_email(self, intervention: Dict[str, Any]) -> None:
        """Send email notification."""
        # Email notification implementation
        # Would integrate with email service
        logger.info(f"Email notification would be sent for {intervention['id']}")
    
    async def _notify_slack(self, intervention: Dict[str, Any]) -> None:
        """Send Slack notification."""
        # Slack notification implementation
        # Would integrate with Slack API
        logger.info(f"Slack notification would be sent for {intervention['id']}")
    
    async def _notify_webhook(self, intervention: Dict[str, Any]) -> None:
        """Send webhook notification."""
        # Webhook notification implementation
        # Would make HTTP request to configured webhook URL
        logger.info(f"Webhook notification would be sent for {intervention['id']}")
```

Now, let's implement the unit tests for the Intervention Interface:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
import json
import os
import tempfile
from datetime import datetime, timedelta

@pytest.fixture
def intervention_interface():
    """Create an InterventionInterface instance for testing."""
    return InterventionInterface(config={
        "auto_approve_level": InterventionLevel.INFORMATION,
        "default_timeout": 0.5,  # Fast for testing
        "notification_channels": ["console"],
        "storage_path": tempfile.mkdtemp(),
        "require_authentication": False
    })

@pytest.fixture
def sample_context():
    """Create a sample intervention context for testing."""
    return InterventionContext(
        component="test_component",
        operation="test_operation",
        related_items=["item1", "item2"],
        metrics={"progress": 50},
        system_state={"status": "running"},
        decision_factors={"risk": "low"}
    )

@pytest.fixture
def sample_request(sample_context):
    """Create a sample intervention request for testing."""
    return InterventionRequest(
        title="Test Intervention",
        description="This is a test intervention",
        level=InterventionLevel.WARNING,
        context=sample_context,
        options=[
            ResponseAction.CONTINUE,
            ResponseAction.MODIFY,
            ResponseAction.CANCEL
        ],
        timeout=1  # Fast for testing
    )

class TestInterventionInterface:
    """Test suite for InterventionInterface."""
    
    @pytest.mark.asyncio
    async def test_request_intervention(self, intervention_interface, sample_request):
        """Test intervention request."""
        # Create intervention
        result = await intervention_interface.request_intervention(sample_request)
        
        assert "intervention_id" in result
        assert result["status"] == InterventionStatus.PENDING.value
        assert not result["auto_approved"]
        assert "expiration" in result
        
        # Verify intervention is stored
        intervention_id = result["intervention_id"]
        assert intervention_id in intervention_interface.interventions
        
        # Verify details
        intervention = intervention_interface.interventions[intervention_id]
        assert intervention["request"]["title"] == "Test Intervention"
        assert intervention["request"]["level"] == "warning"
        assert intervention["status"] == InterventionStatus.PENDING.value
    
    @pytest.mark.asyncio
    async def test_auto_approve(self, intervention_interface, sample_context):
        """Test auto-approval for information-level interventions."""
        # Create info-level request
        info_request = InterventionRequest(
            title="Info Intervention",
            description="This is an info intervention",
            level=InterventionLevel.INFORMATION,
            context=sample_context,
            options=[ResponseAction.CONTINUE]
        )
        
        # Request intervention
        result = await intervention_interface.request_intervention(info_request)
        
        assert result["auto_approved"]
        assert result["status"] == InterventionStatus.APPROVED.value
        assert result["response"]["action"] == "continue"
    
    @pytest.mark.asyncio
    async def test_respond_to_intervention(self, intervention_interface, sample_request):
        """Test responding to an intervention."""
        # Create intervention
        request_result = await intervention_interface.request_intervention(sample_request)
        intervention_id = request_result["intervention_id"]
        
        # Create response
        response = InterventionResponse(
            action=ResponseAction.MODIFY,
            notes="Test modification",
            modifications={"parameter": "new_value"},
            responder="test_user"
        )
        
        # Submit response
        result = await intervention_interface.respond_to_intervention(
            intervention_id,
            response
        )
        
        assert result["status"] == InterventionStatus.MODIFIED.value
        assert result["response"]["action"] == "modify"
        assert result["response"]["notes"] == "Test modification"
        assert result["response"]["modifications"]["parameter"] == "new_value"
        
        # Verify intervention updated
        intervention = intervention_interface.interventions[intervention_id]
        assert intervention["status"] == InterventionStatus.MODIFIED.value
    
    @pytest.mark.asyncio
    async def test_timeout(self, intervention_interface, sample_request):
        """Test intervention timeout."""
        # Reduce timeout for faster testing
        sample_request.timeout = 0.2
        
        # Create intervention
        request_result = await intervention_interface.request_intervention(sample_request)
        intervention_id = request_result["intervention_id"]
        
        # Wait for timeout
        await asyncio.sleep(0.3)
        
        # Verify timeout status
        intervention = intervention_interface.interventions[intervention_id]
        assert intervention["status"] == InterventionStatus.TIMEOUT.value
    
    @pytest.mark.asyncio
    async def test_get_intervention(self, intervention_interface, sample_request):
        """Test getting intervention details."""
        # Create intervention
        request_result = await intervention_interface.request_intervention(sample_request)
        intervention_id = request_result["intervention_id"]
        
        # Get details
        details = await intervention_interface.get_intervention(intervention_id)
        
        assert details["id"] == intervention_id
        assert details["request"]["title"] == "Test Intervention"
        assert details["status"] == InterventionStatus.PENDING.value
        assert "timeout_task" not in details  # Internal field should be excluded
    
    @pytest.mark.asyncio
    async def test_get_pending_interventions(self, intervention_interface, sample_request):
        """Test getting pending interventions."""
        # Create several interventions
        await intervention_interface.request_intervention(sample_request)
        
        # Create an info request that will be auto-approved
        info_request = InterventionRequest(
            title="Info Intervention",
            description="This is an info intervention",
            level=InterventionLevel.INFORMATION,
            context=sample_request.context,
            options=[ResponseAction.CONTINUE]
        )
        await intervention_interface.request_intervention(info_request)
        
        # Create another pending request
        warning_request = InterventionRequest(
            title="Warning Intervention",
            description="This is a warning intervention",
            level=InterventionLevel.WARNING,
            context=sample_request.context,
            options=[ResponseAction.CONTINUE, ResponseAction.CANCEL],
            required_role="supervisor"
        )
        await intervention_interface.request_intervention(warning_request)
        
        # Get all pending interventions
        pending = await intervention_interface.get_pending_interventions()
        assert len(pending) == 2  # The warning and the original request
        
        # Filter by role
        pending_for_supervisor = await intervention_interface.get_pending_interventions(role="supervisor")
        assert len(pending_for_supervisor) == 1
        assert pending_for_supervisor[0]["request"]["title"] == "Warning Intervention"
    
    @pytest.mark.asyncio
    async def test_callbacks(self, intervention_interface, sample_request):
        """Test intervention callbacks."""
        # Create intervention
        request_result = await intervention_interface.request_intervention(sample_request)
        intervention_id = request_result["intervention_id"]
        
        # Setup mock callback
        callback = AsyncMock()
        await intervention_interface.register_callback(intervention_id, callback)
        
        # Create response
        response = InterventionResponse(
            action=ResponseAction.CONTINUE,
            notes="Test response",
            responder="test_user"
        )
        
        # Submit response
        await intervention_interface.respond_to_intervention(
            intervention_id,
            response
        )
        
        # Verify callback called
        callback.assert_called_once()
        assert callback.call_args[0][0] == intervention_id
    
    @pytest.mark.asyncio
    async def test_close_intervention(self, intervention_interface, sample_request):
        """Test closing an intervention."""
        # Create intervention
        request_result = await intervention_interface.request_intervention(sample_request)
        intervention_id = request_result["intervention_id"]
        
        # Close intervention
        result = await intervention_interface.close_intervention(
            intervention_id,
            status=InterventionStatus.CLOSED,
            notes="Closed manually"
        )
        
        assert result["status"] == InterventionStatus.CLOSED.value
        assert "notes" in result["response"]
        assert result["response"]["notes"] == "Closed manually"
        
        # Verify intervention updated
        intervention = intervention_interface.interventions[intervention_id]
        assert intervention["status"] == InterventionStatus.CLOSED.value
    
    @pytest.mark.asyncio
    async def test_save_load_intervention(self, intervention_interface, sample_request, tmpdir):
        """Test saving and loading interventions."""
        # Set storage path
        intervention_interface.config["storage_path"] = str(tmpdir)
        
        # Create intervention
        request_result = await intervention_interface.request_intervention(sample_request)
        intervention_id = request_result["intervention_id"]
        
        # Verify file created
        file_path = os.path.join(str(tmpdir), f"{intervention_id}.json")
        assert os.path.exists(file_path)
        
        # Create new interface
        new_interface = InterventionInterface(config={
            "storage_path": str(tmpdir)
        })
        
        # Load intervention
        await new_interface._load_intervention(intervention_id)
        
        # Verify loaded correctly
        assert intervention_id in new_interface.interventions
        assert new_interface.interventions[intervention_id]["request"]["title"] == "Test Intervention"
```

Now, let's explain how these components connect to the Self-Aware Cerebrum system and the previous phases:

## Integration with Previous Phases

### ProgressTracker (Work Unit 5.1)

The `ProgressTracker` serves as the primary monitoring tool for the system, connecting to several components from previous phases:

1. **Connection to Execution Engine (Phase 3)**:
   - Integrates with the `ExecutionTracker` from Work Unit 3.4 to monitor task execution progress
   - Receives data from the `ParallelExecutionController` (Work Unit 3.3) to track parallel task execution
   - Uses the task structure from the `TaskSelector` (Work Unit 3.1) to organize tracking hierarchically

2. **Connection to Planning Engine (Phase 2)**:
   - Tracks progress against goals defined by the `GoalDecompositionEngine` (Work Unit 2.1)
   - Monitors research tasks from the `ResearchPlanner` (Work Unit 2.2)
   - Tracks implementation plans from the `ImplementationPlanner` (Work Unit 2.3)
   - Connects to the `ResourceAllocationManager` (Work Unit 2.4) to monitor resource usage

3. **Connection to Self-Modification Engine (Phase 4)**:
   - Monitors the progress of self-modification tasks from the `AgenticDevelopmentController` (Work Unit 4.4)
   - Tracks the status of system modifications processed by the `IntegrationManager` (Work Unit 4.3)
   - Monitors safety validations performed by the `SafetyValidator` (Work Unit 4.2)

Key integration points include:
- The `register_item` method allows any component to register plans, tasks, or other items for tracking
- The parent-child relationship enables hierarchical tracking aligned with the goal decomposition structure
- The visualization capabilities provide insights into system execution across all components
- The notification system alerts about issues in any phase of the system

### InterventionInterface (Work Unit 5.2)

The `InterventionInterface` acts as the bridge between the autonomous system and human supervisors, connecting with:

1. **Connection to Self-Modification Engine (Phase 4)**:
   - Integrates with the `SafetyValidator` (Work Unit 4.2) to request approvals for risky code changes
   - Connects to the `IntegrationManager` (Work Unit 4.3) for human approval before applying changes
   - Provides intervention points for the `CodeGenerator` (Work Unit 4.1) when generating significant code changes
   - Works with the `SystemAccessLayer` (Work Unit 4.5) to control sensitive system operations

2. **Connection to Execution Engine (Phase 3)**:
   - Allows the `ParallelExecutionController` (Work Unit 3.3) to request intervention when execution issues arise
   - Integrates with the `ExecutionTracker` (Work Unit 3.4) to trigger interventions based on execution metrics
   - Provides a way for the system to pause or modify task execution based on human input

3. **Connection to Planning Engine (Phase 2)**:
   - Enables the `GoalDecompositionEngine` (Work Unit 2.1) to verify goal understanding with humans
   - Allows the `ImplementationPlanner` (Work Unit 2.3) to confirm implementation approaches
   - Helps the `ResourceAllocationManager` (Work Unit 2.4) to request additional resources when needed

Key integration points include:
- The intervention request/response cycle enables components to seek human guidance when needed
- Different intervention levels allow for appropriate responses based on severity
- The callback mechanism ensures that requesting components can react to human decisions
- The timeout handling prevents system blockage if humans don't respond in time

## System Architecture Impact

These two components form the foundation of the Observability Layer, which provides:

1. **Transparency**: Making system operations visible and understandable to humans
2. **Control**: Enabling appropriate human intervention in autonomous operations
3. **Accountability**: Tracking system actions and decisions for review and analysis
4. **Safety**: Preventing harmful actions through human oversight
5. **Collaboration**: Facilitating human-AI collaboration through structured interaction

Together, they create a comprehensive observability framework that connects to all previous phases, ensuring the system remains transparent and controllable while maintaining its autonomous capabilities.

The next units in Phase 5 (Multi-Human Supervision Hub, Budget & Resource Monitor, Metrics Collector, and Observability Integration) will build upon these foundations to create a complete observability ecosystem.
