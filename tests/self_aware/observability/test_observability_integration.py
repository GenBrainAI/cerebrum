import pytest
import json
import os
import shutil
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock, call

from src.server.observability.observability_integration import ObservabilityLayer
from src.server.observability.mocks import (
    MockProgressTracker,
    MockInterventionInterface,
    MockSupervisionHub,
    MockResourceMonitor,
    MockMetricsCollector
)

class TestObservabilityLayer:
    """Test suite for the ObservabilityLayer class."""

    @pytest.fixture
    def test_storage_path(self, tmp_path):
        """Create a temporary directory for test storage."""
        storage_path = tmp_path / "observability"
        storage_path.mkdir(exist_ok=True)
        
        # Create subdirectories
        (storage_path / "dashboards").mkdir(exist_ok=True)
        (storage_path / "reports").mkdir(exist_ok=True)
        (storage_path / "logs").mkdir(exist_ok=True)
        (storage_path / "exports").mkdir(exist_ok=True)
        
        return str(storage_path)
    
    @pytest.fixture
    def observability_layer(self, test_storage_path):
        """Create an ObservabilityLayer instance for testing."""
        # Configure with test settings
        config = {
            "storage_path": test_storage_path,
            "enable_components": {
                "progress_tracker": True,
                "intervention_interface": True,
                "supervision_hub": True,
                "resource_monitor": True,
                "metrics_collector": True,
                "dashboard": True
            },
            "dashboard_port": 9000,  # Use different port for tests
            "log_level": "INFO",
            "data_retention_days": 7  # Shorter retention for tests
        }
        
        with patch('os.makedirs'), patch('signal.signal'), patch('atexit.register'):
            layer = ObservabilityLayer(config)
            return layer
    
    @pytest.mark.asyncio
    async def test_initialization(self, observability_layer):
        """Test initialization of the observability layer."""
        with patch.object(observability_layer, '_initialize_progress_tracker', new_callable=AsyncMock) as mock_progress, \
             patch.object(observability_layer, '_initialize_intervention_interface', new_callable=AsyncMock) as mock_intervention, \
             patch.object(observability_layer, '_initialize_supervision_hub', new_callable=AsyncMock) as mock_supervision, \
             patch.object(observability_layer, '_initialize_resource_monitor', new_callable=AsyncMock) as mock_resource, \
             patch.object(observability_layer, '_initialize_metrics_collector', new_callable=AsyncMock) as mock_metrics, \
             patch.object(observability_layer, '_initialize_integrations', new_callable=AsyncMock) as mock_integrations, \
             patch.object(observability_layer, '_start_dashboard', new_callable=AsyncMock) as mock_dashboard:
            
            # Set return values for the mock methods
            mock_progress.return_value = {"status": "initialized"}
            mock_intervention.return_value = {"status": "initialized"}
            mock_supervision.return_value = {"status": "initialized"}
            mock_resource.return_value = {"status": "initialized"}
            mock_metrics.return_value = {"status": "initialized"}
            mock_dashboard.return_value = {"status": "started", "port": 9000}
            
            # Test the initialization
            result = await observability_layer.initialize()
            
            # Verify all components were initialized
            mock_progress.assert_called_once()
            mock_intervention.assert_called_once()
            mock_supervision.assert_called_once()
            mock_resource.assert_called_once()
            mock_metrics.assert_called_once()
            mock_integrations.assert_called_once()
            mock_dashboard.assert_called_once()
            
            # Verify the result structure
            assert result["status"] == "initialized"
            assert "components" in result
            assert "system_info" in result
            
            # Verify the layer state
            assert observability_layer.is_initialized == True
            assert "progress_tracker" in observability_layer.component_status
            assert "intervention_interface" in observability_layer.component_status
            assert "supervision_hub" in observability_layer.component_status
            assert "resource_monitor" in observability_layer.component_status
            assert "metrics_collector" in observability_layer.component_status
            assert "dashboard" in observability_layer.component_status
    
    @pytest.mark.asyncio
    async def test_component_initialization_failure(self, observability_layer):
        """Test handling of component initialization failures."""
        with patch.object(observability_layer, '_initialize_progress_tracker', new_callable=AsyncMock) as mock_progress, \
             patch.object(observability_layer, '_initialize_intervention_interface', new_callable=AsyncMock) as mock_intervention, \
             patch.object(observability_layer, '_initialize_supervision_hub', new_callable=AsyncMock) as mock_supervision, \
             patch.object(observability_layer, '_initialize_resource_monitor', new_callable=AsyncMock) as mock_resource, \
             patch.object(observability_layer, '_initialize_metrics_collector', new_callable=AsyncMock) as mock_metrics:
            
            # Set a failure for one component
            mock_progress.return_value = {"status": "initialized"}
            mock_intervention.return_value = {"status": "initialized"}
            mock_supervision.return_value = {"status": "failed", "error": "Connection error"}
            mock_resource.return_value = {"status": "initialized"}
            mock_metrics.return_value = {"status": "initialized"}
            
            # Intentionally raise an exception in one component
            mock_resource.side_effect = Exception("Simulated resource initialization error")
            
            # Test the initialization
            result = await observability_layer.initialize()
            
            # Verify the failed initialization is captured
            assert result["status"] == "initialization_failed"
            assert "error" in result
            
            # Verify component statuses are recorded
            assert "components" in result
            assert observability_layer.is_initialized == False
    
    @pytest.mark.asyncio
    async def test_create_observability_dashboard(self, observability_layer, test_storage_path):
        """Test creation of a custom observability dashboard."""
        # Set up test data
        name = "Test Dashboard"
        panels = [
            {"id": "panel1", "title": "CPU Usage", "type": "line", "metric_id": "resources.cpu_usage"},
            {"id": "panel2", "title": "Memory Usage", "type": "gauge", "metric_id": "resources.memory_usage"},
            {"id": "panel3", "title": "Task Completion", "type": "bar", "metric_id": "progress.completion_rate"}
        ]
        refresh_interval = 30
        
        # Test dashboard creation
        result = await observability_layer.create_observability_dashboard(
            name=name,
            panels=panels,
            refresh_interval=refresh_interval
        )
        
        # Verify the result
        assert result["status"] == "created"
        assert "dashboard_id" in result
        assert result["name"] == name
        assert result["panel_count"] == len(panels)
        
        # Verify the dashboard file was created
        dashboard_dir = os.path.join(test_storage_path, "dashboards")
        dashboard_files = os.listdir(dashboard_dir)
        assert len(dashboard_files) == 1
        
        # Verify dashboard content
        dashboard_path = os.path.join(dashboard_dir, dashboard_files[0])
        with open(dashboard_path, 'r') as f:
            dashboard_data = json.load(f)
            assert dashboard_data["name"] == name
            assert dashboard_data["panels"] == panels
            assert dashboard_data["refresh_interval"] == refresh_interval
            assert "id" in dashboard_data
            assert "created_at" in dashboard_data
    
    @pytest.mark.asyncio
    async def test_create_system_report(self, observability_layer):
        """Test creation of a system report."""
        # Configure the mock components
        observability_layer.progress_tracker = MagicMock()
        observability_layer.progress_tracker.get_progress_report = AsyncMock(return_value={
            "overall_completion": 65,
            "completed_items": 27
        })
        observability_layer.progress_tracker.create_visualization = AsyncMock(return_value={
            "type": "image", 
            "content": "base64_encoded_progress_vis"
        })
        
        observability_layer.resource_monitor = MagicMock()
        observability_layer.resource_monitor.get_budgets = AsyncMock(return_value=[
            {"id": "budget_cpu", "name": "CPU Budget", "usage": 45}
        ])
        observability_layer.resource_monitor.create_usage_report = AsyncMock(return_value={
            "budgets": [{"id": "budget_cpu"}],
            "history": [{"timestamp": "2023-01-01", "cpu": 40}],
            "visualization": {"type": "image", "content": "base64_encoded_resource_vis"}
        })
        
        observability_layer.metrics_collector = MagicMock()
        observability_layer.metrics_collector.create_metrics_report = AsyncMock(return_value={
            "summary": {"total_metrics": 10},
            "metrics": [{"id": "metric1"}],
            "visualizations": {
                "performance_metrics": {"type": "image", "content": "base64_encoded_perf_vis"}
            }
        })
        observability_layer.metrics_collector.get_anomalies = AsyncMock(return_value=[
            {"id": "anomaly1", "metric_id": "metric1", "severity": "warning"}
        ])
        
        observability_layer.intervention_interface = MagicMock()
        observability_layer.intervention_interface.get_interventions_for_period = AsyncMock(return_value=[
            {"id": "int1", "title": "Alert", "status": "resolved"}
        ])
        
        # Test report creation
        with patch('os.makedirs'), patch('builtins.open', create=True), patch('json.dump') as mock_json_dump:
            result = await observability_layer.create_system_report(
                sections=["progress", "resources", "metrics", "interventions", "anomalies"],
                start_time="2023-01-01T00:00:00",
                end_time="2023-01-07T00:00:00"
            )
            
            # Verify the result
            assert result["status"] == "created"
            assert "report_id" in result
            assert "sections" in result
            assert "time_range" in result
            assert "report_path" in result
            
            # Verify component methods were called
            observability_layer.progress_tracker.get_progress_report.assert_called_once()
            observability_layer.resource_monitor.get_budgets.assert_called_once()
            observability_layer.resource_monitor.create_usage_report.assert_called_once()
            observability_layer.metrics_collector.create_metrics_report.assert_called_once()
            observability_layer.metrics_collector.get_anomalies.assert_called_once()
            observability_layer.intervention_interface.get_interventions_for_period.assert_called_once()
            
            # Verify JSON was written
            mock_json_dump.assert_called_once()
            
            # Verify report content
            report_data = mock_json_dump.call_args[0][0]
            assert "timestamp" in report_data
            assert "time_range" in report_data
            assert "system_info" in report_data
            assert "sections" in report_data
            assert "visualizations" in report_data
    
    @pytest.mark.asyncio
    async def test_register_event_handler(self, observability_layer):
        """Test registration of event handlers."""
        # Test event handler
        async def test_handler(event_data):
            pass
        
        # Register the handler
        result = await observability_layer.register_event_handler(
            event_type="system.alert",
            handler=test_handler
        )
        
        # Verify the result
        assert result["status"] == "registered"
        assert result["event_type"] == "system.alert"
        assert result["handler_count"] == 1
        
        # Verify the handler was registered
        assert "system.alert" in observability_layer.event_handlers
        assert test_handler in observability_layer.event_handlers["system.alert"]
        
        # Register another handler for the same event
        async def test_handler2(event_data):
            pass
        
        result2 = await observability_layer.register_event_handler(
            event_type="system.alert",
            handler=test_handler2
        )
        
        # Verify handler count increased
        assert result2["handler_count"] == 2
        assert len(observability_layer.event_handlers["system.alert"]) == 2
    
    @pytest.mark.asyncio
    async def test_trigger_event(self, observability_layer):
        """Test triggering of events and handler execution."""
        # Configure mock metrics collector
        observability_layer.metrics_collector = MagicMock()
        observability_layer.metrics_collector.record_event = AsyncMock(return_value={
            "status": "recorded"
        })
        
        # Create test handlers
        handler1_called = False
        handler2_called = False
        
        async def test_handler1(event_data):
            nonlocal handler1_called
            handler1_called = True
            assert event_data["message"] == "Test event"
        
        async def test_handler2(event_data):
            nonlocal handler2_called
            handler2_called = True
            assert event_data["message"] == "Test event"
        
        # Register handlers
        observability_layer.event_handlers["system.test"] = [test_handler1, test_handler2]
        
        # Test event triggering
        event_data = {"message": "Test event", "severity": "info"}
        result = await observability_layer.trigger_event(
            event_type="system.test",
            event_data=event_data
        )
        
        # Verify the result
        assert result["status"] == "triggered"
        assert result["event_type"] == "system.test"
        assert result["handler_count"] == 2
        
        # Verify metrics collector was called
        observability_layer.metrics_collector.record_event.assert_called_once_with(
            event_type="system.test",
            data=event_data
        )
        
        # Verify handlers were called
        assert handler1_called == True
        assert handler2_called == True
        
        # Test triggering with failing handler
        async def failing_handler(event_data):
            raise Exception("Simulated handler error")
        
        observability_layer.event_handlers["system.test"].append(failing_handler)
        
        # The event should still trigger successfully even if a handler fails
        result = await observability_layer.trigger_event(
            event_type="system.test",
            event_data=event_data
        )
        
        assert result["status"] == "triggered"
        assert result["handler_count"] == 3
    
    @pytest.mark.asyncio
    async def test_create_data_export_json(self, observability_layer):
        """Test creation of data exports in JSON format."""
        # Configure mock components
        observability_layer.progress_tracker = MagicMock()
        observability_layer.progress_tracker.get_progress_data = AsyncMock(return_value=[
            {"timestamp": "2023-01-01", "completion": 50}
        ])
        
        observability_layer.resource_monitor = MagicMock()
        observability_layer.resource_monitor.export_usage_data = AsyncMock(return_value=[
            {"timestamp": "2023-01-01", "cpu": 40, "memory": 15}
        ])
        
        observability_layer.metrics_collector = MagicMock()
        observability_layer.metrics_collector.export_metrics_data = AsyncMock(return_value=[
            {"timestamp": "2023-01-01", "metric_id": "performance.execution_time", "value": 1.2}
        ])
        
        observability_layer.intervention_interface = MagicMock()
        observability_layer.intervention_interface.export_interventions = AsyncMock(return_value=[
            {"id": "int1", "timestamp": "2023-01-01", "status": "resolved"}
        ])
        
        # Test JSON export with patched file operations
        with patch('os.makedirs'), patch('builtins.open', create=True), patch('json.dump') as mock_json_dump:
            result = await observability_layer.create_data_export(
                components=["progress", "resources", "metrics", "interventions"],
                start_time="2023-01-01T00:00:00",
                end_time="2023-01-07T00:00:00",
                format_type="json"
            )
            
            # Verify the result
            assert result["status"] == "created"
            assert "export_id" in result
            assert result["format"] == "json"
            assert "components" in result
            assert "time_range" in result
            assert "export_path" in result
            
            # Verify component methods were called
            observability_layer.progress_tracker.get_progress_data.assert_called_once()
            observability_layer.resource_monitor.export_usage_data.assert_called_once()
            observability_layer.metrics_collector.export_metrics_data.assert_called_once()
            observability_layer.intervention_interface.export_interventions.assert_called_once()
            
            # Verify JSON was written
            mock_json_dump.assert_called_once()
            
            # Verify export content
            export_data = mock_json_dump.call_args[0][0]
            assert "components" in export_data
            assert "time_range" in export_data
            assert "system_info" in export_data
    
    @pytest.mark.asyncio
    async def test_create_data_export_csv(self, observability_layer):
        """Test creation of data exports in CSV format."""
        # Configure mock components
        observability_layer.progress_tracker = MagicMock()
        observability_layer.progress_tracker.get_progress_data = AsyncMock(return_value=[
            {"timestamp": "2023-01-01", "completion": 50}
        ])
        
        observability_layer.resource_monitor = MagicMock()
        observability_layer.resource_monitor.export_usage_data = AsyncMock(return_value=[
            {"timestamp": "2023-01-01", "cpu": 40, "memory": 15}
        ])
        
        # Test CSV export with patched pandas and file operations
        with patch('os.makedirs'), patch('pandas.DataFrame.to_csv'):
            result = await observability_layer.create_data_export(
                components=["progress", "resources"],
                start_time="2023-01-01T00:00:00",
                end_time="2023-01-07T00:00:00",
                format_type="csv"
            )
            
            # Verify the result
            assert result["status"] == "created"
            assert "export_id" in result
            assert result["format"] == "csv"
            assert "components" in result
            assert "time_range" in result
            assert "export_path" in result 
    
    @pytest.mark.asyncio
    async def test_cleanup_old_data(self, observability_layer):
        """Test cleaning up of old observability data."""
        # Configure mock components
        observability_layer.metrics_collector = MagicMock()
        observability_layer.metrics_collector.cleanup_old_data = AsyncMock(return_value={
            "status": "completed", "removed_metrics": 250
        })
        
        observability_layer.resource_monitor = MagicMock()
        observability_layer.resource_monitor.cleanup_old_data = AsyncMock(return_value={
            "status": "completed", "removed_records": 120
        })
        
        observability_layer.intervention_interface = MagicMock()
        observability_layer.intervention_interface.cleanup_old_data = AsyncMock(return_value={
            "status": "completed", "removed_count": 35
        })
        
        # Mock file operations
        with patch('os.path.exists', return_value=True), \
             patch('os.listdir', return_value=["file1.json", "file2.json"]), \
             patch('os.path.isfile', return_value=True), \
             patch('os.path.getmtime', return_value=datetime.now().timestamp() - 60*60*24*30), \
             patch('os.remove') as mock_remove, \
             patch('os.path.isdir', return_value=True), \
             patch('shutil.rmtree') as mock_rmtree:
            
            # Test cleanup with default retention
            result = await observability_layer.cleanup_old_data()
            
            # Verify the result
            assert result["status"] == "completed"
            assert "retention_days" in result
            assert "cutoff_date" in result
            assert "reports_removed" in result
            assert "exports_removed" in result
            assert "component_results" in result
            
            # Verify component methods were called
            observability_layer.metrics_collector.cleanup_old_data.assert_called_once()
            observability_layer.resource_monitor.cleanup_old_data.assert_called_once()
            observability_layer.intervention_interface.cleanup_old_data.assert_called_once()
            
            # Verify files were removed
            assert mock_remove.call_count > 0
            
            # Test with custom retention
            observability_layer.metrics_collector.cleanup_old_data.reset_mock()
            observability_layer.resource_monitor.cleanup_old_data.reset_mock()
            observability_layer.intervention_interface.cleanup_old_data.reset_mock()
            mock_remove.reset_mock()
            
            custom_retention = 14
            result = await observability_layer.cleanup_old_data(retention_days=custom_retention)
            
            assert result["retention_days"] == custom_retention
            
            # Verify component methods were called with custom retention
            observability_layer.metrics_collector.cleanup_old_data.assert_called_once_with(custom_retention)
            observability_layer.resource_monitor.cleanup_old_data.assert_called_once_with(custom_retention)
            observability_layer.intervention_interface.cleanup_old_data.assert_called_once_with(custom_retention)
    
    @pytest.mark.asyncio
    async def test_health_check(self, observability_layer):
        """Test observability health check."""
        # Configure mock components
        observability_layer.progress_tracker = MagicMock()
        observability_layer.progress_tracker.health_check = AsyncMock(return_value={
            "status": "healthy", "metrics": {"tracked_items": 42}
        })
        
        observability_layer.intervention_interface = MagicMock()
        observability_layer.intervention_interface.health_check = AsyncMock(return_value={
            "status": "healthy", "metrics": {"pending_interventions": 2}
        })
        
        observability_layer.supervision_hub = MagicMock()
        observability_layer.supervision_hub.health_check = AsyncMock(return_value={
            "status": "healthy", "metrics": {"active_workflows": 3}
        })
        
        observability_layer.resource_monitor = MagicMock()
        observability_layer.resource_monitor.health_check = AsyncMock(return_value={
            "status": "healthy", "monitoring_active": True, "metrics": {"tracked_budgets": 3}
        })
        
        observability_layer.metrics_collector = MagicMock()
        observability_layer.metrics_collector.health_check = AsyncMock(return_value={
            "status": "healthy", "collection_active": True, "metrics": {"registered_metrics": 15}
        })
        
        observability_layer.is_dashboard_running = True
        
        # Test health check
        result = await observability_layer.health_check()
        
        # Verify the result structure
        assert "system_info" in result
        assert "timestamp" in result
        assert "components" in result
        assert "overall_status" in result
        
        # All components should be healthy, so overall status should be healthy
        assert result["overall_status"] == "healthy"
        
        # Verify all components are included
        assert "progress_tracker" in result["components"]
        assert "intervention_interface" in result["components"]
        assert "supervision_hub" in result["components"]
        assert "resource_monitor" in result["components"]
        assert "metrics_collector" in result["components"]
        assert "dashboard" in result["components"]
        
        # Test with one unhealthy component
        observability_layer.resource_monitor.health_check = AsyncMock(return_value={
            "status": "unhealthy", "error": "Connection lost", "monitoring_active": False
        })
        
        result = await observability_layer.health_check()
        
        # Overall status should now be unhealthy
        assert result["overall_status"] == "unhealthy"
        assert result["components"]["resource_monitor"]["status"] == "unhealthy"
        
        # Test with component raising exception
        observability_layer.metrics_collector.health_check = AsyncMock(side_effect=Exception("Simulated error"))
        
        result = await observability_layer.health_check()
        
        # Overall status should still be unhealthy
        assert result["overall_status"] == "unhealthy"
        assert result["components"]["metrics_collector"]["status"] == "error"
        assert "error" in result["components"]["metrics_collector"]
    
    @pytest.mark.asyncio
    async def test_shutdown(self, observability_layer):
        """Test graceful shutdown of the observability layer."""
        # Configure mock components
        observability_layer.progress_tracker = MagicMock()
        observability_layer.progress_tracker.shutdown = AsyncMock(return_value={
            "status": "shutdown_completed"
        })
        
        observability_layer.intervention_interface = MagicMock()
        observability_layer.intervention_interface.shutdown = AsyncMock(return_value={
            "status": "shutdown_completed"
        })
        
        observability_layer.supervision_hub = MagicMock()
        observability_layer.supervision_hub.shutdown = AsyncMock(return_value={
            "status": "shutdown_completed"
        })
        
        observability_layer.resource_monitor = MagicMock()
        observability_layer.resource_monitor.stop_monitoring = AsyncMock(return_value={
            "status": "stopped"
        })
        
        observability_layer.metrics_collector = MagicMock()
        observability_layer.metrics_collector.stop_collection = AsyncMock(return_value={
            "status": "stopped"
        })
        
        observability_layer.is_dashboard_running = True
        observability_layer.is_initialized = True
        
        # Test shutdown
        result = await observability_layer.shutdown()
        
        # Verify the result
        assert result["status"] == "shutdown_completed"
        assert "component_results" in result
        assert "timestamp" in result
        
        # Verify component methods were called
        observability_layer.progress_tracker.shutdown.assert_called_once()
        observability_layer.intervention_interface.shutdown.assert_called_once()
        observability_layer.supervision_hub.shutdown.assert_called_once()
        observability_layer.resource_monitor.stop_monitoring.assert_called_once()
        observability_layer.metrics_collector.stop_collection.assert_called_once()
        
        # Verify layer state
        assert observability_layer.is_dashboard_running == False
        assert observability_layer.is_initialized == False
        
        # Test with component failure
        # Reset the layer state
        observability_layer.is_dashboard_running = True
        observability_layer.is_initialized = True
        
        # Make one component fail
        observability_layer.resource_monitor.stop_monitoring = AsyncMock(side_effect=Exception("Simulated error"))
        
        # Shutdown should still complete even with component failures
        result = await observability_layer.shutdown()
        
        assert result["status"] == "shutdown_completed"
        assert "component_results" in result
        assert "resource_monitor" in result["component_results"]
        assert result["component_results"]["resource_monitor"]["status"] == "error"
        
        # Verify layer state is still reset
        assert observability_layer.is_dashboard_running == False
        assert observability_layer.is_initialized == False
    
    @pytest.mark.asyncio
    async def test_initialize_integrations(self, observability_layer):
        """Test initialization of cross-component integrations."""
        # Configure mock components
        observability_layer.progress_tracker = MagicMock()
        observability_layer.progress_tracker.register_callback = MagicMock()
        
        observability_layer.intervention_interface = MagicMock()
        observability_layer.intervention_interface.request_intervention = AsyncMock()
        
        observability_layer.supervision_hub = MagicMock()
        observability_layer.supervision_hub.create_approval_workflow = AsyncMock()
        
        observability_layer.resource_monitor = MagicMock()
        observability_layer.resource_monitor.register_alert_callback = MagicMock()
        observability_layer.resource_monitor.get_budgets = AsyncMock(return_value=[
            {"id": "budget_cpu", "name": "CPU Budget", "priority": "high", "resource_type": "cpu", "limit": 100, "unit": "cpu_hours"}
        ])
        
        observability_layer.metrics_collector = MagicMock()
        observability_layer.metrics_collector.register_metric = AsyncMock()
        observability_layer.metrics_collector.register_anomaly_definition = AsyncMock()
        
        # Mock integration methods
        with patch.object(observability_layer, '_integrate_progress_metrics', new_callable=AsyncMock) as mock_progress_metrics, \
             patch.object(observability_layer, '_integrate_resource_alerts', new_callable=AsyncMock) as mock_resource_alerts, \
             patch.object(observability_layer, '_integrate_tracking_metrics', new_callable=AsyncMock) as mock_tracking_metrics, \
             patch.object(observability_layer, '_integrate_anomaly_interventions', new_callable=AsyncMock) as mock_anomaly_interventions, \
             patch.object(observability_layer, '_integrate_resource_supervision', new_callable=AsyncMock) as mock_resource_supervision:
            
            # Test integration initialization
            await observability_layer._initialize_integrations()
            
            # Verify all integration methods were called
            mock_progress_metrics.assert_called_once()
            mock_resource_alerts.assert_called_once()
            mock_tracking_metrics.assert_called_once()
            mock_anomaly_interventions.assert_called_once()
            mock_resource_supervision.assert_called_once()
            
            # Test with missing components
            observability_layer.progress_tracker = None
            
            # Reset mock calls
            mock_progress_metrics.reset_mock()
            mock_resource_alerts.reset_mock()
            mock_tracking_metrics.reset_mock()
            mock_anomaly_interventions.reset_mock()
            mock_resource_supervision.reset_mock()
            
            # Integration should log a warning but not fail
            await observability_layer._initialize_integrations()
            
            # Verify methods were not called due to missing components
            mock_progress_metrics.assert_not_called()
            mock_resource_alerts.assert_not_called()
            mock_tracking_metrics.assert_not_called()
            mock_anomaly_interventions.assert_not_called()
            mock_resource_supervision.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_on_progress_update(self, observability_layer):
        """Test progress update callback."""
        # Configure mock metrics collector
        observability_layer.metrics_collector = MagicMock()
        observability_layer.metrics_collector.record_metric = AsyncMock(return_value={
            "status": "recorded"
        })
        
        # Test progress update handling
        await observability_layer._on_progress_update({
            "overall_completion": 75,
            "completed_items": 30
        })
        
        # Verify metrics were recorded
        assert observability_layer.metrics_collector.record_metric.call_count == 2
        
        # Verify first metric call (progress percentage)
        call_args_list = observability_layer.metrics_collector.record_metric.call_args_list
        assert call_args_list[0][1]["metric_id"] == "cognitive.progress_percentage"
        assert call_args_list[0][1]["value"] == 75
        assert call_args_list[0][1]["component"] == "system"
        
        # Verify second metric call (task completion)
        assert call_args_list[1][1]["metric_id"] == "cognitive.task_completion_rate"
        assert call_args_list[1][1]["value"] == 30
        assert call_args_list[1][1]["component"] == "execution_engine"
    
    @pytest.mark.asyncio
    async def test_on_resource_alert(self, observability_layer):
        """Test resource alert callback."""
        # Configure mock intervention interface
        observability_layer.intervention_interface = MagicMock()
        observability_layer.intervention_interface.request_intervention = AsyncMock(return_value={
            "id": "intervention_1234",
            "status": "pending"
        })
        
        # Test critical resource alert
        await observability_layer._on_resource_alert({
            "percentage": 96,
            "resource_type": "cpu",
            "budget_name": "CPU Budget",
            "budget_id": "budget_cpu",
            "current_usage": 96,
            "budget_limit": 100
        })
        
        # Verify intervention was requested
        observability_layer.intervention_interface.request_intervention.assert_called_once()
        
        # Verify intervention parameters for critical alert
        call_args = observability_layer.intervention_interface.request_intervention.call_args[1]
        assert "CPU Budget" in call_args["title"]
        assert "critical" == call_args["level"]
        assert call_args["context"]["metrics"]["percentage"] == 96
        
        # Reset mock
        observability_layer.intervention_interface.request_intervention.reset_mock()
        
        # Test warning resource alert
        await observability_layer._on_resource_alert({
            "percentage": 85,
            "resource_type": "memory",
            "budget_name": "Memory Budget",
            "budget_id": "budget_memory",
            "current_usage": 17,
            "budget_limit": 20
        })
        
        # Verify intervention parameters for warning alert
        call_args = observability_layer.intervention_interface.request_intervention.call_args[1]
        assert "Memory Budget" in call_args["title"]
        assert "warning" == call_args["level"]
    
    @pytest.mark.asyncio
    async def test_on_anomaly_detected(self, observability_layer):
        """Test anomaly detection callback."""
        # Configure mock intervention interface
        observability_layer.intervention_interface = MagicMock()
        observability_layer.intervention_interface.request_intervention = AsyncMock(return_value={
            "id": "intervention_5678",
            "status": "pending"
        })
        
        # Test critical anomaly
        await observability_layer._on_anomaly_detected(
            event={
                "id": "anomaly_event_1",
                "metric_id": "reliability.task_success_rate",
                "metric_name": "Task Success Rate",
                "value": 65,
                "expected_range": [85, 100],
                "deviation_percentage": 23.53,
                "severity": "critical"
            },
            definition={
                "id": "anomaly_def_1",
                "name": "High Task Failure Rate",
                "description": "Unusually high task failure rate"
            }
        )
        
        # Verify intervention was requested
        observability_layer.intervention_interface.request_intervention.assert_called_once()
        
        # Verify intervention parameters
        call_args = observability_layer.intervention_interface.request_intervention.call_args[1]
        assert "High Task Failure Rate" in call_args["title"]
        assert "critical" == call_args["level"]
        assert "Task Success Rate" in call_args["description"]
        assert call_args["context"]["operation"] == "anomaly_detection"
        
        # Verify context metrics
        assert call_args["context"]["metrics"]["value"] == 65
        assert call_args["context"]["metrics"]["expected_range"] == [85, 100]
        assert call_args["context"]["metrics"]["deviation_percentage"] == 23.53
    
    @pytest.mark.asyncio
    async def test_integrate_resource_supervision(self, observability_layer):
        """Test integration of resource supervision workflows."""
        # Configure mock components
        observability_layer.supervision_hub = MagicMock()
        observability_layer.supervision_hub.create_approval_workflow = AsyncMock(return_value={
            "id": "workflow_abcd1234",
            "status": "active"
        })
        
        observability_layer.resource_monitor = MagicMock()
        observability_layer.resource_monitor.get_budgets = AsyncMock(return_value=[
            {
                "id": "budget_cpu",
                "name": "CPU Budget",
                "resource_type": "cpu",
                "limit": 100,
                "unit": "cpu_hours",
                "priority": "high"
            },
            {
                "id": "budget_memory",
                "name": "Memory Budget",
                "resource_type": "memory",
                "limit": 32,
                "unit": "GB",
                "priority": "normal"
            },
            {
                "id": "budget_api",
                "name": "API Budget",
                "resource_type": "api_calls",
                "limit": 10000,
                "unit": "calls",
                "priority": "critical"
            }
        ])
        
        # Test resource supervision integration
        await observability_layer._integrate_resource_supervision()
        
        # Verify create_approval_workflow was called twice (once for each high/critical budget)
        assert observability_layer.supervision_hub.create_approval_workflow.call_count == 2
        
        # Verify first workflow (high priority CPU budget)
        first_call = observability_layer.supervision_hub.create_approval_workflow.call_args_list[0][1]
        assert "CPU Budget" in first_call["title"]
        assert first_call["metadata"]["budget_id"] == "budget_cpu"
        assert first_call["metadata"]["resource_type"] == "cpu"
        
        # Verify second workflow (critical priority API budget)
        second_call = observability_layer.supervision_hub.create_approval_workflow.call_args_list[1][1]
        assert "API Budget" in second_call["title"]
        assert second_call["metadata"]["budget_id"] == "budget_api"
        assert second_call["metadata"]["resource_type"] == "api_calls"
    
    @pytest.mark.asyncio
    async def test_integrate_tracking_metrics(self, observability_layer):
        """Test integration of tracking metrics."""
        # Configure mock components
        observability_layer.metrics_collector = MagicMock()
        observability_layer.metrics_collector.register_metric = AsyncMock(return_value={"status": "registered"})
        
        # Test tracking metrics integration
        await observability_layer._integrate_tracking_metrics()
        
        # Verify register_metric was called for each defined metric
        assert observability_layer.metrics_collector.register_metric.call_count >= 8
        
        # Verify some key metrics were registered - extract from name/category instead of metric_id
        calls = observability_layer.metrics_collector.register_metric.call_args_list
        registered_metrics = []
        
        for call_args in calls:
            name = call_args[1]["name"]
            category = call_args[1]["category"]
            metric_id = f"{category}.{name.lower().replace(' ', '_')}"
            registered_metrics.append(metric_id)
            print(f"Registered metric: {metric_id}")
        
        # Check for expected metrics by partial matches
        success = False
        for metric in registered_metrics:
            if "success" in metric or "execution" in metric:
                success = True
                break
        assert success, "No success rate metric found"
        
        response = False
        for metric in registered_metrics:
            if "response" in metric or "time" in metric:
                response = True
                break
        assert response, "No response time metric found"
        
        cpu = False
        for metric in registered_metrics:
            if "cpu" in metric or "processor" in metric:
                cpu = True
                break
        assert cpu, "No CPU metric found"
        
        memory = False
        for metric in registered_metrics:
            if "memory" in metric or "ram" in metric:
                memory = True
                break
        assert memory, "No memory metric found"
    
    @pytest.mark.asyncio
    async def test_integrate_anomaly_interventions(self, observability_layer):
        """Test integration of anomaly interventions."""
        # Configure mock components
        observability_layer.metrics_collector = MagicMock()
        observability_layer.metrics_collector.register_anomaly_definition = AsyncMock(return_value={"status": "registered"})
        observability_layer.metrics_collector.register_anomaly_callback = AsyncMock()
        
        # Test anomaly interventions integration
        await observability_layer._integrate_anomaly_interventions()
        
        # Verify register_anomaly_definition was called for each defined anomaly
        assert observability_layer.metrics_collector.register_anomaly_definition.call_count >= 4
        
        # Verify register_anomaly_callback was called once to set up handler
        observability_layer.metrics_collector.register_anomaly_callback.assert_awaited_once()
        
        # Verify callback function is _on_anomaly_detected
        assert observability_layer.metrics_collector.register_anomaly_callback.await_args[0][0] == observability_layer._on_anomaly_detected
        
        # Verify some key anomaly definitions were registered
        anomaly_calls = [call[1]["anomaly_id"] for call in observability_layer.metrics_collector.register_anomaly_definition.call_args_list]
        
        assert "task_failure_spike" in anomaly_calls
        assert "high_memory_usage" in anomaly_calls
        assert "response_time_degradation" in anomaly_calls
    
    @pytest.mark.asyncio
    async def test_integrate_progress_metrics(self, observability_layer):
        """Test integration of progress tracking metrics."""
        # Configure mock components
        observability_layer.progress_tracker = MagicMock()
        observability_layer.progress_tracker.register_callback = MagicMock()
        
        # Need to set metrics_collector to avoid the null check
        observability_layer.metrics_collector = MagicMock()
        observability_layer.metrics_collector.register_metric = AsyncMock(return_value={"status": "registered"})
        
        # Test progress metrics integration
        await observability_layer._integrate_progress_metrics()
        
        # Verify callback registration
        observability_layer.progress_tracker.register_callback.assert_called_once()
        
        # Verify callback function is _on_progress_update
        assert observability_layer.progress_tracker.register_callback.call_args[0][0] == observability_layer._on_progress_update
    
    @pytest.mark.asyncio
    async def test_integrate_resource_alerts(self, observability_layer):
        """Test integration of resource monitoring alerts."""
        # Configure mock components
        observability_layer.resource_monitor = MagicMock()
        observability_layer.resource_monitor.register_alert_callback = MagicMock()
        
        # Test resource alerts integration
        await observability_layer._integrate_resource_alerts()
        
        # Verify callback registration
        observability_layer.resource_monitor.register_alert_callback.assert_called_once()
        
        # Verify callback function is _on_resource_alert
        assert observability_layer.resource_monitor.register_alert_callback.call_args[0][0] == observability_layer._on_resource_alert
    
    @pytest.mark.asyncio
    async def test_system_restart(self, observability_layer):
        """Test system restart handling."""
        # Configure mock components
        observability_layer.dashboard_server = MagicMock()
        observability_layer.dashboard_server.stop = AsyncMock()
        observability_layer.dashboard_server.start = AsyncMock()
        
        observability_layer.metrics_collector = MagicMock()
        observability_layer.metrics_collector.record_event = AsyncMock()
        
        # Set initial state
        observability_layer.is_initialized = True
        observability_layer.is_dashboard_running = True
        
        # Mock shutdown and init methods
        with patch.object(observability_layer, '_shutdown', new_callable=AsyncMock) as mock_shutdown, \
             patch.object(observability_layer, '_initialize_components', new_callable=AsyncMock) as mock_init_components, \
             patch.object(observability_layer, '_initialize_integrations', new_callable=AsyncMock) as mock_init_integrations:
            
            # Test restart
            await observability_layer.restart()
            
            # Verify shutdown was called
            mock_shutdown.assert_called_once()
            
            # Verify initialization methods were called
            mock_init_components.assert_called_once()
            mock_init_integrations.assert_called_once()
            
            # Verify event was recorded
            observability_layer.metrics_collector.record_event.assert_called_once()
            assert observability_layer.metrics_collector.record_event.call_args[1]["event_type"] == "system_restart"
    
    @pytest.mark.asyncio
    async def test_metrics_summary(self, observability_layer):
        """Test generation of metrics summary."""
        # Configure mock metrics collector
        observability_layer.metrics_collector = MagicMock()
        observability_layer.metrics_collector.get_metrics_summary = AsyncMock(return_value={
            "total_metrics": 12,
            "metrics_by_category": {
                "cognitive": 3,
                "performance": 4,
                "resource": 2,
                "reliability": 3
            },
            "recent_events": [
                {"id": "event1", "event_type": "system_restart", "timestamp": "2023-08-01T14:30:00Z"},
                {"id": "event2", "event_type": "anomaly_detected", "timestamp": "2023-08-01T15:45:00Z"}
            ]
        })
        
        # Test metrics summary generation
        result = await observability_layer.get_metrics_summary()
        
        # Verify get_metrics_summary was called
        observability_layer.metrics_collector.get_metrics_summary.assert_called_once()
        
        # Verify result structure
        assert result["total_metrics"] == 12
        assert result["metrics_by_category"]["cognitive"] == 3
        assert len(result["recent_events"]) == 2
        assert result["recent_events"][0]["event_type"] == "system_restart" 