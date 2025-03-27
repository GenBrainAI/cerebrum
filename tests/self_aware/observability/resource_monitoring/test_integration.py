import pytest
import pytest_asyncio
import asyncio
import tempfile
import shutil
import os
from datetime import datetime

from src.server.observability.resource_monitoring.models import (
    ResourceType, BudgetPeriod, ResourceUsage, Budget, BudgetAlert
)
from src.server.observability.resource_monitoring.resource_monitor import ResourceMonitor


@pytest.fixture
def temp_storage_dir():
    """Create a temporary directory for storage during tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest_asyncio.fixture
async def integration_monitor(temp_storage_dir):
    """Create a ResourceMonitor instance for integration testing."""
    monitor = ResourceMonitor(
        config={
            "storage_path": temp_storage_dir,
            "usage_retention_days": 7,
            "system_monitoring_enabled": True,
            "monitoring_interval_seconds": 10,
            "default_alert_thresholds": {
                "warning": 70.0,
                "critical": 90.0
            }
        }
    )
    
    # Initialize the monitor
    await monitor.initialize()
    
    return monitor


class TestResourceMonitorIntegration:
    """Integration tests for the ResourceMonitor class."""
    
    @pytest.mark.asyncio
    async def test_budget_lifecycle(self, integration_monitor):
        """Test the complete lifecycle of a budget."""
        # 1. Create a new budget
        api_budget = await integration_monitor.create_budget(
            resource_type=ResourceType.API_CALLS,
            limit=100.0,
            period=BudgetPeriod.DAILY,
            unit="calls",
            name="API Call Budget",
            description="Daily budget for API calls",
            components=["external_service"],
            tags=["api", "external"],
            alert_thresholds={"warning": 70.0, "critical": 90.0}
        )
        
        # Verify budget was created and stored
        assert api_budget.id in integration_monitor.budgets
        
        # 2. Record usage below warning threshold
        await integration_monitor.record_usage(
            resource_type=ResourceType.API_CALLS,
            component="external_service",
            quantity=50.0,
            unit="calls"
        )
        
        # Check budget status - should be below threshold
        budget_status = await integration_monitor.get_budget(api_budget.id)
        assert budget_status["usage"]["percentage"] == 50.0
        assert budget_status["usage"]["status"] == "ok"
        assert len(integration_monitor.alerts) == 0
        
        # 3. Record usage that crosses warning threshold
        await integration_monitor.record_usage(
            resource_type=ResourceType.API_CALLS,
            component="external_service",
            quantity=25.0,
            unit="calls"
        )
        
        # Check budget status - should be at warning level
        budget_status = await integration_monitor.get_budget(api_budget.id)
        assert budget_status["usage"]["percentage"] == 75.0
        assert budget_status["usage"]["status"] == "warning"
        
        # Should have created an alert
        assert len(integration_monitor.alerts) == 1
        alert_id = list(integration_monitor.alerts.keys())[0]
        alert = integration_monitor.alerts[alert_id]
        assert alert.threshold_name == "warning"
        assert alert.budget_id == api_budget.id
        
        # 4. Acknowledge the alert
        alert_result = await integration_monitor.acknowledge_alert(alert_id)
        assert alert_result["acknowledged"] is True
        
        # 5. Record usage that crosses critical threshold
        await integration_monitor.record_usage(
            resource_type=ResourceType.API_CALLS,
            component="external_service",
            quantity=20.0,
            unit="calls"
        )
        
        # Check budget status - should be at critical level
        budget_status = await integration_monitor.get_budget(api_budget.id)
        assert budget_status["usage"]["percentage"] == 95.0
        assert budget_status["usage"]["status"] == "critical"
        
        # Should have created a new alert - now we expect 3 total (2 warning and 1 critical)
        # One acknowledged warning alert, and two unacknowledged alerts (one warning, one critical) 
        assert len(integration_monitor.alerts) == 3
        
        # Check unacknowledged alerts
        unacknowledged_alerts = [a for a in integration_monitor.alerts.values() if not a.acknowledged]
        assert len(unacknowledged_alerts) == 2
        
        # Verify there's an unacknowledged critical alert
        critical_alerts = [a for a in unacknowledged_alerts if a.threshold_name == "critical"]
        assert len(critical_alerts) == 1
        
        # 6. Update the budget to increase the limit
        updated_budget = await integration_monitor.update_budget(
            api_budget.id,
            {
                "limit": 200.0,
                "name": "Updated API Budget"
            }
        )
        
        # Check that the budget was updated
        assert updated_budget.limit == 200.0
        assert updated_budget.name == "Updated API Budget"
        
        # 7. Check budget status again - should be back to OK
        budget_status = await integration_monitor.get_budget(api_budget.id)
        assert budget_status["usage"]["percentage"] == 47.5  # (50+25+20)/200 * 100
        assert budget_status["usage"]["status"] == "ok"
        
        # 8. Generate a report
        report = await integration_monitor.create_usage_report(
            resource_type=ResourceType.API_CALLS,
            component="external_service"
        )
        
        # Check report contains the usage data
        assert report["status"] == "success"
        assert report["summary"]["total_records"] == 3
        assert report["summary"]["overall"]["total_quantity"] == 95.0
        
        # 9. Create a resource usage history report with grouping
        report = await integration_monitor.create_usage_report(
            resource_type=ResourceType.API_CALLS,
            group_by="component"
        )
        
        # Check that the report includes grouped data
        assert "groups" in report["summary"]
        
        # 10. Clean up old data
        cleanup_result = await integration_monitor.clear_old_data()
        assert cleanup_result["usage_records_removed"] == 0  # Because our data is fresh
        
        # 11. Test storage and retrieval
        # Get budgets directory
        budget_dir = os.path.join(integration_monitor.config["storage_path"], "budgets")
        assert os.path.exists(budget_dir)
        
        # Verify budget file exists
        assert any(f.startswith(api_budget.id) for f in os.listdir(budget_dir))
        
        # Check usage file exists
        usage_file = os.path.join(integration_monitor.config["storage_path"], "usage_records.json")
        assert os.path.exists(usage_file)
        
        # 12. Create a new monitor instance to test loading from disk
        new_monitor = ResourceMonitor(
            config={
                "storage_path": integration_monitor.config["storage_path"],
                "usage_retention_days": 7
            }
        )
        
        # Initialize the new monitor
        await new_monitor.initialize()
        
        # Verify the budget was loaded
        assert api_budget.id in new_monitor.budgets
        loaded_budget = new_monitor.budgets[api_budget.id]
        assert loaded_budget.name == "Updated API Budget"
        assert loaded_budget.limit == 200.0
        
        # Verify usage records were loaded
        assert len(new_monitor.usage_records) == 3 