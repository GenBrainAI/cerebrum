"""
Tests for the metrics monitoring data models.
"""

import pytest
import json
from datetime import datetime

from src.server.observability.metrics_monitoring import (
    MetricType, MetricCategory, MetricPriority, MetricDefinition,
    MetricValue, MetricQuery, AnomalyDefinition, AnomalyEvent
)

class TestMetricTypes:
    """Tests for the enum types."""
    
    def test_metric_type_values(self):
        """Test metric type enum values."""
        assert MetricType.COUNTER.value == "counter"
        assert MetricType.GAUGE.value == "gauge"
        assert MetricType.HISTOGRAM.value == "histogram"
        assert MetricType.RATE.value == "rate"
        assert MetricType.DURATION.value == "duration"
        assert MetricType.STATE.value == "state"
    
    def test_metric_category_values(self):
        """Test metric category enum values."""
        assert MetricCategory.PERFORMANCE.value == "performance"
        assert MetricCategory.RELIABILITY.value == "reliability"
        assert MetricCategory.USAGE.value == "usage"
        assert MetricCategory.BEHAVIORAL.value == "behavioral"
        assert MetricCategory.COGNITIVE.value == "cognitive"
        assert MetricCategory.SYSTEM.value == "system"
        assert MetricCategory.SECURITY.value == "security"
        assert MetricCategory.CUSTOM.value == "custom"
    
    def test_metric_priority_values(self):
        """Test metric priority enum values."""
        assert MetricPriority.LOW.value == "low"
        assert MetricPriority.NORMAL.value == "normal"
        assert MetricPriority.HIGH.value == "high"
        assert MetricPriority.CRITICAL.value == "critical"

class TestMetricDefinition:
    """Tests for the MetricDefinition class."""
    
    def test_create_metric_definition(self):
        """Test creating a metric definition."""
        metric = MetricDefinition(
            id="performance.response_time",
            name="Response Time",
            description="API response time",
            type=MetricType.HISTOGRAM,
            category=MetricCategory.PERFORMANCE,
            unit="ms",
            priority=MetricPriority.HIGH,
            components=["api", "web"],
            tags=["latency", "api"],
            aggregation_method="average",
            sampling_interval=None,
            retention_days=60
        )
        
        assert metric.id == "performance.response_time"
        assert metric.name == "Response Time"
        assert metric.description == "API response time"
        assert metric.type == MetricType.HISTOGRAM
        assert metric.category == MetricCategory.PERFORMANCE
        assert metric.unit == "ms"
        assert metric.priority == MetricPriority.HIGH
        assert metric.components == ["api", "web"]
        assert metric.tags == ["latency", "api"]
        assert metric.aggregation_method == "average"
        assert metric.sampling_interval is None
        assert metric.retention_days == 60
    
    def test_to_dict(self):
        """Test converting metric definition to dictionary."""
        metric = MetricDefinition(
            id="system.cpu.usage",
            name="CPU Usage",
            description="Percentage of CPU usage",
            type=MetricType.GAUGE,
            category=MetricCategory.SYSTEM,
            unit="percent",
            priority=MetricPriority.HIGH,
            components=["system"],
            tags=["resource", "cpu"],
            aggregation_method="average",
            sampling_interval=60,
            retention_days=30
        )
        
        data = metric.to_dict()
        
        assert data["id"] == "system.cpu.usage"
        assert data["name"] == "CPU Usage"
        assert data["description"] == "Percentage of CPU usage"
        assert data["type"] == "gauge"
        assert data["category"] == "system"
        assert data["unit"] == "percent"
        assert data["priority"] == "high"
        assert data["components"] == ["system"]
        assert data["tags"] == ["resource", "cpu"]
        assert data["aggregation_method"] == "average"
        assert data["sampling_interval"] == 60
        assert data["retention_days"] == 30
    
    def test_from_dict(self):
        """Test creating metric definition from dictionary."""
        data = {
            "id": "reliability.errors",
            "name": "Error Count",
            "description": "Number of errors",
            "type": "counter",
            "category": "reliability",
            "unit": "errors",
            "priority": "critical",
            "components": ["api", "database"],
            "tags": ["errors", "reliability"],
            "aggregation_method": "sum",
            "sampling_interval": None,
            "retention_days": 90
        }
        
        metric = MetricDefinition.from_dict(data)
        
        assert metric.id == "reliability.errors"
        assert metric.name == "Error Count"
        assert metric.description == "Number of errors"
        assert metric.type == MetricType.COUNTER
        assert metric.category == MetricCategory.RELIABILITY
        assert metric.unit == "errors"
        assert metric.priority == MetricPriority.CRITICAL
        assert metric.components == ["api", "database"]
        assert metric.tags == ["errors", "reliability"]
        assert metric.aggregation_method == "sum"
        assert metric.sampling_interval is None
        assert metric.retention_days == 90
    
    def test_serialization_roundtrip(self):
        """Test serialization and deserialization roundtrip."""
        original = MetricDefinition(
            id="performance.throughput",
            name="Throughput",
            description="Number of requests per second",
            type=MetricType.RATE,
            category=MetricCategory.PERFORMANCE,
            unit="requests/sec",
            priority=MetricPriority.HIGH,
            components=["api"],
            tags=["performance", "throughput"],
            aggregation_method="average",
            sampling_interval=10,
            retention_days=45
        )
        
        # Convert to dictionary
        data = original.to_dict()
        
        # Convert back to object
        result = MetricDefinition.from_dict(data)
        
        # Check all fields match
        assert result.id == original.id
        assert result.name == original.name
        assert result.description == original.description
        assert result.type == original.type
        assert result.category == original.category
        assert result.unit == original.unit
        assert result.priority == original.priority
        assert result.components == original.components
        assert result.tags == original.tags
        assert result.aggregation_method == original.aggregation_method
        assert result.sampling_interval == original.sampling_interval
        assert result.retention_days == original.retention_days

class TestMetricValue:
    """Tests for the MetricValue class."""
    
    def test_create_metric_value(self):
        """Test creating a metric value."""
        timestamp = datetime.now().isoformat()
        value = MetricValue(
            metric_id="system.cpu.usage",
            value=45.2,
            timestamp=timestamp,
            component="system",
            context={"hostname": "server-1"}
        )
        
        assert value.metric_id == "system.cpu.usage"
        assert value.value == 45.2
        assert value.timestamp == timestamp
        assert value.component == "system"
        assert value.context == {"hostname": "server-1"}
    
    def test_default_timestamp(self):
        """Test default timestamp generation."""
        before = datetime.now().isoformat()
        value = MetricValue(
            metric_id="system.memory.usage",
            value=78.5,
            component="system"
        )
        after = datetime.now().isoformat()
        
        # Timestamp should be between before and after
        assert before <= value.timestamp <= after
    
    def test_to_dict(self):
        """Test converting metric value to dictionary."""
        timestamp = "2023-01-15T12:34:56.789012"
        value = MetricValue(
            metric_id="system.disk.usage",
            value=85.3,
            timestamp=timestamp,
            component="system",
            context={"path": "/"}
        )
        
        data = value.to_dict()
        
        assert data["metric_id"] == "system.disk.usage"
        assert data["value"] == 85.3
        assert data["timestamp"] == timestamp
        assert data["component"] == "system"
        assert data["context"] == {"path": "/"}
    
    def test_from_dict(self):
        """Test creating metric value from dictionary."""
        timestamp = "2023-01-15T12:34:56.789012"
        data = {
            "metric_id": "performance.response_time",
            "value": 125.7,
            "timestamp": timestamp,
            "component": "api",
            "context": {"endpoint": "/users"}
        }
        
        value = MetricValue.from_dict(data)
        
        assert value.metric_id == "performance.response_time"
        assert value.value == 125.7
        assert value.timestamp == timestamp
        assert value.component == "api"
        assert value.context == {"endpoint": "/users"}

class TestAnomalyDefinition:
    """Tests for the AnomalyDefinition class."""
    
    def test_create_anomaly_definition(self):
        """Test creating an anomaly definition."""
        anomaly = AnomalyDefinition(
            id="anomaly_123456",
            name="High CPU Usage",
            description="Detects abnormally high CPU usage",
            metric_id="system.cpu.usage",
            detection_method="threshold",
            parameters={"max": 90.0},
            severity="warning",
            enabled=True
        )
        
        assert anomaly.id == "anomaly_123456"
        assert anomaly.name == "High CPU Usage"
        assert anomaly.description == "Detects abnormally high CPU usage"
        assert anomaly.metric_id == "system.cpu.usage"
        assert anomaly.detection_method == "threshold"
        assert anomaly.parameters == {"max": 90.0}
        assert anomaly.severity == "warning"
        assert anomaly.enabled is True
    
    def test_to_dict(self):
        """Test converting anomaly definition to dictionary."""
        anomaly = AnomalyDefinition(
            id="anomaly_234567",
            name="Slow Response Time",
            description="Detects abnormally slow response times",
            metric_id="performance.response_time",
            detection_method="zscore",
            parameters={"threshold": 3.0},
            severity="critical",
            enabled=True
        )
        
        data = anomaly.to_dict()
        
        assert data["id"] == "anomaly_234567"
        assert data["name"] == "Slow Response Time"
        assert data["description"] == "Detects abnormally slow response times"
        assert data["metric_id"] == "performance.response_time"
        assert data["detection_method"] == "zscore"
        assert data["parameters"] == {"threshold": 3.0}
        assert data["severity"] == "critical"
        assert data["enabled"] is True
    
    def test_from_dict(self):
        """Test creating anomaly definition from dictionary."""
        data = {
            "id": "anomaly_345678",
            "name": "Low Memory",
            "description": "Detects critically low memory",
            "metric_id": "system.memory.available",
            "detection_method": "threshold",
            "parameters": {"min": 500},
            "severity": "critical",
            "enabled": True
        }
        
        anomaly = AnomalyDefinition.from_dict(data)
        
        assert anomaly.id == "anomaly_345678"
        assert anomaly.name == "Low Memory"
        assert anomaly.description == "Detects critically low memory"
        assert anomaly.metric_id == "system.memory.available"
        assert anomaly.detection_method == "threshold"
        assert anomaly.parameters == {"min": 500}
        assert anomaly.severity == "critical"
        assert anomaly.enabled is True

class TestAnomalyEvent:
    """Tests for the AnomalyEvent class."""
    
    def test_create_anomaly_event(self):
        """Test creating an anomaly event."""
        timestamp = datetime.now().isoformat()
        event = AnomalyEvent(
            id="event_123456",
            anomaly_id="anomaly_345678",
            metric_id="system.cpu.usage",
            timestamp=timestamp,
            value=95.2,
            expected_range=(0.0, 90.0),
            deviation_percentage=5.78,
            severity="warning",
            component="system",
            context={"hostname": "server-1"},
            acknowledged=False
        )
        
        assert event.id == "event_123456"
        assert event.anomaly_id == "anomaly_345678"
        assert event.metric_id == "system.cpu.usage"
        assert event.timestamp == timestamp
        assert event.value == 95.2
        assert event.expected_range == (0.0, 90.0)
        assert event.deviation_percentage == 5.78
        assert event.severity == "warning"
        assert event.component == "system"
        assert event.context == {"hostname": "server-1"}
        assert event.acknowledged is False
    
    def test_to_dict(self):
        """Test converting anomaly event to dictionary."""
        timestamp = "2023-01-15T12:34:56.789012"
        event = AnomalyEvent(
            id="event_234567",
            anomaly_id="anomaly_345678",
            metric_id="performance.response_time",
            timestamp=timestamp,
            value=450.5,
            expected_range=(0.0, 300.0),
            deviation_percentage=50.17,
            severity="critical",
            component="api",
            context={"endpoint": "/users"},
            acknowledged=True
        )
        
        data = event.to_dict()
        
        assert data["id"] == "event_234567"
        assert data["anomaly_id"] == "anomaly_345678"
        assert data["metric_id"] == "performance.response_time"
        assert data["timestamp"] == timestamp
        assert data["value"] == 450.5
        assert data["expected_range"] == (0.0, 300.0)
        assert data["deviation_percentage"] == 50.17
        assert data["severity"] == "critical"
        assert data["component"] == "api"
        assert data["context"] == {"endpoint": "/users"}
        assert data["acknowledged"] is True
    
    def test_from_dict(self):
        """Test creating anomaly event from dictionary."""
        timestamp = "2023-01-15T12:34:56.789012"
        data = {
            "id": "event_345678",
            "anomaly_id": "anomaly_456789",
            "metric_id": "reliability.errors",
            "timestamp": timestamp,
            "value": 25,
            "expected_range": (0, 10),
            "deviation_percentage": 150.0,
            "severity": "critical",
            "component": "database",
            "context": {"query": "SELECT * FROM users"},
            "acknowledged": False
        }
        
        event = AnomalyEvent.from_dict(data)
        
        assert event.id == "event_345678"
        assert event.anomaly_id == "anomaly_456789"
        assert event.metric_id == "reliability.errors"
        assert event.timestamp == timestamp
        assert event.value == 25
        assert event.expected_range == (0, 10)
        assert event.deviation_percentage == 150.0
        assert event.severity == "critical"
        assert event.component == "database"
        assert event.context == {"query": "SELECT * FROM users"}
        assert event.acknowledged is False
    
    def test_acknowledge(self):
        """Test acknowledging an anomaly event."""
        event = AnomalyEvent(
            id="event_456789",
            anomaly_id="anomaly_567890",
            metric_id="system.disk.usage",
            timestamp=datetime.now().isoformat(),
            value=98.7,
            expected_range=(0.0, 90.0),
            deviation_percentage=9.67,
            severity="warning",
            component="system",
            context={"path": "/"}
        )
        
        assert event.acknowledged is False
        
        # Acknowledge the event
        event.acknowledged = True
        
        assert event.acknowledged is True 