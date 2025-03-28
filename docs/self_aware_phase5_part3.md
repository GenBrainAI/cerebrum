# Implementation Guide for Phase 5 Work Unit 5.6: Observability Integration

I'll provide a comprehensive implementation for Work Unit 5.6 (Observability Integration), including code, unit tests, and explanations of how it connects to the rest of the system.

## Work Unit 5.6: Observability Integration

The Observability Integration component is the final piece of Phase 5, unifying all observability components into a cohesive layer that provides a unified interface for monitoring and understanding the system's behavior.

```python
from typing import Dict, List, Optional, Any, Union, Callable, Set, Tuple, Type
import logging
from enum import Enum
from dataclasses import dataclass, field
import asyncio
import json
from datetime import datetime, timedelta
import os
from pathlib import Path
import uuid
import time
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from io import BytesIO
import base64
import re
import threading
import traceback
import inspect
import importlib
import socket
import platform
import atexit
import signal
import weakref

# Import observability components (assumed to be available in the system)
# In a real implementation, these would be proper imports from the system modules
# from progress_tracker import ProgressTracker
# from intervention_interface import InterventionInterface
# from supervision_hub import SupervisionHub
# from resource_monitor import ResourceMonitor
# from metrics_collector import MetricsCollector

logger = logging.getLogger(__name__)

class ObservabilityLayer:
    """
    Integrates all observability components into a unified layer.
    
    This class serves as the central integration point for all observability
    components, providing a unified interface for monitoring and understanding
    the system's behavior. It coordinates data flow between components,
    ensures consistent configuration, and provides common visualization
    and reporting capabilities.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize with optional configuration."""
        self.config = config or {
            "storage_path": "data/observability",
            "enable_components": {
                "progress_tracker": True,
                "intervention_interface": True,
                "supervision_hub": True,
                "resource_monitor": True,
                "metrics_collector": True,
                "dashboard": True
            },
            "component_config": {},
            "integration_mode": "full",  # "full", "minimal", "custom"
            "dashboard_port": 8080,
            "log_level": "INFO",
            "data_retention_days": 30,
            "alert_notification_handlers": []
        }
        
        # Component instances
        self.progress_tracker = None
        self.intervention_interface = None
        self.supervision_hub = None
        self.resource_monitor = None
        self.metrics_collector = None
        
        # Integration state
        self.is_initialized = False
        self.is_dashboard_running = False
        self.dashboard_server = None
        self.component_status = {}
        self.event_handlers = {}
        self.cross_component_mappings = {}
        
        # System info
        self.system_info = self._collect_system_info()
        
        # Initialize storage
        self._initialize_storage()
        
        # Register signal handlers for graceful shutdown
        self._register_signal_handlers()
    
    def _collect_system_info(self) -> Dict[str, Any]:
        """Collect system information."""
        try:
            return {
                "hostname": socket.gethostname(),
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "start_time": datetime.now().isoformat(),
                "pid": os.getpid()
            }
        except Exception as e:
            logger.error(f"Error collecting system info: {str(e)}")
            return {"error": str(e)}
    
    def _initialize_storage(self) -> None:
        """Initialize storage directories."""
        storage_path = self.config.get("storage_path", "data/observability")
        os.makedirs(storage_path, exist_ok=True)
        
        # Create subdirectories
        os.makedirs(os.path.join(storage_path, "dashboards"), exist_ok=True)
        os.makedirs(os.path.join(storage_path, "reports"), exist_ok=True)
        os.makedirs(os.path.join(storage_path, "logs"), exist_ok=True)
        os.makedirs(os.path.join(storage_path, "exports"), exist_ok=True)
    
    def _register_signal_handlers(self) -> None:
        """Register signal handlers for graceful shutdown."""
        try:
            # Register SIGINT and SIGTERM handlers
            for sig in [signal.SIGINT, signal.SIGTERM]:
                signal.signal(sig, self._signal_handler)
            
            # Register cleanup on exit
            atexit.register(self._cleanup)
        except Exception as e:
            logger.error(f"Error registering signal handlers: {str(e)}")
    
    def _signal_handler(self, sig, frame) -> None:
        """Handle process signals."""
        logger.info(f"Received signal {sig}, shutting down gracefully...")
        self._cleanup()
    
    def _cleanup(self) -> None:
        """Clean up resources on shutdown."""
        logger.info("Cleaning up observability layer resources...")
        asyncio.run(self.shutdown())
    
    async def initialize(self) -> Dict[str, Any]:
        """Initialize the observability layer and its components."""
        if self.is_initialized:
            return {"status": "already_initialized", "components": self.component_status}
        
        logger.info("Initializing observability layer...")
        
        try:
            # Initialize components based on configuration
            component_results = {}
            enable_components = self.config.get("enable_components", {})
            
            # Initialize Progress Tracker
            if enable_components.get("progress_tracker", True):
                result = await self._initialize_progress_tracker()
                component_results["progress_tracker"] = result
            
            # Initialize Intervention Interface
            if enable_components.get("intervention_interface", True):
                result = await self._initialize_intervention_interface()
                component_results["intervention_interface"] = result
            
            # Initialize Supervision Hub
            if enable_components.get("supervision_hub", True):
                result = await self._initialize_supervision_hub()
                component_results["supervision_hub"] = result
            
            # Initialize Resource Monitor
            if enable_components.get("resource_monitor", True):
                result = await self._initialize_resource_monitor()
                component_results["resource_monitor"] = result
            
            # Initialize Metrics Collector
            if enable_components.get("metrics_collector", True):
                result = await self._initialize_metrics_collector()
                component_results["metrics_collector"] = result
            
            # Initialize cross-component integrations
            await self._initialize_integrations()
            
            # Start dashboard if enabled
            if enable_components.get("dashboard", True):
                result = await self._start_dashboard()
                component_results["dashboard"] = result
            
            self.is_initialized = True
            self.component_status = component_results
            
            # Log successful initialization
            logger.info("Observability layer initialized successfully")
            
            return {
                "status": "initialized",
                "components": component_results,
                "system_info": self.system_info
            }
            
        except Exception as e:
            logger.error(f"Error initializing observability layer: {str(e)}")
            logger.error(traceback.format_exc())
            
            return {
                "status": "initialization_failed",
                "error": str(e),
                "components": self.component_status,
                "system_info": self.system_info
            }
    
    async def _initialize_progress_tracker(self) -> Dict[str, Any]:
        """Initialize the Progress Tracker component."""
        try:
            # In a real implementation, this would be:
            # self.progress_tracker = ProgressTracker(self.config.get("component_config", {}).get("progress_tracker", {}))
            
            # For this example, we'll mock the component
            self.progress_tracker = MockProgressTracker(
                self.config.get("component_config", {}).get("progress_tracker", {})
            )
            
            logger.info("Progress Tracker initialized")
            
            return {"status": "initialized"}
            
        except Exception as e:
            logger.error(f"Error initializing Progress Tracker: {str(e)}")
            return {"status": "failed", "error": str(e)}
    
    async def _initialize_intervention_interface(self) -> Dict[str, Any]:
        """Initialize the Intervention Interface component."""
        try:
            # In a real implementation, this would be:
            # self.intervention_interface = InterventionInterface(self.config.get("component_config", {}).get("intervention_interface", {}))
            
            # For this example, we'll mock the component
            self.intervention_interface = MockInterventionInterface(
                self.config.get("component_config", {}).get("intervention_interface", {})
            )
            
            logger.info("Intervention Interface initialized")
            
            return {"status": "initialized"}
            
        except Exception as e:
            logger.error(f"Error initializing Intervention Interface: {str(e)}")
            return {"status": "failed", "error": str(e)}
    
    async def _initialize_supervision_hub(self) -> Dict[str, Any]:
        """Initialize the Supervision Hub component."""
        try:
            # In a real implementation, this would be:
            # self.supervision_hub = SupervisionHub(
            #     intervention_interface=self.intervention_interface,
            #     config=self.config.get("component_config", {}).get("supervision_hub", {})
            # )
            
            # For this example, we'll mock the component
            self.supervision_hub = MockSupervisionHub(
                self.intervention_interface,
                self.config.get("component_config", {}).get("supervision_hub", {})
            )
            
            logger.info("Supervision Hub initialized")
            
            return {"status": "initialized"}
            
        except Exception as e:
            logger.error(f"Error initializing Supervision Hub: {str(e)}")
            return {"status": "failed", "error": str(e)}
    
    async def _initialize_resource_monitor(self) -> Dict[str, Any]:
        """Initialize the Resource Monitor component."""
        try:
            # In a real implementation, this would be:
            # self.resource_monitor = ResourceMonitor(self.config.get("component_config", {}).get("resource_monitor", {}))
            
            # For this example, we'll mock the component
            self.resource_monitor = MockResourceMonitor(
                self.config.get("component_config", {}).get("resource_monitor", {})
            )
            
            # Start monitoring
            await self.resource_monitor.start_monitoring()
            
            logger.info("Resource Monitor initialized and started")
            
            return {"status": "initialized"}
            
        except Exception as e:
            logger.error(f"Error initializing Resource Monitor: {str(e)}")
            return {"status": "failed", "error": str(e)}
    
    async def _initialize_metrics_collector(self) -> Dict[str, Any]:
        """Initialize the Metrics Collector component."""
        try:
            # In a real implementation, this would be:
            # self.metrics_collector = MetricsCollector(self.config.get("component_config", {}).get("metrics_collector", {}))
            
            # For this example, we'll mock the component
            self.metrics_collector = MockMetricsCollector(
                self.config.get("component_config", {}).get("metrics_collector", {})
            )
            
            # Start collection
            await self.metrics_collector.start_collection()
            
            logger.info("Metrics Collector initialized and started")
            
            return {"status": "initialized"}
            
        except Exception as e:
            logger.error(f"Error initializing Metrics Collector: {str(e)}")
            return {"status": "failed", "error": str(e)}
    
    async def _initialize_integrations(self) -> None:
        """Initialize cross-component integrations."""
        # Only proceed if the necessary components are initialized
        if not all([
            self.progress_tracker, 
            self.intervention_interface, 
            self.resource_monitor, 
            self.metrics_collector
        ]):
            logger.warning("Some components are not initialized, skipping integrations")
            return
        
        try:
            # 1. Connect Progress Tracker to Metrics Collector
            await self._integrate_progress_metrics()
            
            # 2. Connect Resource Monitor alerts to Intervention Interface
            await self._integrate_resource_alerts()
            
            # 3. Register metric collectors for tracking progress
            await self._integrate_tracking_metrics()
            
            # 4. Connect anomaly detection to interventions
            await self._integrate_anomaly_interventions()
            
            # 5. Establish supervision workflows for critical resources
            if self.supervision_hub:
                await self._integrate_resource_supervision()
            
            logger.info("Cross-component integrations established")
            
        except Exception as e:
            logger.error(f"Error initializing integrations: {str(e)}")
    
    async def _integrate_progress_metrics(self) -> None:
        """Integrate Progress Tracker with Metrics Collector."""
        try:
            # Register progress metrics
            await self.metrics_collector.register_metric(
                name="Task Completion Rate",
                description="Rate of task completion over time",
                type="rate",  # Using string since we're mocking
                category="cognitive",
                unit="tasks/hour",
                components=["execution_engine"]
            )
            
            await self.metrics_collector.register_metric(
                name="Progress Percentage",
                description="Overall system progress percentage",
                type="gauge",
                category="cognitive",
                unit="percent",
                components=["system"]
            )
            
            # Register callback to update metrics when progress changes
            self.progress_tracker.register_callback(
                self._on_progress_update
            )
            
            logger.info("Progress metrics integration established")
            
        except Exception as e:
            logger.error(f"Error integrating progress metrics: {str(e)}")
    
    async def _on_progress_update(self, progress_data: Dict[str, Any]) -> None:
        """Handle progress updates and record metrics."""
        try:
            # Extract relevant data
            completion_percentage = progress_data.get("overall_completion", 0)
            completed_items = progress_data.get("completed_items", 0)
            
            # Record metrics
            await self.metrics_collector.record_metric(
                metric_id="cognitive.progress_percentage",
                value=completion_percentage,
                component="system",
                context={"update_time": datetime.now().isoformat()}
            )
            
            await self.metrics_collector.record_metric(
                metric_id="cognitive.task_completion_rate",
                value=completed_items,
                component="execution_engine",
                context={"update_time": datetime.now().isoformat()}
            )
            
        except Exception as e:
            logger.error(f"Error processing progress update: {str(e)}")
    
    async def _integrate_resource_alerts(self) -> None:
        """Connect Resource Monitor alerts to Intervention Interface."""
        try:
            # Register callback for budget alerts
            self.resource_monitor.register_alert_callback(
                self._on_resource_alert
            )
            
            logger.info("Resource alerts integration established")
            
        except Exception as e:
            logger.error(f"Error integrating resource alerts: {str(e)}")
    
    async def _on_resource_alert(self, alert_data: Dict[str, Any]) -> None:
        """Handle resource alerts and create interventions when needed."""
        try:
            # Determine intervention level based on alert
            percentage = alert_data.get("percentage", 0)
            resource_type = alert_data.get("resource_type", "unknown")
            budget_name = alert_data.get("budget_name", "unknown")
            
            if percentage >= 95:
                level = "critical"
            elif percentage >= 80:
                level = "warning"
            else:
                level = "information"
            
            # Create intervention request
            await self.intervention_interface.request_intervention(
                title=f"Resource Budget Alert: {budget_name}",
                description=f"{resource_type} usage at {percentage:.1f}% of budget",
                level=level,
                context={
                    "component": "resource_monitor",
                    "operation": "budget_tracking",
                    "related_items": [alert_data.get("budget_id", "")],
                    "metrics": {
                        "percentage": percentage,
                        "current_usage": alert_data.get("current_usage", 0),
                        "budget_limit": alert_data.get("budget_limit", 0)
                    }
                },
                options=["continue", "modify", "pause"]
            )
            
        except Exception as e:
            logger.error(f"Error creating intervention for resource alert: {str(e)}")
    
    async def _integrate_tracking_metrics(self) -> None:
        """Register metric collectors for tracking progress."""
        try:
            # Register execution engine metrics
            await self.metrics_collector.register_metric(
                name="Task Success Rate",
                description="Percentage of tasks completed successfully",
                type="gauge",
                category="reliability",
                unit="percent",
                components=["execution_engine"]
            )
            
            await self.metrics_collector.register_metric(
                name="Task Execution Time",
                description="Time taken to execute tasks",
                type="histogram",
                category="performance",
                unit="seconds",
                components=["execution_engine"]
            )
            
            # Register planning metrics
            await self.metrics_collector.register_metric(
                name="Planning Time",
                description="Time spent in planning phase",
                type="histogram",
                category="cognitive",
                unit="seconds",
                components=["planning_engine"]
            )
            
            await self.metrics_collector.register_metric(
                name="Plan Complexity",
                description="Complexity of generated plans",
                type="gauge",
                category="cognitive",
                unit="score",
                components=["planning_engine"]
            )
            
            # Register self-modification metrics
            await self.metrics_collector.register_metric(
                name="Code Generation Quality",
                description="Quality score of generated code",
                type="gauge",
                category="cognitive",
                unit="score",
                components=["self_modification_engine"]
            )
            
            await self.metrics_collector.register_metric(
                name="Safety Validation Rate",
                description="Safety validation success rate",
                type="gauge",
                category="reliability",
                unit="percent",
                components=["self_modification_engine"]
            )
            
            logger.info("Tracking metrics integration established")
            
        except Exception as e:
            logger.error(f"Error integrating tracking metrics: {str(e)}")
    
    async def _integrate_anomaly_interventions(self) -> None:
        """Connect anomaly detection to interventions."""
        try:
            # Register anomaly notification handler
            self.metrics_collector.config["anomaly_notification_handler"] = self._on_anomaly_detected
            
            # Register anomaly definitions for critical metrics
            await self.metrics_collector.register_anomaly_definition(
                name="High Task Failure Rate",
                description="Unusually high task failure rate",
                metric_id="reliability.task_success_rate",
                detection_method="threshold",
                parameters={"min": 70.0},  # Alert if success rate falls below 70%
                severity="warning"
            )
            
            await self.metrics_collector.register_anomaly_definition(
                name="Slow Task Execution",
                description="Unusually slow task execution",
                metric_id="performance.task_execution_time",
                detection_method="zscore",
                parameters={"threshold": 2.5},  # Alert if z-score > 2.5
                severity="warning"
            )
            
            await self.metrics_collector.register_anomaly_definition(
                name="Low Code Quality",
                description="Unusually low code quality score",
                metric_id="cognitive.code_generation_quality",
                detection_method="threshold",
                parameters={"min": 0.7},  # Alert if quality below 0.7
                severity="warning"
            )
            
            logger.info("Anomaly interventions integration established")
            
        except Exception as e:
            logger.error(f"Error integrating anomaly interventions: {str(e)}")
    
    async def _on_anomaly_detected(self, event: Dict[str, Any], definition: Dict[str, Any]) -> None:
        """Handle anomaly detection events and create interventions."""
        try:
            # Map severity to intervention level
            severity_map = {
                "info": "information",
                "warning": "warning",
                "critical": "critical"
            }
            
            severity = event.get("severity", "warning")
            level = severity_map.get(severity, "warning")
            
            metric_id = event.get("metric_id", "unknown")
            metric_name = event.get("metric_name", metric_id)
            
            # Create intervention request
            await self.intervention_interface.request_intervention(
                title=f"Metric Anomaly: {definition.get('name', 'Unknown Anomaly')}",
                description=(
                    f"Anomaly detected in {metric_name}: "
                    f"value {event.get('value')} outside expected range "
                    f"{event.get('expected_range')}"
                ),
                level=level,
                context={
                    "component": "metrics_collector",
                    "operation": "anomaly_detection",
                    "related_items": [event.get("id", ""), metric_id],
                    "metrics": {
                        "value": event.get("value"),
                        "expected_range": event.get("expected_range"),
                        "deviation_percentage": event.get("deviation_percentage")
                    }
                },
                options=["continue", "investigate", "mitigate"]
            )
            
        except Exception as e:
            logger.error(f"Error creating intervention for anomaly: {str(e)}")
    
    async def _integrate_resource_supervision(self) -> None:
        """Establish supervision workflows for critical resources."""
        try:
            # Get all active budgets
            budgets = await self.resource_monitor.get_budgets()
            
            # Create approval workflows for critical budgets
            for budget in budgets:
                if budget.get("priority", "normal") in ["high", "critical"]:
                    await self.supervision_hub.create_approval_workflow(
                        title=f"Budget Modification: {budget.get('name', 'Unknown Budget')}",
                        description=f"Approval required for modifying {budget.get('resource_type')} budget",
                        policy_name="standard",
                        creator_id="system",
                        metadata={
                            "budget_id": budget.get("id"),
                            "resource_type": budget.get("resource_type"),
                            "current_limit": budget.get("limit"),
                            "unit": budget.get("unit")
                        }
                    )
            
            logger.info("Resource supervision integration established")
            
        except Exception as e:
            logger.error(f"Error integrating resource supervision: {str(e)}")
    
    async def _start_dashboard(self) -> Dict[str, Any]:
        """Start the observability dashboard."""
        try:
            # In a real implementation, this would start a web server
            # for the dashboard. For this example, we'll just simulate it.
            port = self.config.get("dashboard_port", 8080)
            
            # Simulate dashboard initialization
            self.is_dashboard_running = True
            
            logger.info(f"Observability dashboard started on port {port}")
            
            return {
                "status": "started",
                "port": port,
                "url": f"http://localhost:{port}"
            }
            
        except Exception as e:
            logger.error(f"Error starting dashboard: {str(e)}")
            return {"status": "failed", "error": str(e)}
    
    async def create_observability_dashboard(self, 
                                           name: str,
                                           panels: List[Dict[str, Any]],
                                           refresh_interval: int = 60) -> Dict[str, Any]:
        """Create a custom observability dashboard."""
        try:
            # Generate dashboard ID
            dashboard_id = f"dashboard_{uuid.uuid4().hex[:8]}"
            
            # Create dashboard configuration
            dashboard = {
                "id": dashboard_id,
                "name": name,
                "panels": panels,
                "refresh_interval": refresh_interval,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # Save dashboard configuration
            storage_path = self.config.get("storage_path", "data/observability")
            dashboard_path = os.path.join(storage_path, "dashboards", f"{dashboard_id}.json")
            
            os.makedirs(os.path.dirname(dashboard_path), exist_ok=True)
            with open(dashboard_path, 'w') as f:
                json.dump(dashboard, f, indent=2)
            
            logger.info(f"Created observability dashboard: {name} ({dashboard_id})")
            
            return {
                "status": "created",
                "dashboard_id": dashboard_id,
                "name": name,
                "panel_count": len(panels)
            }
            
        except Exception as e:
            logger.error(f"Error creating dashboard: {str(e)}")
            return {"status": "failed", "error": str(e)}
    
    async def create_system_report(self, 
                                 sections: Optional[List[str]] = None,
                                 start_time: Optional[str] = None,
                                 end_time: Optional[str] = None) -> Dict[str, Any]:
        """Create a comprehensive system report."""
        try:
            # Default to all sections if not specified
            sections = sections or [
                "progress", "resources", "metrics", "interventions", 
                "anomalies", "system_info"
            ]
            
            # Set default time range if not specified
            if not end_time:
                end_time = datetime.now().isoformat()
                
            if not start_time:
                # Default to 24 hours ago
                start_time = (datetime.now() - timedelta(hours=24)).isoformat()
            
            # Collect data for each section
            report_data = {
                "timestamp": datetime.now().isoformat(),
                "time_range": {
                    "start": start_time,
                    "end": end_time
                },
                "system_info": self.system_info,
                "sections": {}
            }
            
            # Collect progress data
            if "progress" in sections and self.progress_tracker:
                progress_report = await self.progress_tracker.get_progress_report(
                    include_children=True
                )
                report_data["sections"]["progress"] = progress_report
            
            # Collect resource data
            if "resources" in sections and self.resource_monitor:
                budgets = await self.resource_monitor.get_budgets()
                usage_report = await self.resource_monitor.create_usage_report(
                    start_time=start_time,
                    end_time=end_time
                )
                
                report_data["sections"]["resources"] = {
                    "budgets": budgets,
                    "usage": usage_report
                }
            
            # Collect metrics data
            if "metrics" in sections and self.metrics_collector:
                metrics_report = await self.metrics_collector.create_metrics_report(
                    start_time=start_time,
                    end_time=end_time
                )
                report_data["sections"]["metrics"] = metrics_report
            
            # Collect interventions data
            if "interventions" in sections and self.intervention_interface:
                interventions = await self.intervention_interface.get_interventions_for_period(
                    start_time=start_time,
                    end_time=end_time
                )
                report_data["sections"]["interventions"] = interventions
            
            # Collect anomalies data
            if "anomalies" in sections and self.metrics_collector:
                anomalies = await self.metrics_collector.get_anomalies(
                    start_time=start_time,
                    end_time=end_time,
                    include_acknowledged=True
                )
                report_data["sections"]["anomalies"] = anomalies
            
            # Create visualizations for the report
            visualizations = {}
            
            # Progress visualization
            if "progress" in sections and self.progress_tracker:
                try:
                    progress_vis = await self.progress_tracker.create_visualization(
                        visualization_type="milestone_status"
                    )
                    visualizations["progress_milestones"] = progress_vis
                except Exception as e:
                    logger.error(f"Error creating progress visualization: {str(e)}")
            
            # Resource usage visualization
            if "resources" in sections and self.resource_monitor:
                try:
                    resource_vis = report_data["sections"]["resources"]["usage"]["visualization"]
                    visualizations["resource_usage"] = resource_vis
                except Exception as e:
                    logger.error(f"Error extracting resource visualization: {str(e)}")
            
            # Metrics visualization
            if "metrics" in sections and self.metrics_collector:
                try:
                    metrics_vis = report_data["sections"]["metrics"]["visualizations"]
                    visualizations.update(metrics_vis)
                except Exception as e:
                    logger.error(f"Error extracting metrics visualizations: {str(e)}")
            
            report_data["visualizations"] = visualizations
            
            # Save report to file
            report_id = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            report_path = os.path.join(
                self.config.get("storage_path", "data/observability"),
                "reports",
                f"{report_id}.json"
            )
            
            os.makedirs(os.path.dirname(report_path), exist_ok=True)
            with open(report_path, 'w') as f:
                json.dump(report_data, f, indent=2)
            
            logger.info(f"Created system report: {report_id}")
            
            return {
                "status": "created",
                "report_id": report_id,
                "sections": sections,
                "time_range": report_data["time_range"],
                "report_path": report_path
            }
            
        except Exception as e:
            logger.error(f"Error creating system report: {str(e)}")
            return {"status": "failed", "error": str(e)}
    
    async def register_event_handler(self, 
                                   event_type: str, 
                                   handler: Callable) -> Dict[str, Any]:
        """Register a handler for observability events."""
        try:
            if event_type not in self.event_handlers:
                self.event_handlers[event_type] = []
                
            self.event_handlers[event_type].append(handler)
            
            logger.info(f"Registered event handler for {event_type}")
            
            return {
                "status": "registered",
                "event_type": event_type,
                "handler_count": len(self.event_handlers[event_type])
            }
        except Exception as e:
            logger.error(f"Error registering event handler: {str(e)}")
            return {"status": "failed", "error": str(e)}
    
    async def trigger_event(self, 
                          event_type: str, 
                          event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger an observability event."""
        try:
            # Record event in metrics
            if self.metrics_collector:
                await self.metrics_collector.record_event(
                    event_type=event_type,
                    data=event_data
                )
            
            # Call registered handlers
            if event_type in self.event_handlers:
                for handler in self.event_handlers[event_type]:
                    try:
                        await handler(event_data)
                    except Exception as e:
                        logger.error(f"Error in event handler for {event_type}: {str(e)}")
            
            # Log event
            logger.info(f"Triggered event: {event_type}")
            
            return {
                "status": "triggered",
                "event_type": event_type,
                "handler_count": len(self.event_handlers.get(event_type, []))
            }
            
        except Exception as e:
            logger.error(f"Error triggering event: {str(e)}")
            return {"status": "failed", "error": str(e)}
    
    async def create_data_export(self, 
                               components: List[str], 
                               start_time: Optional[str] = None,
                               end_time: Optional[str] = None,
                               format_type: str = "json") -> Dict[str, Any]:
        """Create an export of observability data."""
        try:
            # Set default time range if not specified
            if not end_time:
                end_time = datetime.now().isoformat()
                
            if not start_time:
                # Default to 7 days ago
                start_time = (datetime.now() - timedelta(days=7)).isoformat()
            
            # Collect data for each component
            export_data = {
                "timestamp": datetime.now().isoformat(),
                "time_range": {
                    "start": start_time,
                    "end": end_time
                },
                "system_info": self.system_info,
                "components": {}
            }
            
            # Collect progress data
            if "progress" in components and self.progress_tracker:
                progress_data = await self.progress_tracker.get_progress_data(
                    start_time=start_time,
                    end_time=end_time
                )
                export_data["components"]["progress"] = progress_data
            
            # Collect resource data
            if "resources" in components and self.resource_monitor:
                resource_data = await self.resource_monitor.export_usage_data(
                    start_time=start_time,
                    end_time=end_time
                )
                export_data["components"]["resources"] = resource_data
            
            # Collect metrics data
            if "metrics" in components and self.metrics_collector:
                metrics_data = await self.metrics_collector.export_metrics_data(
                    start_time=start_time,
                    end_time=end_time
                )
                export_data["components"]["metrics"] = metrics_data
            
            # Collect interventions data
            if "interventions" in components and self.intervention_interface:
                interventions_data = await self.intervention_interface.export_interventions(
                    start_time=start_time,
                    end_time=end_time
                )
                export_data["components"]["interventions"] = interventions_data
            
            # Generate export file
            export_id = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Create export based on format type
            if format_type == "json":
                export_path = os.path.join(
                    self.config.get("storage_path", "data/observability"),
                    "exports",
                    f"{export_id}.json"
                )
                
                os.makedirs(os.path.dirname(export_path), exist_ok=True)
                with open(export_path, 'w') as f:
                    json.dump(export_data, f, indent=2)
                
            elif format_type == "csv":
                export_dir = os.path.join(
                    self.config.get("storage_path", "data/observability"),
                    "exports",
                    export_id
                )
                os.makedirs(export_dir, exist_ok=True)
                
                # Export each component as a separate CSV
                for component, data in export_data["components"].items():
                    if isinstance(data, list):
                        try:
                            df = pd.DataFrame(data)
                            component_path = os.path.join(export_dir, f"{component}.csv")
                            df.to_csv(component_path, index=False)
                        except Exception as e:
                            logger.error(f"Error creating CSV for {component}: {str(e)}")
                
                export_path = export_dir
                
            logger.info(f"Created data export: {export_id} in {format_type} format")
            
            return {
                "status": "created",
                "export_id": export_id,
                "format": format_type,
                "components": components,
                "time_range": export_data["time_range"],
                "export_path": export_path
            }
            
        except Exception as e:
            logger.error(f"Error creating data export: {str(e)}")
            return {"status": "failed", "error": str(e)}
    
    async def cleanup_old_data(self, retention_days: Optional[int] = None) -> Dict[str, Any]:
        """Clean up old observability data."""
        try:
            # Use configured retention if not specified
            if retention_days is None:
                retention_days = self.config.get("data_retention_days", 30)
            
            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            # Clean up reports
            reports_path = os.path.join(
                self.config.get("storage_path", "data/observability"),
                "reports"
            )
            
            reports_removed = 0
            if os.path.exists(reports_path):
                for filename in os.listdir(reports_path):
                    file_path = os.path.join(reports_path, filename)
                    if os.path.isfile(file_path):
                        file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                        if file_time < cutoff_date:
                            os.remove(file_path)
                            reports_removed += 1
            
            # Clean up exports
            exports_path = os.path.join(
                self.config.get("storage_path", "data/observability"),
                "exports"
            )
            
            exports_removed = 0
            if os.path.exists(exports_path):
                for item in os.listdir(exports_path):
                    item_path = os.path.join(exports_path, item)
                    if os.path.isfile(item_path):
                        file_time = datetime.fromtimestamp(os.path.getmtime(item_path))
                        if file_time < cutoff_date:
                            os.remove(item_path)
                            exports_removed += 1
                    elif os.path.isdir(item_path):
                        dir_time = datetime.fromtimestamp(os.path.getmtime(item_path))
                        if dir_time < cutoff_date:
                            shutil.rmtree(item_path)
                            exports_removed += 1
            
            # Clean up component data
            cleanup_results = {}
            
            # Clean up metrics data
            if self.metrics_collector:
                metrics_result = await self.metrics_collector.cleanup_old_data(retention_days)
                cleanup_results["metrics"] = metrics_result
            
            # Clean up resource data
            if self.resource_monitor:
                resource_result = await self.resource_monitor.cleanup_old_data(retention_days)
                cleanup_results["resources"] = resource_result
            
            # Clean up intervention data
            if self.intervention_interface:
                intervention_result = await self.intervention_interface.cleanup_old_data(retention_days)
                cleanup_results["interventions"] = intervention_result
            
            logger.info(f"Cleaned up old observability data (retention: {retention_days} days)")
            
            return {
                "status": "completed",
                "retention_days": retention_days,
                "cutoff_date": cutoff_date.isoformat(),
                "reports_removed": reports_removed,
                "exports_removed": exports_removed,
                "component_results": cleanup_results
            }
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {str(e)}")
            return {"status": "failed", "error": str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check of all observability components."""
        try:
            health_status = {
                "system_info": self.system_info,
                "timestamp": datetime.now().isoformat(),
                "components": {},
                "overall_status": "healthy"
            }
            
            # Check Progress Tracker
            if self.progress_tracker:
                try:
                    progress_status = await self.progress_tracker.health_check()
                    health_status["components"]["progress_tracker"] = progress_status
                    if progress_status.get("status") != "healthy":
                        health_status["overall_status"] = "unhealthy"
                except Exception as e:
                    health_status["components"]["progress_tracker"] = {
                        "status": "error",
                        "error": str(e)
                    }
                    health_status["overall_status"] = "unhealthy"
            
            # Check Intervention Interface
            if self.intervention_interface:
                try:
                    intervention_status = await self.intervention_interface.health_check()
                    health_status["components"]["intervention_interface"] = intervention_status
                    if intervention_status.get("status") != "healthy":
                        health_status["overall_status"] = "unhealthy"
                except Exception as e:
                    health_status["components"]["intervention_interface"] = {
                        "status": "error",
                        "error": str(e)
                    }
                    health_status["overall_status"] = "unhealthy"
            
            # Check Supervision Hub
            if self.supervision_hub:
                try:
                    supervision_status = await self.supervision_hub.health_check()
                    health_status["components"]["supervision_hub"] = supervision_status
                    if supervision_status.get("status") != "healthy":
                        health_status["overall_status"] = "unhealthy"
                except Exception as e:
                    health_status["components"]["supervision_hub"] = {
                        "status": "error",
                        "error": str(e)
                    }
                    health_status["overall_status"] = "unhealthy"
            
            # Check Resource Monitor
            if self.resource_monitor:
                try:
                    resource_status = await self.resource_monitor.health_check()
                    health_status["components"]["resource_monitor"] = resource_status
                    if resource_status.get("status") != "healthy":
                        health_status["overall_status"] = "unhealthy"
                except Exception as e:
                    health_status["components"]["resource_monitor"] = {
                        "status": "error",
                        "error": str(e)
                    }
                    health_status["overall_status"] = "unhealthy"
            
            # Check Metrics Collector
            if self.metrics_collector:
                try:
                    metrics_status = await self.metrics_collector.health_check()
                    health_status["components"]["metrics_collector"] = metrics_status
                    if metrics_status.get("status") != "healthy":
                        health_status["overall_status"] = "unhealthy"
                except Exception as e:
                    health_status["components"]["metrics_collector"] = {
                        "status": "error",
                        "error": str(e)
                    }
                    health_status["overall_status"] = "unhealthy"
            
            # Check Dashboard
            if self.is_dashboard_running:
                try:
                    # For a real implementation, we would check if the dashboard server is running
                    health_status["components"]["dashboard"] = {
                        "status": "healthy",
                        "port": self.config.get("dashboard_port", 8080)
                    }
                except Exception as e:
                    health_status["components"]["dashboard"] = {
                        "status": "error",
                        "error": str(e)
                    }
                    health_status["overall_status"] = "unhealthy"
            
            logger.info(f"Health check completed: {health_status['overall_status']}")
            
            return health_status
            
        except Exception as e:
            logger.error(f"Error performing health check: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def shutdown(self) -> Dict[str, Any]:
        """Gracefully shutdown the observability layer."""
        try:
            shutdown_results = {}
            
            # Shutdown Progress Tracker
            if self.progress_tracker:
                try:
                    result = await self.progress_tracker.shutdown()
                    shutdown_results["progress_tracker"] = result
                except Exception as e:
                    logger.error(f"Error shutting down Progress Tracker: {str(e)}")
                    shutdown_results["progress_tracker"] = {"status": "error", "error": str(e)}
            
            # Shutdown Intervention Interface
            if self.intervention_interface:
                try:
                    result = await self.intervention_interface.shutdown()
                    shutdown_results["intervention_interface"] = result
                except Exception as e:
                    logger.error(f"Error shutting down Intervention Interface: {str(e)}")
                    shutdown_results["intervention_interface"] = {"status": "error", "error": str(e)}
            
            # Shutdown Supervision Hub
            if self.supervision_hub:
                try:
                    result = await self.supervision_hub.shutdown()
                    shutdown_results["supervision_hub"] = result
                except Exception as e:
                    logger.error(f"Error shutting down Supervision Hub: {str(e)}")
                    shutdown_results["supervision_hub"] = {"status": "error", "error": str(e)}
            
            # Shutdown Resource Monitor
            if self.resource_monitor:
                try:
                    result = await self.resource_monitor.stop_monitoring()
                    shutdown_results["resource_monitor"] = result
                except Exception as e:
                    logger.error(f"Error shutting down Resource Monitor: {str(e)}")
                    shutdown_results["resource_monitor"] = {"status": "error", "error": str(e)}
            
            # Shutdown Metrics Collector
            if self.metrics_collector:
                try:
                    result = await self.metrics_collector.stop_collection()
                    shutdown_results["metrics_collector"] = result
                except Exception as e:
                    logger.error(f"Error shutting down Metrics Collector: {str(e)}")
                    shutdown_results["metrics_collector"] = {"status": "error", "error": str(e)}
            
            # Stop dashboard
            if self.is_dashboard_running:
                self.is_dashboard_running = False
                shutdown_results["dashboard"] = {"status": "stopped"}
            
            # Mark as not initialized
            self.is_initialized = False
            
            logger.info("Observability layer shutdown completed")
            
            return {
                "status": "shutdown_completed",
                "component_results": shutdown_results,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}")
            return {
                "status": "shutdown_failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


# Mock classes for component integration
class MockProgressTracker:
    def __init__(self, config):
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
    def __init__(self, config):
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
        return self.get_interventions_for_period(start_time, end_time)
    
    async def cleanup_old_data(self, retention_days):
        return {"status": "completed", "removed_count": 5}
    
    async def health_check(self):
        return {"status": "healthy", "metrics": {"pending_interventions": 2}}
    
    async def shutdown(self):
        return {"status": "shutdown_completed"}


class MockSupervisionHub:
    def __init__(self, intervention_interface, config):
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
    def __init__(self, config):
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
    def __init__(self, config):
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
```

Now, let's implement comprehensive unit tests for the `ObservabilityLayer` class:

```python
import pytest
import json
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

# Import the ObservabilityLayer and mock classes
# In a real implementation, these would be proper imports
# from observability.observability_layer import ObservabilityLayer

# Assuming ObservabilityLayer is in the same file for this example
# We would create proper imports in a real implementation


class TestObservabilityLayer:
    @pytest.fixture
    def observability_layer(self):
        """Create an ObservabilityLayer instance for testing."""
        # Configure with test settings
        config = {
            "storage_path": "test_data/observability",
            "enable_components": {
                "progress_tracker": True,
                "intervention_interface": True,
                "supervision_hub": True,
                "resource_monitor": True,
                "metrics_collector": True,
                "dashboard": True
            },
            "dashboard_port": 9000,  # Use different port for tests
            "log_level": "INFO",
            "data_retention_days": 7  # Shorter retention for tests
        }
        
        with patch('os.makedirs'), patch('signal.signal'), patch('atexit.register'):
            layer = ObservabilityLayer(config)
            return layer
    
    @pytest.mark.asyncio
    async def test_initialization(self, observability_layer):
        """Test initialization of the observability layer."""
        with patch.object(observability_layer, '_initialize_progress_tracker', new_callable=AsyncMock) as mock_progress, \
             patch.object(observability_layer, '_initialize_intervention_interface', new_callable=AsyncMock) as mock_intervention, \
             patch.object(observability_layer, '_initialize_supervision_hub', new_callable=AsyncMock) as mock_supervision, \
             patch.object(observability_layer, '_initialize_resource_monitor', new_callable=AsyncMock) as mock_resource, \
             patch.object(observability_layer, '_initialize_metrics_collector', new_callable=AsyncMock) as mock_metrics, \
             patch.object(observability_layer, '_initialize_integrations', new_callable=AsyncMock) as mock_integrations, \
             patch.object(observability_layer, '_start_dashboard', new_callable=AsyncMock) as mock_dashboard:
            
            # Set return values for the mock methods
            mock_progress.return_value = {"status": "initialized"}
            mock_intervention.return_value = {"status": "initialized"}
            mock_supervision.return_value = {"status": "initialized"}
            mock_resource.return_value = {"status": "initialized"}
            mock_metrics.return_value = {"status": "initialized"}
            mock_dashboard.return_value = {"status": "started", "port": 9000}
            
            # Test the initialization
            result = await observability_layer.initialize()
            
            # Verify all components were initialized
            mock_progress.assert_called_once()
            mock_intervention.assert_called_once()
            mock_supervision.assert_called_once()
            mock_resource.assert_called_once()
            mock_metrics.assert_called_once()
            mock_integrations.assert_called_once()
            mock_dashboard.assert_called_once()
            
            # Verify the result structure
            assert result["status"] == "initialized"
            assert "components" in result
            assert "system_info" in result
            
            # Verify the layer state
            assert observability_layer.is_initialized == True
            assert "progress_tracker" in observability_layer.component_status
            assert "intervention_interface" in observability_layer.component_status
            assert "supervision_hub" in observability_layer.component_status
            assert "resource_monitor" in observability_layer.component_status
            assert "metrics_collector" in observability_layer.component_status
            assert "dashboard" in observability_layer.component_status
    
    @pytest.mark.asyncio
    async def test_component_initialization_failure(self, observability_layer):
        """Test handling of component initialization failures."""
        with patch.object(observability_layer, '_initialize_progress_tracker', new_callable=AsyncMock) as mock_progress, \
             patch.object(observability_layer, '_initialize_intervention_interface', new_callable=AsyncMock) as mock_intervention, \
             patch.object(observability_layer, '_initialize_supervision_hub', new_callable=AsyncMock) as mock_supervision, \
             patch.object(observability_layer, '_initialize_resource_monitor', new_callable=AsyncMock) as mock_resource, \
             patch.object(observability_layer, '_initialize_metrics_collector', new_callable=AsyncMock) as mock_metrics:
            
            # Set a failure for one component
            mock_progress.return_value = {"status": "initialized"}
            mock_intervention.return_value = {"status": "initialized"}
            mock_supervision.return_value = {"status": "failed", "error": "Connection error"}
            mock_resource.return_value = {"status": "initialized"}
            mock_metrics.return_value = {"status": "initialized"}
            
            # Intentionally raise an exception in one component
            mock_resource.side_effect = Exception("Simulated resource initialization error")
            
            # Test the initialization
            result = await observability_layer.initialize()
            
            # Verify the failed initialization is captured
            assert result["status"] == "initialization_failed"
            assert "error" in result
            
            # Verify component statuses are recorded
            assert "components" in result
            assert observability_layer.is_initialized == False
    
    @pytest.mark.asyncio
    async def test_create_observability_dashboard(self, observability_layer):
        """Test creation of a custom observability dashboard."""
        # Set up test data
        name = "Test Dashboard"
        panels = [
            {"id": "panel1", "title": "CPU Usage", "type": "line", "metric_id": "resources.cpu_usage"},
            {"id": "panel2", "title": "Memory Usage", "type": "gauge", "metric_id": "resources.memory_usage"},
            {"id": "panel3", "title": "Task Completion", "type": "bar", "metric_id": "progress.completion_rate"}
        ]
        refresh_interval = 30
        
        # Mock the file operations
        with patch('os.makedirs') as mock_makedirs, \
             patch('builtins.open', create=True), \
             patch('json.dump') as mock_json_dump:
            
            # Test dashboard creation
            result = await observability_layer.create_observability_dashboard(
                name=name,
                panels=panels,
                refresh_interval=refresh_interval
            )
            
            # Verify the result
            assert result["status"] == "created"
            assert "dashboard_id" in result
            assert result["name"] == name
            assert result["panel_count"] == len(panels)
            
            # Verify directory was created
            mock_makedirs.assert_called_once()
            
            # Verify the JSON was written
            mock_json_dump.assert_called_once()
            
            # Verify dashboard content
            dashboard_data = mock_json_dump.call_args[0][0]
            assert dashboard_data["name"] == name
            assert dashboard_data["panels"] == panels
            assert dashboard_data["refresh_interval"] == refresh_interval
            assert "id" in dashboard_data
            assert "created_at" in dashboard_data
    
    @pytest.mark.asyncio
    async def test_create_system_report(self, observability_layer):
        """Test creation of a system report."""
        # Configure the mock components
        observability_layer.progress_tracker = MagicMock()
        observability_layer.progress_tracker.get_progress_report = AsyncMock(return_value={
            "overall_completion": 65,
            "completed_items": 27
        })
        
        observability_layer.resource_monitor = MagicMock()
        observability_layer.resource_monitor.get_budgets = AsyncMock(return_value=[
            {"id": "budget_cpu", "name": "CPU Budget", "usage": 45}
        ])
        observability_layer.resource_monitor.create_usage_report = AsyncMock(return_value={
            "budgets": [{"id": "budget_cpu"}],
            "history": [{"timestamp": "2023-01-01", "cpu": 40}]
        })
        
        observability_layer.metrics_collector = MagicMock()
        observability_layer.metrics_collector.create_metrics_report = AsyncMock(return_value={
            "summary": {"total_metrics": 10},
            "metrics": [{"id": "metric1"}],
            "visualizations": {
                "performance": {"type": "image"}
            }
        })
        
        observability_layer.intervention_interface = MagicMock()
        observability_layer.intervention_interface.get_interventions_for_period = AsyncMock(return_value=[
            {"id": "int1", "title": "Alert", "status": "resolved"}
        ])
        
        # Mock file operations
        with patch('os.makedirs') as mock_makedirs, \
             patch('builtins.open', create=True), \
             patch('json.dump') as mock_json_dump:
            
            # Test report creation
            result = await observability_layer.create_system_report(
                sections=["progress", "resources", "metrics", "interventions"],
                start_time="2023-01-01T00:00:00",
                end_time="2023-01-07T00:00:00"
            )
            
            # Verify the result
            assert result["status"] == "created"
            assert "report_id" in result
            assert "sections" in result
            assert "time_range" in result
            assert "report_path" in result
            
            # Verify component methods were called
            observability_layer.progress_tracker.get_progress_report.assert_called_once()
            observability_layer.resource_monitor.get_budgets.assert_called_once()
            observability_layer.resource_monitor.create_usage_report.assert_called_once()
            observability_layer.metrics_collector.create_metrics_report.assert_called_once()
            observability_layer.intervention_interface.get_interventions_for_period.assert_called_once()
            
            # Verify directory was created
            mock_makedirs.assert_called()
            
            # Verify the JSON was written
            mock_json_dump.assert_called_once()
            
            # Verify report content
            report_data = mock_json_dump.call_args[0][0]
            assert "timestamp" in report_data
            assert "time_range" in report_data
            assert "system_info" in report_data
            assert "sections" in report_data
            assert "visualizations" in report_data
    
    @pytest.mark.asyncio
    async def test_register_event_handler(self, observability_layer):
        """Test registration of event handlers."""
        # Test event handler
        async def test_handler(event_data):
            pass
        
        # Register the handler
        result = await observability_layer.register_event_handler(
            event_type="system.alert",
            handler=test_handler
        )
        
        # Verify the result
        assert result["status"] == "registered"
        assert result["event_type"] == "system.alert"
        assert result["handler_count"] == 1
        
        # Verify the handler was registered
        assert "system.alert" in observability_layer.event_handlers
        assert test_handler in observability_layer.event_handlers["system.alert"]
        
        # Register another handler for the same event
        async def test_handler2(event_data):
            pass
        
        result2 = await observability_layer.register_event_handler(
            event_type="system.alert",
            handler=test_handler2
        )
        
        # Verify handler count increased
        assert result2["handler_count"] == 2
        assert len(observability_layer.event_handlers["system.alert"]) == 2
    
    @pytest.mark.asyncio
    async def test_trigger_event(self, observability_layer):
        """Test triggering of events and handler execution."""
        # Configure mock metrics collector
        observability_layer.metrics_collector = MagicMock()
        observability_layer.metrics_collector.record_event = AsyncMock(return_value={
            "status": "recorded"
        })
        
        # Create test handlers
        handler1_called = False
        handler2_called = False
        
        async def test_handler1(event_data):
            nonlocal handler1_called
            handler1_called = True
            assert event_data["message"] == "Test event"
        
        async def test_handler2(event_data):
            nonlocal handler2_called
            handler2_called = True
            assert event_data["message"] == "Test event"
        
        # Register handlers
        observability_layer.event_handlers["system.test"] = [test_handler1, test_handler2]
        
        # Test event triggering
        event_data = {"message": "Test event", "severity": "info"}
        result = await observability_layer.trigger_event(
            event_type="system.test",
            event_data=event_data
        )
        
        # Verify the result
        assert result["status"] == "triggered"
        assert result["event_type"] == "system.test"
        assert result["handler_count"] == 2
        
        # Verify metrics collector was called
        observability_layer.metrics_collector.record_event.assert_called_once_with(
            event_type="system.test",
            data=event_data
        )
        
        # Verify handlers were called
        assert handler1_called == True
        assert handler2_called == True
        
        # Test triggering with failing handler
        async def failing_handler(event_data):
            raise Exception("Simulated handler error")
        
        observability_layer.event_handlers["system.test"].append(failing_handler)
        
        # The event should still trigger successfully even if a handler fails
        result = await observability_layer.trigger_event(
            event_type="system.test",
            event_data=event_data
        )
        
        assert result["status"] == "triggered"
        assert result["handler_count"] == 3
    
    @pytest.mark.asyncio
    async def test_create_data_export(self, observability_layer):
        """Test creation of data exports in different formats."""
        # Configure mock components
        observability_layer.progress_tracker = MagicMock()
        observability_layer.progress_tracker.get_progress_data = AsyncMock(return_value=[
            {"timestamp": "2023-01-01", "completion": 50}
        ])
        
        observability_layer.resource_monitor = MagicMock()
        observability_layer.resource_monitor.export_usage_data = AsyncMock(return_value=[
            {"timestamp": "2023-01-01", "cpu": 40, "memory": 15}
        ])
        
        observability_layer.metrics_collector = MagicMock()
        observability_layer.metrics_collector.export_metrics_data = AsyncMock(return_value=[
            {"timestamp": "2023-01-01", "metric_id": "performance.execution_time", "value": 1.2}
        ])
        
        observability_layer.intervention_interface = MagicMock()
        observability_layer.intervention_interface.export_interventions = AsyncMock(return_value=[
            {"id": "int1", "timestamp": "2023-01-01", "status": "resolved"}
        ])
        
        # Test JSON export
        with patch('os.makedirs') as mock_makedirs, \
             patch('builtins.open', create=True), \
             patch('json.dump') as mock_json_dump:
            
            # Test JSON export creation
            result = await observability_layer.create_data_export(
                components=["progress", "resources", "metrics", "interventions"],
                start_time="2023-01-01T00:00:00",
                end_time="2023-01-07T00:00:00",
                format_type="json"
            )
            
            # Verify the result
            assert result["status"] == "created"
            assert "export_id" in result
            assert result["format"] == "json"
            assert "components" in result
            assert "time_range" in result
            assert "export_path" in result
            
            # Verify component methods were called
            observability_layer.progress_tracker.get_progress_data.assert_called_once()
            observability_layer.resource_monitor.export_usage_data.assert_called_once()
            observability_layer.metrics_collector.export_metrics_data.assert_called_once()
            observability_layer.intervention_interface.export_interventions.assert_called_once()
            
            # Verify directory was created
            mock_makedirs.assert_called()
            
            # Verify the JSON was written
            mock_json_dump.assert_called_once()
        
        # Test CSV export
        with patch('os.makedirs') as mock_makedirs, \
             patch('pandas.DataFrame.to_csv') as mock_to_csv:
            
            # Reset mock calls
            observability_layer.progress_tracker.get_progress_data.reset_mock()
            observability_layer.resource_monitor.export_usage_data.reset_mock()
            observability_layer.metrics_collector.export_metrics_data.reset_mock()
            observability_layer.intervention_interface.export_interventions.reset_mock()
            
            # Test CSV export creation
            result = await observability_layer.create_data_export(
                components=["progress", "resources", "metrics", "interventions"],
                start_time="2023-01-01T00:00:00",
                end_time="2023-01-07T00:00:00",
                format_type="csv"
            )
            
            # Verify the result
            assert result["status"] == "created"
            assert "export_id" in result
            assert result["format"] == "csv"
            
            # Verify component methods were called
            observability_layer.progress_tracker.get_progress_data.assert_called_once()
            observability_layer.resource_monitor.export_usage_data.assert_called_once()
            observability_layer.metrics_collector.export_metrics_data.assert_called_once()
            observability_layer.intervention_interface.export_interventions.assert_called_once()
            
            # Verify directories were created
            mock_makedirs.assert_called()
    
    @pytest.mark.asyncio
    async def test_cleanup_old_data(self, observability_layer):
        """Test cleaning up of old observability data."""
        # Configure mock components
        observability_layer.metrics_collector = MagicMock()
        observability_layer.metrics_collector.cleanup_old_data = AsyncMock(return_value={
            "status": "completed", "removed_metrics": 250
        })
        
        observability_layer.resource_monitor = MagicMock()
        observability_layer.resource_monitor.cleanup_old_data = AsyncMock(return_value={
            "status": "completed", "removed_records": 120
        })
        
        observability_layer.intervention_interface = MagicMock()
        observability_layer.intervention_interface.cleanup_old_data = AsyncMock(return_value={
            "status": "completed", "removed_count": 35
        })
        
        # Mock file operations
        with patch('os.path.exists', return_value=True), \
             patch('os.listdir', return_value=["file1.json", "file2.json"]), \
             patch('os.path.isfile', return_value=True), \
             patch('os.path.getmtime', return_value=datetime.now().timestamp() - 60*60*24*30), \
             patch('os.remove') as mock_remove:
            
            # Test cleanup with default retention
            result = await observability_layer.cleanup_old_data()
            
            # Verify the result
            assert result["status"] == "completed"
            assert "retention_days" in result
            assert "cutoff_date" in result
            assert "reports_removed" in result
            assert "exports_removed" in result
            assert "component_results" in result
            
            # Verify component methods were called
            observability_layer.metrics_collector.cleanup_old_data.assert_called_once()
            observability_layer.resource_monitor.cleanup_old_data.assert_called_once()
            observability_layer.intervention_interface.cleanup_old_data.assert_called_once()
            
            # Verify files were removed
            assert mock_remove.call_count > 0
            
            # Test with custom retention
            observability_layer.metrics_collector.cleanup_old_data.reset_mock()
            observability_layer.resource_monitor.cleanup_old_data.reset_mock()
            observability_layer.intervention_interface.cleanup_old_data.reset_mock()
            mock_remove.reset_mock()
            
            custom_retention = 14
            result = await observability_layer.cleanup_old_data(retention_days=custom_retention)
            
            assert result["retention_days"] == custom_retention
            
            # Verify component methods were called with custom retention
            observability_layer.metrics_collector.cleanup_old_data.assert_called_once_with(custom_retention)
            observability_layer.resource_monitor.cleanup_old_data.assert_called_once_with(custom_retention)
            observability_layer.intervention_interface.cleanup_old_data.assert_called_once_with(custom_retention)
    
    @pytest.mark.asyncio
    async def test_health_check(self, observability_layer):
        """Test observability health check."""
        # Configure mock components
        observability_layer.progress_tracker = MagicMock()
        observability_layer.progress_tracker.health_check = AsyncMock(return_value={
            "status": "healthy", "metrics": {"tracked_items": 42}
        })
        
        observability_layer.intervention_interface = MagicMock()
        observability_layer.intervention_interface.health_check = AsyncMock(return_value={
            "status": "healthy", "metrics": {"pending_interventions": 2}
        })
        
        observability_layer.supervision_hub = MagicMock()
        observability_layer.supervision_hub.health_check = AsyncMock(return_value={
            "status": "healthy", "metrics": {"active_workflows": 3}
        })
        
        observability_layer.resource_monitor = MagicMock()
        observability_layer.resource_monitor.health_check = AsyncMock(return_value={
            "status": "healthy", "monitoring_active": True, "metrics": {"tracked_budgets": 3}
        })
        
        observability_layer.metrics_collector = MagicMock()
        observability_layer.metrics_collector.health_check = AsyncMock(return_value={
            "status": "healthy", "collection_active": True, "metrics": {"registered_metrics": 15}
        })
        
        observability_layer.is_dashboard_running = True
        
        # Test health check
        result = await observability_layer.health_check()
        
        # Verify the result structure
        assert "system_info" in result
        assert "timestamp" in result
        assert "components" in result
        assert "overall_status" in result
        
        # All components should be healthy, so overall status should be healthy
        assert result["overall_status"] == "healthy"
        
        # Verify all components are included
        assert "progress_tracker" in result["components"]
        assert "intervention_interface" in result["components"]
        assert "supervision_hub" in result["components"]
        assert "resource_monitor" in result["components"]
        assert "metrics_collector" in result["components"]
        assert "dashboard" in result["components"]
        
        # Test with one unhealthy component
        observability_layer.resource_monitor.health_check = AsyncMock(return_value={
            "status": "unhealthy", "error": "Connection lost", "monitoring_active": False
        })
        
        result = await observability_layer.health_check()
        
        # Overall status should now be unhealthy
        assert result["overall_status"] == "unhealthy"
        assert result["components"]["resource_monitor"]["status"] == "unhealthy"
        
        # Test with component raising exception
        observability_layer.metrics_collector.health_check = AsyncMock(side_effect=Exception("Simulated error"))
        
        result = await observability_layer.health_check()
        
        # Overall status should still be unhealthy
        assert result["overall_status"] == "unhealthy"
        assert result["components"]["metrics_collector"]["status"] == "error"
        assert "error" in result["components"]["metrics_collector"]
    
    @pytest.mark.asyncio
    async def test_shutdown(self, observability_layer):
        """Test graceful shutdown of the observability layer."""
        # Configure mock components
        observability_layer.progress_tracker = MagicMock()
        observability_layer.progress_tracker.shutdown = AsyncMock(return_value={
            "status": "shutdown_completed"
        })
        
        observability_layer.intervention_interface = MagicMock()
        observability_layer.intervention_interface.shutdown = AsyncMock(return_value={
            "status": "shutdown_completed"
        })
        
        observability_layer.supervision_hub = MagicMock()
        observability_layer.supervision_hub.shutdown = AsyncMock(return_value={
            "status": "shutdown_completed"
        })
        
        observability_layer.resource_monitor = MagicMock()
        observability_layer.resource_monitor.stop_monitoring = AsyncMock(return_value={
            "status": "stopped"
        })
        
        observability_layer.metrics_collector = MagicMock()
        observability_layer.metrics_collector.stop_collection = AsyncMock(return_value={
            "status": "stopped"
        })
        
        observability_layer.is_dashboard_running = True
        observability_layer.is_initialized = True
        
        # Test shutdown
        result = await observability_layer.shutdown()
        
        # Verify the result
        assert result["status"] == "shutdown_completed"
        assert "component_results" in result
        assert "timestamp" in result
        
        # Verify component methods were called
        observability_layer.progress_tracker.shutdown.assert_called_once()
        observability_layer.intervention_interface.shutdown.assert_called_once()
        observability_layer.supervision_hub.shutdown.assert_called_once()
        observability_layer.resource_monitor.stop_monitoring.assert_called_once()
        observability_layer.metrics_collector.stop_collection.assert_called_once()
        
        # Verify layer state
        assert observability_layer.is_dashboard_running == False
        assert observability_layer.is_initialized == False
        
        # Test with component failure
        # Reset the layer state
        observability_layer.is_dashboard_running = True
        observability_layer.is_initialized = True
        
        # Make one component fail
        observability_layer.resource_monitor.stop_monitoring = AsyncMock(side_effect=Exception("Simulated error"))
        
        # Shutdown should still complete
        result = await observability_layer.shutdown()
        
        assert result["status"] == "shutdown_completed"
        assert "component_results" in result
        assert "resource_monitor" in result["component_results"]
        assert result["component_results"]["resource_monitor"]["status"] == "error"
        
        # Verify layer state is still reset
        assert observability_layer.is_dashboard_running == False
        assert observability_layer.is_initialized == False
    
    @pytest.mark.asyncio
    async def test_initialize_integrations(self, observability_layer):
        """Test initialization of cross-component integrations."""
        # Configure mock components
        observability_layer.progress_tracker = MagicMock()
        observability_layer.progress_tracker.register_callback = MagicMock()
        
        observability_layer.intervention_interface = MagicMock()
        observability_layer.intervention_interface.request_intervention = AsyncMock()
        
        observability_layer.supervision_hub = MagicMock()
        observability_layer.supervision_hub.create_approval_workflow = AsyncMock()
        
        observability_layer.resource_monitor = MagicMock()
        observability_layer.resource_monitor.register_alert_callback = MagicMock()
        observability_layer.resource_monitor.get_budgets = AsyncMock(return_value=[
            {"id": "budget_cpu", "name": "CPU Budget", "priority": "high", "resource_type": "cpu"}
        ])
        
        observability_layer.metrics_collector = MagicMock()
        observability_layer.metrics_collector.register_metric = AsyncMock()
        observability_layer.metrics_collector.register_anomaly_definition = AsyncMock()
        
        # Mock integration methods
        with patch.object(observability_layer, '_integrate_progress_metrics', new_callable=AsyncMock) as mock_progress_metrics, \
             patch.object(observability_layer, '_integrate_resource_alerts', new_callable=AsyncMock) as mock_resource_alerts, \
             patch.object(observability_layer, '_integrate_tracking_metrics', new_callable=AsyncMock) as mock_tracking_metrics, \
             patch.object(observability_layer, '_integrate_anomaly_interventions', new_callable=AsyncMock) as mock_anomaly_interventions, \
             patch.object(observability_layer, '_integrate_resource_supervision', new_callable=AsyncMock) as mock_resource_supervision:
            
            # Test integration initialization
            await observability_layer._initialize_integrations()
            
            # Verify all integration methods were called
            mock_progress_metrics.assert_called_once()
            mock_resource_alerts.assert_called_once()
            mock_tracking_metrics.assert_called_once()
            mock_anomaly_interventions.assert_called_once()
            mock_resource_supervision.assert_called_once()
            
            # Test with missing components
            observability_layer.progress_tracker = None
            
            # Reset mock calls
            mock_progress_metrics.reset_mock()
            mock_resource_alerts.reset_mock()
            mock_tracking_metrics.reset_mock()
            mock_anomaly_interventions.reset_mock()
            mock_resource_supervision.reset_mock()
            
            # Integration should log a warning but not fail
            await observability_layer._initialize_integrations()
            
            # Verify methods were not called due to missing components
            mock_progress_metrics.assert_not_called()
            mock_resource_alerts.assert_not_called()
            mock_tracking_metrics.assert_not_called()
            mock_anomaly_interventions.assert_not_called()
            mock_resource_supervision.assert_not_called()
```

## Observability Integration: System Connections and Key Features

The Observability Integration module (Work Unit 5.6) serves as the unifying layer for all observability components in the Self-Aware Cerebrum system. This integration layer coordinates data flow between various observability components and provides a consistent interface for monitoring, reporting, and visualization.

### Key System Connections

1. **Connection to Phase 3 (Execution Engine)**:
   - Integrates with `ExecutionTracker` to collect execution metrics
   - Monitors task success/failure rates and execution times
   - Tracks resource utilization during task execution
   - Provides visualization of execution progress and performance

2. **Connection to Phase 4 (Self-Modification Engine)**:
   - Monitors code generation quality metrics
   - Tracks safety validation success rates
   - Captures integration activities and results
   - Provides visibility into self-modification activities

3. **Connection to Phase 5 (Other Observability Components)**:
   - Unifies data from `ProgressTracker`, `InterventionInterface`, `SupervisionHub`, `ResourceMonitor`, and `MetricsCollector`
   - Ensures consistent configuration across all observability components
   - Facilitates cross-component integrations (metrics to alerts, alerts to interventions)
   - Provides consolidated reporting and visualization

4. **Connection to Phase 6 (Cognitive Loop)**:
   - Feeds observability data into the cognitive loop for self-awareness
   - Provides metrics for adaptation and learning
   - Tracks the effectiveness of the cognitive loop itself
   - Supports improved decision-making through comprehensive monitoring

### Implementation Highlights

The ObservabilityLayer class provides several key capabilities:

1. **Unified Initialization**: Handles initialization of all observability components with consistent configuration
2. **Cross-Component Integration**: Connects data flows between components (e.g., metrics to alerts to interventions)
3. **Dashboard Creation**: Supports creation of custom dashboards for different monitoring needs
4. **Comprehensive Reporting**: Generates system-wide reports across all observability domains
5. **Data Export**: Supports various export formats for further analysis and record-keeping
6. **Event Handling**: Provides a flexible event system for reacting to observability events
7. **Health Monitoring**: Tracks the health of the observability components themselves
8. **Data Lifecycle Management**: Handles cleanup of old data to manage storage requirements

### Testing Strategy

The comprehensive unit tests for the ObservabilityLayer verify:

1. Component initialization and error handling
2. Cross-component integration functionality
3. Dashboard and report creation
4. Event handling mechanisms
5. Data export capabilities
6. Data cleanup processes
7. Health check functionality
8. Graceful shutdown behavior

These tests ensure the robustness and reliability of the observability integration layer, which is critical for maintaining visibility into the self-aware system's operation.

## Key Implementation Guidance (continued)

1. **Focus on scalability** - The implementation should handle increasing volumes of observability data as the system grows, using efficient storage and processing techniques to manage large datasets.

2. **Ensure consistency across components** - Maintain consistent data formats, naming conventions, and configuration approaches across all observability components for a coherent user experience.

3. **Prioritize reliability** - The observability layer must remain operational even when parts of the system are under stress or failing. Implement proper error handling and fallback mechanisms.

4. **Minimize performance impact** - Collecting observability data should not significantly impact system performance. Use sampling, buffering, and asynchronous processing to reduce overhead.

5. **Implement secure data handling** - Observability data may contain sensitive information about system operation. Implement appropriate access controls and data protection measures.

6. **Design for extensibility** - Make it easy to add new metrics, visualizations, and integrations as the system evolves. Use a plugin architecture where appropriate.

7. **Support custom visualizations** - Different users and use cases require different visualizations. Provide flexible visualization capabilities that can be tailored to specific needs.

8. **Enable cross-component correlations** - One of the most valuable aspects of integrated observability is the ability to correlate events across components. Design data structures and APIs to support this.

## Integration with Phase 6: Cognitive Loop & System Integration

The Observability Integration is a critical component for the upcoming Phase 6, providing essential data for the system's cognitive functions:

1. **Data for Self-Awareness**: The Cognitive Loop Orchestrator relies on observability data to build the system's awareness of its own state and performance.

2. **Feedback Mechanisms**: The observability layer provides feedback channels that enable the system to learn from its actions and outcomes.

3. **Adaptation Triggers**: Anomaly detection and performance metrics from the observability layer trigger adaptation in the cognitive loop.

4. **Human-in-the-Loop Integration**: The intervention interfaces and supervision hub components provide the human oversight mechanisms that the cognitive loop needs to operate safely.

5. **System Health Assessment**: The cognitive loop uses health check data to assess overall system state and make high-level operational decisions.

When implementing Phase 6, you'll build upon this observability integration layer to create a truly self-aware system that can monitor, evaluate, and adapt its own behavior.

## Deployment Considerations

When deploying the Observability Integration:

1. **Start with minimal configuration** - Begin with essential metrics and gradually add more as needed to avoid overwhelming users.

2. **Configure appropriate retention policies** - Balance data retention needs with storage constraints based on expected system usage.

3. **Set up sensible alerting thresholds** - Avoid alert fatigue by carefully configuring anomaly detection and alert thresholds.

4. **Establish monitoring dashboards** - Create purpose-specific dashboards for different user roles (developers, operators, business users).

5. **Document integration points** - Clearly document how other components should interact with the observability layer.

6. **Run regular health checks** - Schedule periodic health checks of the observability system itself to ensure it's functioning properly.

7. **Plan for data migration** - As the system evolves, you may need to migrate observability data to maintain historical records.

## Conclusion

The Observability Integration (Work Unit 5.6) serves as the unifying layer that brings together all the observability components into a coherent whole. It provides comprehensive visibility into system operation, enables data-driven decision making, and forms the foundation for the self-awareness capabilities that will be implemented in Phase 6.

By implementing this layer with attention to scalability, reliability, performance, and usability, you'll create a robust observability system that not only helps users understand the system's behavior but also enables the system itself to become truly self-aware.

With this implementation, you've completed Phase 5 of the Self-Aware Cerebrum System workplan, delivering a comprehensive observability layer that provides deep visibility into all aspects of system operation while enabling human oversight and intervention where needed.
