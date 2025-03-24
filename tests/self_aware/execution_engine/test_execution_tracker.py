import unittest
from unittest.mock import Mock, patch, MagicMock
import os
import tempfile
import shutil
from datetime import datetime, timedelta
import json
import threading
import time

from server.execution_engine.execution_tracker import (
    ExecutionTracker, TrackingLevel, ExecutionMetrics, AlertRule
)
from server.execution_engine.task_selector import TaskSelector, Task, TaskStatus, TaskPriority
from server.execution_engine.context_manager import ContextManager, ContextType
from server.execution_engine.parallel_execution_controller import ParallelExecutionController, ExecutionResult

class TestExecutionTracker(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.task_selector = Mock(spec=TaskSelector)
        self.context_manager = Mock(spec=ContextManager)
        self.execution_controller = Mock(spec=ParallelExecutionController)
        
        # Create temp directory for output
        self.temp_dir = tempfile.mkdtemp()
        
        # Configure mocks
        self.task_selector.tasks = {
            "task1": Mock(
                id="task1",
                name="Test Task 1",
                status=TaskStatus.IN_PROGRESS,
                priority=TaskPriority.MEDIUM,
                dependencies=[],
                estimated_duration=10.0,
                estimated_resources={"cpu": 1.0},
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            "task2": Mock(
                id="task2",
                name="Test Task 2",
                status=TaskStatus.READY,
                priority=TaskPriority.HIGH,
                dependencies=[],
                estimated_duration=20.0,
                estimated_resources={"cpu": 2.0},
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        }
        
        self.execution_controller.completed_tasks = {
            "completed_task": ExecutionResult(
                task_id="completed_task",
                success=True,
                output={"result": "success"},
                start_time=datetime.now() - timedelta(minutes=5),
                end_time=datetime.now() - timedelta(minutes=4),
                duration=60.0
            ),
            "failed_task": ExecutionResult(
                task_id="failed_task",
                success=False,
                output={},
                start_time=datetime.now() - timedelta(minutes=3),
                end_time=datetime.now() - timedelta(minutes=2),
                error="Test error",
                duration=60.0
            )
        }
        
        # Create tracker
        self.tracker = ExecutionTracker(
            self.task_selector,
            self.context_manager,
            self.execution_controller,
            tracking_level=TrackingLevel.STANDARD,
            output_dir=self.temp_dir
        )
    
    def tearDown(self):
        """Clean up after tests."""
        if self.tracker.is_tracking:
            self.tracker.stop_tracking()
        
        # Remove temp directory
        shutil.rmtree(self.temp_dir)
    
    def test_start_stop_tracking(self):
        """Test starting and stopping tracking."""
        # Start tracking
        self.tracker.start_tracking()
        
        # Verify tracking is active
        self.assertTrue(self.tracker.is_tracking)
        self.assertIsNotNone(self.tracker.tracking_thread)
        self.assertTrue(self.tracker.tracking_thread.is_alive())
        
        # Verify start event was recorded
        self.assertGreaterEqual(len(self.tracker.execution_history), 1)
        self.assertEqual(self.tracker.execution_history[0]["event_type"], "tracking_started")
        
        # Stop tracking
        self.tracker.stop_tracking()
        
        # Verify tracking is stopped
        self.assertFalse(self.tracker.is_tracking)
        self.assertFalse(self.tracker.tracking_thread.is_alive())
        
        # Verify stop event was recorded
        self.assertGreaterEqual(len(self.tracker.execution_history), 2)
        self.assertEqual(self.tracker.execution_history[-1]["event_type"], "tracking_stopped")
    
    def test_track_task_execution(self):
        """Test tracking a task execution result."""
        # Create execution result
        result = ExecutionResult(
            task_id="task1",
            success=True,
            output={"result": "success"},
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(seconds=1),
            duration=1.0
        )
        
        # Track execution
        self.tracker.track_task_execution("task1", result)
        
        # Verify task status history was updated
        self.assertIn("task1", self.tracker.task_status_history)
        self.assertEqual(self.tracker.task_durations["task1"], 1.0)
        
        # Verify execution event was recorded
        self.assertTrue(any(e["task_id"] == "task1" for e in self.tracker.execution_history))
    
    def test_track_failed_task(self):
        """Test tracking a failed task execution."""
        # Create failed execution result
        result = ExecutionResult(
            task_id="task1",
            success=False,
            output={},
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(seconds=1),
            error="Test error",
            duration=1.0
        )
        
        # Track execution
        self.tracker.track_task_execution("task1", result)
        
        # Verify error was logged
        self.assertEqual(len(self.tracker.error_log), 1)
        self.assertEqual(self.tracker.error_log[0]["task_id"], "task1")
        self.assertEqual(self.tracker.error_log[0]["error"], "Test error")
    
    def test_get_execution_summary(self):
        """Test getting execution summary."""
        # Start tracking
        self.tracker.start_tracking()
        
        # Wait for metrics to be collected
        time.sleep(0.1)
        
        # Get summary
        summary = self.tracker.get_execution_summary()
        
        # Verify summary structure
        self.assertIn("total_tasks", summary)
        self.assertIn("completed_tasks", summary)
        self.assertIn("failed_tasks", summary)
        self.assertIn("success_rate", summary)
        self.assertIn("average_execution_time", summary)
        self.assertIn("throughput", summary)
        
        # Stop tracking
        self.tracker.stop_tracking()
    
    def test_alert_rules(self):
        """Test alert rule registration and triggering."""
        # Register test alert rule
        self.tracker.register_alert_rule(
            name="test_rule",
            condition=lambda metrics, **kwargs: metrics.total_tasks > 0,
            message_template="Test alert: {metrics.total_tasks} tasks",
            alert_type="info",
            cooldown_period=1
        )
        
        # Start tracking
        self.tracker.start_tracking()
        
        # Simulate task activity
        task_result = ExecutionResult(
            task_id="test_task",
            success=True,
            output={"result": "success"},
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(seconds=1),
            duration=1.0,
            resource_usage={"cpu": 0.5, "memory": 1024}
        )
        self.tracker.track_task_execution("test_task", task_result)
        
        # Wait for alerts to be checked
        time.sleep(0.2)  # Increased wait time
        
        # Verify alert was triggered
        self.assertGreater(len(self.tracker.alert_history), 0)
        self.assertIn("test_rule", self.tracker.alert_counters)
        
        # Stop tracking
        self.tracker.stop_tracking()
    
    def test_export_metrics(self):
        """Test exporting metrics to CSV."""
        # Start tracking
        self.tracker.start_tracking()
        
        # Wait for metrics to be collected
        time.sleep(0.1)
        
        # Export metrics
        csv_path = self.tracker.export_metrics_csv("test_metrics.csv")
        
        # Verify file was created
        self.assertTrue(os.path.exists(csv_path))
        
        # Stop tracking
        self.tracker.stop_tracking()
    
    def test_export_execution_report(self):
        """Test exporting execution report."""
        # Start tracking
        self.tracker.start_tracking()
        
        # Simulate task activity with proper resource usage
        task_result = ExecutionResult(
            task_id="test_task",
            success=True,
            output={"result": "success"},
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(seconds=1),
            duration=1.0,
            resource_usage={"cpu": 0.5, "memory": 1024}
        )
        self.tracker.track_task_execution("test_task", task_result)
        
        # Wait for metrics to be collected
        time.sleep(0.1)
        
        # Export report
        report_path = self.tracker.export_execution_report("test_report.json")
        
        # Verify file was created
        self.assertTrue(os.path.exists(report_path))
        
        # Load and verify report structure
        with open(report_path, 'r') as f:
            report = json.load(f)
            self.assertIn("summary", report)
            self.assertIn("task_performance", report)
            self.assertIn("metrics", report)
            self.assertIn("errors", report)
        
        # Stop tracking
        self.tracker.stop_tracking()
    
    def test_visualization_data(self):
        """Test generating visualization data."""
        # Start tracking
        self.tracker.start_tracking()
        
        # Wait for metrics to be collected
        time.sleep(0.1)
        
        # Generate timeline visualization
        timeline_data = self.tracker.generate_visualization_data("status_timeline")
        self.assertIn("timeline", timeline_data)
        
        # Generate resource utilization visualization
        resource_data = self.tracker.generate_visualization_data("resource_utilization")
        self.assertIn("resources", resource_data)
        self.assertIn("timestamps", resource_data)
        
        # Generate performance comparison visualization
        perf_data = self.tracker.generate_visualization_data("performance_comparison")
        self.assertIn("task_types", perf_data)
        self.assertIn("avg_durations", perf_data)
        
        # Stop tracking
        self.tracker.stop_tracking()
    
    def test_tracking_levels(self):
        """Test different tracking levels."""
        # Test minimal tracking
        self.tracker.set_tracking_level(TrackingLevel.MINIMAL)
        self.tracker.start_tracking()
        time.sleep(0.1)
        self.tracker.stop_tracking()
        
        minimal_history_size = len(self.tracker.execution_history)
        
        # Test detailed tracking
        self.tracker.set_tracking_level(TrackingLevel.DETAILED)
        self.tracker.start_tracking()
        time.sleep(0.1)
        self.tracker.stop_tracking()
        
        detailed_history_size = len(self.tracker.execution_history)
        
        # Verify more data is collected in detailed mode
        self.assertGreater(detailed_history_size, minimal_history_size)

class TestAlertRule(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.rule = AlertRule(
            name="test_rule",
            condition=lambda value, **kwargs: value > 10,
            message_template="Value {value} exceeds threshold",
            alert_type="warning",
            cooldown_period=1
        )
    
    def test_check_condition_true(self):
        """Test alert rule when condition is true."""
        alert = self.rule.check(value=15)
        
        self.assertIsNotNone(alert)
        self.assertEqual(alert["rule_name"], "test_rule")
        self.assertEqual(alert["type"], "warning")
        self.assertEqual(alert["message"], "Value 15 exceeds threshold")
        self.assertEqual(alert["trigger_count"], 1)
    
    def test_check_condition_false(self):
        """Test alert rule when condition is false."""
        alert = self.rule.check(value=5)
        
        self.assertIsNone(alert)
        self.assertEqual(self.rule.trigger_count, 0)
    
    def test_cooldown_period(self):
        """Test alert rule cooldown period."""
        # First alert should trigger
        alert1 = self.rule.check(value=15)
        self.assertIsNotNone(alert1)
        
        # Second alert within cooldown should not trigger
        alert2 = self.rule.check(value=15)
        self.assertIsNone(alert2)
        
        # Wait for cooldown to expire
        time.sleep(1.1)
        
        # Third alert should trigger
        alert3 = self.rule.check(value=15)
        self.assertIsNotNone(alert3)
        self.assertEqual(alert3["trigger_count"], 2)

class TestExecutionMetrics(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.metrics = ExecutionMetrics()
    
    def test_update_derived_metrics(self):
        """Test updating derived metrics."""
        # Set base metrics
        self.metrics.total_tasks = 10
        self.metrics.completed_tasks = 8
        self.metrics.total_execution_time = 100
        self.metrics.start_time = datetime.now() - timedelta(minutes=5)
        self.metrics.end_time = datetime.now()
        
        # Update derived metrics
        self.metrics.update_derived_metrics()
        
        # Verify calculations
        self.assertEqual(self.metrics.success_rate, 80.0)  # (8/10) * 100
        self.assertEqual(self.metrics.average_execution_time, 12.5)  # 100/8
        self.assertGreater(self.metrics.total_duration, 290)  # ~300 seconds
        self.assertGreater(self.metrics.throughput, 1.5)  # ~1.6 tasks/minute
    
    def test_zero_division_handling(self):
        """Test handling of zero division cases."""
        # Set metrics that would cause zero division
        self.metrics.total_tasks = 0
        self.metrics.completed_tasks = 0
        self.metrics.total_execution_time = 0
        
        # Update derived metrics
        self.metrics.update_derived_metrics()
        
        # Verify no errors occurred
        self.assertEqual(self.metrics.success_rate, 0)
        self.assertEqual(self.metrics.average_execution_time, 0)
        self.assertEqual(self.metrics.throughput, 0)

if __name__ == '__main__':
    unittest.main() 