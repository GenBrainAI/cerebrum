"""
Data models for the metrics monitoring system.

This module defines the core data structures used by the MetricsCollector for
tracking system metrics, defining anomaly detection rules, and storing metric values.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import uuid
from datetime import datetime
from enum import Enum


class MetricType(Enum):
    """Types of metrics that can be collected."""
    COUNTER = "counter"       # Monotonically increasing value
    GAUGE = "gauge"           # Value that can increase or decrease
    HISTOGRAM = "histogram"   # Distribution of values
    RATE = "rate"             # Rate of change over time
    DURATION = "duration"     # Time duration measurement
    STATE = "state"           # Categorical state information


class MetricCategory(Enum):
    """Categories of metrics."""
    PERFORMANCE = "performance"    # Performance-related metrics
    RELIABILITY = "reliability"    # Reliability-related metrics
    USAGE = "usage"                # Usage-related metrics
    BEHAVIORAL = "behavioral"      # Behavior-related metrics
    COGNITIVE = "cognitive"        # Cognitive process metrics
    SYSTEM = "system"              # System-level metrics
    SECURITY = "security"          # Security-related metrics
    CUSTOM = "custom"              # Custom/user-defined metrics


class MetricPriority(Enum):
    """Priority levels for metrics."""
    LOW = "low"           # Nice to have, not critical
    NORMAL = "normal"     # Standard importance
    HIGH = "high"         # Important for monitoring
    CRITICAL = "critical" # Essential for system health


@dataclass
class MetricDefinition:
    """Definition of a metric to be collected."""
    id: str
    name: str
    description: str
    type: MetricType
    category: MetricCategory
    unit: str
    priority: MetricPriority = MetricPriority.NORMAL
    components: List[str] = field(default_factory=list)  # Components this metric applies to
    tags: List[str] = field(default_factory=list)
    aggregation_method: str = "average"  # How to aggregate multiple values
    sampling_interval: Optional[int] = None  # In seconds, None for event-based
    retention_days: int = 30
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "type": self.type.value,
            "category": self.category.value,
            "unit": self.unit,
            "priority": self.priority.value,
            "components": self.components,
            "tags": self.tags,
            "aggregation_method": self.aggregation_method,
            "sampling_interval": self.sampling_interval,
            "retention_days": self.retention_days
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MetricDefinition':
        """Create from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            description=data.get("description", ""),
            type=MetricType(data.get("type")),
            category=MetricCategory(data.get("category")),
            unit=data.get("unit", ""),
            priority=MetricPriority(data.get("priority", "normal")),
            components=data.get("components", []),
            tags=data.get("tags", []),
            aggregation_method=data.get("aggregation_method", "average"),
            sampling_interval=data.get("sampling_interval"),
            retention_days=data.get("retention_days", 30)
        )


@dataclass
class MetricValue:
    """A single metric value."""
    metric_id: str
    value: Any
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    component: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "metric_id": self.metric_id,
            "value": self.value,
            "timestamp": self.timestamp,
            "component": self.component,
            "context": self.context
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MetricValue':
        """Create from dictionary."""
        return cls(
            metric_id=data.get("metric_id", ""),
            value=data.get("value"),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            component=data.get("component", ""),
            context=data.get("context", {})
        )


@dataclass
class MetricQuery:
    """Query parameters for retrieving metric values."""
    metric_ids: Optional[List[str]] = None
    components: Optional[List[str]] = None
    categories: Optional[List[MetricCategory]] = None
    tags: Optional[List[str]] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    limit: int = 1000
    aggregation: Optional[str] = None  # Override aggregation method
    group_by: Optional[str] = None  # Group results by field


@dataclass
class AnomalyDefinition:
    """Definition of an anomaly detection rule."""
    id: str
    name: str
    description: str
    metric_id: str
    detection_method: str  # "threshold", "zscore", "mad", "iqr", "custom"
    parameters: Dict[str, Any]  # Method-specific parameters
    severity: str  # "info", "warning", "critical"
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "metric_id": self.metric_id,
            "detection_method": self.detection_method,
            "parameters": self.parameters,
            "severity": self.severity,
            "enabled": self.enabled
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnomalyDefinition':
        """Create from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            description=data.get("description", ""),
            metric_id=data.get("metric_id", ""),
            detection_method=data.get("detection_method", ""),
            parameters=data.get("parameters", {}),
            severity=data.get("severity", "warning"),
            enabled=data.get("enabled", True)
        )


@dataclass
class AnomalyEvent:
    """An detected anomaly event."""
    id: str
    anomaly_id: str
    metric_id: str
    timestamp: str
    value: Any
    expected_range: Tuple[float, float]
    deviation_percentage: float
    severity: str
    component: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "anomaly_id": self.anomaly_id,
            "metric_id": self.metric_id,
            "timestamp": self.timestamp,
            "value": self.value,
            "expected_range": self.expected_range,
            "deviation_percentage": self.deviation_percentage,
            "severity": self.severity,
            "component": self.component,
            "context": self.context,
            "acknowledged": self.acknowledged
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnomalyEvent':
        """Create from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            anomaly_id=data.get("anomaly_id", ""),
            metric_id=data.get("metric_id", ""),
            timestamp=data.get("timestamp", ""),
            value=data.get("value"),
            expected_range=tuple(data.get("expected_range", (0, 0))),
            deviation_percentage=data.get("deviation_percentage", 0.0),
            severity=data.get("severity", "warning"),
            component=data.get("component"),
            context=data.get("context", {}),
            acknowledged=data.get("acknowledged", False)
        ) 