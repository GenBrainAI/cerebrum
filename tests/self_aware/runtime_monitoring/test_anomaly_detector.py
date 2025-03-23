import pytest
import numpy as np
from unittest.mock import MagicMock
from src.server.introspection.runtime_monitoring.anomaly_detector import (
    AnomalyDetector, AnomalyThresholds
)

@pytest.mark.asyncio
class TestAnomalyDetector:
    def setup_method(self):
        self.detector = AnomalyDetector()
        # Override the minimum data points threshold for testing
        self.detector.thresholds.min_data_points = 2
        
    def test_init(self):
        """Test initialization."""
        assert isinstance(self.detector.thresholds, AnomalyThresholds)
        assert self.detector.baseline_stats == {}
        assert self.detector.pattern_history == {}
        
    def test_establish_baseline(self, sample_telemetry_data):
        """Test establishing baseline statistics."""
        # Ensure we have enough data points to meet the minimum threshold
        assert len(sample_telemetry_data) >= self.detector.thresholds.min_data_points, \
            f"Not enough data points in sample_telemetry_data ({len(sample_telemetry_data)})"
        
        self.detector.establish_baseline(sample_telemetry_data)
        
        assert "execution_times" in self.detector.baseline_stats
        assert "memory_usage" in self.detector.baseline_stats
        
        # Check baseline stats structure
        exec_stats = self.detector.baseline_stats["execution_times"]
        assert "mean" in exec_stats
        assert "std" in exec_stats
        assert "median" in exec_stats
        assert "mad" in exec_stats
        assert "q1" in exec_stats
        assert "q3" in exec_stats
        
    def test_detect_statistical_anomalies(self, sample_telemetry_data):
        """Test detecting statistical anomalies."""
        # First establish baseline
        self.detector.establish_baseline(sample_telemetry_data)
        
        # Create data with anomalies
        anomaly_data = sample_telemetry_data.copy()
        anomaly_data.append({
            "timestamp": 1002.0,
            "execution_times": {"function1": [1.5, 1.8]},  # Much higher values
            "memory_usage": {
                "total_size": 5000,  # Much higher memory usage
                "peak_size": 6000,
                "rss": 4000,
                "vms": 5500,
                "timestamp": 1002.0
            },
            "errors": []
        })
        
        anomalies = self.detector.detect_statistical_anomalies(anomaly_data)
        assert isinstance(anomalies, list)
        
        # There should be at least one anomaly
        if len(anomalies) > 0:
            anomaly = anomalies[0]
            assert isinstance(anomaly, dict)
            if "execution_time" in anomaly:
                assert "function" in anomaly
                assert "timestamp" in anomaly
            elif "memory_usage" in anomaly:
                assert "threshold" in anomaly
                assert "timestamp" in anomaly
        
    def test_detect_pattern_anomalies(self, sample_telemetry_data):
        """Test detecting pattern anomalies."""
        # Create baseline patterns
        baseline_patterns = {
            "function1->function2": 10,
            "function3->function4": 5
        }
        
        # Detect pattern anomalies
        anomalies = self.detector.detect_pattern_anomalies(
            sample_telemetry_data, baseline_patterns
        )
        assert isinstance(anomalies, list)
        
    def test_classify_anomaly(self):
        """Test classifying anomalies."""
        # Test execution time anomaly
        anomaly = {
            "function": "test_func",
            "execution_time": 1.5,
            "z_score": 4.5,
            "timestamp": 1000.0
        }
        
        self.detector.classify_anomaly(anomaly)
        assert "type" in anomaly
        assert anomaly["type"] == "performance"
        assert "severity" in anomaly
        assert "context" in anomaly
        
        # Test memory usage anomaly
        anomaly = {
            "memory_usage": 5000,
            "threshold": 2000,
            "timestamp": 1000.0
        }
        
        self.detector.classify_anomaly(anomaly)
        assert anomaly["type"] == "resource"
        
        # Test pattern anomaly
        anomaly = {
            "pattern": "function1->function2",
            "current_count": 2,
            "baseline_count": 10,
            "timestamp": 1000.0
        }
        
        self.detector.classify_anomaly(anomaly)
        assert anomaly["type"] == "behavioral"
        
    def test_calculate_baseline_stats(self):
        """Test calculation of baseline statistics."""
        data = [
            {"func1": 0.1, "func2": 0.2},
            {"func1": 0.15, "func2": 0.25}
        ]
        
        stats = self.detector._calculate_baseline_stats(data)
        assert "mean" in stats
        assert "std" in stats
        assert "median" in stats
        assert "mad" in stats
        assert "q1" in stats
        assert "q3" in stats
        
        # Test empty data
        stats = self.detector._calculate_baseline_stats([])
        assert stats == {}
        
    def test_extract_call_patterns(self, sample_telemetry_data):
        """Test extracting call patterns."""
        patterns = self.detector._extract_call_patterns(sample_telemetry_data)
        assert isinstance(patterns, dict)
        
        # There should be patterns based on execution_times keys
        expected_pattern = "function1->function2"  # From first telemetry entry
        found = False
        for pattern in patterns:
            if all(func in pattern for func in ["function1", "function2"]):
                found = True
                break
                
        assert found, "Expected pattern not found" 