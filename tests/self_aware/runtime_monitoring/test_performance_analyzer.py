import pytest
import numpy as np
from cerebrum.introspection.runtime_monitoring.performance_analyzer import (
    PerformanceAnalyzer, PerformanceThresholds
)

@pytest.fixture
def performance_data():
    """Fixture providing performance data for testing."""
    return [
        {
            "execution_times": {
                "test_func": [0.1, 0.11, 0.12],
                "slow_func": [1.1, 1.2, 1.3]
            },
            "memory_usage": {
                "total_size": 1000,
                "peak_size": 1500,
                "rss": 2000,
                "vms": 3000
            },
            "cpu_usage": {
                "user": 0.5,
                "system": 0.3
            },
            "io_operations": {
                "reads": 100,
                "writes": 50
            }
        },
        {
            "execution_times": {
                "test_func": [0.11, 0.12, 0.13],
                "slow_func": [1.2, 1.3, 1.4]
            },
            "memory_usage": {
                "total_size": 1100,
                "peak_size": 1600,
                "rss": 2100,
                "vms": 3100
            },
            "cpu_usage": {
                "user": 0.6,
                "system": 0.4
            },
            "io_operations": {
                "reads": 110,
                "writes": 55
            }
        }
    ]

class TestPerformanceAnalyzer:
    def setup_method(self):
        self.analyzer = PerformanceAnalyzer()
        
    def test_calculate_execution_times(self, performance_data):
        """Test calculating execution time statistics."""
        stats = self.analyzer.calculate_execution_times(performance_data)
        
        assert isinstance(stats, dict)
        assert "test_func" in stats
        assert "slow_func" in stats
        
        # Check statistics structure
        for func_stats in stats.values():
            assert "mean" in func_stats
            assert "median" in func_stats
            assert "std" in func_stats
            assert "min" in func_stats
            assert "max" in func_stats
            assert "count" in func_stats
            
        # Verify values
        assert stats["test_func"]["mean"] < stats["slow_func"]["mean"]
        assert stats["test_func"]["count"] == 6  # 3 times in each data point
        
    def test_calculate_memory_usage(self, performance_data):
        """Test calculating memory usage statistics."""
        stats = self.analyzer.calculate_memory_usage(performance_data)
        
        assert isinstance(stats, dict)
        assert "total_allocated" in stats
        assert "peak_usage" in stats
        assert "allocation_rate" in stats
        
        # Check statistics structure
        for metric_stats in stats.values():
            assert "current" in metric_stats
            assert "mean" in metric_stats
            assert "max" in metric_stats
            assert "trend" in metric_stats
            
        # Verify values
        assert stats["total_allocated"]["current"] == 1100  # Last value
        assert stats["peak_usage"]["max"] == 1600
        
    def test_calculate_cpu_usage(self, performance_data):
        """Test calculating CPU usage statistics."""
        stats = self.analyzer.calculate_cpu_usage(performance_data)
        
        assert isinstance(stats, dict)
        assert "user_time" in stats
        assert "system_time" in stats
        assert "total_time" in stats
        
        # Check statistics structure
        for metric_stats in stats.values():
            assert "current" in metric_stats
            assert "mean" in metric_stats
            assert "max" in metric_stats
            assert "trend" in metric_stats
            
        # Verify values
        assert stats["total_time"]["current"] == 1.0  # 0.6 + 0.4
        
    def test_calculate_io_operations(self, performance_data):
        """Test calculating I/O operation statistics."""
        stats = self.analyzer.calculate_io_operations(performance_data)
        
        assert isinstance(stats, dict)
        assert "read_ops" in stats
        assert "write_ops" in stats
        assert "total_ops" in stats
        
        # Check statistics structure
        for metric_stats in stats.values():
            assert "current" in metric_stats
            assert "mean" in metric_stats
            assert "max" in metric_stats
            assert "trend" in metric_stats
            
        # Verify values
        assert stats["total_ops"]["current"] == 165  # 110 + 55
        
    def test_identify_hotspots(self, performance_data):
        """Test identifying performance hotspots."""
        # Calculate metrics first
        exec_times = self.analyzer.calculate_execution_times(performance_data)
        memory_usage = self.analyzer.calculate_memory_usage(performance_data)
        cpu_usage = self.analyzer.calculate_cpu_usage(performance_data)
        io_ops = self.analyzer.calculate_io_operations(performance_data)
        
        # Identify hotspots
        hotspots = self.analyzer.identify_hotspots(
            exec_times, memory_usage, cpu_usage, io_ops
        )
        
        assert isinstance(hotspots, list)
        
        # Verify hotspot structure
        for hotspot in hotspots:
            assert "type" in hotspot
            assert "metric" in hotspot
            assert "value" in hotspot
            assert "threshold" in hotspot
            
    def test_identify_slow_methods(self, performance_data):
        """Test identifying slow methods."""
        exec_times = self.analyzer.calculate_execution_times(performance_data)
        slow_methods = self.analyzer.identify_slow_methods(exec_times)
        
        assert isinstance(slow_methods, dict)
        assert "slow_func" in slow_methods  # Should be identified as slow
        assert "test_func" not in slow_methods  # Should not be identified as slow
        
        # Check result structure
        for method, (time, freq) in slow_methods.items():
            assert isinstance(time, float)
            assert isinstance(freq, int)
            
    def test_identify_resource_bottlenecks(self, performance_data):
        """Test identifying resource bottlenecks."""
        memory_usage = self.analyzer.calculate_memory_usage(performance_data)
        cpu_usage = self.analyzer.calculate_cpu_usage(performance_data)
        io_ops = self.analyzer.calculate_io_operations(performance_data)
        
        bottlenecks = self.analyzer.identify_resource_bottlenecks(
            memory_usage, cpu_usage, io_ops
        )
        
        assert isinstance(bottlenecks, list)
        
        # Verify bottleneck structure
        for bottleneck in bottlenecks:
            assert "type" in bottleneck
            if bottleneck["type"] == "memory_growth":
                assert "current_usage" in bottleneck
                assert "growth_rate" in bottleneck
            elif bottleneck["type"] == "cpu_saturation":
                assert "current_usage" in bottleneck
                assert "threshold" in bottleneck
            elif bottleneck["type"] == "io_saturation":
                assert "current_ops" in bottleneck
                assert "threshold" in bottleneck
                
    def test_analyze_call_chains(self, performance_data):
        """Test analyzing call chains for bottlenecks."""
        exec_times = self.analyzer.calculate_execution_times(performance_data)
        bottlenecks = self.analyzer.analyze_call_chains(exec_times)
        
        assert isinstance(bottlenecks, list)
        
        # Verify bottleneck structure
        for bottleneck in bottlenecks:
            if bottleneck["type"] == "slow_call_chain":
                assert "path" in bottleneck
                assert "total_time" in bottleneck
                
    def test_calculate_trend(self):
        """Test calculating trend in values."""
        # Test increasing trend
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        trend = self.analyzer._calculate_trend(values)
        assert trend > 0
        
        # Test decreasing trend
        values = [5.0, 4.0, 3.0, 2.0, 1.0]
        trend = self.analyzer._calculate_trend(values)
        assert trend < 0
        
        # Test flat trend
        values = [1.0, 1.0, 1.0, 1.0, 1.0]
        trend = self.analyzer._calculate_trend(values)
        assert trend == 0
        
        # Test insufficient data
        values = [1.0]
        trend = self.analyzer._calculate_trend(values)
        assert trend == 0.0 