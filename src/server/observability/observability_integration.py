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
import shutil
import pandas as pd
import numpy as np
import socket
import platform
import atexit
import signal
import weakref
import traceback

# Import observability components
try:
    from src.server.observability.progress_tracker import ProgressTracker
    from src.server.observability.intervention_interface import InterventionInterface
    from src.server.observability.supervision_hub import SupervisionHub
    from src.server.observability.resource_monitor import ResourceMonitor
    from src.server.observability.metrics_collector import MetricsCollector
except ImportError:
    # For testing, use mocks if real components are not available
    from src.server.observability.mocks import (
        MockProgressTracker as ProgressTracker,
        MockInterventionInterface as InterventionInterface,
        MockSupervisionHub as SupervisionHub,
        MockResourceMonitor as ResourceMonitor,
        MockMetricsCollector as MetricsCollector
    )

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
            self.progress_tracker = ProgressTracker(
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
            self.intervention_interface = InterventionInterface(
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
            self.supervision_hub = SupervisionHub(
                intervention_interface=self.intervention_interface,
                config=self.config.get("component_config", {}).get("supervision_hub", {})
            )
            
            logger.info("Supervision Hub initialized")
            
            return {"status": "initialized"}
            
        except Exception as e:
            logger.error(f"Error initializing Supervision Hub: {str(e)}")
            return {"status": "failed", "error": str(e)}
    
    async def _initialize_resource_monitor(self) -> Dict[str, Any]:
        """Initialize the Resource Monitor component."""
        try:
            self.resource_monitor = ResourceMonitor(
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
            self.metrics_collector = MetricsCollector(
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
            if not self.progress_tracker or not self.metrics_collector:
                logger.error("Cannot integrate progress metrics: components not initialized")
                return
            
            # Register progress metrics
            await self.metrics_collector.register_metric(
                name="Task Completion Rate",
                description="Rate of task completion over time",
                type="rate",
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
            self.progress_tracker.register_callback(self._on_progress_update)
            
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
            
            # Register resource utilization metrics
            await self.metrics_collector.register_metric(
                name="CPU Utilization",
                description="CPU utilization percentage",
                type="gauge",
                category="resource",
                unit="percent",
                components=["system"]
            )
            
            await self.metrics_collector.register_metric(
                name="Memory Utilization",
                description="Memory utilization percentage",
                type="gauge",
                category="resource",
                unit="percent",
                components=["system"]
            )
            
            # Register additional performance metrics
            await self.metrics_collector.register_metric(
                name="Response Time",
                description="System response time",
                type="histogram",
                category="performance",
                unit="seconds",
                components=["system", "api"]
            )
            
            await self.metrics_collector.register_metric(
                name="Request Throughput",
                description="Number of requests processed per minute",
                type="gauge",
                category="performance",
                unit="requests/minute",
                components=["api"]
            )
            
            logger.info("Tracking metrics integration established")
            
        except Exception as e:
            logger.error(f"Error integrating tracking metrics: {str(e)}")
    
    async def _integrate_anomaly_interventions(self) -> None:
        """Connect anomaly detection to interventions."""
        try:
            # Register callback for anomaly detection
            await self.metrics_collector.register_anomaly_callback(self._on_anomaly_detected)
            
            # Register anomaly definitions for critical metrics
            await self.metrics_collector.register_anomaly_definition(
                name="High Task Failure Rate",
                description="Unusually high task failure rate",
                metric_id="reliability.task_success_rate",
                detection_method="threshold",
                parameters={"min": 70.0},  # Alert if success rate falls below 70%
                severity="warning",
                anomaly_id="task_failure_spike"
            )
            
            await self.metrics_collector.register_anomaly_definition(
                name="Slow Task Execution",
                description="Unusually slow task execution",
                metric_id="performance.task_execution_time",
                detection_method="zscore",
                parameters={"threshold": 2.5},  # Alert if z-score > 2.5
                severity="warning",
                anomaly_id="slow_execution"
            )
            
            await self.metrics_collector.register_anomaly_definition(
                name="Low Code Quality",
                description="Unusually low code quality score",
                metric_id="cognitive.code_generation_quality",
                detection_method="threshold",
                parameters={"min": 0.7},  # Alert if quality below 0.7
                severity="warning",
                anomaly_id="low_code_quality"
            )
            
            await self.metrics_collector.register_anomaly_definition(
                name="High Memory Usage",
                description="Unusually high memory utilization",
                metric_id="resource.memory_utilization",
                detection_method="threshold",
                parameters={"max": 85.0},  # Alert if memory usage exceeds 85%
                severity="warning",
                anomaly_id="high_memory_usage"
            )
            
            await self.metrics_collector.register_anomaly_definition(
                name="Response Time Degradation",
                description="Significant degradation in response time",
                metric_id="performance.response_time",
                detection_method="zscore",
                parameters={"threshold": 2.0},  # Alert if z-score > 2.0
                severity="warning",
                anomaly_id="response_time_degradation"
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
    
    async def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of metrics from the metrics collector."""
        try:
            if not self.metrics_collector:
                return {
                    "status": "error",
                    "error": "Metrics collector not initialized",
                    "timestamp": datetime.now().isoformat()
                }
            
            summary = await self.metrics_collector.get_metrics_summary()
            
            return {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                **summary
            }
            
        except Exception as e:
            logger.error(f"Error getting metrics summary: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _shutdown(self) -> None:
        """Internal method to shutdown components without returning a result."""
        try:
            # Shutdown all components
            # Progress Tracker
            if self.progress_tracker:
                try:
                    await self.progress_tracker.shutdown()
                except Exception as e:
                    logger.error(f"Error shutting down Progress Tracker: {str(e)}")
            
            # Intervention Interface
            if self.intervention_interface:
                try:
                    await self.intervention_interface.shutdown()
                except Exception as e:
                    logger.error(f"Error shutting down Intervention Interface: {str(e)}")
            
            # Supervision Hub
            if self.supervision_hub:
                try:
                    await self.supervision_hub.shutdown()
                except Exception as e:
                    logger.error(f"Error shutting down Supervision Hub: {str(e)}")
            
            # Resource Monitor
            if self.resource_monitor:
                try:
                    await self.resource_monitor.stop_monitoring()
                except Exception as e:
                    logger.error(f"Error shutting down Resource Monitor: {str(e)}")
            
            # Metrics Collector
            if self.metrics_collector:
                try:
                    await self.metrics_collector.stop_collection()
                except Exception as e:
                    logger.error(f"Error shutting down Metrics Collector: {str(e)}")
            
            # Mark as not initialized
            self.is_initialized = False
            self.is_dashboard_running = False
            
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}")
    
    async def restart(self) -> Dict[str, Any]:
        """Restart the observability layer."""
        try:
            logger.info("Restarting observability layer...")
            
            # Shutdown all components
            await self._shutdown()
            
            # Reinitialize components
            await self._initialize_components()
            
            # Reinitialize integrations
            await self._initialize_integrations()
            
            # Record restart event
            if self.metrics_collector:
                await self.metrics_collector.record_event(
                    event_type="system_restart",
                    data={
                        "timestamp": datetime.now().isoformat(),
                        "reason": "manual_restart"
                    }
                )
            
            logger.info("Observability layer restarted successfully")
            
            return {
                "status": "restarted",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error restarting observability layer: {str(e)}")
            return {
                "status": "restart_failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _initialize_components(self) -> Dict[str, Any]:
        """Initialize all components."""
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
        
        self.component_status = component_results
        return component_results 