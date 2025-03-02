from typing import Dict, List, Optional, Any, Set, Tuple, Union
import asyncio
import logging
import os
import json
import time
import statistics
from datetime import datetime, timedelta
from pathlib import Path
import uuid

logger = logging.getLogger(__name__)

class MetricsCollector:
    """Collects, stores, and analyzes system metrics."""
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize with storage path for metrics data.
        
        Args:
            storage_path: Path to store metrics data
        """
        self.storage_path = storage_path or os.path.join(os.path.expanduser("~"), ".cerebrum", "metrics")
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Create subdirectories
        self.metrics_path = os.path.join(self.storage_path, "metrics")
        self.tasks_path = os.path.join(self.storage_path, "tasks")
        self.health_path = os.path.join(self.storage_path, "health")
        
        os.makedirs(self.metrics_path, exist_ok=True)
        os.makedirs(self.tasks_path, exist_ok=True)
        os.makedirs(self.health_path, exist_ok=True)
        
        # Initialize metrics state
        self.collection_running = False
        self.collection_task = None
        self.collection_interval = 60.0  # seconds
        self.metrics_cache: Dict[str, List[Dict[str, Any]]] = {}
        self.task_metrics_cache: Dict[str, Dict[str, Any]] = {}
        self.health_metrics: Dict[str, Any] = {}
    
    async def start_collection(self, interval_seconds: float = 60.0) -> None:
        """
        Start metrics collection at the specified interval.
        
        Args:
            interval_seconds: Collection interval in seconds
        """
        if self.collection_running:
            logger.info("Metrics collection already running")
            return
        
        logger.info(f"Starting metrics collection with interval {interval_seconds} seconds")
        self.collection_running = True
        self.collection_interval = interval_seconds
        self.collection_task = asyncio.create_task(self._collection_loop())
    
    async def stop_collection(self) -> None:
        """Stop metrics collection."""
        if not self.collection_running:
            logger.info("Metrics collection not running")
            return
        
        logger.info("Stopping metrics collection")
        self.collection_running = False
        
        if self.collection_task:
            self.collection_task.cancel()
            try:
                await self.collection_task
            except asyncio.CancelledError:
                pass
            
            self.collection_task = None
    
    async def record_metric(self, metric_name: str, value: float, 
                           tags: Optional[Dict[str, str]] = None) -> None:
        """
        Record a single metric value.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            tags: Optional tags for the metric
        """
        # Create metric record
        metric_record = {
            "id": str(uuid.uuid4()),
            "name": metric_name,
            "value": value,
            "tags": tags or {},
            "timestamp": datetime.now().isoformat()
        }
        
        # Add to metrics cache
        if metric_name not in self.metrics_cache:
            self.metrics_cache[metric_name] = []
        
        self.metrics_cache[metric_name].append(metric_record)
        
        # Trim cache if it gets too large
        if len(self.metrics_cache[metric_name]) > 1000:
            self.metrics_cache[metric_name] = self.metrics_cache[metric_name][-1000:]
        
        # Save metric record
        self._save_metric_record(metric_record)
        
        # Update health metrics
        self._update_health_metrics(metric_name, value)
    
    async def record_task_metrics(self, task_id: str, execution_time: float, 
                                 memory_usage: float, success: bool, 
                                 additional_metrics: Optional[Dict[str, float]] = None) -> None:
        """
        Record metrics for a task execution.
        
        Args:
            task_id: ID of the task
            execution_time: Execution time in seconds
            memory_usage: Memory usage in MB
            success: Whether the task succeeded
            additional_metrics: Optional additional metrics
        """
        # Create task metrics record
        task_record = {
            "id": str(uuid.uuid4()),
            "task_id": task_id,
            "execution_time": execution_time,
            "memory_usage": memory_usage,
            "success": success,
            "additional_metrics": additional_metrics or {},
            "timestamp": datetime.now().isoformat()
        }
        
        # Add to task metrics cache
        self.task_metrics_cache[task_id] = task_record
        
        # Save task metrics record
        self._save_task_record(task_record)
        
        # Record individual metrics
        await self.record_metric(
            metric_name="task_execution_time",
            value=execution_time,
            tags={"task_id": task_id, "success": str(success)}
        )
        
        await self.record_metric(
            metric_name="task_memory_usage",
            value=memory_usage,
            tags={"task_id": task_id, "success": str(success)}
        )
        
        if additional_metrics:
            for metric_name, metric_value in additional_metrics.items():
                await self.record_metric(
                    metric_name=f"task_{metric_name}",
                    value=metric_value,
                    tags={"task_id": task_id, "success": str(success)}
                )
    
    async def get_metrics(self, metric_name: str, start_time: Optional[datetime] = None, 
                         end_time: Optional[datetime] = None, 
                         aggregation: str = "avg") -> List[Dict[str, Any]]:
        """
        Get metrics for a specific metric name with optional time range and aggregation.
        
        Args:
            metric_name: Name of the metric
            start_time: Optional start time
            end_time: Optional end time
            aggregation: Aggregation method (avg, sum, min, max, count)
            
        Returns:
            List of metric records
        """
        # Load metrics if not in cache
        if metric_name not in self.metrics_cache:
            self._load_metrics(metric_name)
        
        # Get metrics from cache
        metrics = self.metrics_cache.get(metric_name, [])
        
        # Filter by time range
        if start_time or end_time:
            filtered_metrics = []
            
            for metric in metrics:
                timestamp = datetime.fromisoformat(metric["timestamp"])
                
                if start_time and timestamp < start_time:
                    continue
                    
                if end_time and timestamp > end_time:
                    continue
                    
                filtered_metrics.append(metric)
            
            metrics = filtered_metrics
        
        # Return raw metrics if no aggregation
        if not aggregation or aggregation == "none":
            return metrics
        
        # Aggregate metrics
        aggregated = []
        
        # Group by hour
        hour_groups: Dict[str, List[Dict[str, Any]]] = {}
        
        for metric in metrics:
            timestamp = datetime.fromisoformat(metric["timestamp"])
            hour_key = timestamp.strftime("%Y-%m-%d %H:00:00")
            
            if hour_key not in hour_groups:
                hour_groups[hour_key] = []
            
            hour_groups[hour_key].append(metric)
        
        # Aggregate each hour
        for hour_key, hour_metrics in hour_groups.items():
            values = [metric["value"] for metric in hour_metrics]
            
            if not values:
                continue
                
            if aggregation == "avg":
                agg_value = statistics.mean(values)
            elif aggregation == "sum":
                agg_value = sum(values)
            elif aggregation == "min":
                agg_value = min(values)
            elif aggregation == "max":
                agg_value = max(values)
            elif aggregation == "count":
                agg_value = len(values)
            else:
                # Default to average
                agg_value = statistics.mean(values)
            
            aggregated.append({
                "timestamp": hour_key,
                "value": agg_value,
                "count": len(values),
                "aggregation": aggregation
            })
        
        # Sort by timestamp
        aggregated.sort(key=lambda x: x["timestamp"])
        
        return aggregated
    
    async def get_system_health(self) -> Dict[str, Any]:
        """
        Get overall system health metrics.
        
        Returns:
            Dictionary with system health metrics
        """
        # Update health metrics
        self._update_system_health()
        
        return self.health_metrics
    
    async def export_metrics(self, format: str = "json", 
                            path: Optional[str] = None) -> str:
        """
        Export metrics in the specified format.
        
        Args:
            format: Export format (json, csv)
            path: Path to write the export file
            
        Returns:
            Path to the export file
        """
        # Determine export path
        if not path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(self.storage_path, f"metrics_export_{timestamp}.{format}")
        
        # Load all metrics
        all_metrics = {}
        
        for metric_dir in os.listdir(self.metrics_path):
            metric_path = os.path.join(self.metrics_path, metric_dir)
            if os.path.isdir(metric_path):
                self._load_metrics(metric_dir)
                all_metrics[metric_dir] = self.metrics_cache.get(metric_dir, [])
        
        # Export in the specified format
        if format == "json":
            with open(path, "w") as f:
                json.dump(all_metrics, f, indent=2)
        elif format == "csv":
            import csv
            
            with open(path, "w", newline="") as f:
                writer = csv.writer(f)
                
                # Write header
                writer.writerow(["metric_name", "timestamp", "value", "tags"])
                
                # Write data
                for metric_name, metrics in all_metrics.items():
                    for metric in metrics:
                        writer.writerow([
                            metric_name,
                            metric["timestamp"],
                            metric["value"],
                            json.dumps(metric.get("tags", {}))
                        ])
        else:
            return f"Unsupported export format: {format}"
        
        return path
    
    async def _collection_loop(self) -> None:
        """Background task for continuous metrics collection."""
        try:
            while self.collection_running:
                # Collect system metrics
                await self._collect_system_metrics()
                
                # Update system health
                self._update_system_health()
                
                # Wait for next collection interval
                await asyncio.sleep(self.collection_interval)
        except asyncio.CancelledError:
            logger.info("Metrics collection loop cancelled")
        except Exception as e:
            logger.exception(f"Error in metrics collection loop: {e}")
            self.collection_running = False
    
    async def _collect_system_metrics(self) -> None:
        """Collect system metrics."""
        try:
            # CPU usage
            import psutil
            cpu_percent = psutil.cpu_percent(interval=1)
            await self.record_metric("system_cpu_percent", cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = memory.used / (1024 * 1024)
            await self.record_metric("system_memory_percent", memory_percent)
            await self.record_metric("system_memory_used_mb", memory_used_mb)
            
            # Disk usage
            disk = psutil.disk_usage(os.path.expanduser("~"))
            disk_percent = disk.percent
            disk_used_gb = disk.used / (1024 * 1024 * 1024)
            await self.record_metric("system_disk_percent", disk_percent)
            await self.record_metric("system_disk_used_gb", disk_used_gb)
            
            # Network usage
            net_io = psutil.net_io_counters()
            net_sent_mb = net_io.bytes_sent / (1024 * 1024)
            net_recv_mb = net_io.bytes_recv / (1024 * 1024)
            await self.record_metric("system_net_sent_mb", net_sent_mb)
            await self.record_metric("system_net_recv_mb", net_recv_mb)
            
            # Process metrics
            process = psutil.Process()
            process_cpu_percent = process.cpu_percent(interval=1)
            process_memory_mb = process.memory_info().rss / (1024 * 1024)
            await self.record_metric("process_cpu_percent", process_cpu_percent)
            await self.record_metric("process_memory_mb", process_memory_mb)
        except Exception as e:
            logger.exception(f"Error collecting system metrics: {e}")
    
    def _load_metrics(self, metric_name: str) -> None:
        """Load metrics for a specific metric name."""
        try:
            metric_path = os.path.join(self.metrics_path, metric_name)
            if not os.path.exists(metric_path):
                os.makedirs(metric_path, exist_ok=True)
                self.metrics_cache[metric_name] = []
                return
            
            metrics = []
            
            # Load metrics from the last 7 days
            now = datetime.now()
            for i in range(7):
                date = now - timedelta(days=i)
                date_str = date.strftime("%Y-%m-%d")
                file_path = os.path.join(metric_path, f"{date_str}.jsonl")
                
                if os.path.exists(file_path):
                    with open(file_path, "r") as f:
                        for line in f:
                            metric = json.loads(line.strip())
                            metrics.append(metric)
            
            self.metrics_cache[metric_name] = metrics
        except Exception as e:
            logger.exception(f"Error loading metrics for {metric_name}: {e}")
            self.metrics_cache[metric_name] = []
    
    def _save_metric_record(self, metric: Dict[str, Any]) -> None:
        """Save metric record to storage."""
        try:
            metric_name = metric["name"]
            timestamp = datetime.fromisoformat(metric["timestamp"])
            date_str = timestamp.strftime("%Y-%m-%d")
            
            metric_path = os.path.join(self.metrics_path, metric_name)
            os.makedirs(metric_path, exist_ok=True)
            
            file_path = os.path.join(metric_path, f"{date_str}.jsonl")
            
            with open(file_path, "a") as f:
                f.write(json.dumps(metric) + "\n")
        except Exception as e:
            logger.exception(f"Error saving metric record: {e}")
    
    def _save_task_record(self, task: Dict[str, Any]) -> None:
        """Save task metrics record to storage."""
        try:
            task_id = task["task_id"]
            timestamp = datetime.fromisoformat(task["timestamp"])
            date_str = timestamp.strftime("%Y-%m-%d")
            
            date_path = os.path.join(self.tasks_path, date_str)
            os.makedirs(date_path, exist_ok=True)
            
            file_path = os.path.join(date_path, f"{task_id}.json")
            
            with open(file_path, "w") as f:
                json.dump(task, f, indent=2)
        except Exception as e:
            logger.exception(f"Error saving task record: {e}")
    
    def _update_health_metrics(self, metric_name: str, value: float) -> None:
        """Update health metrics with a new metric value."""
        try:
            # Initialize health metrics for this metric if not exists
            if metric_name not in self.health_metrics:
                self.health_metrics[metric_name] = {
                    "current": value,
                    "min": value,
                    "max": value,
                    "avg": value,
                    "count": 1,
                    "sum": value,
                    "last_updated": datetime.now().isoformat()
                }
                return
            
            # Update health metrics
            health = self.health_metrics[metric_name]
            health["current"] = value
            health["min"] = min(health["min"], value)
            health["max"] = max(health["max"], value)
            health["count"] += 1
            health["sum"] += value
            health["avg"] = health["sum"] / health["count"]
            health["last_updated"] = datetime.now().isoformat()
        except Exception as e:
            logger.exception(f"Error updating health metrics for {metric_name}: {e}")
    
    def _update_system_health(self) -> None:
        """Update overall system health metrics."""
        try:
            # Calculate system health score
            system_health_score = 100.0
            
            # Check CPU usage
            if "system_cpu_percent" in self.health_metrics:
                cpu_percent = self.health_metrics["system_cpu_percent"]["current"]
                if cpu_percent > 90:
                    system_health_score -= 30
                elif cpu_percent > 70:
                    system_health_score -= 15
                elif cpu_percent > 50:
                    system_health_score -= 5
            
            # Check memory usage
            if "system_memory_percent" in self.health_metrics:
                memory_percent = self.health_metrics["system_memory_percent"]["current"]
                if memory_percent > 90:
                    system_health_score -= 30
                elif memory_percent > 70:
                    system_health_score -= 15
                elif memory_percent > 50:
                    system_health_score -= 5
            
            # Check disk usage
            if "system_disk_percent" in self.health_metrics:
                disk_percent = self.health_metrics["system_disk_percent"]["current"]
                if disk_percent > 90:
                    system_health_score -= 20
                elif disk_percent > 70:
                    system_health_score -= 10
                elif disk_percent > 50:
                    system_health_score -= 3
            
            # Ensure score is between 0 and 100
            system_health_score = max(0, min(100, system_health_score))
            
            # Update system health
            self.health_metrics["system_health_score"] = {
                "current": system_health_score,
                "last_updated": datetime.now().isoformat()
            }
            
            # Determine health status
            if system_health_score >= 90:
                health_status = "excellent"
            elif system_health_score >= 70:
                health_status = "good"
            elif system_health_score >= 50:
                health_status = "fair"
            elif system_health_score >= 30:
                health_status = "poor"
            else:
                health_status = "critical"
            
            self.health_metrics["system_health_status"] = {
                "current": health_status,
                "last_updated": datetime.now().isoformat()
            }
            
            # Save health metrics
            self._save_health_metrics()
        except Exception as e:
            logger.exception(f"Error updating system health: {e}")
    
    def _save_health_metrics(self) -> None:
        """Save health metrics to storage."""
        try:
            file_path = os.path.join(self.health_path, "current_health.json")
            
            with open(file_path, "w") as f:
                json.dump({
                    "metrics": self.health_metrics,
                    "timestamp": datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.exception(f"Error saving health metrics: {e}")
    
    async def get_task_metrics(self, task_id: Optional[str] = None, 
                              start_time: Optional[datetime] = None,
                              end_time: Optional[datetime] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Get metrics for a specific task or all tasks in a time range.
        
        Args:
            task_id: Optional task ID
            start_time: Optional start time
            end_time: Optional end time
            
        Returns:
            Task metrics dictionary or list of dictionaries
        """
        # If task ID is provided, return metrics for that task
        if task_id:
            if task_id in self.task_metrics_cache:
                return self.task_metrics_cache[task_id]
            
            # Try to load from storage
            try:
                # Search in all date directories
                for date_dir in os.listdir(self.tasks_path):
                    date_path = os.path.join(self.tasks_path, date_dir)
                    if os.path.isdir(date_path):
                        file_path = os.path.join(date_path, f"{task_id}.json")
                        if os.path.exists(file_path):
                            with open(file_path, "r") as f:
                                task_metrics = json.load(f)
                                self.task_metrics_cache[task_id] = task_metrics
                                return task_metrics
            except Exception as e:
                logger.exception(f"Error loading task metrics for {task_id}: {e}")
            
            return {"error": f"Task metrics not found for task ID: {task_id}"}
        
        # If no task ID, return all tasks in time range
        tasks = []
        
        try:
            # Determine date range
            if start_time:
                start_date = start_time.date()
            else:
                # Default to 7 days ago
                start_date = (datetime.now() - timedelta(days=7)).date()
            
            if end_time:
                end_date = end_time.date()
            else:
                # Default to today
                end_date = datetime.now().date()
            
            # Iterate through dates in range
            current_date = start_date
            while current_date <= end_date:
                date_str = current_date.strftime("%Y-%m-%d")
                date_path = os.path.join(self.tasks_path, date_str)
                
                if os.path.exists(date_path):
                    for file_name in os.listdir(date_path):
                        if file_name.endswith(".json"):
                            file_path = os.path.join(date_path, file_name)
                            with open(file_path, "r") as f:
                                task_metrics = json.load(f)
                                
                                # Filter by time range if provided
                                task_time = datetime.fromisoformat(task_metrics["timestamp"])
                                if start_time and task_time < start_time:
                                    continue
                                if end_time and task_time > end_time:
                                    continue
                                
                                tasks.append(task_metrics)
                
                # Move to next day
                current_date += timedelta(days=1)
            
            # Sort by timestamp (newest first)
            tasks.sort(key=lambda t: t["timestamp"], reverse=True)
        except Exception as e:
            logger.exception(f"Error getting task metrics: {e}")
        
        return tasks
    
    async def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all metrics.
        
        Returns:
            Dictionary with metrics summary
        """
        summary = {
            "metrics_count": 0,
            "metrics_by_name": {},
            "task_metrics_count": 0,
            "system_health": await self.get_system_health(),
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Count metrics by name
            for metric_dir in os.listdir(self.metrics_path):
                metric_path = os.path.join(self.metrics_path, metric_dir)
                if os.path.isdir(metric_path):
                    count = 0
                    for file_name in os.listdir(metric_path):
                        if file_name.endswith(".jsonl"):
                            file_path = os.path.join(metric_path, file_name)
                            with open(file_path, "r") as f:
                                count += sum(1 for _ in f)
                    
                    summary["metrics_by_name"][metric_dir] = count
                    summary["metrics_count"] += count
            
            # Count task metrics
            for date_dir in os.listdir(self.tasks_path):
                date_path = os.path.join(self.tasks_path, date_dir)
                if os.path.isdir(date_path):
                    summary["task_metrics_count"] += sum(1 for f in os.listdir(date_path) if f.endswith(".json"))
        except Exception as e:
            logger.exception(f"Error getting metrics summary: {e}")
        
        return summary 