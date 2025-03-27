from typing import Dict, List, Optional, Any, Callable, Union
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
import base64
from io import BytesIO
import matplotlib.pyplot as plt
import pandas as pd

from src.server.observability.resource_monitoring.models import (
    ResourceType, BudgetPeriod, ResourceUsage, Budget, BudgetAlert
)

logger = logging.getLogger(__name__)


class ResourceMonitor:
    """Monitors and manages system resource usage and budgets."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize with optional configuration."""
        self.config = config or {
            "storage_path": "data/resources",
            "usage_retention_days": 30,
            "system_monitoring_enabled": True,
            "monitoring_interval_seconds": 60,
            "default_alert_thresholds": {
                "warning": 70.0,
                "critical": 90.0
            }
        }
        
        self.budgets: Dict[str, Budget] = {}
        self.usage_records: List[ResourceUsage] = []
        self.alerts: Dict[str, BudgetAlert] = {}
        
        self.system_monitor_task = None
        self.is_monitoring = False
        # Initialize resource type handlers
        self.resource_handlers: Dict[ResourceType, Callable] = {
            ResourceType.CPU: self._monitor_cpu,
            ResourceType.MEMORY: self._monitor_memory,
            ResourceType.STORAGE: self._monitor_storage,
            ResourceType.NETWORK: self._monitor_network,
            ResourceType.API_CALLS: self._monitor_api_calls,
            ResourceType.MODEL_TOKENS: self._monitor_model_tokens,
            ResourceType.PROCESSING_TIME: self._monitor_processing_time,
            ResourceType.CONCURRENT_TASKS: self._monitor_concurrent_tasks
        }
        
        # Do not call _load_data here since it's async and can't be awaited in __init__
        
    async def initialize(self) -> None:
        """Initialize the resource monitor by loading data from storage.
        Call this method after creating the ResourceMonitor instance.
        """
        await self._load_data()
    
    async def start_monitoring(self) -> Dict[str, Any]:
        """Start system resource monitoring."""
        if self.is_monitoring:
            return {"status": "already_monitoring"}
        
        if not self.config.get("system_monitoring_enabled", True):
            return {"status": "monitoring_disabled"}
        
        self.is_monitoring = True
        
        # Start background monitoring task
        self.system_monitor_task = asyncio.create_task(self._run_system_monitoring())
        
        logger.info("System resource monitoring started")
        
        return {
            "status": "monitoring_started",
            "interval": self.config.get("monitoring_interval_seconds", 60)
        }
    
    async def stop_monitoring(self) -> Dict[str, Any]:
        """Stop system resource monitoring."""
        if not self.is_monitoring:
            return {"status": "not_monitoring"}
        
        self.is_monitoring = False
        
        # Cancel monitoring task
        if self.system_monitor_task and not self.system_monitor_task.done():
            self.system_monitor_task.cancel()
            
            try:
                await self.system_monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("System resource monitoring stopped")
        
        return {"status": "monitoring_stopped"}
    
    async def create_budget(self,
                          resource_type: ResourceType,
                          limit: float,
                          period: BudgetPeriod,
                          unit: str,
                          name: str,
                          description: str,
                          components: Optional[List[str]] = None,
                          tags: Optional[List[str]] = None,
                          alert_thresholds: Optional[Dict[str, float]] = None,
                          start_date: Optional[str] = None) -> Budget:
        """Create a new resource budget."""
        # Generate budget ID
        budget_id = f"budget_{uuid.uuid4().hex[:8]}"
        
        # Use defaults if not provided
        components = components or []
        tags = tags or []
        alert_thresholds = alert_thresholds or self.config.get("default_alert_thresholds", {})
        start_date = start_date or datetime.now().isoformat()
        
        # Create budget
        budget = Budget(
            id=budget_id,
            resource_type=resource_type,
            components=components,
            limit=limit,
            period=period,
            unit=unit,
            start_date=start_date,
            name=name,
            description=description,
            tags=tags,
            alert_thresholds=alert_thresholds
        )
        
        # Store budget
        self.budgets[budget_id] = budget
        
        # Save to storage
        await self._save_budget(budget)
        
        logger.info(f"Created budget {budget_id}: {name}")
        
        return budget
    
    async def record_usage(self,
                         resource_type: ResourceType,
                         component: str,
                         quantity: float,
                         unit: str,
                         metadata: Optional[Dict[str, Any]] = None) -> ResourceUsage:
        """Record resource usage."""
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
        if self.config.get("max_usage_records"):
            max_records = self.config["max_usage_records"]
            if len(self.usage_records) > max_records:
                self.usage_records = self.usage_records[-max_records:]
        
        # Check against budgets
        await self._check_budget_thresholds(usage)
        
        # Save to storage periodically
        # (in a real system, would batch these writes)
        if len(self.usage_records) % 100 == 0:
            await self._save_usage_records()
        
        return usage
    
    async def get_budget(self, budget_id: str) -> Dict[str, Any]:
        """Get details of a budget."""
        if budget_id not in self.budgets:
            raise ValueError(f"Budget {budget_id} not found")
        
        budget = self.budgets[budget_id]
        
        # Calculate current usage
        usage_data = await self._calculate_budget_usage(budget)
        
        result = budget.to_dict()
        result.update(usage_data)
        
        return result
    
    async def get_budgets(self, 
                        resource_type: Optional[ResourceType] = None,
                        component: Optional[str] = None,
                        tag: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all budgets, optionally filtered."""
        results = []
        
        for budget_id, budget in self.budgets.items():
            # Apply filters
            if resource_type and budget.resource_type != resource_type:
                continue
            
            # Component filtering - only filter out if budget has components and the component isn't in them
            if component and budget.components and component not in budget.components:
                continue
                
            if tag and tag not in budget.tags:
                continue
            
            # Calculate usage
            usage_data = await self._calculate_budget_usage(budget)
            
            # Build result
            result = budget.to_dict()
            result.update(usage_data)
            
            results.append(result)
        
        return results
    
    async def update_budget(self,
                          budget_id: str,
                          updates: Dict[str, Any]) -> Budget:
        """Update a budget."""
        if budget_id not in self.budgets:
            raise ValueError(f"Budget {budget_id} not found")
        
        budget = self.budgets[budget_id]
        
        # Apply updates
        if "name" in updates:
            budget.name = updates["name"]
            
        if "description" in updates:
            budget.description = updates["description"]
            
        if "limit" in updates:
            budget.limit = updates["limit"]
            
        if "period" in updates:
            budget.period = updates["period"] if isinstance(updates["period"], BudgetPeriod) else BudgetPeriod(updates["period"])
            
        if "components" in updates:
            budget.components = updates["components"]
            
        if "tags" in updates:
            budget.tags = updates["tags"]
            
        if "alert_thresholds" in updates:
            budget.alert_thresholds = updates["alert_thresholds"]
            
        if "active" in updates:
            budget.active = updates["active"]
        
        # Save budget
        await self._save_budget(budget)
        
        # Check thresholds after update
        for usage in self.usage_records[-10:]:  # Check recent usage
            if usage.resource_type == budget.resource_type:
                await self._check_budget_thresholds(usage)
        
        logger.info(f"Updated budget {budget_id}")
        
        return budget
    
    async def get_resource_usage(self,
                               resource_type: Optional[ResourceType] = None,
                               component: Optional[str] = None,
                               start_time: Optional[str] = None,
                               end_time: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get resource usage records, optionally filtered."""
        results = []
        
        for usage in self.usage_records:
            # Apply filters
            if resource_type and usage.resource_type != resource_type:
                continue
                
            if component and usage.component != component:
                continue
                
            if start_time and usage.timestamp < start_time:
                continue
                
            if end_time and usage.timestamp > end_time:
                continue
            
            # Add to results
            results.append({
                "resource_type": usage.resource_type.value,
                "component": usage.component,
                "quantity": usage.quantity,
                "unit": usage.unit,
                "timestamp": usage.timestamp,
                "metadata": usage.metadata
            })
        
        return results
    
    async def get_alerts(self,
                       budget_id: Optional[str] = None,
                       include_acknowledged: bool = False) -> List[Dict[str, Any]]:
        """Get budget alerts, optionally filtered."""
        results = []
        
        for alert_id, alert in self.alerts.items():
            # Apply filters
            if budget_id and alert.budget_id != budget_id:
                continue
                
            if not include_acknowledged and alert.acknowledged:
                continue
            
            # Add to results
            results.append(alert.to_dict())
        
        return results
    
    async def acknowledge_alert(self, alert_id: str) -> Dict[str, Any]:
        """Acknowledge a budget alert."""
        if alert_id not in self.alerts:
            raise ValueError(f"Alert {alert_id} not found")
        
        alert = self.alerts[alert_id]
        alert.acknowledged = True
        
        # Save to storage
        await self._save_alerts()
        
        return alert.to_dict()
    
    async def create_usage_report(self,
                                resource_type: Optional[ResourceType] = None,
                                component: Optional[str] = None,
                                start_time: Optional[str] = None,
                                end_time: Optional[str] = None,
                                group_by: Optional[str] = None) -> Dict[str, Any]:
        """Create a report of resource usage."""
        # Get usage data
        usage_data = await self.get_resource_usage(
            resource_type=resource_type,
            component=component,
            start_time=start_time,
            end_time=end_time
        )
        
        if not usage_data:
            return {
                "status": "no_data",
                "resource_type": resource_type.value if resource_type else "all",
                "component": component or "all"
            }
        
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame(usage_data)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        
        # Summary stats
        summary = {
            "total_records": len(df),
            "date_range": {
                "start": df["timestamp"].min().isoformat(),
                "end": df["timestamp"].max().isoformat()
            },
            "resource_types": df["resource_type"].unique().tolist(),
            "components": df["component"].unique().tolist()
        }
        
        # Group data if requested
        if group_by:
            if group_by == "resource_type":
                grouped = df.groupby("resource_type")
            elif group_by == "component":
                grouped = df.groupby("component")
            elif group_by == "day":
                grouped = df.groupby(df["timestamp"].dt.date)
            elif group_by == "hour":
                grouped = df.groupby(df["timestamp"].dt.strftime("%Y-%m-%d %H:00"))
            else:
                grouped = df.groupby(group_by)
                
            # Calculate stats by group
            group_stats = []
            for name, group in grouped:
                group_stats.append({
                    "group": str(name),
                    "count": len(group),
                    "total_quantity": group["quantity"].sum(),
                    "average_quantity": group["quantity"].mean(),
                    "min_quantity": group["quantity"].min(),
                    "max_quantity": group["quantity"].max()
                })
                
            summary["grouped_by"] = group_by
            summary["groups"] = group_stats
        
        # Overall stats
        summary["overall"] = {
            "total_quantity": df["quantity"].sum(),
            "average_quantity": df["quantity"].mean(),
            "min_quantity": df["quantity"].min(),
            "max_quantity": df["quantity"].max()
        }
        
        # Create visualization
        visualization = await self._create_usage_visualization(
            df, 
            resource_type.value if resource_type else "all", 
            component or "all",
            group_by
        )
        
        # Build final report
        report = {
            "status": "success",
            "summary": summary,
            "visualization": visualization,
            "timestamp": datetime.now().isoformat()
        }
        
        return report
        
    async def _create_usage_visualization(self,
                                        df: pd.DataFrame,
                                        resource_type_str: str,
                                        component_str: str,
                                        group_by: Optional[str]) -> Dict[str, Any]:
        """Create visualization of usage data."""
        if len(df) < 2:
            return {"status": "insufficient_data"}
        
        # Create different visualizations based on grouping
        if group_by == "resource_type":
            return await self._visualize_by_resource_type(df)
        elif group_by == "component":
            return await self._visualize_by_component(df)
        else:
            # Time series visualization
            return await self._visualize_time_series(df, resource_type_str, component_str)
    
    async def _visualize_time_series(self,
                                   df: pd.DataFrame,
                                   resource_type_str: str,
                                   component_str: str) -> Dict[str, Any]:
        """Create time series visualization."""
        plt.figure(figsize=(12, 6))
        
        # If multiple resource types or components, use a grouped visualization
        if len(df["resource_type"].unique()) > 1 or len(df["component"].unique()) > 1:
            # Group by resource type and component
            groups = df.groupby(["resource_type", "component"])
            
            for (res_type, comp), group in groups:
                plt.plot(
                    group["timestamp"], 
                    group["quantity"], 
                    label=f"{res_type} - {comp}",
                    marker='o' if len(group) < 10 else None
                )
        else:
            plt.plot(
                df["timestamp"], 
                df["quantity"], 
                label=f"{resource_type_str} - {component_str}",
                marker='o' if len(df) < 10 else None
            )
        
        plt.title(f"Resource Usage Over Time: {resource_type_str}")
        plt.xlabel("Time")
        plt.ylabel(f"Quantity ({df['unit'].iloc[0]})")
        plt.grid(True)
        plt.legend()
        
        # Add budget lines if applicable
        for budget in self.budgets.values():
            if (resource_type_str == "all" or budget.resource_type.value == resource_type_str) and \
               (component_str == "all" or not budget.components or component_str in budget.components):
                plt.axhline(
                    y=budget.limit, 
                    color='r', 
                    linestyle='--', 
                    label=f"Budget: {budget.name} ({budget.limit} {budget.unit})"
                )
        
        plt.tight_layout()
        
        # Convert to base64
        buffer = BytesIO()
        plt.savefig(buffer, format="png")
        plt.close()
        
        image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        return {
            "type": "time_series",
            "image": f"data:image/png;base64,{image_base64}"
        }
    
    async def _visualize_by_resource_type(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Create visualization grouped by resource type."""
        plt.figure(figsize=(10, 6))
        
        # Group by resource type
        grouped = df.groupby("resource_type")["quantity"].sum()
        
        # Create bar chart
        ax = grouped.plot(kind="bar", color="skyblue")
        plt.title("Resource Usage by Type")
        plt.xlabel("Resource Type")
        plt.ylabel(f"Total Quantity")
        plt.grid(True, axis='y')
        
        # Add labels
        for i, v in enumerate(grouped):
            ax.text(i, v * 1.01, f"{v:.1f}", ha='center')
        
        plt.tight_layout()
        
        # Convert to base64
        buffer = BytesIO()
        plt.savefig(buffer, format="png")
        plt.close()
        
        image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        return {
            "type": "resource_type_distribution",
            "image": f"data:image/png;base64,{image_base64}"
        }
    
    async def _visualize_by_component(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Create visualization grouped by component."""
        plt.figure(figsize=(12, 6))
        
        # Group by component
        grouped = df.groupby("component")["quantity"].sum().sort_values(ascending=False)
        
        # Limit to top 10 if too many
        if len(grouped) > 10:
            grouped = grouped.head(10)
        
        # Create bar chart
        ax = grouped.plot(kind="bar", color="lightgreen")
        plt.title("Resource Usage by Component")
        plt.xlabel("Component")
        plt.ylabel(f"Total Quantity")
        plt.grid(True, axis='y')
        
        # Add labels
        for i, v in enumerate(grouped):
            ax.text(i, v * 1.01, f"{v:.1f}", ha='center')
        
        plt.tight_layout()
        
        # Convert to base64
        buffer = BytesIO()
        plt.savefig(buffer, format="png")
        plt.close()
        
        image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        return {
            "type": "component_distribution",
            "image": f"data:image/png;base64,{image_base64}"
        }
    
    async def _run_system_monitoring(self) -> None:
        """Run periodic system monitoring."""
        try:
            while self.is_monitoring:
                # Monitor system resources
                await self._collect_system_metrics()
                
                # Sleep until next interval
                interval = self.config.get("monitoring_interval_seconds", 60)
                await asyncio.sleep(interval)
                
        except asyncio.CancelledError:
            logger.info("System monitoring task canceled")
        except Exception as e:
            logger.error(f"Error in system monitoring: {str(e)}")
            self.is_monitoring = False
            raise
    
    async def _collect_system_metrics(self) -> None:
        """Collect system resource metrics."""
        try:
            # Use resource handlers for each resource type
            # CPU usage
            cpu_data = self.resource_handlers[ResourceType.CPU]()
            await self.record_usage(
                resource_type=ResourceType.CPU,
                component="system",
                quantity=cpu_data["percentage"],
                unit="percent",
                metadata=cpu_data
            )
            
            # Memory usage
            memory_data = self.resource_handlers[ResourceType.MEMORY]()
            await self.record_usage(
                resource_type=ResourceType.MEMORY,
                component="system",
                quantity=memory_data["percentage"],
                unit="percent",
                metadata=memory_data
            )
            
            # Disk usage
            storage_data = self.resource_handlers[ResourceType.STORAGE]()
            await self.record_usage(
                resource_type=ResourceType.STORAGE,
                component="system",
                quantity=storage_data["percentage"],
                unit="percent",
                metadata=storage_data
            )
            
            # Network IO
            network_data = self.resource_handlers[ResourceType.NETWORK]()
            await self.record_usage(
                resource_type=ResourceType.NETWORK,
                component="system",
                quantity=network_data["bytes_sent"] + network_data["bytes_recv"],
                unit="bytes",
                metadata=network_data
            )
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {str(e)}")
    
    async def _calculate_budget_usage(self, budget: Budget) -> Dict[str, Any]:
        """Calculate current usage for a budget."""
        # Determine time window based on budget period
        start_time = None
        
        # Get budget start date
        budget_start = datetime.fromisoformat(budget.start_date)
        
        # Calculate period start time
        now = datetime.now()
        if budget.period == BudgetPeriod.HOURLY:
            start_time = now.replace(minute=0, second=0, microsecond=0)
        elif budget.period == BudgetPeriod.DAILY:
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif budget.period == BudgetPeriod.WEEKLY:
            # Start of week (Monday)
            start_time = (now - timedelta(days=now.weekday())).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        elif budget.period == BudgetPeriod.MONTHLY:
            start_time = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif budget.period == BudgetPeriod.QUARTERLY:
            quarter_month = ((now.month - 1) // 3) * 3 + 1
            start_time = now.replace(
                month=quarter_month, day=1, hour=0, minute=0, second=0, microsecond=0
            )
        elif budget.period == BudgetPeriod.YEARLY:
            start_time = now.replace(
                month=1, day=1, hour=0, minute=0, second=0, microsecond=0
            )
        elif budget.period == BudgetPeriod.PERPETUAL:
            start_time = budget_start
        
        # Ensure we don't go before budget start
        if start_time < budget_start:
            start_time = budget_start
        
        start_time_str = start_time.isoformat()
        
        # Filter usage records
        usage_in_period = []
        for usage in self.usage_records:
            # Match resource type
            if usage.resource_type != budget.resource_type:
                continue
            
            # Match component (if budget specifies components)
            if budget.components and usage.component not in budget.components:
                continue
            
            # Check time period
            if usage.timestamp < start_time_str:
                continue
            
            usage_in_period.append(usage)
        
        # Calculate total usage
        total_usage = sum(usage.quantity for usage in usage_in_period)
        usage_count = len(usage_in_period)
        
        # Calculate percentage of budget used
        percentage_used = (total_usage / budget.limit * 100) if budget.limit > 0 else 0
        
        # Determine status
        status = "ok"
        if percentage_used >= 90:
            status = "critical"
        elif percentage_used >= 70:
            status = "warning"
        
        return {
            "usage": {
                "total": total_usage,
                "count": usage_count,
                "percentage": percentage_used,
                "status": status,
                "period_start": start_time_str,
                "period_end": now.isoformat(),
                "remaining": max(0, budget.limit - total_usage)
            }
        }
    
    async def _load_data(self) -> None:
        """Load budgets, usage records and alerts from storage."""
        storage_path = self.config.get("storage_path", "data/resources")
        
        # Load budgets
        budgets_dir = os.path.join(storage_path, "budgets")
        if os.path.exists(budgets_dir):
            for filename in os.listdir(budgets_dir):
                if filename.endswith(".json"):
                    try:
                        with open(os.path.join(budgets_dir, filename), 'r') as f:
                            data = json.load(f)
                            budget = Budget.from_dict(data)
                            self.budgets[budget.id] = budget
                    except Exception as e:
                        logger.error(f"Error loading budget from {filename}: {str(e)}")
        
        # Load usage records
        usage_file = os.path.join(storage_path, "usage_records.json")
        if os.path.exists(usage_file):
            try:
                with open(usage_file, 'r') as f:
                    data = json.load(f)
                    
                    records = []
                    for record_data in data:
                        try:
                            resource_type = ResourceType(record_data.get("resource_type"))
                            record = ResourceUsage(
                                resource_type=resource_type,
                                component=record_data.get("component", ""),
                                quantity=record_data.get("quantity", 0.0),
                                unit=record_data.get("unit", ""),
                                timestamp=record_data.get("timestamp", datetime.now().isoformat()),
                                metadata=record_data.get("metadata", {})
                            )
                            records.append(record)
                        except Exception as e:
                            logger.error(f"Error parsing usage record: {str(e)}")
                    
                    self.usage_records = records
            except Exception as e:
                logger.error(f"Error loading usage records: {str(e)}")
        
        # Load alerts
        alerts_file = os.path.join(storage_path, "alerts.json")
        if os.path.exists(alerts_file):
            try:
                with open(alerts_file, 'r') as f:
                    data = json.load(f)
                    
                    alerts = {}
                    for alert_data in data:
                        try:
                            alert = BudgetAlert.from_dict(alert_data)
                            alerts[alert.id] = alert
                        except Exception as e:
                            logger.error(f"Error parsing alert: {str(e)}")
                    
                    self.alerts = alerts
            except Exception as e:
                logger.error(f"Error loading alerts: {str(e)}")
    
    async def _save_budget(self, budget: Budget) -> None:
        """Save budget to storage."""
        storage_path = self.config.get("storage_path", "data/resources")
        budgets_dir = os.path.join(storage_path, "budgets")
        os.makedirs(budgets_dir, exist_ok=True)
        
        file_path = os.path.join(budgets_dir, f"{budget.id}.json")
        
        with open(file_path, 'w') as f:
            json.dump(budget.to_dict(), f, indent=2)
            
        logger.debug(f"Budget {budget.id} saved to {file_path}")
    
    async def _save_usage_records(self) -> None:
        """Save usage records to storage."""
        storage_path = self.config.get("storage_path", "data/resources")
        os.makedirs(storage_path, exist_ok=True)
        
        file_path = os.path.join(storage_path, "usage_records.json")
        
        # Convert to list of dictionaries
        data = []
        for usage in self.usage_records:
            data.append({
                "resource_type": usage.resource_type.value,
                "component": usage.component,
                "quantity": usage.quantity,
                "unit": usage.unit,
                "timestamp": usage.timestamp,
                "metadata": usage.metadata
            })
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
            
        logger.debug(f"Saved {len(data)} usage records to {file_path}")
    
    async def _save_alerts(self) -> None:
        """Save alerts to storage."""
        storage_path = self.config.get("storage_path", "data/resources")
        os.makedirs(storage_path, exist_ok=True)
        
        file_path = os.path.join(storage_path, "alerts.json")
        
        # Convert to list of dictionaries
        data = [alert.to_dict() for alert in self.alerts.values()]
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
            
        logger.debug(f"Saved {len(data)} alerts to {file_path}")
    
    async def clear_old_data(self) -> Dict[str, Any]:
        """Clear old usage records and acknowledged alerts."""
        now = datetime.now()
        retention_days = self.config.get("usage_retention_days", 30)
        cutoff_date = (now - timedelta(days=retention_days)).isoformat()
        
        # Filter usage records
        old_count = len(self.usage_records)
        self.usage_records = [
            usage for usage in self.usage_records
            if usage.timestamp >= cutoff_date
        ]
        usage_removed = old_count - len(self.usage_records)
        
        # Filter acknowledged alerts
        old_alert_count = len(self.alerts)
        self.alerts = {
            alert_id: alert for alert_id, alert in self.alerts.items()
            if not alert.acknowledged or alert.timestamp >= cutoff_date
        }
        alerts_removed = old_alert_count - len(self.alerts)
        
        # Save updated data
        await self._save_usage_records()
        await self._save_alerts()
        
        return {
            "usage_records_removed": usage_removed,
            "alerts_removed": alerts_removed,
            "cutoff_date": cutoff_date
        }
    
    async def _check_budget_thresholds(self, usage: ResourceUsage) -> None:
        """Check if usage triggers any budget thresholds."""
        # Find relevant budgets
        for budget_id, budget in self.budgets.items():
            # Skip inactive budgets
            if not budget.active:
                continue
            
            # Match resource type
            if budget.resource_type != usage.resource_type:
                continue
            
            # Match component (if budget specifies components)
            if budget.components and usage.component not in budget.components:
                continue
            
            # Calculate current usage
            usage_data = await self._calculate_budget_usage(budget)
            current_usage = usage_data["usage"]["total"]
            percentage = usage_data["usage"]["percentage"]
            
            # Check thresholds
            for threshold_name, threshold_value in budget.alert_thresholds.items():
                # Convert threshold to percentage if it's not already
                threshold_percentage = threshold_value
                if threshold_value > 1 and threshold_value <= 100:
                    threshold_percentage = threshold_value
                elif threshold_value <= 1:
                    threshold_percentage = threshold_value * 100
                
                # Check if threshold crossed
                if percentage >= threshold_percentage:
                    # Create alert ID
                    alert_id = f"alert_{uuid.uuid4().hex[:8]}"
                    
                    # Check if similar alert already exists
                    for existing_alert in self.alerts.values():
                        if (existing_alert.budget_id == budget_id and
                            existing_alert.threshold_name == threshold_name and
                            not existing_alert.acknowledged):
                            # Already have an unacknowledged alert for this
                            return
                    
                    # Create new alert
                    alert = BudgetAlert(
                        id=alert_id,
                        budget_id=budget_id,
                        threshold_name=threshold_name,
                        threshold_value=threshold_value,
                        current_usage=current_usage,
                        percentage=percentage
                    )
                    
                    # Store alert
                    self.alerts[alert_id] = alert
                    
                    # Save alerts
                    await self._save_alerts()
                    
                    logger.warning(
                        f"Budget alert: {budget.name} ({threshold_name} threshold at {threshold_percentage}%) - "
                        f"Current usage: {current_usage} {budget.unit} ({percentage:.1f}%)"
                    )
    
    def _monitor_cpu(self) -> Dict[str, Any]:
        """Monitor CPU usage."""
        return {
            "percentage": psutil.cpu_percent(interval=1),
            "count": psutil.cpu_count()
        }
    
    def _monitor_memory(self) -> Dict[str, Any]:
        """Monitor memory usage."""
        memory = psutil.virtual_memory()
        return {
            "total": memory.total,
            "available": memory.available,
            "used": memory.used,
            "percentage": memory.percent
        }
    
    def _monitor_storage(self) -> Dict[str, Any]:
        """Monitor storage usage."""
        disk = psutil.disk_usage('/')
        return {
            "total": disk.total,
            "free": disk.free,
            "used": disk.used,
            "percentage": disk.percent
        }
    
    def _monitor_network(self) -> Dict[str, Any]:
        """Monitor network usage."""
        net_io = psutil.net_io_counters()
        return {
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv
        }
    
    def _monitor_api_calls(self) -> Dict[str, Any]:
        """Monitor API calls."""
        # This would be integrated with your API tracking
        return {}
    
    def _monitor_model_tokens(self) -> Dict[str, Any]:
        """Monitor model token usage."""
        # This would be integrated with your LLM usage tracking
        return {}
    
    def _monitor_processing_time(self) -> Dict[str, Any]:
        """Monitor processing time."""
        # This would track processing time for various operations
        return {}
    
    def _monitor_concurrent_tasks(self) -> Dict[str, Any]:
        """Monitor concurrent tasks."""
        # This would track the number of parallel tasks running
        return {} 