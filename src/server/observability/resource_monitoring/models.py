from typing import Dict, List, Optional, Any, Union, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import uuid
import json


class ResourceType(Enum):
    """Types of resources that can be monitored."""
    CPU = "cpu"
    MEMORY = "memory"
    STORAGE = "storage"
    NETWORK = "network"
    API_CALLS = "api_calls"
    MODEL_TOKENS = "model_tokens"
    PROCESSING_TIME = "processing_time"
    CONCURRENT_TASKS = "concurrent_tasks"
    GPU = "gpu"
    DATABASE = "database"
    EXTERNAL_SERVICE = "external_service"
    CUSTOM = "custom"


class BudgetPeriod(Enum):
    """Time periods for budget tracking."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    PERPETUAL = "perpetual"


class AlertLevel(Enum):
    """Severity levels for resource alerts."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class ResourceUnit(Enum):
    """Units for measuring resources."""
    PERCENTAGE = "percentage"
    BYTES = "bytes"
    KB = "KB"
    MB = "MB"
    GB = "GB"
    REQUESTS = "requests"
    TOKENS = "tokens"
    MILLISECONDS = "ms"
    SECONDS = "seconds"
    COUNT = "count"
    OPERATIONS = "operations"
    CUSTOM = "custom"
    
    @classmethod
    def convert(cls, value: float, from_unit: 'ResourceUnit', to_unit: 'ResourceUnit') -> float:
        """Convert between compatible units."""
        # Memory unit conversions
        memory_units = {
            cls.BYTES: 1,
            cls.KB: 1024,
            cls.MB: 1024 * 1024,
            cls.GB: 1024 * 1024 * 1024
        }
        
        # Time unit conversions
        time_units = {
            cls.MILLISECONDS: 1,
            cls.SECONDS: 1000
        }
        
        # Check if units are compatible
        if from_unit in memory_units and to_unit in memory_units:
            return value * memory_units[from_unit] / memory_units[to_unit]
        
        if from_unit in time_units and to_unit in time_units:
            return value * time_units[from_unit] / time_units[to_unit]
        
        # If units are the same or incompatible, return original value
        return value


@dataclass
class ResourceUsage:
    """Usage data for a specific resource."""
    resource_type: ResourceType
    component: str
    quantity: float
    unit: ResourceUnit
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "resource_type": self.resource_type.value,
            "component": self.component,
            "quantity": self.quantity,
            "unit": self.unit.value,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResourceUsage':
        """Create from dictionary."""
        return cls(
            resource_type=ResourceType(data.get("resource_type")),
            component=data.get("component", ""),
            quantity=data.get("quantity", 0.0),
            unit=ResourceUnit(data.get("unit")),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            metadata=data.get("metadata", {})
        )
    
    def convert_unit(self, to_unit: ResourceUnit) -> 'ResourceUsage':
        """Convert to a different unit and return new ResourceUsage."""
        new_quantity = ResourceUnit.convert(self.quantity, self.unit, to_unit)
        return ResourceUsage(
            resource_type=self.resource_type,
            component=self.component,
            quantity=new_quantity,
            unit=to_unit,
            timestamp=self.timestamp,
            metadata=self.metadata.copy()
        )


@dataclass
class Budget:
    """Budget for a specific resource."""
    id: str
    resource_type: ResourceType
    components: List[str]  # Components this budget applies to, empty means all
    limit: float
    period: BudgetPeriod
    unit: ResourceUnit
    start_date: str
    name: str
    description: str
    tags: List[str] = field(default_factory=list)
    alert_thresholds: Dict[str, float] = field(default_factory=dict)
    active: bool = True
    priority: int = 0  # Higher priority budgets override lower ones
    owners: List[str] = field(default_factory=list)  # User IDs who own/manage this budget
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "resource_type": self.resource_type.value,
            "components": self.components,
            "limit": self.limit,
            "period": self.period.value,
            "unit": self.unit.value,
            "start_date": self.start_date,
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "alert_thresholds": self.alert_thresholds,
            "active": self.active,
            "priority": self.priority,
            "owners": self.owners
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Budget':
        """Create from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            resource_type=ResourceType(data.get("resource_type")),
            components=data.get("components", []),
            limit=data.get("limit", 0.0),
            period=BudgetPeriod(data.get("period")),
            unit=ResourceUnit(data.get("unit")),
            start_date=data.get("start_date", datetime.now().isoformat()),
            name=data.get("name", ""),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            alert_thresholds=data.get("alert_thresholds", {}),
            active=data.get("active", True),
            priority=data.get("priority", 0),
            owners=data.get("owners", [])
        )
    
    def get_period_start(self, current_time: Optional[datetime] = None) -> datetime:
        """Calculate the start of the current budget period."""
        if not current_time:
            current_time = datetime.now()
            
        start_date = datetime.fromisoformat(self.start_date)
        
        if self.period == BudgetPeriod.HOURLY:
            return current_time.replace(minute=0, second=0, microsecond=0)
        
        elif self.period == BudgetPeriod.DAILY:
            return current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        
        elif self.period == BudgetPeriod.WEEKLY:
            # Start of the current week (Monday)
            return (current_time - timedelta(days=current_time.weekday())).replace(
                hour=0, minute=0, second=0, microsecond=0)
        
        elif self.period == BudgetPeriod.MONTHLY:
            return current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        elif self.period == BudgetPeriod.QUARTERLY:
            # Find start of quarter
            quarter_month = ((current_time.month - 1) // 3) * 3 + 1
            return current_time.replace(month=quarter_month, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        elif self.period == BudgetPeriod.YEARLY:
            return current_time.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        elif self.period == BudgetPeriod.PERPETUAL:
            return start_date
        
        # Default to start of day
        return current_time.replace(hour=0, minute=0, second=0, microsecond=0)


@dataclass
class BudgetAlert:
    """Alert when a budget threshold is reached."""
    id: str
    budget_id: str
    threshold_name: str
    threshold_value: float
    current_usage: float
    percentage: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    acknowledged: bool = False
    level: AlertLevel = AlertLevel.WARNING
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "budget_id": self.budget_id,
            "threshold_name": self.threshold_name,
            "threshold_value": self.threshold_value,
            "current_usage": self.current_usage,
            "percentage": self.percentage,
            "timestamp": self.timestamp,
            "acknowledged": self.acknowledged,
            "level": self.level.value,
            "details": self.details
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BudgetAlert':
        """Create from dictionary."""
        level_str = data.get("level", "warning")
        try:
            level = AlertLevel(level_str)
        except ValueError:
            level = AlertLevel.WARNING
            
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            budget_id=data.get("budget_id", ""),
            threshold_name=data.get("threshold_name", ""),
            threshold_value=data.get("threshold_value", 0.0),
            current_usage=data.get("current_usage", 0.0),
            percentage=data.get("percentage", 0.0),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            acknowledged=data.get("acknowledged", False),
            level=level,
            details=data.get("details", {})
        )


@dataclass
class ResourceAllocation:
    """Resource allocation for a component."""
    id: str
    resource_type: ResourceType
    component: str
    allocated: float
    unit: ResourceUnit
    priority: int
    start_time: str
    end_time: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "resource_type": self.resource_type.value,
            "component": self.component,
            "allocated": self.allocated,
            "unit": self.unit.value,
            "priority": self.priority,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResourceAllocation':
        """Create from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            resource_type=ResourceType(data.get("resource_type")),
            component=data.get("component", ""),
            allocated=data.get("allocated", 0.0),
            unit=ResourceUnit(data.get("unit")),
            priority=data.get("priority", 0),
            start_time=data.get("start_time", datetime.now().isoformat()),
            end_time=data.get("end_time"),
            metadata=data.get("metadata", {})
        )


@dataclass
class ResourceForecast:
    """Forecast of resource usage."""
    id: str
    resource_type: ResourceType
    component: str
    forecasted_usage: List[Tuple[str, float]]  # [(timestamp, value), ...]
    unit: ResourceUnit
    method: str  # Forecasting method used
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    confidence: float = 0.0  # Confidence level (0-1)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "resource_type": self.resource_type.value,
            "component": self.component,
            "forecasted_usage": self.forecasted_usage,
            "unit": self.unit.value,
            "method": self.method,
            "created_at": self.created_at,
            "confidence": self.confidence,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResourceForecast':
        """Create from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            resource_type=ResourceType(data.get("resource_type")),
            component=data.get("component", ""),
            forecasted_usage=data.get("forecasted_usage", []),
            unit=ResourceUnit(data.get("unit")),
            method=data.get("method", ""),
            created_at=data.get("created_at", datetime.now().isoformat()),
            confidence=data.get("confidence", 0.0),
            metadata=data.get("metadata", {})
        ) 