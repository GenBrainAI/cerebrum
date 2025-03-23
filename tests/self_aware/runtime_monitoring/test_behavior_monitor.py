import pytest
import asyncio
from src.server.introspection.runtime_monitoring.behavior_monitor import (
    BehaviorMonitor, MonitoringSession, PerformanceMetrics
)

@pytest.mark.asyncio
class TestBehaviorMonitor:
    @pytest.fixture(autouse=True)
    def setup_method(self, mock_telemetry_system):
        self.mock_telemetry_system = mock_telemetry_system
        self.monitor = BehaviorMonitor(self.mock_telemetry_system)
        
    async def test_start_monitoring(self):
        """Test starting a monitoring session."""
        components = ["component1.py", "component2.py"]
        session_id = await self.monitor.start_monitoring(components)
        
        assert isinstance(session_id, str)
        assert session_id in self.monitor.monitoring_sessions
        assert session_id in self.monitor.active_monitors
        
        session = self.monitor.monitoring_sessions[session_id]
        assert isinstance(session, MonitoringSession)
        assert session.components == components
        assert session.active
        
    async def test_start_monitoring_discover_components(self):
        """Test starting monitoring with component discovery."""
        session_id = await self.monitor.start_monitoring()
        
        assert isinstance(session_id, str)
        assert session_id in self.monitor.monitoring_sessions
        assert session_id in self.monitor.active_monitors
        
        session = self.monitor.monitoring_sessions[session_id]
        assert isinstance(session.components, list)
        
    async def test_analyze_performance(self, sample_telemetry_data):
        """Test analyzing performance metrics."""
        # Start monitoring
        session_id = await self.monitor.start_monitoring(["test_component.py"])
        session = self.monitor.monitoring_sessions[session_id]
        
        # Add sample data
        session.telemetry_data["test_component.py"] = sample_telemetry_data
        
        # Test with duration
        metrics = await self.monitor.analyze_performance({"duration": 300})
        assert isinstance(metrics, PerformanceMetrics)
        assert isinstance(metrics.execution_times, dict)
        assert isinstance(metrics.memory_usage, dict)
        assert isinstance(metrics.cpu_usage, dict)
        assert isinstance(metrics.io_operations, dict)
        assert isinstance(metrics.hotspots, list)
        
        # Test with time range
        metrics = await self.monitor.analyze_performance({
            "start_time": 1000.0,
            "end_time": 1001.0
        })
        assert isinstance(metrics, PerformanceMetrics)
        
    async def test_detect_anomalies(self, sample_telemetry_data):
        """Test detecting anomalies."""
        # Start monitoring
        session_id = await self.monitor.start_monitoring(["test_component.py"])
        session = self.monitor.monitoring_sessions[session_id]
        
        # Add sample data
        session.telemetry_data["test_component.py"] = sample_telemetry_data
        
        anomalies = await self.monitor.detect_anomalies()
        assert isinstance(anomalies, list)
        
    async def test_identify_bottlenecks(self, sample_telemetry_data):
        """Test identifying bottlenecks."""
        # Start monitoring
        session_id = await self.monitor.start_monitoring(["test_component.py"])
        session = self.monitor.monitoring_sessions[session_id]
        
        # Add sample data
        session.telemetry_data["test_component.py"] = sample_telemetry_data
        
        bottlenecks = await self.monitor.identify_bottlenecks()
        assert isinstance(bottlenecks, list)
        
        # Check bottleneck structure
        if bottlenecks:
            bottleneck = bottlenecks[0]
            assert "component" in bottleneck
            assert "type" in bottleneck
            assert "suggestions" in bottleneck
            
    async def test_discover_components(self):
        """Test discovering monitorable components."""
        components = await self.monitor._discover_components()
        assert isinstance(components, list)
        assert all(isinstance(c, str) for c in components)
        
    async def test_collect_telemetry(self):
        """Test collecting telemetry data."""
        # Start monitoring
        session_id = await self.monitor.start_monitoring(["test_component.py"])
        session = self.monitor.monitoring_sessions[session_id]
        
        # Create a task for collection and let it run briefly
        collection_task = asyncio.create_task(self.monitor._collect_telemetry(session_id))
        
        # Wait briefly to allow some data collection
        await asyncio.sleep(0.1)
        
        # Deactivate the session to stop collection
        session.active = False
        
        # Wait for collection task to complete
        try:
            # Set a timeout to avoid hanging if the fix doesn't work
            await asyncio.wait_for(collection_task, timeout=1.0)
        except asyncio.TimeoutError:
            # If we hit timeout, cancel the task
            collection_task.cancel()
            try:
                await collection_task
            except asyncio.CancelledError:
                pass
        
        # Check collected data
        assert "test_component.py" in session.telemetry_data
        assert len(session.telemetry_data["test_component.py"]) > 0
        
        # Verify data structure
        data = session.telemetry_data["test_component.py"][0]
        assert "timestamp" in data
        assert "execution_times" in data
        assert "memory_usage" in data
        assert "errors" in data
        
    def test_generate_improvement_suggestions(self):
        """Test generating improvement suggestions."""
        # Test slow execution bottleneck
        bottleneck = {
            "type": "slow_execution",
            "component": "test_component.py",
            "method": "test_method",
            "execution_time": 2.0
        }
        suggestions = self.monitor._generate_improvement_suggestions(bottleneck)
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        
        # Test high memory bottleneck
        bottleneck = {
            "type": "high_memory",
            "component": "test_component.py",
            "current_usage": 1000000
        }
        suggestions = self.monitor._generate_improvement_suggestions(bottleneck)
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        
        # Test high CPU bottleneck
        bottleneck = {
            "type": "high_cpu",
            "component": "test_component.py",
            "current_usage": 0.95
        }
        suggestions = self.monitor._generate_improvement_suggestions(bottleneck)
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0 