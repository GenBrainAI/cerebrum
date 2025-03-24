from typing import List, Dict, Set, Optional, Any, Tuple, Callable
from enum import Enum
from dataclasses import dataclass, field
import uuid
from datetime import datetime, timedelta
import json
import logging
import threading
import time
import os
import csv
from collections import defaultdict
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

# Import components from previous work units
from server.execution_engine.task_selector import TaskSelector, Task, TaskStatus, TaskPriority
from server.execution_engine.context_manager import ContextManager, ContextType
from server.execution_engine.parallel_execution_controller import ParallelExecutionController, ExecutionResult, ExecutionMode

logger = logging.getLogger(__name__)

class TrackingLevel(Enum):
    MINIMAL = "minimal"  # Basic task status only
    STANDARD = "standard"  # Task status, timing, and basic metrics
    DETAILED = "detailed"  # Full execution details including context and resources
    DEBUG = "debug"  # All possible information for debugging

@dataclass
class ExecutionMetrics:
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    running_tasks: int = 0
    blocked_tasks: int = 0
    pending_tasks: int = 0
    total_execution_time: float = 0.0  # in seconds
    average_execution_time: float = 0.0  # in seconds
    resource_utilization: Dict[str, float] = field(default_factory=dict)
    success_rate: float = 0.0  # percentage
    throughput: float = 0.0  # tasks per minute
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_duration: float = 0.0  # in seconds
    
    def update_derived_metrics(self):
        """Update metrics that are derived from other metrics."""
        self.success_rate = (self.completed_tasks / self.total_tasks * 100) if self.total_tasks > 0 else 0
        self.average_execution_time = (self.total_execution_time / self.completed_tasks) if self.completed_tasks > 0 else 0
        
        if self.start_time and self.end_time:
            self.total_duration = (self.end_time - self.start_time).total_seconds()
            minutes = self.total_duration / 60
            self.throughput = (self.completed_tasks / minutes) if minutes > 0 else 0

class AlertRule:
    """
    Rule for generating alerts based on execution metrics or events.
    """
    def __init__(self, name: str, condition: Callable[..., bool], 
                message_template: str, alert_type: str = "info",
                cooldown_period: float = 60):  # cooldown in seconds
        self.name = name
        self.condition = condition
        self.message_template = message_template
        self.alert_type = alert_type  # "info", "warning", "error", "critical"
        self.cooldown_period = cooldown_period
        self.last_triggered = None
        self.trigger_count = 0
    
    def check(self, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Check if the rule condition is met and generate an alert if needed.
        Returns alert data if triggered, None otherwise.
        """
        now = datetime.now()
        
        # Check cooldown period
        if self.last_triggered:
            elapsed = (now - self.last_triggered).total_seconds()
            if elapsed < self.cooldown_period:
                return None
        
        # Check condition
        if self.condition(**kwargs):
            self.last_triggered = now
            self.trigger_count += 1
            
            # Generate message from template
            try:
                message = self.message_template.format(**kwargs)
            except KeyError:
                message = f"Alert triggered: {self.name}"
            
            return {
                "rule_name": self.name,
                "type": self.alert_type,
                "message": message,
                "timestamp": now.isoformat(),
                "trigger_count": self.trigger_count
            }
        
        return None

class ExecutionTracker:
    """
    Tracks and monitors task execution, including progress monitoring,
    failure detection, performance metrics collection, and reporting.
    """
    
    def __init__(self, task_selector: TaskSelector, context_manager: ContextManager,
                execution_controller: ParallelExecutionController, 
                tracking_level: TrackingLevel = TrackingLevel.STANDARD,
                output_dir: str = None):
        self.task_selector = task_selector
        self.context_manager = context_manager
        self.execution_controller = execution_controller
        self.tracking_level = tracking_level
        self.output_dir = output_dir or os.getcwd()
        
        # Tracking state
        self.is_tracking = False
        self.tracking_thread = None
        self.thread_lock = threading.Lock()
        self.tracking_interval = 1.0  # seconds
        
        # Execution history and metrics
        self.execution_history = []  # List of execution events
        self.task_durations = {}  # task_id -> duration
        self.metrics_history = []  # List of metric snapshots
        self.error_log = []  # List of error events
        self.alert_rules = []  # List of alert rules
        self.alert_history = []  # List of triggered alerts
        self.alert_counters = defaultdict(int)  # rule_name -> count
        self.task_status_history = defaultdict(list)  # task_id -> list of (timestamp, status) tuples
        
        # Register default alert rules
        self._register_default_alert_rules()
        
        logger.info(f"Execution tracker initialized with tracking level: {tracking_level.value}")
    
    def _register_default_alert_rules(self):
        """Register default alert rules."""
        self.register_alert_rule(
            name="high_failure_rate",
            condition=lambda metrics, **kwargs: metrics.success_rate < 70 and metrics.total_tasks > 5,
            message_template="High failure rate detected: {metrics.success_rate:.1f}% success rate across {metrics.total_tasks} tasks",
            alert_type="warning",
            cooldown_period=300  # 5 minutes
        )
        
        self.register_alert_rule(
            name="task_failure",
            condition=lambda metrics, task_id, task_result, **kwargs: not task_result.success,
            message_template="Task {task_id} failed: {task_result.error}",
            alert_type="error",
            cooldown_period=60  # 1 minute
        )
        
        self.register_alert_rule(
            name="long_execution",
            condition=lambda metrics, task_id, task_result, **kwargs: task_result.duration > 300,  # 5 minutes
            message_template="Task {task_id} took too long: {task_result.duration:.1f} seconds",
            alert_type="warning",
            cooldown_period=120  # 2 minutes
        )
        
        self.register_alert_rule(
            name="high_resource_usage",
            condition=lambda metrics, task_id, task_result, **kwargs: any(usage > 0.9 for usage in task_result.resource_usage.values()),
            message_template="High resource usage detected for task {task_id}",
            alert_type="warning",
            cooldown_period=180  # 3 minutes
        )
    
    def register_alert_rule(self, name: str, condition: Callable[..., bool], 
                          message_template: str, alert_type: str = "info",
                          cooldown_period: float = 60):
        """Register a new alert rule."""
        rule = AlertRule(
            name=name,
            condition=condition,
            message_template=message_template,
            alert_type=alert_type,
            cooldown_period=cooldown_period
        )
        self.alert_rules.append(rule)
        logger.debug(f"Registered alert rule: {name}")
    
    def start_tracking(self):
        """Start tracking task execution."""
        if self.is_tracking:
            logger.warning("Tracking is already active")
            return
        
        with self.thread_lock:
            # Record start event
            self._record_execution_event({
                "event_type": "tracking_started",
                "timestamp": datetime.now()
            })
            
            # Start tracking thread
            self.is_tracking = True
            self.tracking_thread = threading.Thread(target=self._tracking_loop)
            self.tracking_thread.daemon = True  # Thread will be terminated when main program exits
            self.tracking_thread.start()
            
            # Wait for thread to start
            time.sleep(0.1)  # Give the thread a moment to start
            
            logger.info("Execution tracking started")
    
    def stop_tracking(self):
        """Stop tracking task execution."""
        if not self.is_tracking:
            return
        
        with self.thread_lock:
            # Signal thread to stop
            self.is_tracking = False
            
            # Wait for thread to finish
            if self.tracking_thread and self.tracking_thread.is_alive():
                self.tracking_thread.join(timeout=5.0)  # Wait up to 5 seconds
                
                # If thread is still alive after timeout, log a warning
                if self.tracking_thread.is_alive():
                    logger.warning("Tracking thread did not stop within timeout period")
            
            # Record stop event
            self._record_execution_event({
                "event_type": "tracking_stopped",
                "timestamp": datetime.now()
            })
            
            logger.info("Execution tracking stopped")
    
    def _tracking_loop(self):
        """Main tracking loop that monitors task execution."""
        try:
            while self.is_tracking:
                # Get current metrics
                metrics = self.get_current_metrics()
                
                # Record metrics
                self.metrics_history.append({
                    "timestamp": datetime.now(),
                    "metrics": self._metrics_to_dict(metrics)
                })
                
                # Check alert rules with no specific task
                try:
                    self._check_alert_rules(metrics=metrics, task_id=None, result=None)
                except Exception as e:
                    logger.error(f"Error checking alert rules: {e}")
                
                # Sleep for tracking interval
                time.sleep(self.tracking_interval)
                
        except Exception as e:
            logger.error(f"Error in tracking loop: {e}")
            self.error_log.append({
                "timestamp": datetime.now(),
                "error": str(e)
            })
            
        finally:
            # Ensure we're marked as not tracking when the loop exits
            self.is_tracking = False
            
            # Record stop event if not already recorded
            if not any(e.get("event_type") == "tracking_stopped" for e in self.execution_history[-5:]):
                self._record_execution_event({
                    "event_type": "tracking_stopped",
                    "timestamp": datetime.now()
                })
    
    def _update_tracking_data(self):
        """Update tracking data by polling task selector and execution controller."""
        # Get current task status counts
        status_counts = self._get_task_status_counts()
        
        # Get execution results
        running_tasks = self.execution_controller.get_running_tasks()
        
        # Update task status history
        for task_id, task in self.task_selector.tasks.items():
            if task_id not in self.task_status_history:
                self.task_status_history[task_id] = []
            
            # Only add entry if status changed or it's a new task
            status_history = self.task_status_history[task_id]
            if not status_history or status_history[-1][1] != task.status:
                self.task_status_history[task_id].append((datetime.now(), task.status))
        
        # Update task durations for completed tasks
        for task_id, task in self.task_selector.tasks.items():
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                result = self.execution_controller.get_execution_result(task_id)
                if result and task_id not in self.task_durations:
                    self.task_durations[task_id] = result.duration
        
        # Calculate and store metrics
        metrics = self._calculate_metrics(status_counts, running_tasks)
        self.metrics_history.append({
            "timestamp": datetime.now().isoformat(),
            "metrics": self._metrics_to_dict(metrics)
        })
        
        # Update performance history (at lower frequency)
        current_time = datetime.now()
        last_performance_time = max(self.performance_history.keys()) if self.performance_history else None
        
        if not last_performance_time or (current_time - datetime.fromisoformat(last_performance_time)).total_seconds() > 60:
            # Record performance metrics every minute
            perf_metrics = self._get_performance_metrics()
            self.performance_history[current_time.isoformat()] = perf_metrics
            
            # Limit history size
            if len(self.performance_history) > 1440:  # Keep 24 hours of minute-level data
                oldest_key = min(self.performance_history.keys())
                del self.performance_history[oldest_key]
        
        # Record execution event
        self._record_execution_event({
            "timestamp": datetime.now().isoformat(),
            "status_counts": status_counts,
            "running_tasks": running_tasks,
            "metrics": self._metrics_to_dict(metrics)
        })
    
    def _get_task_status_counts(self) -> Dict[str, int]:
        """Get counts of tasks by status."""
        counts = {status.value: 0 for status in TaskStatus}
        
        for task in self.task_selector.tasks.values():
            counts[task.status.value] += 1
        
        return counts
    
    def _calculate_metrics(self, status_counts: Dict[str, int], running_tasks: List[str]) -> ExecutionMetrics:
        """Calculate execution metrics based on current state."""
        metrics = ExecutionMetrics()
        
        # Set basic counts
        metrics.total_tasks = sum(status_counts.values())
        metrics.completed_tasks = status_counts.get(TaskStatus.COMPLETED.value, 0)
        metrics.failed_tasks = status_counts.get(TaskStatus.FAILED.value, 0)
        metrics.running_tasks = status_counts.get(TaskStatus.IN_PROGRESS.value, 0)
        metrics.blocked_tasks = status_counts.get(TaskStatus.BLOCKED.value, 0)
        metrics.pending_tasks = status_counts.get(TaskStatus.PENDING.value, 0) + status_counts.get(TaskStatus.READY.value, 0)
        
        # Calculate execution times
        metrics.total_execution_time = sum(self.task_durations.values())
        
        # Calculate resource utilization (if available)
        if hasattr(self.execution_controller, 'resource_manager'):
            resource_mgr = self.execution_controller.resource_manager
            total_resources = {k: v for k, v in resource_mgr.available_resources.items()}
            used_resources = {}
            
            # Sum up allocated resources
            allocated = resource_mgr.get_allocated_resources()
            for task_resources in allocated.values():
                for res_type, amount in task_resources.items():
                    if res_type not in used_resources:
                        used_resources[res_type] = 0
                    used_resources[res_type] += amount
            
            # Calculate utilization percentages
            for res_type, total in total_resources.items():
                if total > 0:
                    used = used_resources.get(res_type, 0)
                    metrics.resource_utilization[res_type] = (used / total) * 100
        
        # Calculate start and end times
        if self.task_status_history:
            # Find earliest task creation and latest completion
            start_times = []
            end_times = []
            
            for task_id, history in self.task_status_history.items():
                if history:
                    start_times.append(history[0][0])  # First status change timestamp
                    
                    # Check if task is completed or failed
                    if history[-1][1] in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                        end_times.append(history[-1][0])  # Last status change timestamp
            
            if start_times:
                metrics.start_time = min(start_times)
            
            if end_times and len(end_times) == metrics.total_tasks:
                # Only set end time if all tasks are done
                metrics.end_time = max(end_times)
            else:
                metrics.end_time = datetime.now()
        
        # Update derived metrics
        metrics.update_derived_metrics()
        
        return metrics
    
    def _metrics_to_dict(self, metrics: ExecutionMetrics) -> Dict[str, Any]:
        """Convert ExecutionMetrics to a dictionary."""
        return {
            "total_tasks": metrics.total_tasks,
            "completed_tasks": metrics.completed_tasks,
            "failed_tasks": metrics.failed_tasks,
            "running_tasks": metrics.running_tasks,
            "blocked_tasks": metrics.blocked_tasks,
            "pending_tasks": metrics.pending_tasks,
            "total_execution_time": metrics.total_execution_time,
            "average_execution_time": metrics.average_execution_time,
            "resource_utilization": metrics.resource_utilization,
            "success_rate": metrics.success_rate,
            "throughput": metrics.throughput,
            "start_time": metrics.start_time.isoformat() if metrics.start_time else None,
            "end_time": metrics.end_time.isoformat() if metrics.end_time else None,
            "total_duration": metrics.total_duration
        }
    
    def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics."""
        perf_metrics = {}
        
        # Get resource utilization
        if hasattr(self.execution_controller, 'resource_manager'):
            resource_mgr = self.execution_controller.resource_manager
            perf_metrics["resource_utilization"] = {
                res_type: (amount, resource_mgr.available_resources.get(res_type, 0))
                for res_type, amount in resource_mgr.get_allocated_resources().items()
            }
        
        # Get task execution metrics
        execution_times = {}
        for task_id, duration in self.task_durations.items():
            task = self.task_selector.get_task_by_id(task_id)
            if task:
                task_type = task.metadata.get("type", "unknown")
                if task_type not in execution_times:
                    execution_times[task_type] = []
                execution_times[task_type].append(duration)
        
        # Calculate average times by task type
        perf_metrics["avg_execution_by_type"] = {
            task_type: sum(times) / len(times)
            for task_type, times in execution_times.items()
        }
        
        # Get throughput metrics
        current_metrics = self._calculate_metrics(self._get_task_status_counts(), 
                                                self.execution_controller.get_running_tasks())
        perf_metrics["current_throughput"] = current_metrics.throughput
        
        # Get context metrics if in detailed mode
        if self.tracking_level in [TrackingLevel.DETAILED, TrackingLevel.DEBUG]:
            if self.context_manager:
                ctx = self.context_manager.get_current_context()
                perf_metrics["context_size"] = len(ctx)
        
        return perf_metrics
    
    def _record_execution_event(self, event_data: Dict[str, Any]):
        """Record an execution event to history."""
        # Limit history size based on tracking level
        max_events = {
            TrackingLevel.MINIMAL: 100,
            TrackingLevel.STANDARD: 500,
            TrackingLevel.DETAILED: 1000,
            TrackingLevel.DEBUG: 5000
        }
        
        self.execution_history.append(event_data)
        
        # Trim history if needed
        if len(self.execution_history) > max_events[self.tracking_level]:
            self.execution_history = self.execution_history[-max_events[self.tracking_level]:]
    
    def _check_alert_rules(self, metrics: ExecutionMetrics, task_id: str, result: ExecutionResult):
        """Check all alert rules against current metrics and task result."""
        try:
            # Check all rules
            for rule in self.alert_rules:
                kwargs = {
                    "metrics": metrics,
                    "task_id": task_id,
                    "task_result": result
                }
                
                alert = rule.check(**kwargs)
                if alert:
                    self.alert_history.append(alert)
                    self.alert_counters[rule.name] += 1
                    logger.warning(f"Alert triggered: {alert['message']}")
                    
        except Exception as e:
            logger.error(f"Error checking alert rules: {e}")
    
    def track_task_execution(self, task_id: str, result: ExecutionResult):
        """Track the execution of a task and update metrics."""
        try:
            timestamp = datetime.now()
            
            # Convert success to status
            status = TaskStatus.COMPLETED if result.success else TaskStatus.FAILED
            
            # Record task status
            if task_id not in self.task_status_history:
                self.task_status_history[task_id] = []
            self.task_status_history[task_id].append((timestamp, status))
            
            # Record execution event
            event = {
                "timestamp": timestamp,
                "task_id": task_id,
                "status": status.value,
                "duration": result.duration,
                "error": result.error if result.error else None,
                "resource_usage": result.resource_usage
            }
            self.execution_history.append(event)
            
            # Update task duration
            if result.duration is not None:
                self.task_durations[task_id] = result.duration
            
            # Record errors if any
            if result.error:
                self.error_log.append({
                    "timestamp": timestamp,
                    "task_id": task_id,
                    "error": str(result.error)
                })
            
            # Update metrics
            metrics = self.get_current_metrics()
            self.metrics_history.append({
                "timestamp": timestamp,
                "metrics": self._metrics_to_dict(metrics)
            })
            
            # Check alert rules
            self._check_alert_rules(metrics=metrics, task_id=task_id, result=result)
            
        except Exception as e:
            logger.error(f"Error tracking task execution: {e}")
            self.error_log.append({
                "timestamp": datetime.now(),
                "task_id": task_id,
                "error": str(e)
            })
    
    def get_current_metrics(self) -> ExecutionMetrics:
        """Get current execution metrics."""
        return self._calculate_metrics(self._get_task_status_counts(), 
                                     self.execution_controller.get_running_tasks())
    
    def get_task_status_timeline(self, task_id: str) -> List[Dict[str, Any]]:
        """Get the status timeline for a specific task."""
        if task_id not in self.task_status_history:
            return []
        
        return [
            {
                "timestamp": timestamp.isoformat(),
                "status": status.value
            }
            for timestamp, status in self.task_status_history[task_id]
        ]
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get a summary of the execution progress and metrics."""
        try:
            metrics = self.get_current_metrics()
            metrics_dict = self._metrics_to_dict(metrics)
            
            # Calculate success rate
            total_tasks = len(self.task_status_history)
            completed_tasks = sum(1 for history in self.task_status_history.values() 
                                if history and history[-1][1] == TaskStatus.COMPLETED)
            success_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            
            # Get task status counts
            status_counts = defaultdict(int)
            for history in self.task_status_history.values():
                if history:  # Check if there's any history
                    status_counts[history[-1][1].value] += 1
            
            # Get error counts
            error_count = len(self.error_log)
            
            # Get alert counts
            alert_counts = dict(self.alert_counters)
            
            # Calculate average duration
            durations = [duration for duration in self.task_durations.values() if duration is not None]
            avg_duration = sum(durations) / len(durations) if durations else 0
            
            return {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "failed_tasks": metrics_dict["failed_tasks"],
                "running_tasks": metrics_dict["running_tasks"],
                "blocked_tasks": metrics_dict["blocked_tasks"],
                "pending_tasks": metrics_dict["pending_tasks"],
                "status_counts": dict(status_counts),
                "success_rate": success_rate,
                "error_count": error_count,
                "alert_counts": alert_counts,
                "average_execution_time": metrics_dict["average_execution_time"],
                "throughput": metrics_dict["throughput"],
                "resource_utilization": metrics_dict["resource_utilization"],
                "metrics": metrics_dict,
                "tracking_level": self.tracking_level.value
            }
            
        except Exception as e:
            logger.error(f"Error generating execution summary: {e}")
            return {
                "error": str(e),
                "total_tasks": 0,
                "completed_tasks": 0,
                "failed_tasks": 0,
                "running_tasks": 0,
                "blocked_tasks": 0,
                "pending_tasks": 0,
                "status_counts": {},
                "success_rate": 0,
                "error_count": 0,
                "alert_counts": {},
                "average_execution_time": 0,
                "throughput": 0,
                "resource_utilization": {},
                "metrics": {},
                "tracking_level": self.tracking_level.value
            }
    
    def get_task_performance_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get performance statistics for each task type."""
        task_stats = defaultdict(lambda: {
            "count": 0,
            "total_duration": 0,
            "min_duration": float('inf'),
            "max_duration": 0,
            "avg_duration": 0,
            "success_count": 0,
            "failure_count": 0
        })
        
        for event in self.execution_history:
            if "task_id" in event and "duration" in event:
                task = self.task_selector.get_task_by_id(event["task_id"])
                if not task:
                    continue
                
                task_type = str(task.name)  # Use task name as type
                stats = task_stats[task_type]
                duration = event["duration"]
                
                stats["count"] += 1
                stats["total_duration"] += duration
                stats["min_duration"] = min(stats["min_duration"], duration)
                stats["max_duration"] = max(stats["max_duration"], duration)
                stats["avg_duration"] = stats["total_duration"] / stats["count"]
                
                if event["status"] == TaskStatus.COMPLETED.value:
                    stats["success_count"] += 1
                elif event["status"] == TaskStatus.FAILED.value:
                    stats["failure_count"] += 1
        
        # Clean up infinite values
        for stats in task_stats.values():
            if stats["min_duration"] == float('inf'):
                stats["min_duration"] = 0
        
        return dict(task_stats)
    
    def get_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent execution errors."""
        return sorted(self.error_log, key=lambda x: x["timestamp"], reverse=True)[:limit]
    
    def get_resource_utilization_history(self) -> List[Dict[str, Any]]:
        """Get history of resource utilization."""
        result = []
        
        for entry in self.metrics_history:
            if "metrics" in entry and "resource_utilization" in entry["metrics"]:
                result.append({
                    "timestamp": entry["timestamp"],
                    "utilization": entry["metrics"]["resource_utilization"]
                })
        
        return result
    
    def export_metrics_csv(self, filepath: str) -> str:
        """Export metrics history to a CSV file."""
        try:
            # Get all unique metric keys
            columns = {"timestamp"}
            for entry in self.metrics_history:
                if isinstance(entry["metrics"], dict):
                    columns.update(entry["metrics"].keys())
            
            # Write to CSV
            with open(filepath, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=list(columns))
                writer.writeheader()
                
                for entry in self.metrics_history:
                    row = {"timestamp": entry["timestamp"].isoformat() if isinstance(entry["timestamp"], datetime) else entry["timestamp"]}
                    if isinstance(entry["metrics"], dict):
                        row.update(entry["metrics"])
                    writer.writerow(row)
            
            return filepath
            
        except Exception as e:
            logger.error(f"Error exporting metrics CSV: {e}")
            return None
    
    def export_execution_report(self, filepath: str) -> str:
        """Export execution report to a JSON file."""
        try:
            # Get current metrics
            metrics = self.get_current_metrics()
            metrics_dict = self._metrics_to_dict(metrics)
            
            # Get task performance stats
            task_performance = self.get_task_performance_stats()
            
            # Prepare execution history
            execution_history = []
            for event in self.execution_history:
                event_dict = {
                    "timestamp": event["timestamp"].isoformat() if isinstance(event["timestamp"], datetime) else event["timestamp"],
                    "event_type": event.get("event_type", "task_execution")
                }
                
                # Add task-specific fields if present
                if "task_id" in event:
                    event_dict.update({
                        "task_id": event["task_id"],
                        "status": event["status"],
                        "duration": event["duration"],
                        "error": event["error"],
                        "resource_usage": event.get("resource_usage", {})
                    })
                
                execution_history.append(event_dict)
            
            # Prepare metrics history
            metrics_history = [
                {
                    "timestamp": entry["timestamp"].isoformat() if isinstance(entry["timestamp"], datetime) else entry["timestamp"],
                    "metrics": entry["metrics"]
                }
                for entry in self.metrics_history
            ]
            
            # Prepare error log
            error_log = [
                {
                    "timestamp": error["timestamp"].isoformat() if isinstance(error["timestamp"], datetime) else error["timestamp"],
                    "error": error["error"],
                    "task_id": error.get("task_id")
                }
                for error in self.error_log
            ]
            
            # Prepare report
            report = {
                "summary": self.get_execution_summary(),
                "task_performance": task_performance,
                "metrics": metrics_dict,  # Top-level metrics as expected by test
                "errors": error_log,  # Top-level errors as expected by test
                "execution_history": execution_history,
                "metrics_history": metrics_history,
                "alert_history": self.alert_history,
                "tracking_level": self.tracking_level.value
            }
            
            # Write report to file
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2)
            
            return filepath
            
        except Exception as e:
            logger.error(f"Error exporting execution report: {e}")
            return None
    
    def generate_visualization_data(self, visualization_type: str) -> Dict[str, Any]:
        """Generate data for visualization."""
        try:
            if visualization_type == "status_timeline":
                timeline = []
                for task_id, history in self.task_status_history.items():
                    task_timeline = []
                    for i, (timestamp, status) in enumerate(history):
                        end_time = history[i+1][0] if i+1 < len(history) else datetime.now()
                        task_timeline.append({
                            "task_id": task_id,
                            "status": status.value,
                            "start_time": timestamp.isoformat(),
                            "end_time": end_time.isoformat(),
                            "duration": (end_time - timestamp).total_seconds()
                        })
                    timeline.extend(task_timeline)
                return {"timeline": timeline}
            
            elif visualization_type == "resource_utilization":
                # Group resource usage by type over time
                resources = defaultdict(list)
                timestamps = []
                
                for event in self.execution_history:
                    if "resource_usage" in event:
                        timestamp = event["timestamp"]
                        timestamps.append(timestamp)
                        
                        for res_type, value in event["resource_usage"].items():
                            resources[res_type].append((timestamp, value))
                
                # Sort timestamps and remove duplicates
                timestamps = sorted(set(timestamps))
                
                # Convert resources to the expected format
                resources_data = {}
                for res_type, values in resources.items():
                    resources_data[res_type] = [
                        {
                            "timestamp": t.isoformat() if isinstance(t, datetime) else t,
                            "value": v
                        }
                        for t, v in values
                    ]
                
                return {
                    "resources": resources_data,
                    "timestamps": [t.isoformat() if isinstance(t, datetime) else t for t in timestamps]
                }
            
            elif visualization_type == "performance_comparison":
                # Get task performance stats
                perf_stats = self.get_task_performance_stats()
                
                # Extract data for visualization
                task_types = list(perf_stats.keys())
                avg_durations = [stats["avg_duration"] for stats in perf_stats.values()]
                min_durations = [stats["min_duration"] for stats in perf_stats.values()]
                max_durations = [stats["max_duration"] for stats in perf_stats.values()]
                counts = [stats["count"] for stats in perf_stats.values()]
                success_rates = [
                    (stats["success_count"] / stats["count"] * 100) if stats["count"] > 0 else 0
                    for stats in perf_stats.values()
                ]
                
                return {
                    "task_types": task_types,
                    "avg_durations": avg_durations,
                    "min_durations": min_durations,
                    "max_durations": max_durations,
                    "counts": counts,
                    "success_rates": success_rates
                }
            
            elif visualization_type == "performance_metrics":
                data = []
                for entry in self.metrics_history:
                    data.append({
                        "timestamp": entry["timestamp"].isoformat() if isinstance(entry["timestamp"], datetime) else entry["timestamp"],
                        "metrics": entry["metrics"]
                    })
                return {"metrics": data}
            
            elif visualization_type == "error_distribution":
                error_counts = defaultdict(int)
                for error in self.error_log:
                    error_type = type(error.get("error", "Unknown")).__name__
                    error_counts[error_type] += 1
                return {"error_counts": dict(error_counts)}
            
            else:
                raise ValueError(f"Unsupported visualization type: {visualization_type}")
                
        except Exception as e:
            logger.error(f"Error generating visualization data: {e}")
            return {"error": str(e)}
    
    def get_alerts(self, alert_type: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent alerts, optionally filtered by type."""
        filtered_alerts = self.alert_history
        
        if alert_type:
            filtered_alerts = [a for a in filtered_alerts if a["type"] == alert_type]
        
        # Return most recent alerts first
        return sorted(filtered_alerts, key=lambda x: x["timestamp"], reverse=True)[:limit]
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get a summary of triggered alerts."""
        type_counts = defaultdict(int)
        for alert in self.alert_history:
            type_counts[alert["type"]] += 1
        # Calculate time periods
        alert_periods = {}
        if self.alert_history:
            first_alert = datetime.fromisoformat(min(a["timestamp"] for a in self.alert_history))
            last_alert = datetime.fromisoformat(max(a["timestamp"] for a in self.alert_history))
            total_seconds = (last_alert - first_alert).total_seconds()
            
            if total_seconds > 0:
                for alert_type, count in type_counts.items():
                    alert_periods[alert_type] = total_seconds / count  # Average seconds between alerts
        
        return {
            "total_alerts": len(self.alert_history),
            "type_counts": dict(type_counts),
            "alert_periods": alert_periods,
            "rule_counters": dict(self.alert_counters)
        }
    
    def clear_alerts(self, older_than: datetime = None) -> int:
        """Clear alerts, optionally only those older than a specified time."""
        if older_than is None:
            count = len(self.alert_history)
            self.alert_history = []
            return count
        
        original_count = len(self.alert_history)
        self.alert_history = [
            alert for alert in self.alert_history
            if datetime.fromisoformat(alert["timestamp"]) >= older_than
        ]
        return original_count - len(self.alert_history)

    def set_tracking_level(self, level: TrackingLevel):
        """Set the tracking detail level."""
        self.tracking_level = level
        logger.info(f"Set tracking level to {level.value}")
    
    def get_tracking_level(self) -> TrackingLevel:
        """Get the current tracking detail level."""
        return self.tracking_level 