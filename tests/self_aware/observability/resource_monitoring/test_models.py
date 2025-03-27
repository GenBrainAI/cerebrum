import pytest
from datetime import datetime, timedelta
import uuid

from src.server.observability.resource_monitoring.models import (
    ResourceType, BudgetPeriod, ResourceUsage, Budget, BudgetAlert
)


class TestResourceType:
    """Tests for the ResourceType enum."""
    
    def test_resource_types(self):
        """Test that the ResourceType enum contains expected values."""
        assert ResourceType.CPU.value == "cpu"
        assert ResourceType.MEMORY.value == "memory"
        assert ResourceType.STORAGE.value == "storage"
        assert ResourceType.NETWORK.value == "network"
        assert ResourceType.API_CALLS.value == "api_calls"
        assert ResourceType.MODEL_TOKENS.value == "model_tokens"
        assert ResourceType.PROCESSING_TIME.value == "processing_time"
        assert ResourceType.CONCURRENT_TASKS.value == "concurrent_tasks"


class TestBudgetPeriod:
    """Tests for the BudgetPeriod enum."""
    
    def test_budget_periods(self):
        """Test that the BudgetPeriod enum contains expected values."""
        assert BudgetPeriod.HOURLY.value == "hourly"
        assert BudgetPeriod.DAILY.value == "daily"
        assert BudgetPeriod.WEEKLY.value == "weekly"
        assert BudgetPeriod.MONTHLY.value == "monthly"
        assert BudgetPeriod.QUARTERLY.value == "quarterly"
        assert BudgetPeriod.YEARLY.value == "yearly"
        assert BudgetPeriod.PERPETUAL.value == "perpetual"


class TestResourceUsage:
    """Tests for the ResourceUsage class."""
    
    def test_resource_usage_creation(self):
        """Test creating a ResourceUsage instance."""
        usage = ResourceUsage(
            resource_type=ResourceType.CPU,
            component="system",
            quantity=75.5,
            unit="percent",
            metadata={"process_id": 1234}
        )
        
        assert usage.resource_type == ResourceType.CPU
        assert usage.component == "system"
        assert usage.quantity == 75.5
        assert usage.unit == "percent"
        assert "timestamp" in usage.__dict__
        assert usage.metadata == {"process_id": 1234}
    
    def test_resource_usage_to_dict(self):
        """Test converting ResourceUsage to dictionary."""
        timestamp = datetime.now().isoformat()
        usage = ResourceUsage(
            resource_type=ResourceType.MEMORY,
            component="database",
            quantity=512.0,
            unit="MB",
            timestamp=timestamp,
            metadata={"db_name": "main"}
        )
        
        usage_dict = usage.to_dict()
        
        assert usage_dict["resource_type"] == "memory"
        assert usage_dict["component"] == "database"
        assert usage_dict["quantity"] == 512.0
        assert usage_dict["unit"] == "MB"
        assert usage_dict["timestamp"] == timestamp
        assert usage_dict["metadata"] == {"db_name": "main"}


class TestBudget:
    """Tests for the Budget class."""
    
    def test_budget_creation(self):
        """Test creating a Budget instance."""
        budget_id = str(uuid.uuid4())
        start_date = datetime.now().isoformat()
        
        budget = Budget(
            id=budget_id,
            resource_type=ResourceType.API_CALLS,
            components=["service_a", "service_b"],
            limit=1000.0,
            period=BudgetPeriod.DAILY,
            unit="calls",
            start_date=start_date,
            name="API Rate Limit",
            description="Daily API call budget",
            tags=["api", "external"],
            alert_thresholds={"warning": 70.0, "critical": 90.0},
            active=True
        )
        
        assert budget.id == budget_id
        assert budget.resource_type == ResourceType.API_CALLS
        assert budget.components == ["service_a", "service_b"]
        assert budget.limit == 1000.0
        assert budget.period == BudgetPeriod.DAILY
        assert budget.unit == "calls"
        assert budget.start_date == start_date
        assert budget.name == "API Rate Limit"
        assert budget.description == "Daily API call budget"
        assert budget.tags == ["api", "external"]
        assert budget.alert_thresholds == {"warning": 70.0, "critical": 90.0}
        assert budget.active is True
    
    def test_budget_to_dict(self):
        """Test converting Budget to dictionary."""
        budget_id = "test_budget_1"
        start_date = datetime.now().isoformat()
        
        budget = Budget(
            id=budget_id,
            resource_type=ResourceType.MODEL_TOKENS,
            components=["gpt-4"],
            limit=100000.0,
            period=BudgetPeriod.MONTHLY,
            unit="tokens",
            start_date=start_date,
            name="LLM Token Budget",
            description="Monthly token usage budget",
            tags=["llm", "cost"],
            alert_thresholds={"warning": 80.0, "critical": 95.0},
            active=True
        )
        
        budget_dict = budget.to_dict()
        
        assert budget_dict["id"] == budget_id
        assert budget_dict["resource_type"] == "model_tokens"
        assert budget_dict["components"] == ["gpt-4"]
        assert budget_dict["limit"] == 100000.0
        assert budget_dict["period"] == "monthly"
        assert budget_dict["unit"] == "tokens"
        assert budget_dict["start_date"] == start_date
        assert budget_dict["name"] == "LLM Token Budget"
        assert budget_dict["description"] == "Monthly token usage budget"
        assert budget_dict["tags"] == ["llm", "cost"]
        assert budget_dict["alert_thresholds"] == {"warning": 80.0, "critical": 95.0}
        assert budget_dict["active"] is True
    
    def test_budget_from_dict(self):
        """Test creating Budget from dictionary."""
        budget_dict = {
            "id": "test_budget_2",
            "resource_type": "storage",
            "components": ["user_uploads"],
            "limit": 5120.0,
            "period": "weekly",
            "unit": "MB",
            "start_date": datetime.now().isoformat(),
            "name": "Storage Budget",
            "description": "Weekly storage usage budget",
            "tags": ["storage", "uploads"],
            "alert_thresholds": {"warning": 70.0, "critical": 90.0},
            "active": True
        }
        
        budget = Budget.from_dict(budget_dict)
        
        assert budget.id == "test_budget_2"
        assert budget.resource_type == ResourceType.STORAGE
        assert budget.components == ["user_uploads"]
        assert budget.limit == 5120.0
        assert budget.period == BudgetPeriod.WEEKLY
        assert budget.unit == "MB"
        assert budget.start_date == budget_dict["start_date"]
        assert budget.name == "Storage Budget"
        assert budget.description == "Weekly storage usage budget"
        assert budget.tags == ["storage", "uploads"]
        assert budget.alert_thresholds == {"warning": 70.0, "critical": 90.0}
        assert budget.active is True


class TestBudgetAlert:
    """Tests for the BudgetAlert class."""
    
    def test_budget_alert_creation(self):
        """Test creating a BudgetAlert instance."""
        alert_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        alert = BudgetAlert(
            id=alert_id,
            budget_id="test_budget_1",
            threshold_name="warning",
            threshold_value=70.0,
            current_usage=75.5,
            percentage=75.5,
            timestamp=timestamp,
            acknowledged=False
        )
        
        assert alert.id == alert_id
        assert alert.budget_id == "test_budget_1"
        assert alert.threshold_name == "warning"
        assert alert.threshold_value == 70.0
        assert alert.current_usage == 75.5
        assert alert.percentage == 75.5
        assert alert.timestamp == timestamp
        assert alert.acknowledged is False
    
    def test_budget_alert_to_dict(self):
        """Test converting BudgetAlert to dictionary."""
        alert_id = "test_alert_1"
        timestamp = datetime.now().isoformat()
        
        alert = BudgetAlert(
            id=alert_id,
            budget_id="test_budget_2",
            threshold_name="critical",
            threshold_value=90.0,
            current_usage=95.0,
            percentage=95.0,
            timestamp=timestamp,
            acknowledged=True
        )
        
        alert_dict = alert.to_dict()
        
        assert alert_dict["id"] == alert_id
        assert alert_dict["budget_id"] == "test_budget_2"
        assert alert_dict["threshold_name"] == "critical"
        assert alert_dict["threshold_value"] == 90.0
        assert alert_dict["current_usage"] == 95.0
        assert alert_dict["percentage"] == 95.0
        assert alert_dict["timestamp"] == timestamp
        assert alert_dict["acknowledged"] is True
    
    def test_budget_alert_from_dict(self):
        """Test creating BudgetAlert from dictionary."""
        alert_dict = {
            "id": "test_alert_2",
            "budget_id": "test_budget_3",
            "threshold_name": "warning",
            "threshold_value": 80.0,
            "current_usage": 85.5,
            "percentage": 85.5,
            "timestamp": datetime.now().isoformat(),
            "acknowledged": False
        }
        
        alert = BudgetAlert.from_dict(alert_dict)
        
        assert alert.id == "test_alert_2"
        assert alert.budget_id == "test_budget_3"
        assert alert.threshold_name == "warning"
        assert alert.threshold_value == 80.0
        assert alert.current_usage == 85.5
        assert alert.percentage == 85.5
        assert alert.timestamp == alert_dict["timestamp"]
        assert alert.acknowledged is False 