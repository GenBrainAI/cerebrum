import pytest
import time
from cerebrum.introspection.runtime_monitoring.telemetry_collector import TelemetryCollector

@pytest.mark.asyncio
class TestTelemetryCollector:
    def setup_method(self):
        self.collector = TelemetryCollector()
        
    async def test_instrument_component(self, temp_python_file):
        """Test instrumenting a component."""
        await self.collector.instrument_component(temp_python_file)
        
        assert temp_python_file in self.collector.instrumented_components
        assert temp_python_file in self.collector.execution_times
        assert temp_python_file in self.collector.memory_snapshots
        assert temp_python_file in self.collector.error_logs
        
    async def test_collect_execution_times(self, temp_python_file):
        """Test collecting execution time data."""
        # First instrument the component
        await self.collector.instrument_component(temp_python_file)
        
        # Collect execution times
        times = await self.collector.collect_execution_times(temp_python_file)
        assert isinstance(times, dict)
        
        # Test non-existent component
        times = await self.collector.collect_execution_times("nonexistent.py")
        assert times == {}
        
    async def test_collect_memory_usage(self, temp_python_file):
        """Test collecting memory usage data."""
        # First instrument the component
        await self.collector.instrument_component(temp_python_file)
        
        # Collect memory usage
        memory_data = await self.collector.collect_memory_usage(temp_python_file)
        assert isinstance(memory_data, dict)
        assert "total_size" in memory_data
        assert "peak_size" in memory_data
        assert "rss" in memory_data
        assert "vms" in memory_data
        assert "timestamp" in memory_data
        
        # Test non-existent component
        memory_data = await self.collector.collect_memory_usage("nonexistent.py")
        assert memory_data == {}
        
    async def test_collect_error_data(self, temp_python_file):
        """Test collecting error data."""
        # First instrument the component
        await self.collector.instrument_component(temp_python_file)
        
        # Collect error data
        errors = await self.collector.collect_error_data(temp_python_file)
        assert isinstance(errors, list)
        
        # Test non-existent component
        errors = await self.collector.collect_error_data("nonexistent.py")
        assert errors == []
        
    async def test_instrument_function(self, temp_python_file):
        """Test function instrumentation wrapper."""
        # Create a test function
        async def test_func(x: int) -> int:
            return x + 1
            
        # Instrument the function
        wrapped_func = self.collector._instrument_function(
            test_func, temp_python_file
        )
        
        # Test normal execution
        result = await wrapped_func(5)
        assert result == 6
        
        # Test error handling
        async def error_func(x: int) -> int:
            raise ValueError("Test error")
            
        wrapped_error_func = self.collector._instrument_function(
            error_func, temp_python_file
        )
        
        try:
            await wrapped_error_func(5)
        except ValueError:
            pass
            
        # Check execution time recording
        assert temp_python_file in self.collector.execution_times
        assert "test_func" in self.collector.execution_times[temp_python_file]
        
        # Check error logging
        assert temp_python_file in self.collector.error_logs
        assert len(self.collector.error_logs[temp_python_file]) > 0
        
        error_log = self.collector.error_logs[temp_python_file][0]
        assert error_log["type"] == "ValueError"
        assert error_log["message"] == "Test error"
        assert error_log["function"] == "error_func"
        assert "traceback" in error_log
        assert "timestamp" in error_log
        
    async def test_execution_time_limit(self, temp_python_file):
        """Test limiting stored execution times."""
        # Create a test function
        async def test_func(x: int) -> int:
            return x + 1
            
        # Instrument the function
        wrapped_func = self.collector._instrument_function(
            test_func, temp_python_file
        )
        
        # Call function more than 100 times
        for i in range(150):
            await wrapped_func(i)
            
        # Check that only last 100 execution times are kept
        assert len(self.collector.execution_times[temp_python_file]["test_func"]) == 100
        
    async def test_memory_snapshot_limit(self, temp_python_file):
        """Test limiting stored memory snapshots."""
        # First instrument the component
        await self.collector.instrument_component(temp_python_file)
        
        # Collect memory snapshots more than 100 times
        for _ in range(150):
            await self.collector.collect_memory_usage(temp_python_file)
            
        # Check that only last 100 snapshots are kept
        assert len(self.collector.memory_snapshots[temp_python_file]) == 100 