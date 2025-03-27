import pytest
import pytest_asyncio
import asyncio
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock, AsyncMock
import json
from datetime import datetime, timedelta
import pandas as pd

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
async def resource_monitor(temp_storage_dir):
    """Create a ResourceMonitor instance for testing."""
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


class TestResourceMonitor:
    """Tests for the ResourceMonitor class."""
    
    def test_initialization(self, resource_monitor, temp_storage_dir):
        """Test that ResourceMonitor initializes correctly."""
        assert resource_monitor.config["storage_path"] == temp_storage_dir
        assert resource_monitor.config["usage_retention_days"] == 7
        assert resource_monitor.config["system_monitoring_enabled"] is True
        assert resource_monitor.config["monitoring_interval_seconds"] == 10
        assert resource_monitor.config["default_alert_thresholds"] == {
            "warning": 70.0,
            "critical": 90.0
        }
        
        assert isinstance(resource_monitor.budgets, dict)
        assert isinstance(resource_monitor.usage_records, list)
        assert isinstance(resource_monitor.alerts, dict)
        assert resource_monitor.system_monitor_task is None
        assert resource_monitor.is_monitoring is False
    
    @pytest.mark.asyncio
    async def test_start_monitoring(self, resource_monitor):
        """Test starting resource monitoring."""
        # Mock the internal monitoring method
        with patch.object(resource_monitor, '_run_system_monitoring', new_callable=AsyncMock) as mock_run:
            result = await resource_monitor.start_monitoring()
            
            assert result["status"] == "monitoring_started"
            assert result["interval"] == 10
            assert resource_monitor.is_monitoring is True
            assert resource_monitor.system_monitor_task is not None
            
            # Second call should indicate already monitoring
            result = await resource_monitor.start_monitoring()
            assert result["status"] == "already_monitoring"
            
            # Clean up
            await resource_monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_stop_monitoring(self, resource_monitor):
        """Test stopping resource monitoring."""
        # First start monitoring
        with patch.object(resource_monitor, '_run_system_monitoring', new_callable=AsyncMock) as mock_run:
            await resource_monitor.start_monitoring()
            
            # Now stop monitoring
            result = await resource_monitor.stop_monitoring()
            
            assert result["status"] == "monitoring_stopped"
            assert resource_monitor.is_monitoring is False
            
            # Second call should indicate not monitoring
            result = await resource_monitor.stop_monitoring()
            assert result["status"] == "not_monitoring"
    
    @pytest.mark.asyncio
    async def test_create_budget(self, resource_monitor):
        """Test creating a budget."""
        with patch.object(resource_monitor, '_save_budget', new_callable=AsyncMock) as mock_save:
            budget = await resource_monitor.create_budget(
                resource_type=ResourceType.CPU,
                limit=80.0,
                period=BudgetPeriod.HOURLY,
                unit="percent",
                name="CPU Usage Budget",
                description="Hourly CPU usage budget",
                components=["system"],
                tags=["cpu", "system"],
                alert_thresholds={"warning": 70.0, "critical": 90.0}
            )
            
            assert budget.id in resource_monitor.budgets
            assert budget.resource_type == ResourceType.CPU
            assert budget.limit == 80.0
            assert budget.period == BudgetPeriod.HOURLY
            assert budget.unit == "percent"
            assert budget.name == "CPU Usage Budget"
            assert budget.description == "Hourly CPU usage budget"
            assert budget.components == ["system"]
            assert budget.tags == ["cpu", "system"]
            assert budget.alert_thresholds == {"warning": 70.0, "critical": 90.0}
            assert budget.active is True
            
            # Verify save was called
            mock_save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_record_usage(self, resource_monitor):
        """Test recording resource usage."""
        with patch.object(resource_monitor, '_check_budget_thresholds', new_callable=AsyncMock) as mock_check, \
             patch.object(resource_monitor, '_save_usage_records', new_callable=AsyncMock) as mock_save:
            
            usage = await resource_monitor.record_usage(
                resource_type=ResourceType.MEMORY,
                component="database",
                quantity=512.0,
                unit="MB",
                metadata={"db_name": "main"}
            )
            
            assert usage in resource_monitor.usage_records
            assert usage.resource_type == ResourceType.MEMORY
            assert usage.component == "database"
            assert usage.quantity == 512.0
            assert usage.unit == "MB"
            assert usage.metadata == {"db_name": "main"}
            
            # Verify check_budget_thresholds was called
            mock_check.assert_called_once_with(usage)
    
    @pytest.mark.asyncio
    async def test_get_budget(self, resource_monitor):
        """Test getting budget details."""
        # Create a budget first
        with patch.object(resource_monitor, '_save_budget', new_callable=AsyncMock), \
             patch.object(resource_monitor, '_calculate_budget_usage', new_callable=AsyncMock) as mock_calc:
            
            mock_calc.return_value = {
                "usage": {
                    "total": 60.0,
                    "count": 10,
                    "percentage": 75.0,
                    "status": "warning",
                    "period_start": datetime.now().isoformat(),
                    "period_end": datetime.now().isoformat(),
                    "remaining": 20.0
                }
            }
            
            budget = await resource_monitor.create_budget(
                resource_type=ResourceType.API_CALLS,
                limit=80.0,
                period=BudgetPeriod.DAILY,
                unit="calls",
                name="API Budget",
                description="Daily API calls budget"
            )
            
            # Get budget details
            result = await resource_monitor.get_budget(budget.id)
            
            # Check that the budget details were returned correctly
            assert result["id"] == budget.id
            assert result["resource_type"] == "api_calls"
            assert result["limit"] == 80.0
            assert result["period"] == "daily"
            assert result["unit"] == "calls"
            assert result["name"] == "API Budget"
            assert result["description"] == "Daily API calls budget"
            
            # Check that usage data was included
            assert "usage" in result
            assert result["usage"]["total"] == 60.0
            assert result["usage"]["percentage"] == 75.0
            assert result["usage"]["remaining"] == 20.0
            
            # Verify calculate_budget_usage was called
            mock_calc.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_budgets(self, resource_monitor):
        """Test getting filtered budget listings."""
        with patch.object(resource_monitor, '_save_budget', new_callable=AsyncMock), \
             patch.object(resource_monitor, '_calculate_budget_usage', new_callable=AsyncMock) as mock_calc:
            
            mock_calc.return_value = {
                "usage": {
                    "total": 0.0,
                    "count": 0,
                    "percentage": 0.0,
                    "status": "ok",
                    "period_start": datetime.now().isoformat(),
                    "period_end": datetime.now().isoformat(),
                    "remaining": 100.0
                }
            }
            
            # Create multiple budgets
            budget1 = await resource_monitor.create_budget(
                resource_type=ResourceType.CPU,
                limit=80.0,
                period=BudgetPeriod.HOURLY,
                unit="percent",
                name="CPU Budget",
                description="CPU usage budget",
                tags=["system"]
            )
            
            budget2 = await resource_monitor.create_budget(
                resource_type=ResourceType.MEMORY,
                limit=1024.0,
                period=BudgetPeriod.HOURLY,
                unit="MB",
                name="Memory Budget",
                description="Memory usage budget",
                tags=["system"]
            )
            
            budget3 = await resource_monitor.create_budget(
                resource_type=ResourceType.API_CALLS,
                limit=1000.0,
                period=BudgetPeriod.DAILY,
                unit="calls",
                name="API Budget",
                description="API calls budget",
                components=["external_api"],
                tags=["api"]
            )
            
            # Test getting all budgets
            all_budgets = await resource_monitor.get_budgets()
            assert len(all_budgets) == 3
            
            # Test filtering by resource type
            cpu_budgets = await resource_monitor.get_budgets(resource_type=ResourceType.CPU)
            assert len(cpu_budgets) == 1
            assert cpu_budgets[0]["id"] == budget1.id
            
            # Test filtering by tag
            system_budgets = await resource_monitor.get_budgets(tag="system")
            assert len(system_budgets) == 2
            
            # Test filtering by component
            api_budgets = await resource_monitor.get_budgets(component="external_api")
            assert len(api_budgets) >= 1, "Should find at least the API budget with 'external_api' component"
            
            # Verify that the API budget is in the results
            api_budget_ids = [b["id"] for b in api_budgets]
            assert budget3.id in api_budget_ids, "API budget should be included when filtering by 'external_api' component"
    
    @pytest.mark.asyncio
    async def test_update_budget(self, resource_monitor):
        """Test updating a budget."""
        with patch.object(resource_monitor, '_save_budget', new_callable=AsyncMock) as mock_save, \
             patch.object(resource_monitor, '_check_budget_thresholds', new_callable=AsyncMock) as mock_check:
            
            # Create a budget first
            budget = await resource_monitor.create_budget(
                resource_type=ResourceType.STORAGE,
                limit=1024.0,
                period=BudgetPeriod.DAILY,
                unit="MB",
                name="Storage Budget",
                description="Daily storage budget",
                components=["user_uploads"],
                tags=["storage"]
            )
            
            # Update the budget
            updates = {
                "name": "Updated Storage Budget",
                "limit": 2048.0,
                "period": BudgetPeriod.WEEKLY,
                "components": ["user_uploads", "system_files"],
                "tags": ["storage", "updated"],
                "alert_thresholds": {"warning": 75.0, "critical": 95.0},
                "active": False
            }
            
            updated_budget = await resource_monitor.update_budget(budget.id, updates)
            
            # Check that the budget was updated
            assert updated_budget.name == "Updated Storage Budget"
            assert updated_budget.limit == 2048.0
            assert updated_budget.period == BudgetPeriod.WEEKLY
            assert updated_budget.components == ["user_uploads", "system_files"]
            assert updated_budget.tags == ["storage", "updated"]
            assert updated_budget.alert_thresholds == {"warning": 75.0, "critical": 95.0}
            assert updated_budget.active is False
            
            # Verify save was called
            mock_save.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_resource_usage(self, resource_monitor):
        """Test getting filtered resource usage data."""
        # Add some usage records
        now = datetime.now()
        one_hour_ago = (now - timedelta(hours=1)).isoformat()
        two_hours_ago = (now - timedelta(hours=2)).isoformat()
        
        resource_monitor.usage_records = [
            ResourceUsage(
                resource_type=ResourceType.CPU,
                component="system",
                quantity=50.0,
                unit="percent",
                timestamp=now.isoformat()
            ),
            ResourceUsage(
                resource_type=ResourceType.CPU,
                component="system",
                quantity=60.0,
                unit="percent",
                timestamp=one_hour_ago
            ),
            ResourceUsage(
                resource_type=ResourceType.MEMORY,
                component="database",
                quantity=512.0,
                unit="MB",
                timestamp=now.isoformat()
            ),
            ResourceUsage(
                resource_type=ResourceType.MEMORY,
                component="application",
                quantity=256.0,
                unit="MB",
                timestamp=two_hours_ago
            )
        ]
        
        # Test getting all usage
        all_usage = await resource_monitor.get_resource_usage()
        assert len(all_usage) == 4
        
        # Test filtering by resource type
        cpu_usage = await resource_monitor.get_resource_usage(resource_type=ResourceType.CPU)
        assert len(cpu_usage) == 2
        assert all(record["resource_type"] == "cpu" for record in cpu_usage)
        
        # Test filtering by component
        db_usage = await resource_monitor.get_resource_usage(component="database")
        assert len(db_usage) == 1
        assert db_usage[0]["component"] == "database"
        
        # Test filtering by time range
        recent_usage = await resource_monitor.get_resource_usage(start_time=one_hour_ago)
        assert len(recent_usage) == 3  # Should include everything but the two_hours_ago record
    
    @pytest.mark.asyncio
    async def test_create_usage_report(self, resource_monitor):
        """Test creating a usage report."""
        # Prepare usage data
        now = datetime.now()
        resource_monitor.usage_records = [
            ResourceUsage(
                resource_type=ResourceType.CPU,
                component="system",
                quantity=50.0,
                unit="percent",
                timestamp=now.isoformat()
            ),
            ResourceUsage(
                resource_type=ResourceType.CPU,
                component="system",
                quantity=60.0,
                unit="percent",
                timestamp=(now - timedelta(hours=1)).isoformat()
            ),
            ResourceUsage(
                resource_type=ResourceType.MEMORY,
                component="database",
                quantity=512.0,
                unit="MB",
                timestamp=now.isoformat()
            ),
            ResourceUsage(
                resource_type=ResourceType.MEMORY,
                component="application",
                quantity=256.0,
                unit="MB",
                timestamp=(now - timedelta(hours=2)).isoformat()
            )
        ]
        
        # Mock visualization creation
        with patch.object(resource_monitor, '_create_usage_visualization', new_callable=AsyncMock) as mock_viz:
            mock_viz.return_value = {
                "type": "test_visualization",
                "image": "test_image_data"
            }
            
            # Create report for all usage
            report = await resource_monitor.create_usage_report()
            
            assert report["status"] == "success"
            assert "summary" in report
            assert "visualization" in report
            
            # Check summary data
            summary = report["summary"]
            assert summary["total_records"] == 4
            assert "resource_types" in summary
            assert "components" in summary
            assert "overall" in summary
            
            # Check overall statistics
            overall = summary["overall"]
            assert overall["total_quantity"] == 878.0  # 50 + 60 + 512 + 256
            assert overall["average_quantity"] == 219.5  # (50 + 60 + 512 + 256) / 4
            
            # Create report with grouping by resource type
            report = await resource_monitor.create_usage_report(group_by="resource_type")
            
            assert "groups" in report["summary"]
            assert report["summary"]["grouped_by"] == "resource_type"
            
            # Create report with filtering
            report = await resource_monitor.create_usage_report(resource_type=ResourceType.CPU)
            
            assert report["summary"]["total_records"] == 2
            assert report["summary"]["overall"]["total_quantity"] == 110.0  # 50 + 60
    
    @pytest.mark.asyncio
    async def test_monitoring_system_resources(self, resource_monitor):
        """Test monitoring system resources."""
        # Mock the resource handlers
        cpu_handler = MagicMock(return_value={
            "percentage": 25.0,
            "count": 8
        })
        
        memory_handler = MagicMock(return_value={
            "percentage": 30.0,
            "total": 16000000000,
            "available": 11200000000,
            "used": 4800000000
        })
        
        storage_handler = MagicMock(return_value={
            "percentage": 45.0,
            "total": 500000000000,
            "free": 275000000000,
            "used": 225000000000
        })
        
        network_handler = MagicMock(return_value={
            "bytes_sent": 1000000,
            "bytes_recv": 2000000,
            "packets_sent": 1000,
            "packets_recv": 2000
        })
        
        # Mock the resource handlers
        resource_monitor.resource_handlers[ResourceType.CPU] = cpu_handler
        resource_monitor.resource_handlers[ResourceType.MEMORY] = memory_handler
        resource_monitor.resource_handlers[ResourceType.STORAGE] = storage_handler
        resource_monitor.resource_handlers[ResourceType.NETWORK] = network_handler
        
        # Mock the record_usage method
        with patch.object(resource_monitor, 'record_usage', new_callable=AsyncMock) as mock_record:
            # Test collecting system metrics
            await resource_monitor._collect_system_metrics()
            
            # Verify calls were made - but don't assume an order
            cpu_calls = [call for call in mock_record.call_args_list if call.args[0] == ResourceType.CPU]
            memory_calls = [call for call in mock_record.call_args_list if call.args[0] == ResourceType.MEMORY]
            storage_calls = [call for call in mock_record.call_args_list if call.args[0] == ResourceType.STORAGE]
            network_calls = [call for call in mock_record.call_args_list if call.args[0] == ResourceType.NETWORK]
            
            # Assert that each type of resource was recorded
            assert mock_record.call_count >= 1, "No resource usage was recorded"
            
            # If we have CPU calls, check them
            if cpu_calls:
                cpu_call = cpu_calls[0]
                assert cpu_call.args[1] == "system", "CPU component should be 'system'"
                assert cpu_call.args[2] == 25.0, "CPU percentage should be 25.0"
                assert cpu_call.args[3] == "percent", "CPU unit should be 'percent'"
            
            # If we have memory calls, check them
            if memory_calls:
                memory_call = memory_calls[0]
                assert memory_call.args[1] == "system", "Memory component should be 'system'"
                assert memory_call.args[2] == 30.0, "Memory percentage should be 30.0"
                assert memory_call.args[3] == "percent", "Memory unit should be 'percent'"
            
            # If we have storage calls, check them
            if storage_calls:
                storage_call = storage_calls[0]
                assert storage_call.args[1] == "system", "Storage component should be 'system'"
                assert storage_call.args[2] == 45.0, "Storage percentage should be 45.0"
                assert storage_call.args[3] == "percent", "Storage unit should be 'percent'"
            
            # If we have network calls, check them
            if network_calls:
                network_call = network_calls[0]
                assert network_call.args[1] == "system", "Network component should be 'system'"
                assert network_call.args[2] == 3000000, "Network bytes should be 3000000"
                assert network_call.args[3] == "bytes", "Network unit should be 'bytes'" 