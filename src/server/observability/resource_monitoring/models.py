from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import uuid


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


class BudgetPeriod(Enum):
    """Time periods for budget tracking."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    PERPETUAL = "perpetual"


@dataclass
class ResourceUsage:
    """Usage data for a specific resource."""
    resource_type: ResourceType
    component: str
    quantity: float
    unit: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "resource_type": self.resource_type.value,
            "component": self.component,
            "quantity": self.quantity,
            "unit": self.unit,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }


@dataclass
class Budget:
    """Budget for a specific resource."""
    id: str
    resource_type: ResourceType
    components: List[str]  # Components this budget applies to, empty means all
    limit: float
    period: BudgetPeriod
    unit: str
    start_date: str
    name: str
    description: str
    tags: List[str] = field(default_factory=list)
    alert_thresholds: Dict[str, float] = field(default_factory=dict)
    active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "resource_type": self.resource_type.value,
            "components": self.components,
            "limit": self.limit,
            "period": self.period.value,
            "unit": self.unit,
            "start_date": self.start_date,
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "alert_thresholds": self.alert_thresholds,
            "active": self.active
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
            unit=data.get("unit", ""),
            start_date=data.get("start_date", datetime.now().isoformat()),
            name=data.get("name", ""),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            alert_thresholds=data.get("alert_thresholds", {}),
            active=data.get("active", True)
        )


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
            "acknowledged": self.acknowledged
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BudgetAlert':
        """Create from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            budget_id=data.get("budget_id", ""),
            threshold_name=data.get("threshold_name", ""),
            threshold_value=data.get("threshold_value", 0.0),
            current_usage=data.get("current_usage", 0.0),
            percentage=data.get("percentage", 0.0),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            acknowledged=data.get("acknowledged", False)
        ) 