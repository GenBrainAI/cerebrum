from typing import Dict, List, Optional, Any, Set, Tuple
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

logger = logging.getLogger(__name__)

class ResourceMonitor:
    """Monitors and manages resource usage and budgets."""
    
    def __init__(self, budget_config: Optional[Dict[str, Any]] = None):
        """
        Initialize with budget configuration.
        
        Args:
            budget_config: Dictionary with budget settings
                - cpu: CPU usage budget (percentage)
                - memory: Memory usage budget (MB)
                - disk: Disk usage budget (MB)
                - api_calls: API call budget (count)
                - tokens: Token usage budget (count)
        """
        self.storage_path = os.path.join(os.path.expanduser("~"), ".cerebrum", "resource_monitor")
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Create subdirectories
        self.budgets_path = os.path.join(self.storage_path, "budgets")
        self.usage_path = os.path.join(self.storage_path, "usage")
        self.alerts_path = os.path.join(self.storage_path, "alerts")
        
        os.makedirs(self.budgets_path, exist_ok=True)
        os.makedirs(self.usage_path, exist_ok=True)
        os.makedirs(self.alerts_path, exist_ok=True)
        
        # Set default budgets
        self.budgets: Dict[str, Dict[str, Any]] = {
            "cpu": {
                "limit": 80.0,  # 80% CPU usage
                "period": "hourly",
                "alert_threshold": 70.0,
                "enabled": True
            },
            "memory": {
                "limit": 1024.0,  # 1GB memory usage
                "period": "hourly",
                "alert_threshold": 900.0,
                "enabled": True
            },
            "disk": {
                "limit": 1024.0,  # 1GB disk usage
                "period": "daily",
                "alert_threshold": 900.0,
                "enabled": True
            },
            "api_calls": {
                "limit": 1000.0,  # 1000 API calls
                "period": "daily",
                "alert_threshold": 900.0,
                "enabled": True
            },
            "tokens": {
                "limit": 100000.0,  # 100K tokens
                "period": "daily",
                "alert_threshold": 90000.0,
                "enabled": True
            }
        }
        
        # Override with provided config
        if budget_config:
            for resource_type, config in budget_config.items():
                if resource_type in self.budgets:
                    self.budgets[resource_type].update(config)
                else:
                    self.budgets[resource_type] = config
        
        # Load existing budgets
        self._load_budgets()
        
        # Initialize monitoring state
        self.monitoring = False
        self.monitor_task = None
        self.monitor_interval = 60.0  # seconds
        self.current_usage: Dict[str, float] = {}
        self.usage_history: Dict[str, List[Dict[str, Any]]] = {}
        self.alerts: List[Dict[str, Any]] = []
    
    async def start_monitoring(self) -> None:
        """Start resource monitoring."""
        if self.monitoring:
            logger.info("Resource monitoring already running")
            return
        
        logger.info("Starting resource monitoring")
        self.monitoring = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
    
    async def stop_monitoring(self) -> None:
        """Stop resource monitoring."""
        if not self.monitoring:
            logger.info("Resource monitoring not running")
            return
        
        logger.info("Stopping resource monitoring")
        self.monitoring = False
        
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
            
            self.monitor_task = None
    
    async def get_current_usage(self) -> Dict[str, float]:
        """
        Get current resource usage statistics.
        
        Returns:
            Dictionary with resource usage values
        """
        # Update system resource usage
        await self._update_system_resources()
        
        return self.current_usage
    
    async def set_budget(self, resource_type: str, limit: float, 
                        period: str = "daily") -> Dict[str, Any]:
        """
        Set a budget for a specific resource type.
        
        Args:
            resource_type: Type of resource (cpu, memory, disk, api_calls, tokens)
            limit: Budget limit value
            period: Budget period (hourly, daily, weekly, monthly)
            
        Returns:
            Dictionary with budget information
        """
        # Validate period
        valid_periods = ["hourly", "daily", "weekly", "monthly"]
        if period not in valid_periods:
            return {
                "success": False,
                "message": f"Invalid period: {period}. Must be one of {valid_periods}",
                "resource_type": resource_type
            }
        
        # Create or update budget
        if resource_type not in self.budgets:
            self.budgets[resource_type] = {
                "limit": limit,
                "period": period,
                "alert_threshold": limit * 0.9,  # 90% of limit
                "enabled": True
            }
        else:
            self.budgets[resource_type]["limit"] = limit
            self.budgets[resource_type]["period"] = period
            self.budgets[resource_type]["alert_threshold"] = limit * 0.9  # 90% of limit
        
        # Save budget
        self._save_budget(resource_type)
        
        return {
            "success": True,
            "message": f"Budget set for {resource_type}",
            "resource_type": resource_type,
            "budget": self.budgets[resource_type]
        }
    
    async def check_budget(self, resource_type: str) -> Dict[str, Any]:
        """
        Check current usage against budget for a resource type.
        
        Args:
            resource_type: Type of resource to check
            
        Returns:
            Dictionary with budget check results
        """
        # Check if budget exists
        if resource_type not in self.budgets:
            return {
                "success": False,
                "message": f"No budget defined for {resource_type}",
                "resource_type": resource_type
            }
        
        # Get budget
        budget = self.budgets[resource_type]
        
        # Get current period usage
        period_usage = await self._get_period_usage(resource_type, budget["period"])
        
        # Calculate percentage of budget used
        if budget["limit"] > 0:
            percentage_used = (period_usage / budget["limit"]) * 100.0
        else:
            percentage_used = 0.0
        
        # Check if over budget
        over_budget = period_usage > budget["limit"]
        
        # Check if approaching budget
        approaching_budget = period_usage > budget["alert_threshold"]
        
        # Create result
        result = {
            "success": True,
            "resource_type": resource_type,
            "budget_limit": budget["limit"],
            "period": budget["period"],
            "period_usage": period_usage,
            "percentage_used": percentage_used,
            "over_budget": over_budget,
            "approaching_budget": approaching_budget,
            "remaining": max(0, budget["limit"] - period_usage)
        }
        
        # Create alert if over budget or approaching budget
        if over_budget and budget["enabled"]:
            await self._create_alert(
                resource_type=resource_type,
                level="error",
                message=f"{resource_type} usage exceeds budget",
                details={
                    "budget_limit": budget["limit"],
                    "current_usage": period_usage,
                    "percentage_used": percentage_used,
                    "period": budget["period"]
                }
            )
        elif approaching_budget and budget["enabled"]:
            await self._create_alert(
                resource_type=resource_type,
                level="warning",
                message=f"{resource_type} usage approaching budget",
                details={
                    "budget_limit": budget["limit"],
                    "current_usage": period_usage,
                    "percentage_used": percentage_used,
                    "period": budget["period"]
                }
            )
        
        return result
    
    async def record_usage(self, resource_type: str, amount: float, 
                          operation_id: Optional[str] = None) -> None:
        """
        Record usage of a resource.
        
        Args:
            resource_type: Type of resource used
            amount: Amount of resource used
            operation_id: Optional operation identifier
        """
        # Create usage record
        usage_record = {
            "id": str(uuid.uuid4()),
            "resource_type": resource_type,
            "amount": amount,
            "timestamp": datetime.now().isoformat(),
            "operation_id": operation_id
        }
        
        # Add to usage history
        if resource_type not in self.usage_history:
            self.usage_history[resource_type] = []
        
        self.usage_history[resource_type].append(usage_record)
        
        # Update current usage
        if resource_type in self.current_usage:
            self.current_usage[resource_type] += amount
        else:
            self.current_usage[resource_type] = amount
        
        # Save usage record
        self._save_usage_record(usage_record)
        
        # Check budget
        await self.check_budget(resource_type)
    
    async def get_usage_history(self, resource_type: str, 
                               period: str = "daily") -> List[Dict[str, Any]]:
        """
        Get historical usage for a resource type.
        
        Args:
            resource_type: Type of resource
            period: Period to aggregate by (hourly, daily, weekly, monthly)
            
        Returns:
            List of usage records aggregated by period
        """
        # Load usage history if not already loaded
        if resource_type not in self.usage_history:
            self._load_usage_history(resource_type)
        
        # Get raw usage records
        records = self.usage_history.get(resource_type, [])
        
        # Aggregate by period
        aggregated = []
        
        if period == "hourly":
            # Group by hour
            hour_groups: Dict[str, List[Dict[str, Any]]] = {}
            
            for record in records:
                timestamp = datetime.fromisoformat(record["timestamp"])
                hour_key = timestamp.strftime("%Y-%m-%d %H:00:00")
                
                if hour_key not in hour_groups:
                    hour_groups[hour_key] = []
                
                hour_groups[hour_key].append(record)
            
            # Aggregate each hour
            for hour_key, hour_records in hour_groups.items():
                total_amount = sum(record["amount"] for record in hour_records)
                count = len(hour_records)
                
                aggregated.append({
                    "period": hour_key,
                    "total_amount": total_amount,
                    "count": count,
                    "average": total_amount / count if count > 0 else 0
                })
        
        elif period == "daily":
            # Group by day
            day_groups: Dict[str, List[Dict[str, Any]]] = {}
            
            for record in records:
                timestamp = datetime.fromisoformat(record["timestamp"])
                day_key = timestamp.strftime("%Y-%m-%d")
                
                if day_key not in day_groups:
                    day_groups[day_key] = []
                
                day_groups[day_key].append(record)
            
            # Aggregate each day
            for day_key, day_records in day_groups.items():
                total_amount = sum(record["amount"] for record in day_records)
                count = len(day_records)
                
                aggregated.append({
                    "period": day_key,
                    "total_amount": total_amount,
                    "count": count,
                    "average": total_amount / count if count > 0 else 0
                })
        
        elif period == "weekly":
            # Group by week
            week_groups: Dict[str, List[Dict[str, Any]]] = {}
            
            for record in records:
                timestamp = datetime.fromisoformat(record["timestamp"])
                week_key = timestamp.strftime("%Y-W%U")
                
                if week_key not in week_groups:
                    week_groups[week_key] = []
                
                week_groups[week_key].append(record)
            
            # Aggregate each week
            for week_key, week_records in week_groups.items():
                total_amount = sum(record["amount"] for record in week_records)
                count = len(week_records)
                
                aggregated.append({
                    "period": week_key,
                    "total_amount": total_amount,
                    "count": count,
                    "average": total_amount / count if count > 0 else 0
                })
        
        elif period == "monthly":
            # Group by month
            month_groups: Dict[str, List[Dict[str, Any]]] = {}
            
            for record in records:
                timestamp = datetime.fromisoformat(record["timestamp"])
                month_key = timestamp.strftime("%Y-%m")
                
                if month_key not in month_groups:
                    month_groups[month_key] = []
                
                month_groups[month_key].append(record)
            
            # Aggregate each month
            for month_key, month_records in month_groups.items():
                total_amount = sum(record["amount"] for record in month_records)
                count = len(month_records)
                
                aggregated.append({
                    "period": month_key,
                    "total_amount": total_amount,
                    "count": count,
                    "average": total_amount / count if count > 0 else 0
                })
        
        # Sort by period
        aggregated.sort(key=lambda x: x["period"])
        
        return aggregated
    
    async def get_budget_alerts(self) -> List[Dict[str, Any]]:
        """
        Get alerts for budget thresholds that have been crossed.
        
        Returns:
            List of alert dictionaries
        """
        # Load alerts if not already loaded
        self._load_alerts()
        
        return self.alerts
    
    async def _monitoring_loop(self) -> None:
        """Background task for continuous resource monitoring."""
        try:
            while self.monitoring:
                # Update system resource usage
                await self._update_system_resources()
                
                # Check budgets for system resources
                for resource_type in ["cpu", "memory", "disk"]:
                    if resource_type in self.budgets and self.budgets[resource_type]["enabled"]:
                        await self.check_budget(resource_type)
                
                # Wait for next monitoring interval
                await asyncio.sleep(self.monitor_interval)
        except asyncio.CancelledError:
            logger.info("Resource monitoring loop cancelled")
        except Exception as e:
            logger.exception(f"Error in resource monitoring loop: {e}")
            self.monitoring = False
    
    async def _update_system_resources(self) -> None:
        """Update current system resource usage."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.current_usage["cpu"] = cpu_percent
            
            # Memory usage (MB)
            memory = psutil.virtual_memory()
            memory_used_mb = memory.used / (1024 * 1024)
            self.current_usage["memory"] = memory_used_mb
            
            # Disk usage (MB)
            disk = psutil.disk_usage(os.path.expanduser("~"))
            disk_used_mb = disk.used / (1024 * 1024)
            self.current_usage["disk"] = disk_used_mb
            
            # Record system resource usage
            for resource_type in ["cpu", "memory", "disk"]:
                await self.record_usage(
                    resource_type=resource_type,
                    amount=self.current_usage[resource_type],
                    operation_id="system_monitor"
                )
        except Exception as e:
            logger.exception(f"Error updating system resources: {e}")
    
    async def _get_period_usage(self, resource_type: str, period: str) -> float:
        """
        Get total usage for a resource type in the current period.
        
        Args:
            resource_type: Type of resource
            period: Period to aggregate by (hourly, daily, weekly, monthly)
            
        Returns:
            Total usage in the current period
        """
        # Determine period start time
        now = datetime.now()
        
        if period == "hourly":
            period_start = now.replace(minute=0, second=0, microsecond=0)
        elif period == "daily":
            period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "weekly":
            # Start of week (Monday)
            days_since_monday = now.weekday()
            period_start = (now - timedelta(days=days_since_monday)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        elif period == "monthly":
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            # Default to daily
            period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Load usage history if not already loaded
        if resource_type not in self.usage_history:
            self._load_usage_history(resource_type)
        
        # Filter records in the current period
        period_records = [
            record for record in self.usage_history.get(resource_type, [])
            if datetime.fromisoformat(record["timestamp"]) >= period_start
        ]
        
        # Sum usage
        total_usage = sum(record["amount"] for record in period_records)
        
        return total_usage
    
    async def _create_alert(self, resource_type: str, level: str, message: str, 
                           details: Dict[str, Any]) -> None:
        """
        Create a budget alert.
        
        Args:
            resource_type: Type of resource
            level: Alert level (info, warning, error)
            message: Alert message
            details: Alert details
        """
        # Create alert record
        alert = {
            "id": str(uuid.uuid4()),
            "resource_type": resource_type,
            "level": level,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat(),
            "acknowledged": False
        }
        
        # Add to alerts
        self.alerts.append(alert)
        
        # Save alert
        self._save_alert(alert)
        
        # Log alert
        if level == "error":
            logger.error(f"Resource alert: {message}")
        elif level == "warning":
            logger.warning(f"Resource alert: {message}")
        else:
            logger.info(f"Resource alert: {message}")
    
    def _load_budgets(self) -> None:
        """Load budgets from storage."""
        try:
            for file_path in Path(self.budgets_path).glob("*.json"):
                with open(file_path, "r") as f:
                    budget = json.load(f)
                    resource_type = budget.get("resource_type")
                    if resource_type:
                        self.budgets[resource_type] = budget
        except Exception as e:
            logger.exception(f"Error loading budgets: {e}")
    
    def _save_budget(self, resource_type: str) -> None:
        """Save budget to storage."""
        try:
            budget = self.budgets[resource_type].copy()
            budget["resource_type"] = resource_type
            
            file_path = os.path.join(self.budgets_path, f"{resource_type}.json")
            with open(file_path, "w") as f:
                json.dump(budget, f, indent=2)
        except Exception as e:
            logger.exception(f"Error saving budget for {resource_type}: {e}")
    
    def _load_usage_history(self, resource_type: str) -> None:
        """Load usage history for a resource type."""
        try:
            resource_path = os.path.join(self.usage_path, resource_type)
            if not os.path.exists(resource_path):
                os.makedirs(resource_path, exist_ok=True)
                self.usage_history[resource_type] = []
                return
            
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
                            records.append(record)
            
            self.usage_history[resource_type] = records
        except Exception as e:
            logger.exception(f"Error loading usage history for {resource_type}: {e}")
            self.usage_history[resource_type] = []
    
    def _save_usage_record(self, record: Dict[str, Any]) -> None:
        """Save usage record to storage."""
        try:
            resource_type = record["resource_type"]
            timestamp = datetime.fromisoformat(record["timestamp"])
            date_str = timestamp.strftime("%Y-%m-%d")
            
            resource_path = os.path.join(self.usage_path, resource_type)
            os.makedirs(resource_path, exist_ok=True)
            
            file_path = os.path.join(resource_path, f"{date_str}.jsonl")
            
            with open(file_path, "a") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            logger.exception(f"Error saving usage record: {e}")
    
    def _load_alerts(self) -> None:
        """Load alerts from storage."""
        try:
            alerts = []
            
            for file_path in Path(self.alerts_path).glob("*.json"):
                with open(file_path, "r") as f:
                    alert = json.load(f)
                    alerts.append(alert)
            
            # Sort by timestamp (newest first)
            alerts.sort(key=lambda a: a["timestamp"], reverse=True)
            
            self.alerts = alerts
        except Exception as e:
            logger.exception(f"Error loading alerts: {e}")
            self.alerts = []
    
    def _save_alert(self, alert: Dict[str, Any]) -> None:
        """Save alert to storage."""
        try:
            file_path = os.path.join(self.alerts_path, f"{alert['id']}.json")
            with open(file_path, "w") as f:
                json.dump(alert, f, indent=2)
        except Exception as e:
            logger.exception(f"Error saving alert: {e}")
    
    async def acknowledge_alert(self, alert_id: str) -> Dict[str, Any]:
        """
        Acknowledge an alert.
        
        Args:
            alert_id: ID of the alert to acknowledge
            
        Returns:
            Dictionary with acknowledgement result
        """
        # Load alerts if not already loaded
        self._load_alerts()
        
        # Find alert
        for alert in self.alerts:
            if alert["id"] == alert_id:
                if alert["acknowledged"]:
                    return {
                        "success": True,
                        "message": f"Alert {alert_id} already acknowledged",
                        "alert_id": alert_id
                    }
                
                # Update alert
                alert["acknowledged"] = True
                alert["acknowledged_at"] = datetime.now().isoformat()
                
                # Save alert
                self._save_alert(alert)
                
                return {
                    "success": True,
                    "message": f"Alert {alert_id} acknowledged",
                    "alert_id": alert_id
                }
        
        return {
            "success": False,
            "message": f"Alert {alert_id} not found",
            "alert_id": alert_id
        }
    
    async def get_system_info(self) -> Dict[str, Any]:
        """
        Get system information.
        
        Returns:
            Dictionary with system information
        """
        try:
            # Get CPU info
            cpu_count = psutil.cpu_count(logical=False)
            cpu_count_logical = psutil.cpu_count(logical=True)
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Get memory info
            memory = psutil.virtual_memory()
            memory_total_gb = memory.total / (1024 * 1024 * 1024)
            memory_used_gb = memory.used / (1024 * 1024 * 1024)
            memory_percent = memory.percent
            
            # Get disk info
            disk = psutil.disk_usage(os.path.expanduser("~"))
            disk_total_gb = disk.total / (1024 * 1024 * 1024)
            disk_used_gb = disk.used / (1024 * 1024 * 1024)
            disk_percent = disk.percent
            
            # Get network info
            net_io = psutil.net_io_counters()
            net_sent_mb = net_io.bytes_sent / (1024 * 1024)
            net_recv_mb = net_io.bytes_recv / (1024 * 1024)
            
            # Get system info
            system = platform.system()
            release = platform.release()
            version = platform.version()
            machine = platform.machine()
            processor = platform.processor()
            
            # Get Python info
            python_version = platform.python_version()
            python_implementation = platform.python_implementation()
            
            return {
                "cpu": {
                    "count": cpu_count,
                    "count_logical": cpu_count_logical,
                    "percent": cpu_percent
                },
                "memory": {
                    "total_gb": memory_total_gb,
                    "used_gb": memory_used_gb,
                    "percent": memory_percent
                },
                "disk": {
                    "total_gb": disk_total_gb,
                    "used_gb": disk_used_gb,
                    "percent": disk_percent
                },
                "network": {
                    "sent_mb": net_sent_mb,
                    "recv_mb": net_recv_mb
                },
                "system": {
                    "system": system,
                    "release": release,
                    "version": version,
                    "machine": machine,
                    "processor": processor
                },
                "python": {
                    "version": python_version,
                    "implementation": python_implementation
                },
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.exception(f"Error getting system info: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            } 