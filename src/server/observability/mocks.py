from typing import Dict, List, Optional, Any, Callable
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

class MockProgressTracker:
    """Mock implementation of ProgressTracker for testing."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.callbacks = []
    
    async def get_progress_report(self, include_children=False):
        return {
            "overall_completion": 65,
            "completed_items": 27,
            "total_items": 42,
            "milestones": [
                {"name": "Phase 1", "completion": 100},
                {"name": "Phase 2", "completion": 100},
                {"name": "Phase 3", "completion": 95},
                {"name": "Phase 4", "completion": 50},
                {"name": "Phase 5", "completion": 30},
                {"name": "Phase 6", "completion": 0},
                {"name": "Phase 7", "completion": 0}
            ]
        }
    
    async def get_progress_data(self, start_time=None, end_time=None):
        return [
            {"timestamp": "2023-01-01T12:00:00", "overall_completion": 50},
            {"timestamp": "2023-01-02T12:00:00", "overall_completion": 55},
            {"timestamp": "2023-01-03T12:00:00", "overall_completion": 60},
            {"timestamp": "2023-01-04T12:00:00", "overall_completion": 65}
        ]
    
    async def create_visualization(self, visualization_type):
        return {"type": "image", "content": "base64_encoded_image_data"}
    
    def register_callback(self, callback):
        self.callbacks.append(callback)
    
    async def health_check(self):
        return {"status": "healthy", "metrics": {"tracked_items": 42}}
    
    async def shutdown(self):
        return {"status": "shutdown_completed"}


class MockInterventionInterface:
    """Mock implementation of InterventionInterface for testing."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    async def request_intervention(self, title, description, level, context, options):
        return {
            "id": f"int_{uuid.uuid4().hex[:8]}",
            "status": "pending",
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_interventions_for_period(self, start_time, end_time):
        return [
            {
                "id": "int_1234abcd",
                "title": "Resource Budget Alert",
                "level": "warning",
                "timestamp": "2023-01-02T15:30:00",
                "status": "resolved"
            },
            {
                "id": "int_5678efgh",
                "title": "Metric Anomaly",
                "level": "critical",
                "timestamp": "2023-01-03T09:15:00",
                "status": "pending"
            }
        ]
    
    async def export_interventions(self, start_time, end_time):
        return await self.get_interventions_for_period(start_time, end_time)
    
    async def cleanup_old_data(self, retention_days):
        return {"status": "completed", "removed_count": 5}
    
    async def health_check(self):
        return {"status": "healthy", "metrics": {"pending_interventions": 2}}
    
    async def shutdown(self):
        return {"status": "shutdown_completed"}


class MockSupervisionHub:
    """Mock implementation of SupervisionHub for testing."""
    
    def __init__(self, intervention_interface, config: Dict[str, Any]):
        self.intervention_interface = intervention_interface
        self.config = config
    
    async def create_approval_workflow(self, title, description, policy_name, creator_id, metadata):
        return {
            "id": f"workflow_{uuid.uuid4().hex[:8]}",
            "status": "active",
            "timestamp": datetime.now().isoformat()
        }
    
    async def health_check(self):
        return {"status": "healthy", "metrics": {"active_workflows": 3}}
    
    async def shutdown(self):
        return {"status": "shutdown_completed"}


class MockResourceMonitor:
    """Mock implementation of ResourceMonitor for testing."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.alert_callbacks = []
        self.is_monitoring = False
    
    async def start_monitoring(self):
        self.is_monitoring = True
        return {"status": "started"}
    
    async def stop_monitoring(self):
        self.is_monitoring = False
        return {"status": "stopped"}
    
    async def get_budgets(self):
        return [
            {
                "id": "budget_cpu",
                "name": "CPU Budget",
                "resource_type": "cpu",
                "limit": 100,
                "unit": "cpu_hours",
                "usage": 45,
                "priority": "high"
            },
            {
                "id": "budget_memory",
                "name": "Memory Budget",
                "resource_type": "memory",
                "limit": 32,
                "unit": "GB",
                "usage": 18,
                "priority": "normal"
            },
            {
                "id": "budget_api",
                "name": "API Budget",
                "resource_type": "api_calls",
                "limit": 10000,
                "unit": "calls",
                "usage": 4350,
                "priority": "critical"
            }
        ]
    
    async def create_usage_report(self, start_time, end_time):
        return {
            "budgets": await self.get_budgets(),
            "history": [
                {"timestamp": "2023-01-01T12:00:00", "cpu": 40, "memory": 15, "api_calls": 3500},
                {"timestamp": "2023-01-02T12:00:00", "cpu": 42, "memory": 16, "api_calls": 3900},
                {"timestamp": "2023-01-03T12:00:00", "cpu": 44, "memory": 17, "api_calls": 4100},
                {"timestamp": "2023-01-04T12:00:00", "cpu": 45, "memory": 18, "api_calls": 4350}
            ],
            "visualization": {"type": "image", "content": "base64_encoded_resource_chart"}
        }
    
    async def export_usage_data(self, start_time, end_time):
        report = await self.create_usage_report(start_time, end_time)
        return report["history"]
    
    def register_alert_callback(self, callback):
        self.alert_callbacks.append(callback)
    
    async def cleanup_old_data(self, retention_days):
        return {"status": "completed", "removed_records": 120}
    
    async def health_check(self):
        return {
            "status": "healthy", 
            "monitoring_active": self.is_monitoring,
            "metrics": {"tracked_budgets": 3}
        }


class MockMetricsCollector:
    """Mock implementation of MetricsCollector for testing."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.is_collecting = False
        self.registered_metrics = {}
        self.registered_anomalies = {}
    
    async def start_collection(self):
        self.is_collecting = True
        return {"status": "started"}
    
    async def stop_collection(self):
        self.is_collecting = False
        return {"status": "stopped"}
    
    async def register_metric(self, name, description, type, category, unit, components):
        metric_id = f"{category}.{name.lower().replace(' ', '_')}"
        self.registered_metrics[metric_id] = {
            "id": metric_id,
            "name": name,
            "description": description,
            "type": type,
            "category": category,
            "unit": unit,
            "components": components
        }
        return {"status": "registered", "metric_id": metric_id}
    
    async def record_metric(self, metric_id, value, component, context=None):
        return {
            "status": "recorded",
            "metric_id": metric_id,
            "timestamp": datetime.now().isoformat()
        }
    
    async def register_anomaly_definition(self, name, description, metric_id, detection_method, parameters, severity):
        anomaly_id = f"anomaly_{uuid.uuid4().hex[:8]}"
        self.registered_anomalies[anomaly_id] = {
            "id": anomaly_id,
            "name": name,
            "description": description,
            "metric_id": metric_id,
            "detection_method": detection_method,
            "parameters": parameters,
            "severity": severity
        }
        return {"status": "registered", "anomaly_id": anomaly_id}
    
    async def record_event(self, event_type, data):
        return {
            "status": "recorded",
            "event_type": event_type,
            "timestamp": datetime.now().isoformat()
        }
    
    async def create_metrics_report(self, start_time, end_time):
        return {
            "summary": {
                "total_metrics": len(self.registered_metrics),
                "total_anomalies": 3,
                "time_period": f"{start_time} to {end_time}"
            },
            "metrics": list(self.registered_metrics.values()),
            "anomalies": await self.get_anomalies(start_time, end_time),
            "visualizations": {
                "performance_metrics": {"type": "image", "content": "base64_encoded_performance_chart"},
                "reliability_metrics": {"type": "image", "content": "base64_encoded_reliability_chart"},
                "cognitive_metrics": {"type": "image", "content": "base64_encoded_cognitive_chart"}
            }
        }
    
    async def export_metrics_data(self, start_time, end_time):
        return [
            {"timestamp": "2023-01-01T12:00:00", "metric_id": "performance.task_execution_time", "value": 1.2},
            {"timestamp": "2023-01-02T12:00:00", "metric_id": "performance.task_execution_time", "value": 1.3},
            {"timestamp": "2023-01-03T12:00:00", "metric_id": "performance.task_execution_time", "value": 1.1},
            {"timestamp": "2023-01-04T12:00:00", "metric_id": "performance.task_execution_time", "value": 1.4},
            {"timestamp": "2023-01-01T12:00:00", "metric_id": "reliability.task_success_rate", "value": 92},
            {"timestamp": "2023-01-02T12:00:00", "metric_id": "reliability.task_success_rate", "value": 94},
            {"timestamp": "2023-01-03T12:00:00", "metric_id": "reliability.task_success_rate", "value": 91},
            {"timestamp": "2023-01-04T12:00:00", "metric_id": "reliability.task_success_rate", "value": 95}
        ]
    
    async def get_anomalies(self, start_time, end_time, include_acknowledged=False):
        return [
            {
                "id": "anomaly_event_1",
                "anomaly_definition_id": "anomaly_def_1",
                "metric_id": "performance.task_execution_time",
                "timestamp": "2023-01-02T14:30:00",
                "value": 3.5,
                "expected_range": [0.8, 1.6],
                "deviation_percentage": 118.75,
                "severity": "warning",
                "status": "acknowledged"
            },
            {
                "id": "anomaly_event_2",
                "anomaly_definition_id": "anomaly_def_2",
                "metric_id": "reliability.task_success_rate",
                "timestamp": "2023-01-03T09:15:00",
                "value": 65,
                "expected_range": [85, 100],
                "deviation_percentage": 23.53,
                "severity": "critical",
                "status": "active"
            }
        ]
    
    async def cleanup_old_data(self, retention_days):
        return {"status": "completed", "removed_metrics": 250, "removed_anomalies": 12}
    
    async def health_check(self):
        return {
            "status": "healthy",
            "collection_active": self.is_collecting,
            "metrics": {
                "registered_metrics": len(self.registered_metrics),
                "registered_anomalies": len(self.registered_anomalies)
            }
        } 