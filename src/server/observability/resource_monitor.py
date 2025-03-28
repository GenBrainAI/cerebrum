from typing import Dict, List, Optional, Any, Set, Tuple, Union, Callable
import asyncio
import logging
import os
import json
import time
import psutil
import platform
from datetime import datetime, timedelta
from pathlib import Path
import uuid
import numpy as np
from collections import defaultdict

from .resource_monitoring.models import (
    ResourceType, BudgetPeriod, AlertLevel, ResourceUnit,
    ResourceUsage, Budget, BudgetAlert, ResourceAllocation, ResourceForecast
)

logger = logging.getLogger(__name__)

try:
    import pandas as pd
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure
    import io
    import base64
    VISUALIZATION_AVAILABLE = True
except ImportError:
    logger.warning("Visualization dependencies not available. Install pandas and matplotlib for visualization support.")
    VISUALIZATION_AVAILABLE = False

class ResourceMonitor:
    """Monitors and manages resource usage and budgets."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, 
                supervision_hub: Optional[Any] = None):
        """
        Initialize with configuration and optional supervision hub.
        
        Args:
            config: Configuration dictionary
                - storage_path: Path to store monitoring data
                - default_budgets: Default budget settings for resource types
                - monitoring_interval: Interval for monitoring in seconds
                - alert_thresholds: Default alert thresholds
                - max_usage_records: Maximum number of usage records to keep
                - enable_forecasting: Whether to enable usage forecasting
                - visualization_format: Format for visualizations ("svg", "png", etc.)
                - supervision_level_map: Map alert levels to supervision levels
            supervision_hub: Optional supervision hub for alerts
        """
        # Set default configuration
        self.config = {
            "storage_path": os.path.join(os.path.expanduser("~"), ".cerebrum", "resource_monitor"),
            "monitoring_interval": 60.0,  # seconds
            "alert_thresholds": {
                "warning": 70.0,
                "critical": 90.0
            },
            "max_usage_records": 10000,
            "enable_forecasting": False,
            "forecasting_models": ["linear", "moving_average"],
            "visualization_format": "png",
            "supervision_level_map": {
                "info": "information",
                "warning": "suggestion",
                "critical": "warning",
                "emergency": "critical"
            }
        }
        
        # Override with provided config
        if config:
            self.config.update(config)
        
        # Create storage directory
        self.storage_path = self.config["storage_path"]
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Create subdirectories
        self.budgets_path = os.path.join(self.storage_path, "budgets")
        self.usage_path = os.path.join(self.storage_path, "usage")
        self.alerts_path = os.path.join(self.storage_path, "alerts")
        self.forecasts_path = os.path.join(self.storage_path, "forecasts")
        self.allocations_path = os.path.join(self.storage_path, "allocations")
        self.visualizations_path = os.path.join(self.storage_path, "visualizations")
        
        os.makedirs(self.budgets_path, exist_ok=True)
        os.makedirs(self.usage_path, exist_ok=True)
        os.makedirs(self.alerts_path, exist_ok=True)
        os.makedirs(self.forecasts_path, exist_ok=True)
        os.makedirs(self.allocations_path, exist_ok=True)
        os.makedirs(self.visualizations_path, exist_ok=True)
        
        # Set supervision hub
        self.supervision_hub = supervision_hub
        
        # Load data
        self.budgets: Dict[str, Budget] = self._load_budgets()
        self.alerts: Dict[str, BudgetAlert] = self._load_alerts()
        self.allocations: Dict[str, ResourceAllocation] = self._load_allocations()
        self.forecasts: Dict[str, ResourceForecast] = self._load_forecasts()
        
        # Usage records
        self.usage_records: List[ResourceUsage] = []
        self._load_recent_usage()
        
        # Monitoring state
        self.monitoring = False
        self.monitor_task = None
        self.monitor_interval = self.config["monitoring_interval"]
        self.current_usage: Dict[str, float] = {}
        
        # Register resource callbacks
        self.resource_callbacks: Dict[ResourceType, List[Callable]] = defaultdict(list)
        
        # Create default budgets
        if config and "default_budgets" in config:
            asyncio.create_task(self._create_default_budgets())
    
    def __del__(self):
        """Clean up when object is deleted."""
        if self.monitoring and self.monitor_task:
            asyncio.create_task(self.stop_monitoring())
    
    async def _create_default_budgets(self):
        """Create default budgets from config."""
        default_budgets = self.config.get("default_budgets", {})
        
        for resource_type_str, budget_config in default_budgets.items():
            try:
                resource_type = ResourceType(resource_type_str)
                
                # Check if budget already exists
                existing = False
                for budget in self.budgets.values():
                    if (budget.resource_type == resource_type and 
                        not budget.components and  # only global budgets
                        budget.name.startswith("Default")):
                        existing = True
                        break
                
                if not existing:
                    # Create default budget
                    await self.create_budget(
                        resource_type=resource_type,
                        limit=budget_config.get("limit", 100.0),
                        period=BudgetPeriod(budget_config.get("period", "daily")),
                        unit=ResourceUnit(budget_config.get("unit", "percentage")),
                        name=f"Default {resource_type.value} Budget",
                        description=f"Default budget for {resource_type.value}",
                        alert_thresholds=budget_config.get("alert_thresholds", self.config["alert_thresholds"]),
                        components=[]  # Apply to all components
                    )
            except Exception as e:
                logger.error(f"Error creating default budget for {resource_type_str}: {e}")
    
    def _load_budgets(self) -> Dict[str, Budget]:
        """Load budgets from storage."""
        budgets = {}
        
        try:
            for file_path in Path(self.budgets_path).glob("*.json"):
                with open(file_path, "r") as f:
                    budget_data = json.load(f)
                    budget_id = budget_data.get("id")
                    if budget_id:
                        budgets[budget_id] = Budget.from_dict(budget_data)
        except Exception as e:
            logger.exception(f"Error loading budgets: {e}")
        
        return budgets
    
    def _load_alerts(self) -> Dict[str, BudgetAlert]:
        """Load alerts from storage."""
        alerts = {}
        
        try:
            for file_path in Path(self.alerts_path).glob("*.json"):
                with open(file_path, "r") as f:
                    alert_data = json.load(f)
                    alert_id = alert_data.get("id")
                    if alert_id:
                        alerts[alert_id] = BudgetAlert.from_dict(alert_data)
        except Exception as e:
            logger.exception(f"Error loading alerts: {e}")
        
        return alerts
    
    def _load_allocations(self) -> Dict[str, ResourceAllocation]:
        """Load resource allocations from storage."""
        allocations = {}
        
        try:
            for file_path in Path(self.allocations_path).glob("*.json"):
                with open(file_path, "r") as f:
                    allocation_data = json.load(f)
                    allocation_id = allocation_data.get("id")
                    if allocation_id:
                        allocations[allocation_id] = ResourceAllocation.from_dict(allocation_data)
        except Exception as e:
            logger.exception(f"Error loading allocations: {e}")
        
        return allocations
    
    def _load_forecasts(self) -> Dict[str, ResourceForecast]:
        """Load resource forecasts from storage."""
        forecasts = {}
        
        try:
            for file_path in Path(self.forecasts_path).glob("*.json"):
                with open(file_path, "r") as f:
                    forecast_data = json.load(f)
                    forecast_id = forecast_data.get("id")
                    if forecast_id:
                        forecasts[forecast_id] = ResourceForecast.from_dict(forecast_data)
        except Exception as e:
            logger.exception(f"Error loading forecasts: {e}")
        
        return forecasts
    
    def _load_recent_usage(self) -> None:
        """Load recent usage records from storage."""
        try:
            # Get most recent usage file
            usage_files = sorted(Path(self.usage_path).glob("*.jsonl"), key=os.path.getmtime, reverse=True)
            
            # Load up to max_records records
            max_records = self.config.get("max_usage_records", 10000)
            loaded_records = 0
            
            for file_path in usage_files[:10]:  # Limit to 10 most recent files
                with open(file_path, "r") as f:
                    for line in f:
                        if loaded_records >= max_records:
                            break
                            
                        try:
                            usage_data = json.loads(line.strip())
                            self.usage_records.append(ResourceUsage.from_dict(usage_data))
                            loaded_records += 1
                        except Exception as e:
                            logger.error(f"Error parsing usage record: {e}")
                
                if loaded_records >= max_records:
                    break
            
            # Sort by timestamp
            self.usage_records.sort(key=lambda u: u.timestamp)
            
            logger.info(f"Loaded {loaded_records} usage records")
        except Exception as e:
            logger.exception(f"Error loading usage records: {e}")
    
    async def _save_budget(self, budget: Budget) -> None:
        """Save budget to storage."""
        try:
            file_path = os.path.join(self.budgets_path, f"{budget.id}.json")
            with open(file_path, "w") as f:
                json.dump(budget.to_dict(), f, indent=2)
        except Exception as e:
            logger.exception(f"Error saving budget {budget.id}: {e}")
    
    async def _save_alert(self, alert: BudgetAlert) -> None:
        """Save alert to storage."""
        try:
            file_path = os.path.join(self.alerts_path, f"{alert.id}.json")
            with open(file_path, "w") as f:
                json.dump(alert.to_dict(), f, indent=2)
        except Exception as e:
            logger.exception(f"Error saving alert {alert.id}: {e}")
    
    async def _save_allocation(self, allocation: ResourceAllocation) -> None:
        """Save resource allocation to storage."""
        try:
            file_path = os.path.join(self.allocations_path, f"{allocation.id}.json")
            with open(file_path, "w") as f:
                json.dump(allocation.to_dict(), f, indent=2)
        except Exception as e:
            logger.exception(f"Error saving allocation {allocation.id}: {e}")
    
    async def _save_forecast(self, forecast: ResourceForecast) -> None:
        """Save resource forecast to storage."""
        try:
            file_path = os.path.join(self.forecasts_path, f"{forecast.id}.json")
            with open(file_path, "w") as f:
                json.dump(forecast.to_dict(), f, indent=2)
        except Exception as e:
            logger.exception(f"Error saving forecast {forecast.id}: {e}")
    
    async def _save_usage_records(self) -> None:
        """Save usage records to storage."""
        if not self.usage_records:
            return
            
        try:
            # Group records by day
            records_by_day = {}
            for record in self.usage_records:
                day = datetime.fromisoformat(record.timestamp).strftime("%Y-%m-%d")
                if day not in records_by_day:
                    records_by_day[day] = []
                records_by_day[day].append(record)
            
            # Save each day's records
            for day, records in records_by_day.items():
                file_path = os.path.join(self.usage_path, f"usage_{day}.jsonl")
                
                # Append or create
                mode = "a" if os.path.exists(file_path) else "w"
                
                with open(file_path, mode) as f:
                    for record in records:
                        f.write(json.dumps(record.to_dict()) + "\n")
                        
            logger.debug(f"Saved {len(self.usage_records)} usage records")
            
            # Clear records that have been saved
            self.usage_records = []
        except Exception as e:
            logger.exception(f"Error saving usage records: {e}")
    
    async def start_monitoring(self) -> Dict[str, Any]:
        """
        Start resource monitoring.
        
        Returns:
            Dictionary with result
        """
        if self.monitoring:
            return {
                "status": "already_monitoring",
                "message": "Resource monitoring already running"
            }
        
        logger.info("Starting resource monitoring")
        self.monitoring = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        
        return {
            "status": "monitoring_started",
            "message": "Resource monitoring started",
            "interval": self.monitor_interval
        }
    
    async def stop_monitoring(self) -> Dict[str, Any]:
        """
        Stop resource monitoring.
        
        Returns:
            Dictionary with result
        """
        if not self.monitoring:
            return {
                "status": "not_monitoring",
                "message": "Resource monitoring not running"
            }
        
        logger.info("Stopping resource monitoring")
        self.monitoring = False
        
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
            
            self.monitor_task = None
        
        # Save any pending usage records
        await self._save_usage_records()
        
        return {
            "status": "monitoring_stopped",
            "message": "Resource monitoring stopped"
        }
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop, runs periodically to collect system metrics."""
        while self.monitoring:
            try:
                # Update system resource usage
                await self._update_system_resources()
                
                # Check budgets
                for budget_id, budget in self.budgets.items():
                    if budget.active:
                        await self._check_budget(budget)
                
                # Save usage records periodically
                if len(self.usage_records) >= 100:
                    await self._save_usage_records()
                
                # Update forecasts periodically
                if self.config.get("enable_forecasting", False) and len(self.usage_records) > 0:
                    if datetime.now().minute % 15 == 0:  # Every 15 minutes
                        await self._update_forecasts()
            except Exception as e:
                logger.exception(f"Error in monitoring loop: {e}")
            
            # Wait for next monitoring interval
            await asyncio.sleep(self.monitor_interval)
    
    async def _update_system_resources(self) -> None:
        """Update system resource usage metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self.current_usage["cpu"] = cpu_percent
            
            # Record CPU usage
            await self.record_usage(
                resource_type=ResourceType.CPU,
                component="system",
                quantity=cpu_percent,
                unit=ResourceUnit.PERCENTAGE
            )
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_used_mb = memory.used / (1024 * 1024)
            memory_total_mb = memory.total / (1024 * 1024)
            memory_percent = memory.percent
            
            self.current_usage["memory"] = memory_used_mb
            self.current_usage["memory_percent"] = memory_percent
            
            # Record memory usage
            await self.record_usage(
                resource_type=ResourceType.MEMORY,
                component="system",
                quantity=memory_used_mb,
                unit=ResourceUnit.MB,
                metadata={
                    "total_mb": memory_total_mb,
                    "percent": memory_percent
                }
            )
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_used_gb = disk.used / (1024 * 1024 * 1024)
            disk_total_gb = disk.total / (1024 * 1024 * 1024)
            disk_percent = disk.percent
            
            self.current_usage["disk"] = disk_used_gb
            self.current_usage["disk_percent"] = disk_percent
            
            # Record disk usage
            await self.record_usage(
                resource_type=ResourceType.STORAGE,
                component="system",
                quantity=disk_used_gb,
                unit=ResourceUnit.GB,
                metadata={
                    "total_gb": disk_total_gb,
                    "percent": disk_percent
                }
            )
            
            # Network stats (if available)
            try:
                net_io = psutil.net_io_counters()
                self.current_usage["network_sent_mb"] = net_io.bytes_sent / (1024 * 1024)
                self.current_usage["network_recv_mb"] = net_io.bytes_recv / (1024 * 1024)
                
                # Record network usage
                await self.record_usage(
                    resource_type=ResourceType.NETWORK,
                    component="system",
                    quantity=net_io.bytes_sent / (1024 * 1024),
                    unit=ResourceUnit.MB,
                    metadata={
                        "direction": "sent",
                        "packets": net_io.packets_sent
                    }
                )
                
                await self.record_usage(
                    resource_type=ResourceType.NETWORK,
                    component="system",
                    quantity=net_io.bytes_recv / (1024 * 1024),
                    unit=ResourceUnit.MB,
                    metadata={
                        "direction": "received",
                        "packets": net_io.packets_recv
                    }
                )
            except Exception as e:
                logger.debug(f"Could not collect network stats: {e}")
            
            # GPU stats (if available)
            try:
                if hasattr(self, "_collect_gpu_stats"):
                    gpu_stats = await self._collect_gpu_stats()
                    
                    for gpu_id, stats in gpu_stats.items():
                        self.current_usage[f"gpu_{gpu_id}_memory"] = stats["memory_used_mb"]
                        self.current_usage[f"gpu_{gpu_id}_utilization"] = stats["utilization_percent"]
                        
                        await self.record_usage(
                            resource_type=ResourceType.GPU,
                            component=f"gpu_{gpu_id}",
                            quantity=stats["memory_used_mb"],
                            unit=ResourceUnit.MB,
                            metadata={
                                "total_mb": stats["memory_total_mb"],
                                "utilization_percent": stats["utilization_percent"],
                                "temperature": stats.get("temperature_c")
                            }
                        )
            except Exception as e:
                logger.debug(f"Could not collect GPU stats: {e}")
        except Exception as e:
            logger.exception(f"Error updating system resources: {e}")
    
    async def get_current_usage(self) -> Dict[str, float]:
        """
        Get current resource usage statistics.
        
        Returns:
            Dictionary with resource usage values
        """
        # Update system resource usage if not already monitoring
        if not self.monitoring:
            await self._update_system_resources()
        
        return self.current_usage
    
    async def create_budget(self,
                           resource_type: ResourceType,
                           limit: float,
                           period: BudgetPeriod,
                           unit: ResourceUnit,
                           name: str,
                           description: str = "",
                           components: Optional[List[str]] = None,
                           tags: Optional[List[str]] = None,
                           alert_thresholds: Optional[Dict[str, float]] = None,
                           owners: Optional[List[str]] = None,
                           priority: int = 0) -> Budget:
        """
        Create a new budget for a resource type.
        
        Args:
            resource_type: Type of resource
            limit: Budget limit
            period: Budget period
            unit: Unit of measurement
            name: Budget name
            description: Budget description
            components: Components this budget applies to (empty for all)
            tags: Tags for categorization
            alert_thresholds: Alert thresholds (e.g., {"warning": 70, "critical": 90})
            owners: List of user IDs who own/manage this budget
            priority: Priority (higher overrides lower)
            
        Returns:
            The created Budget object
        """
        # Generate budget ID
        budget_id = str(uuid.uuid4())
        
        # Set defaults
        components = components or []
        tags = tags or []
        owners = owners or []
        
        # Set default alert thresholds if not provided
        if not alert_thresholds:
            alert_thresholds = self.config.get("alert_thresholds", {
                "warning": 70.0,
                "critical": 90.0
            })
        
        # Create budget
        budget = Budget(
            id=budget_id,
            resource_type=resource_type,
            components=components,
            limit=limit,
            period=period,
            unit=unit,
            start_date=datetime.now().isoformat(),
            name=name,
            description=description,
            tags=tags,
            alert_thresholds=alert_thresholds,
            priority=priority,
            owners=owners
        )
        
        # Save budget
        self.budgets[budget_id] = budget
        await self._save_budget(budget)
        
        logger.info(f"Created budget {budget_id}: {name}")
        
        return budget
    
    async def record_usage(self,
                         resource_type: ResourceType,
                         component: str,
                         quantity: float,
                         unit: ResourceUnit,
                         metadata: Optional[Dict[str, Any]] = None) -> ResourceUsage:
        """
        Record resource usage.
        
        Args:
            resource_type: Type of resource
            component: Component using the resource
            quantity: Amount used
            unit: Unit of measurement
            metadata: Additional metadata
            
        Returns:
            The created ResourceUsage object
        """
        # Create usage record
        usage = ResourceUsage(
            resource_type=resource_type,
            component=component,
            quantity=quantity,
            unit=unit,
            timestamp=datetime.now().isoformat(),
            metadata=metadata or {}
        )
        
        # Add to records
        self.usage_records.append(usage)
        
        # Trim records if needed
        max_records = self.config.get("max_usage_records")
        if max_records and len(self.usage_records) > max_records:
            self.usage_records = self.usage_records[-max_records:]
        
        # Check against budgets
        if self.budgets:
            relevant_budgets = [
                budget for budget in self.budgets.values()
                if (budget.resource_type == resource_type and
                    (not budget.components or component in budget.components) and
                    budget.active)
            ]
            
            # Sort by priority (highest first)
            relevant_budgets.sort(key=lambda b: b.priority, reverse=True)
            
            for budget in relevant_budgets:
                await self._check_budget_for_usage(budget, usage)
        
        # Call registered callbacks
        callbacks = self.resource_callbacks.get(resource_type, [])
        for callback in callbacks:
            try:
                result = callback(usage)
                if asyncio.iscoroutine(result):
                    asyncio.create_task(result)
            except Exception as e:
                logger.error(f"Error in resource callback for {resource_type}: {e}")
        
        return usage
    
    async def _check_budget_for_usage(self, budget: Budget, usage: ResourceUsage) -> None:
        """Check a budget against a specific usage record."""
        # Check if units are compatible
        if budget.unit != usage.unit:
            # Try to convert
            try:
                converted_usage = usage.convert_unit(budget.unit)
                quantity = converted_usage.quantity
            except Exception:
                logger.warning(f"Cannot compare usage with unit {usage.unit.value} to budget with unit {budget.unit.value}")
                return
        else:
            quantity = usage.quantity
        
        # Get usage for current period
        period_start = budget.get_period_start()
        
        period_usage = 0.0
        for record in self.usage_records:
            if (record.resource_type == budget.resource_type and
                (not budget.components or record.component in budget.components) and
                datetime.fromisoformat(record.timestamp) >= period_start):
                
                if record.unit != budget.unit:
                    # Try to convert
                    try:
                        converted_record = record.convert_unit(budget.unit)
                        period_usage += converted_record.quantity
                    except Exception:
                        continue
                else:
                    period_usage += record.quantity
        
        # Add current usage
        period_usage += quantity
        
        # Calculate percentage of budget used
        if budget.limit > 0:
            percentage_used = (period_usage / budget.limit) * 100.0
        else:
            percentage_used = 0.0
        
        # Check thresholds
        for threshold_name, threshold_value in budget.alert_thresholds.items():
            threshold_percentage = threshold_value
            
            # Only check if usage crosses threshold
            is_over_threshold = percentage_used >= threshold_percentage
            
            # If first time crossing threshold or significant increase, create alert
            create_alert = False
            
            # Check if we already have an active alert for this threshold
            existing_alert = None
            for alert in self.alerts.values():
                if (alert.budget_id == budget.id and
                    alert.threshold_name == threshold_name and
                    not alert.acknowledged):
                    existing_alert = alert
                    break
            
            if is_over_threshold:
                if not existing_alert:
                    # First time crossing threshold
                    create_alert = True
                elif percentage_used >= existing_alert.percentage + 10:
                    # Significant increase (10% or more)
                    create_alert = True
            
            if create_alert:
                # Determine alert level
                if threshold_name == "critical":
                    level = AlertLevel.CRITICAL
                elif threshold_name == "warning":
                    level = AlertLevel.WARNING
                elif threshold_name == "emergency":
                    level = AlertLevel.EMERGENCY
                else:
                    level = AlertLevel.INFO
                
                # Create alert
                alert_id = str(uuid.uuid4())
                alert = BudgetAlert(
                    id=alert_id,
                    budget_id=budget.id,
                    threshold_name=threshold_name,
                    threshold_value=threshold_percentage,
                    current_usage=period_usage,
                    percentage=percentage_used,
                    level=level,
                    details={
                        "resource_type": budget.resource_type.value,
                        "component": usage.component,
                        "period": budget.period.value,
                        "period_start": period_start.isoformat(),
                        "budget_name": budget.name,
                        "budget_limit": budget.limit,
                        "budget_unit": budget.unit.value
                    }
                )
                
                # Save alert
                self.alerts[alert_id] = alert
                await self._save_alert(alert)
                
                # Log alert
                logger.warning(
                    f"Budget alert: {budget.name} {threshold_name} threshold crossed. "
                    f"Usage: {period_usage:.2f} {budget.unit.value} "
                    f"({percentage_used:.2f}% of limit)."
                )
                
                # Send alert to supervision hub if available
                if self.supervision_hub:
                    await self._send_alert_to_supervision(alert)
    
    async def _check_budget(self, budget: Budget) -> Dict[str, Any]:
        """
        Check current usage against a budget.
        
        Args:
            budget: Budget to check
            
        Returns:
            Dictionary with budget check results
        """
        try:
            # Get period start
            period_start = budget.get_period_start()
            
            # Calculate period usage
            period_usage = 0.0
            for record in self.usage_records:
                if (record.resource_type == budget.resource_type and
                    (not budget.components or record.component in budget.components) and
                    datetime.fromisoformat(record.timestamp) >= period_start):
                    
                    if record.unit != budget.unit:
                        # Try to convert
                        try:
                            converted_record = record.convert_unit(budget.unit)
                            period_usage += converted_record.quantity
                        except Exception:
                            continue
                    else:
                        period_usage += record.quantity
            
            # Calculate percentage of budget used
            if budget.limit > 0:
                percentage_used = (period_usage / budget.limit) * 100.0
            else:
                percentage_used = 0.0
            
            # Check if over budget
            over_budget = period_usage > budget.limit
            
            # Determine status
            if over_budget:
                status = "over_budget"
            elif percentage_used >= budget.alert_thresholds.get("critical", 90.0):
                status = "critical"
            elif percentage_used >= budget.alert_thresholds.get("warning", 70.0):
                status = "warning"
            else:
                status = "ok"
            
            return {
                "budget_id": budget.id,
                "name": budget.name,
                "resource_type": budget.resource_type.value,
                "period": budget.period.value,
                "period_start": period_start.isoformat(),
                "limit": budget.limit,
                "unit": budget.unit.value,
                "current_usage": period_usage,
                "percentage_used": percentage_used,
                "status": status,
                "over_budget": over_budget,
                "remaining": max(0, budget.limit - period_usage)
            }
        except Exception as e:
            logger.exception(f"Error checking budget {budget.id}: {e}")
            return {
                "budget_id": budget.id,
                "error": str(e),
                "status": "error"
            }
    
    async def _send_alert_to_supervision(self, alert: BudgetAlert) -> None:
        """Send an alert to the supervision hub."""
        if not self.supervision_hub:
            return
            
        try:
            # Map alert level to supervision level
            level_map = self.config.get("supervision_level_map", {
                "info": "information",
                "warning": "suggestion",
                "critical": "warning",
                "emergency": "critical"
            })
            
            supervision_level = level_map.get(alert.level.value, "warning")
            
            # Format alert message
            budget = self.budgets.get(alert.budget_id)
            if not budget:
                return
                
            message = (
                f"Resource Budget Alert: {budget.name}\n"
                f"Threshold: {alert.threshold_name} ({alert.threshold_value}%)\n"
                f"Current Usage: {alert.current_usage:.2f} {budget.unit.value} "
                f"({alert.percentage:.2f}% of limit)"
            )
            
            # Send to supervision hub
            await self.supervision_hub.create_notification(
                supervisor_ids=budget.owners if budget.owners else ["admin"],
                message=message,
                level=alert.level.value,
                context={
                    "alert_id": alert.id,
                    "budget_id": budget.id,
                    "resource_type": budget.resource_type.value,
                    "current_usage": alert.current_usage,
                    "limit": budget.limit,
                    "percentage": alert.percentage,
                    "threshold": alert.threshold_name
                }
            )
            
            # For critical and emergency alerts, create an intervention request
            if alert.level in [AlertLevel.CRITICAL, AlertLevel.EMERGENCY]:
                if hasattr(self.supervision_hub, "handle_intervention_request"):
                    # Create intervention ID
                    intervention_id = f"resource_alert_{alert.id}"
                    
                    # Send intervention request
                    await self.supervision_hub.handle_intervention_request(
                        intervention_id=intervention_id,
                        level=supervision_level,
                        title=f"Resource Budget Critical Alert: {budget.name}",
                        description=message,
                        context={
                            "alert_id": alert.id,
                            "budget_id": budget.id,
                            "resource_type": budget.resource_type.value,
                            "current_usage": alert.current_usage,
                            "limit": budget.limit,
                            "percentage": alert.percentage,
                            "threshold": alert.threshold_name
                        }
                    )
        except Exception as e:
            logger.exception(f"Error sending alert to supervision: {e}")
    
    async def _update_forecasts(self) -> None:
        """Update resource usage forecasts."""
        try:
            # Collect historical data
            historical_data = self.usage_records[-100:]
            
            # Train forecasting models
            for model_name in self.config["forecasting_models"]:
                model = self._train_model(model_name, historical_data)
                
                # Generate forecast
                forecast = model.predict(len(self.usage_records))
                
                # Save forecast
                forecast_id = str(uuid.uuid4())
                forecast_obj = ResourceForecast(
                    id=forecast_id,
                    resource_type=historical_data[-1].resource_type,
                    model_name=model_name,
                    start_date=datetime.now().isoformat(),
                    data=forecast.tolist()
                )
                
                self.forecasts[forecast_id] = forecast_obj
                await self._save_forecast(forecast_obj)
        except Exception as e:
            logger.exception(f"Error updating forecasts: {e}")
    
    def _train_model(self, model_name: str, historical_data: List[ResourceUsage]) -> Any:
        """Train a forecasting model."""
        # Implementation of model training logic based on the selected model
        # This is a placeholder and should be replaced with actual model training logic
        # based on the selected model (e.g., linear regression, moving average, etc.)
        # For example, you can use a simple moving average model for demonstration:
        if model_name == "moving_average":
            return self._moving_average_forecast(historical_data)
        else:
            return self._linear_forecast(historical_data)
    
    def _load_usage_history(self, resource_type: ResourceType) -> None:
        """Load usage history for a resource type."""
        try:
            resource_path = os.path.join(self.usage_path, resource_type.value)
            if not os.path.exists(resource_path):
                os.makedirs(resource_path, exist_ok=True)
            
            records = []
            
            # Load records from the last 30 days
            now = datetime.now()
            for i in range(30):
                date = now - timedelta(days=i)
                date_str = date.strftime("%Y-%m-%d")
                file_path = os.path.join(resource_path, f"{date_str}.jsonl")
                
                if os.path.exists(file_path):
                    with open(file_path, "r") as f:
                        for line in f:
                            record = json.loads(line.strip())
                            records.append(ResourceUsage.from_dict(record))
            
            self.usage_records = records
        except Exception as e:
            logger.exception(f"Error loading usage history for {resource_type}: {e}")
            self.usage_records = []
    
    async def generate_visualization(self, 
                               resource_type: Optional[ResourceType] = None,
                               component: Optional[str] = None,
                               start_time: Optional[str] = None,
                               end_time: Optional[str] = None,
                               include_forecast: bool = True) -> Dict[str, Any]:
        """
        Generate visualization of resource usage.
        
        Args:
            resource_type: Optional resource type to filter
            component: Optional component to filter
            start_time: Optional start time (ISO format)
            end_time: Optional end time (ISO format)
            include_forecast: Whether to include forecast
            
        Returns:
            Dictionary with visualization data
        """
        if not VISUALIZATION_AVAILABLE:
            return {
                "success": False,
                "message": "Visualization dependencies not available. Install pandas and matplotlib."
            }
            
        try:
            # Filter usage records
            filtered_records = []
            
            for record in self.usage_records:
                if resource_type and record.resource_type != resource_type:
                    continue
                    
                if component and record.component != component:
                    continue
                    
                if start_time and record.timestamp < start_time:
                    continue
                    
                if end_time and record.timestamp > end_time:
                    continue
                    
                filtered_records.append(record)
            
            if not filtered_records:
                return {
                    "success": False,
                    "message": "No data available for the specified filters."
                }
            
            # Convert to DataFrame
            try:
                df = pd.DataFrame([
                    {
                        "timestamp": datetime.fromisoformat(r.timestamp),
                        "resource_type": r.resource_type.value,
                        "component": r.component,
                        "quantity": r.quantity,
                        "unit": r.unit.value
                    }
                    for r in filtered_records
                ])
                
                # Set timestamp as index
                df.set_index("timestamp", inplace=True)
                
                # Sort by timestamp
                df.sort_index(inplace=True)
            except Exception as e:
                logger.exception(f"Error creating DataFrame: {e}")
                return {
                    "success": False,
                    "message": f"Error creating visualization data: {str(e)}"
                }
            
            # Get forecast if requested
            forecast_data = None
            forecast = None
            
            if include_forecast and resource_type:
                try:
                    # Find most recent forecast for this resource type and component
                    relevant_forecasts = [
                        f for f in self.forecasts.values()
                        if f.resource_type == resource_type and
                        (not component or f.component == component)
                    ]
                    
                    if relevant_forecasts:
                        # Sort by created_at (newest first)
                        relevant_forecasts.sort(key=lambda f: f.created_at, reverse=True)
                        forecast = relevant_forecasts[0]
                        
                        # Create forecast DataFrame
                        forecast_data = pd.DataFrame([
                            {
                                "timestamp": datetime.fromisoformat(t),
                                "quantity": v,
                                "source": "forecast"
                            }
                            for t, v in forecast.forecasted_usage
                        ])
                        
                        forecast_data.set_index("timestamp", inplace=True)
                except Exception as e:
                    logger.warning(f"Error preparing forecast data: {e}")
            
            # Create figure
            try:
                fig, ax = plt.subplots(figsize=(10, 6))
                
                # Plot actual data
                try:
                    if resource_type and component:
                        # Single series
                        df.plot(y="quantity", ax=ax, label=f"Actual {component}")
                    elif resource_type:
                        # Group by component
                        for comp, group in df.groupby("component"):
                            group.plot(y="quantity", ax=ax, label=f"Actual {comp}")
                    else:
                        # Group by resource type and component
                        for (res_type, comp), group in df.groupby(["resource_type", "component"]):
                            group.plot(y="quantity", ax=ax, label=f"Actual {res_type}/{comp}")
                except Exception as e:
                    logger.warning(f"Error plotting data: {e}")
                
                # Plot forecast if available
                if forecast_data is not None:
                    try:
                        forecast_data.plot(y="quantity", ax=ax, style="--", label=f"Forecast {component}")
                        
                        # Add confidence interval if available
                        if forecast and forecast.confidence > 0:
                            try:
                                confidence_factor = 1.0 + (1.0 - forecast.confidence)
                                upper = forecast_data["quantity"] * confidence_factor
                                lower = forecast_data["quantity"] / confidence_factor
                                
                                ax.fill_between(forecast_data.index, lower, upper, alpha=0.2)
                            except Exception as e:
                                logger.warning(f"Could not add confidence interval: {e}")
                    except Exception as e:
                        logger.warning(f"Error plotting forecast: {e}")
                
                # Add budgets if applicable
                if resource_type:
                    for budget in self.budgets.values():
                        if budget.resource_type == resource_type and budget.active:
                            if not budget.components or (component and component in budget.components):
                                try:
                                    # Add horizontal line for budget limit
                                    ax.axhline(y=budget.limit, color="r", linestyle="-", label=f"Budget: {budget.name}")
                                    
                                    # Add warning threshold
                                    warning = budget.alert_thresholds.get("warning")
                                    if warning:
                                        threshold = budget.limit * warning / 100.0
                                        ax.axhline(y=threshold, color="y", linestyle="--", label="Warning Threshold")
                                except Exception as e:
                                    logger.warning(f"Could not add budget line for {budget.name}: {e}")
                
                # Set labels
                unit = df["unit"].iloc[0] if not df["unit"].empty else ""
                ax.set_ylabel(f"Usage ({unit})")
                
                resource_name = resource_type.value if resource_type else "All Resources"
                component_name = component if component else "All Components"
                ax.set_title(f"Resource Usage: {resource_name}/{component_name}")
                
                # Add grid
                ax.grid(True, alpha=0.3)
                
                # Rotate x-axis labels
                plt.xticks(rotation=45)
                
                # Add legend
                ax.legend()
                
                # Adjust layout
                plt.tight_layout()
                
                # Save figure to buffer
                buf = io.BytesIO()
                format_type = self.config.get("visualization_format", "png")
                plt.savefig(buf, format=format_type, dpi=100)
                buf.seek(0)
                
                # Convert to base64
                image_base64 = base64.b64encode(buf.read()).decode()
                
                # Close figure
                plt.close(fig)
                
                return {
                    "success": True,
                    "visualization": f"data:image/{format_type};base64,{image_base64}",
                    "resource_type": resource_type.value if resource_type else "all",
                    "component": component if component else "all",
                    "data_points": len(df),
                    "start_time": df.index.min().isoformat(),
                    "end_time": df.index.max().isoformat(),
                    "includes_forecast": forecast_data is not None,
                    "format": format_type
                }
            except Exception as e:
                logger.exception(f"Error creating visualization: {e}")
                return {
                    "success": False,
                    "message": f"Error creating visualization: {str(e)}"
                }
        except Exception as e:
            logger.exception(f"Error generating visualization: {e}")
            return {
                "success": False,
                "message": f"Error generating visualization: {str(e)}"
            }


