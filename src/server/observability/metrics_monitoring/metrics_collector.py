"""
Metrics Collector for the Self-Aware System.

This module provides a comprehensive system for collecting, aggregating, analyzing,
and reporting metrics from across the entire system. It provides a unified view of
system performance, behavior, and health.
"""

from typing import Dict, List, Optional, Any, Union, Set, Tuple
import logging
import asyncio
import json
import os
from pathlib import Path
import uuid
import time
import re
import statistics
from datetime import datetime, timedelta
from collections import defaultdict
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from io import BytesIO
import base64
import psutil

from src.server.observability.metrics_monitoring.models import (
    MetricType, MetricCategory, MetricPriority, MetricDefinition, 
    MetricValue, MetricQuery, AnomalyDefinition, AnomalyEvent
)

logger = logging.getLogger(__name__)

class MetricsCollector:
    """Collects, aggregates, and analyzes system metrics."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize with optional configuration."""
        self.config = config or {
            "storage_path": "data/metrics",
            "default_retention_days": 30,
            "batch_size": 100,
            "sampling_enabled": True,
            "anomaly_detection_enabled": True,
            "anomaly_notification_handler": None,
            "max_values_per_metric": 1000
        }
        
        self.metric_definitions: Dict[str, MetricDefinition] = {}
        self.metric_values: Dict[str, List[MetricValue]] = defaultdict(list)
        self.anomaly_definitions: Dict[str, AnomalyDefinition] = {}
        self.anomaly_events: Dict[str, AnomalyEvent] = {}
        
        self.metric_samplers: Dict[str, asyncio.Task] = {}
        self.is_collecting = False
        self.batch_count = 0
        
        # Register built-in metrics
        self._register_builtin_metrics()
        
        # Initialize storage
        self._initialize_storage()
        
        # Load existing data
        self._load_data()
    
    def _register_builtin_metrics(self) -> None:
        """Register built-in system metrics."""
        builtin_metrics = [
            # System metrics
            MetricDefinition(
                id="system.cpu.usage",
                name="System CPU Usage",
                description="Percentage of CPU usage",
                type=MetricType.GAUGE,
                category=MetricCategory.SYSTEM,
                unit="percent",
                priority=MetricPriority.HIGH,
                sampling_interval=60
            ),
            MetricDefinition(
                id="system.memory.usage",
                name="System Memory Usage",
                description="Percentage of memory usage",
                type=MetricType.GAUGE,
                category=MetricCategory.SYSTEM,
                unit="percent",
                priority=MetricPriority.HIGH,
                sampling_interval=60
            ),
            MetricDefinition(
                id="system.disk.usage",
                name="System Disk Usage",
                description="Percentage of disk usage",
                type=MetricType.GAUGE,
                category=MetricCategory.SYSTEM,
                unit="percent",
                priority=MetricPriority.NORMAL,
                sampling_interval=300
            ),
            
            # Performance metrics
            MetricDefinition(
                id="performance.response_time",
                name="Response Time",
                description="Time taken to respond to requests",
                type=MetricType.HISTOGRAM,
                category=MetricCategory.PERFORMANCE,
                unit="milliseconds",
                priority=MetricPriority.HIGH
            ),
            MetricDefinition(
                id="performance.throughput",
                name="Throughput",
                description="Number of operations processed per second",
                type=MetricType.RATE,
                category=MetricCategory.PERFORMANCE,
                unit="ops/sec",
                priority=MetricPriority.HIGH
            ),
            
            # Reliability metrics
            MetricDefinition(
                id="reliability.errors",
                name="Error Count",
                description="Number of errors",
                type=MetricType.COUNTER,
                category=MetricCategory.RELIABILITY,
                unit="errors",
                priority=MetricPriority.CRITICAL
            ),
            MetricDefinition(
                id="reliability.uptime",
                name="Uptime",
                description="System uptime",
                type=MetricType.GAUGE,
                category=MetricCategory.RELIABILITY,
                unit="seconds",
                priority=MetricPriority.HIGH,
                sampling_interval=300
            ),
            
            # Cognitive metrics
            MetricDefinition(
                id="cognitive.planning_time",
                name="Planning Time",
                description="Time spent in planning phase",
                type=MetricType.DURATION,
                category=MetricCategory.COGNITIVE,
                unit="seconds",
                priority=MetricPriority.NORMAL
            ),
            MetricDefinition(
                id="cognitive.execution_time",
                name="Execution Time",
                description="Time spent in execution phase",
                type=MetricType.DURATION,
                category=MetricCategory.COGNITIVE,
                unit="seconds",
                priority=MetricPriority.NORMAL
            ),
            MetricDefinition(
                id="cognitive.decision_confidence",
                name="Decision Confidence",
                description="Confidence level in decisions",
                type=MetricType.GAUGE,
                category=MetricCategory.COGNITIVE,
                unit="percent",
                priority=MetricPriority.HIGH
            )
        ]
        
        for metric in builtin_metrics:
            self.metric_definitions[metric.id] = metric
    
    def _initialize_storage(self) -> None:
        """Initialize storage directories."""
        storage_path = self.config.get("storage_path", "data/metrics")
        os.makedirs(storage_path, exist_ok=True)
        
        # Create subdirectories
        os.makedirs(os.path.join(storage_path, "definitions"), exist_ok=True)
        os.makedirs(os.path.join(storage_path, "values"), exist_ok=True)
        os.makedirs(os.path.join(storage_path, "anomalies"), exist_ok=True)
        os.makedirs(os.path.join(storage_path, "anomalies", "definitions"), exist_ok=True)
        os.makedirs(os.path.join(storage_path, "anomalies", "events"), exist_ok=True)
    
    def _load_data(self) -> None:
        """Load metric definitions and anomaly definitions from storage."""
        storage_path = self.config.get("storage_path", "data/metrics")
        
        # Load metric definitions
        definitions_dir = os.path.join(storage_path, "definitions")
        if os.path.exists(definitions_dir):
            for filename in os.listdir(definitions_dir):
                if filename.endswith(".json"):
                    try:
                        with open(os.path.join(definitions_dir, filename), 'r') as f:
                            data = json.load(f)
                            metric = MetricDefinition.from_dict(data)
                            self.metric_definitions[metric.id] = metric
                    except Exception as e:
                        logger.error(f"Error loading metric definition from {filename}: {str(e)}")
        
        # Load anomaly definitions
        anomalies_dir = os.path.join(storage_path, "anomalies", "definitions")
        if os.path.exists(anomalies_dir):
            for filename in os.listdir(anomalies_dir):
                if filename.endswith(".json"):
                    try:
                        with open(os.path.join(anomalies_dir, filename), 'r') as f:
                            data = json.load(f)
                            anomaly = AnomalyDefinition.from_dict(data)
                            self.anomaly_definitions[anomaly.id] = anomaly
                    except Exception as e:
                        logger.error(f"Error loading anomaly definition from {filename}: {str(e)}")
        
        # Load recent anomaly events
        events_dir = os.path.join(storage_path, "anomalies", "events")
        if os.path.exists(events_dir):
            for filename in os.listdir(events_dir):
                if filename.endswith(".json"):
                    try:
                        with open(os.path.join(events_dir, filename), 'r') as f:
                            data = json.load(f)
                            event = AnomalyEvent.from_dict(data)
                            self.anomaly_events[event.id] = event
                    except Exception as e:
                        logger.error(f"Error loading anomaly event from {filename}: {str(e)}")
    
    async def _save_metric_definition(self, metric: MetricDefinition) -> None:
        """Save metric definition to storage."""
        storage_path = self.config.get("storage_path", "data/metrics")
        definitions_dir = os.path.join(storage_path, "definitions")
        os.makedirs(definitions_dir, exist_ok=True)
        
        file_path = os.path.join(definitions_dir, f"{metric.id}.json")
        
        with open(file_path, 'w') as f:
            json.dump(metric.to_dict(), f, indent=2)
            
        logger.debug(f"Metric definition {metric.id} saved to {file_path}")
    
    async def _save_metric_values(self) -> None:
        """Save metric values to storage."""
        storage_path = self.config.get("storage_path", "data/metrics")
        values_dir = os.path.join(storage_path, "values")
        os.makedirs(values_dir, exist_ok=True)
        
        for metric_id, values in self.metric_values.items():
            if not values:
                continue
                
            # Group values by day for efficient storage
            days = defaultdict(list)
            for value in values:
                day = value.timestamp.split('T')[0]  # Extract YYYY-MM-DD
                days[day].append(value.to_dict())
            
            # Save each day's values
            for day, day_values in days.items():
                file_path = os.path.join(values_dir, f"{metric_id}_{day}.json")
                
                # Append to existing file if it exists
                existing_values = []
                if os.path.exists(file_path):
                    try:
                        with open(file_path, 'r') as f:
                            existing_values = json.load(f)
                    except Exception as e:
                        logger.error(f"Error reading metric values from {file_path}: {str(e)}")
                
                # Combine values and save
                combined_values = existing_values + day_values
                
                with open(file_path, 'w') as f:
                    json.dump(combined_values, f)
        
        logger.debug(f"Saved metric values to {values_dir}")
    
    async def _save_anomaly_definition(self, anomaly: AnomalyDefinition) -> None:
        """Save anomaly definition to storage."""
        storage_path = self.config.get("storage_path", "data/metrics")
        anomalies_dir = os.path.join(storage_path, "anomalies", "definitions")
        os.makedirs(anomalies_dir, exist_ok=True)
        
        file_path = os.path.join(anomalies_dir, f"{anomaly.id}.json")
        
        with open(file_path, 'w') as f:
            json.dump(anomaly.to_dict(), f, indent=2)
            
        logger.debug(f"Anomaly definition {anomaly.id} saved to {file_path}")
    
    async def _save_anomaly_event(self, event: AnomalyEvent) -> None:
        """Save anomaly event to storage."""
        storage_path = self.config.get("storage_path", "data/metrics")
        events_dir = os.path.join(storage_path, "anomalies", "events")
        os.makedirs(events_dir, exist_ok=True)
        
        file_path = os.path.join(events_dir, f"{event.id}.json")
        
        with open(file_path, 'w') as f:
            json.dump(event.to_dict(), f, indent=2)
            
        logger.debug(f"Anomaly event {event.id} saved to {file_path}")
    
    async def start_collection(self) -> Dict[str, Any]:
        """Start metric collection."""
        if self.is_collecting:
            return {"status": "already_collecting"}
        
        self.is_collecting = True
        
        # Start scheduled samplers
        await self._start_metric_samplers()
        
        logger.info("Metric collection started")
        
        return {
            "status": "collection_started",
            "active_samplers": len(self.metric_samplers)
        }
    
    async def stop_collection(self) -> Dict[str, Any]:
        """Stop metric collection."""
        if not self.is_collecting:
            return {"status": "not_collecting"}
        
        self.is_collecting = False
        
        # Stop all metric samplers
        for metric_id, task in self.metric_samplers.items():
            if not task.done():
                task.cancel()
                
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        self.metric_samplers.clear()
        
        logger.info("Metric collection stopped")
        
        return {"status": "collection_stopped"}
    
    async def _start_metric_samplers(self) -> None:
        """Start samplers for metrics with sampling intervals."""
        for metric_id, metric in self.metric_definitions.items():
            if metric.sampling_interval is not None and metric.sampling_interval > 0:
                # Skip if already sampling
                if metric_id in self.metric_samplers and not self.metric_samplers[metric_id].done():
                    continue
                
                # Start sampler task
                task = asyncio.create_task(self._sample_metric(metric_id, metric.sampling_interval))
                self.metric_samplers[metric_id] = task
    
    async def _sample_metric(self, metric_id: str, interval: int) -> None:
        """Sample a metric at regular intervals."""
        try:
            while self.is_collecting:
                # Get system metric value
                if metric_id.startswith("system."):
                    value = await self._collect_system_metric(metric_id)
                    if value is not None:
                        await self.record_metric(
                            metric_id=metric_id,
                            value=value,
                            component="system"
                        )
                
                # Wait for next interval
                await asyncio.sleep(interval)
                
        except asyncio.CancelledError:
            logger.debug(f"Metric sampler for {metric_id} canceled")
        except Exception as e:
            logger.error(f"Error in metric sampler for {metric_id}: {str(e)}")
    
    async def _collect_system_metric(self, metric_id: str) -> Optional[float]:
        """Collect a system metric value."""
        try:
            if metric_id == "system.cpu.usage":
                return psutil.cpu_percent(interval=1)
                
            elif metric_id == "system.memory.usage":
                memory = psutil.virtual_memory()
                return memory.percent
                
            elif metric_id == "system.disk.usage":
                disk = psutil.disk_usage('/')
                return disk.percent
                
            elif metric_id == "system.uptime":
                # Return uptime in seconds
                return time.time() - psutil.boot_time()
                
        except Exception as e:
            logger.error(f"Error collecting system metric {metric_id}: {str(e)}")
            
        return None
    
    async def register_metric(self, 
                           name: str,
                           description: str,
                           type: MetricType,
                           category: MetricCategory,
                           unit: str,
                           priority: MetricPriority = MetricPriority.NORMAL,
                           components: Optional[List[str]] = None,
                           tags: Optional[List[str]] = None,
                           aggregation_method: str = "average",
                           sampling_interval: Optional[int] = None,
                           retention_days: Optional[int] = None) -> MetricDefinition:
        """Register a new metric definition."""
        # Generate ID from name
        metric_id = self._generate_metric_id(name, category)
        
        # Use defaults if not provided
        components = components or []
        tags = tags or []
        retention_days = retention_days or self.config.get("default_retention_days", 30)
        
        # Create metric definition
        metric = MetricDefinition(
            id=metric_id,
            name=name,
            description=description,
            type=type,
            category=category,
            unit=unit,
            priority=priority,
            components=components,
            tags=tags,
            aggregation_method=aggregation_method,
            sampling_interval=sampling_interval,
            retention_days=retention_days
        )
        
        # Store metric definition
        self.metric_definitions[metric_id] = metric
        
        # Save to storage
        await self._save_metric_definition(metric)
        
        # Start sampler if needed
        if self.is_collecting and sampling_interval is not None and sampling_interval > 0:
            task = asyncio.create_task(self._sample_metric(metric_id, sampling_interval))
            self.metric_samplers[metric_id] = task
        
        logger.info(f"Registered metric: {metric_id} ({name})")
        
        return metric
    
    def _generate_metric_id(self, name: str, category: MetricCategory) -> str:
        """Generate a metric ID from name and category."""
        # Convert name to snake_case
        name_snake = re.sub(r'[^a-zA-Z0-9]+', '_', name.lower())
        name_snake = re.sub(r'_+', '_', name_snake)
        
        # Create ID in format category.name
        metric_id = f"{category.value}.{name_snake}"
        
        # Check if ID already exists, append number if needed
        base_id = metric_id
        counter = 1
        while metric_id in self.metric_definitions:
            metric_id = f"{base_id}_{counter}"
            counter += 1
        
        return metric_id
    
    async def record_metric(self,
                         metric_id: str,
                         value: Any,
                         component: str = "",
                         context: Optional[Dict[str, Any]] = None) -> MetricValue:
        """Record a metric value."""
        # Check if metric exists
        if metric_id not in self.metric_definitions:
            raise ValueError(f"Unknown metric ID: {metric_id}")
        
        # Create metric value
        metric_value = MetricValue(
            metric_id=metric_id,
            value=value,
            timestamp=datetime.now().isoformat(),
            component=component,
            context=context or {}
        )
        
        # Add to values list
        self.metric_values[metric_id].append(metric_value)
        
        # Limit list size to avoid memory issues
        max_values_per_metric = self.config.get("max_values_per_metric", 1000)
        if len(self.metric_values[metric_id]) > max_values_per_metric:
            self.metric_values[metric_id] = self.metric_values[metric_id][-max_values_per_metric:]
        
        # Increment batch count and save if batch size reached
        self.batch_count += 1
        batch_size = self.config.get("batch_size", 100)
        if self.batch_count >= batch_size:
            await self._save_metric_values()
            self.batch_count = 0
        
        # Check for anomalies if enabled
        if self.config.get("anomaly_detection_enabled", True):
            await self._check_anomalies(metric_value)
        
        return metric_value
    
    async def register_anomaly_definition(self,
                                       name: str,
                                       description: str,
                                       metric_id: str,
                                       detection_method: str,
                                       parameters: Dict[str, Any],
                                       severity: str = "warning") -> AnomalyDefinition:
        """Register a new anomaly detection definition."""
        # Check if metric exists
        if metric_id not in self.metric_definitions:
            raise ValueError(f"Unknown metric ID: {metric_id}")
        
        # Validate detection method
        valid_methods = ["threshold", "zscore", "mad", "iqr", "custom"]
        if detection_method not in valid_methods:
            raise ValueError(f"Invalid detection method: {detection_method}. Valid methods: {valid_methods}")
        
        # Validate parameters based on method
        self._validate_anomaly_parameters(detection_method, parameters)
        
        # Generate ID
        anomaly_id = f"anomaly_{uuid.uuid4().hex[:8]}"
        
        # Create anomaly definition
        anomaly = AnomalyDefinition(
            id=anomaly_id,
            name=name,
            description=description,
            metric_id=metric_id,
            detection_method=detection_method,
            parameters=parameters,
            severity=severity,
            enabled=True
        )
        
        # Store anomaly definition
        self.anomaly_definitions[anomaly_id] = anomaly
        
        # Save to storage
        await self._save_anomaly_definition(anomaly)
        
        logger.info(f"Registered anomaly definition: {anomaly_id} ({name})")
        
        return anomaly
    
    def _validate_anomaly_parameters(self, method: str, parameters: Dict[str, Any]) -> None:
        """Validate anomaly detection parameters based on method."""
        if method == "threshold":
            if "min" not in parameters and "max" not in parameters:
                raise ValueError("Threshold method requires at least one of 'min' or 'max' parameters")
                
        elif method == "zscore":
            if "threshold" not in parameters:
                raise ValueError("Z-score method requires 'threshold' parameter")
                
        elif method == "mad":
            if "threshold" not in parameters:
                raise ValueError("MAD method requires 'threshold' parameter")
                
        elif method == "iqr":
            if "multiplier" not in parameters:
                raise ValueError("IQR method requires 'multiplier' parameter")
                
        elif method == "custom":
            if "function" not in parameters:
                raise ValueError("Custom method requires 'function' parameter")
    
    async def _check_anomalies(self, metric_value: MetricValue) -> None:
        """Check if a metric value triggers any anomaly detections."""
        metric_id = metric_value.metric_id
        
        # Find anomaly definitions for this metric
        for anomaly_id, anomaly in self.anomaly_definitions.items():
            if not anomaly.enabled:
                continue
                
            if anomaly.metric_id != metric_id:
                continue
            
            # Get historical values for this metric
            values = [v.value for v in self.metric_values.get(metric_id, [])]
            if not values:
                continue
            
            # Detect anomaly based on method
            try:
                is_anomaly, expected_range, deviation = await self._detect_anomaly(
                    anomaly.detection_method,
                    anomaly.parameters,
                    metric_value.value,
                    values
                )
                
                if is_anomaly:
                    # Create anomaly event
                    event_id = f"event_{uuid.uuid4().hex[:8]}"
                    event = AnomalyEvent(
                        id=event_id,
                        anomaly_id=anomaly_id,
                        metric_id=metric_id,
                        timestamp=metric_value.timestamp,
                        value=metric_value.value,
                        expected_range=expected_range,
                        deviation_percentage=deviation,
                        severity=anomaly.severity,
                        component=metric_value.component,
                        context=metric_value.context
                    )
                    
                    # Store event
                    self.anomaly_events[event_id] = event
                    
                    # Save event
                    await self._save_anomaly_event(event)
                    
                    # Notify
                    await self._handle_anomaly_notification(event, anomaly)
                    
                    logger.warning(
                        f"Anomaly detected: {anomaly.name}, metric: {metric_id}, "
                        f"value: {metric_value.value}, expected range: {expected_range}"
                    )
            except Exception as e:
                logger.error(f"Error detecting anomaly {anomaly_id} for metric {metric_id}: {str(e)}")
    
    async def _detect_anomaly(self,
                           method: str,
                           parameters: Dict[str, Any],
                           value: Any,
                           historical_values: List[Any]) -> Tuple[bool, Tuple[float, float], float]:
        """Detect if a value is anomalous using the specified method."""
        if method == "threshold":
            return self._detect_threshold_anomaly(parameters, value)
            
        elif method == "zscore":
            return self._detect_zscore_anomaly(parameters, value, historical_values)
            
        elif method == "mad":
            return self._detect_mad_anomaly(parameters, value, historical_values)
            
        elif method == "iqr":
            return self._detect_iqr_anomaly(parameters, value, historical_values)
            
        elif method == "custom":
            # This would call a custom function
            # For safety, we're not implementing this in the example
            return False, (0, 0), 0
            
        return False, (0, 0), 0
    
    def _detect_threshold_anomaly(self, 
                               parameters: Dict[str, Any], 
                               value: float) -> Tuple[bool, Tuple[float, float], float]:
        """Detect anomaly using threshold method."""
        min_val = parameters.get("min", float('-inf'))
        max_val = parameters.get("max", float('inf'))
        
        is_anomaly = value < min_val or value > max_val
        
        # Calculate expected range and deviation
        expected_range = (min_val, max_val)
        
        if value < min_val:
            deviation = (min_val - value) / abs(min_val) * 100 if min_val != 0 else 100
        elif value > max_val:
            deviation = (value - max_val) / abs(max_val) * 100 if max_val != 0 else 100
        else:
            deviation = 0
            
        return is_anomaly, expected_range, deviation
    
    def _detect_zscore_anomaly(self, 
                            parameters: Dict[str, Any], 
                            value: float, 
                            historical_values: List[float]) -> Tuple[bool, Tuple[float, float], float]:
        """Detect anomaly using Z-score method."""
        threshold = parameters.get("threshold", 3.0)
        
        # Need at least 2 values for standard deviation
        if len(historical_values) < 2:
            return False, (value, value), 0
            
        # Calculate mean and standard deviation
        mean = statistics.mean(historical_values)
        stdev = statistics.stdev(historical_values)
        
        if stdev == 0:
            return False, (mean, mean), 0
            
        # Calculate z-score
        z_score = abs((value - mean) / stdev)
        
        # Determine if anomalous
        is_anomaly = z_score > threshold
        
        # Calculate expected range and deviation
        expected_range = (mean - threshold * stdev, mean + threshold * stdev)
        deviation = (z_score / threshold) * 100
            
        return is_anomaly, expected_range, deviation
    
    def _detect_mad_anomaly(self, 
                         parameters: Dict[str, Any], 
                         value: float, 
                         historical_values: List[float]) -> Tuple[bool, Tuple[float, float], float]:
        """Detect anomaly using Median Absolute Deviation method."""
        threshold = parameters.get("threshold", 3.0)
        
        # Need at least 2 values
        if len(historical_values) < 2:
            return False, (value, value), 0
            
        # Calculate median and MAD
        median = statistics.median(historical_values)
        mad = statistics.median([abs(x - median) for x in historical_values])
        
        if mad == 0:
            return False, (median, median), 0
            
        # Calculate deviation score
        score = abs(value - median) / mad
        
        # Determine if anomalous
        is_anomaly = score > threshold
        
        # Calculate expected range and deviation
        expected_range = (median - threshold * mad, median + threshold * mad)
        deviation = (score / threshold) * 100
            
        return is_anomaly, expected_range, deviation
    
    def _detect_iqr_anomaly(self, 
                         parameters: Dict[str, Any], 
                         value: float, 
                         historical_values: List[float]) -> Tuple[bool, Tuple[float, float], float]:
        """Detect anomaly using Interquartile Range method."""
        multiplier = parameters.get("multiplier", 1.5)
        
        # Need at least 4 values for quartiles
        if len(historical_values) < 4:
            return False, (value, value), 0
            
        # Calculate quartiles
        sorted_values = sorted(historical_values)
        q1_idx = int(len(sorted_values) * 0.25)
        q3_idx = int(len(sorted_values) * 0.75)
        
        q1 = sorted_values[q1_idx]
        q3 = sorted_values[q3_idx]
        
        # Calculate IQR
        iqr = q3 - q1
        
        if iqr == 0:
            return False, (q1, q3), 0
            
        # Calculate bounds
        lower_bound = q1 - multiplier * iqr
        upper_bound = q3 + multiplier * iqr
        
        # Determine if anomalous
        is_anomaly = value < lower_bound or value > upper_bound
        
        # Calculate deviation
        if value < lower_bound:
            deviation = (lower_bound - value) / iqr * 100
        elif value > upper_bound:
            deviation = (value - upper_bound) / iqr * 100
        else:
            deviation = 0
            
        return is_anomaly, (lower_bound, upper_bound), deviation
    
    async def _handle_anomaly_notification(self, event: AnomalyEvent, anomaly: AnomalyDefinition) -> None:
        """Handle notification for detected anomaly."""
        # Check if we have a notification handler
        handler = self.config.get("anomaly_notification_handler")
        if handler:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event, anomaly)
                else:
                    handler(event, anomaly)
            except Exception as e:
                logger.error(f"Error in anomaly notification handler: {str(e)}")
        
        # Log the anomaly
        metric_name = self.metric_definitions[event.metric_id].name if event.metric_id in self.metric_definitions else event.metric_id
        
        log_message = (
            f"ANOMALY DETECTED: {anomaly.name}\n"
            f"Metric: {metric_name} ({event.metric_id})\n"
            f"Value: {event.value}\n"
            f"Expected Range: {event.expected_range}\n"
            f"Deviation: {event.deviation_percentage:.2f}%\n"
            f"Severity: {event.severity}\n"
            f"Component: {event.component or 'N/A'}\n"
            f"Timestamp: {event.timestamp}\n"
        )
        
        if event.severity == "critical":
            logger.critical(log_message)
        elif event.severity == "warning":
            logger.warning(log_message)
        else:
            logger.info(log_message)
            
    async def acknowledge_anomaly(self, event_id: str) -> Dict[str, Any]:
        """Acknowledge an anomaly event."""
        if event_id not in self.anomaly_events:
            raise ValueError(f"Unknown anomaly event ID: {event_id}")
        
        event = self.anomaly_events[event_id]
        event.acknowledged = True
        
        # Save to storage
        await self._save_anomaly_event(event)
        
        return event.to_dict()
    
    async def query_metrics(self, query: MetricQuery) -> Dict[str, Any]:
        """Query metric values based on criteria."""
        # Determine which metrics to include
        metric_ids = set(query.metric_ids or self.metric_definitions.keys())
        
        # Filter by category if specified
        if query.categories:
            category_values = [c.value for c in query.categories]
            category_metrics = {
                metric_id for metric_id, metric in self.metric_definitions.items()
                if metric.category.value in category_values
            }
            metric_ids = metric_ids.intersection(category_metrics)
        
        # Filter by tags if specified
        if query.tags:
            tag_metrics = {
                metric_id for metric_id, metric in self.metric_definitions.items()
                if any(tag in metric.tags for tag in query.tags)
            }
            metric_ids = metric_ids.intersection(tag_metrics)
        
        # Prepare result
        results = []
        
        # Process each metric
        for metric_id in metric_ids:
            # Get metric definition
            if metric_id not in self.metric_definitions:
                continue
                
            metric_def = self.metric_definitions[metric_id]
            
            # Get values for this metric
            values = self.metric_values.get(metric_id, [])
            
            # Filter by component if specified
            if query.components:
                values = [v for v in values if v.component in query.components]
            
            # Filter by time range if specified
            if query.start_time:
                values = [v for v in values if v.timestamp >= query.start_time]
                
            if query.end_time:
                values = [v for v in values if v.timestamp <= query.end_time]
            
            # Sort by timestamp
            values = sorted(values, key=lambda v: v.timestamp)
            
            # Apply limit
            if query.limit > 0:
                values = values[-query.limit:]
            
            # Convert to dictionaries
            value_dicts = [v.to_dict() for v in values]
            
            # Add metric metadata
            result = {
                "metric_id": metric_id,
                "name": metric_def.name,
                "description": metric_def.description,
                "type": metric_def.type.value,
                "category": metric_def.category.value,
                "unit": metric_def.unit,
                "values": value_dicts
            }
            
            # Add aggregations if requested
            if query.aggregation or metric_def.aggregation_method:
                aggregation_method = query.aggregation or metric_def.aggregation_method
                
                if values:
                    try:
                        numeric_values = [float(v.value) for v in values if isinstance(v.value, (int, float))]
                        if numeric_values:
                            if aggregation_method == "average":
                                result["aggregated_value"] = statistics.mean(numeric_values)
                            elif aggregation_method == "sum":
                                result["aggregated_value"] = sum(numeric_values)
                            elif aggregation_method == "min":
                                result["aggregated_value"] = min(numeric_values)
                            elif aggregation_method == "max":
                                result["aggregated_value"] = max(numeric_values)
                            elif aggregation_method == "median":
                                result["aggregated_value"] = statistics.median(numeric_values)
                            elif aggregation_method == "count":
                                result["aggregated_value"] = len(numeric_values)
                    except Exception as e:
                        logger.error(f"Error calculating aggregation for {metric_id}: {str(e)}")
            
            results.append(result)
        
        # Group results if requested
        if query.group_by:
            grouped_results = self._group_results(results, query.group_by)
            return {
                "status": "success",
                "query": {
                    "metric_ids": list(metric_ids),
                    "components": query.components,
                    "start_time": query.start_time,
                    "end_time": query.end_time,
                    "limit": query.limit,
                    "group_by": query.group_by
                },
                "grouped_results": grouped_results,
                "timestamp": datetime.now().isoformat()
            }
        
        return {
            "status": "success",
            "query": {
                "metric_ids": list(metric_ids),
                "components": query.components,
                "start_time": query.start_time,
                "end_time": query.end_time,
                "limit": query.limit
            },
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
    
    def _group_results(self, results: List[Dict[str, Any]], group_by: str) -> Dict[str, List[Dict[str, Any]]]:
        """Group query results by the specified field."""
        grouped = defaultdict(list)
        
        if group_by == "category":
            for result in results:
                grouped[result["category"]].append(result)
        elif group_by == "component":
            # Group by component requires checking each value
            for result in results:
                # Get unique components in this metric's values
                components = {v.get("component", "") for v in result.get("values", [])}
                
                for component in components:
                    # Create a copy of the result with only values for this component
                    component_result = result.copy()
                    component_result["values"] = [
                        v for v in result.get("values", [])
                        if v.get("component", "") == component
                    ]
                    grouped[component or "unknown"].append(component_result)
        else:
            # Default to grouping by metric_id
            for result in results:
                grouped[result["metric_id"]].append(result)
        
        return dict(grouped)
    
    async def get_anomalies(self,
                         metric_id: Optional[str] = None,
                         severity: Optional[str] = None,
                         start_time: Optional[str] = None,
                         end_time: Optional[str] = None,
                         include_acknowledged: bool = False) -> List[Dict[str, Any]]:
        """Get anomaly events, optionally filtered."""
        results = []
        
        for event_id, event in self.anomaly_events.items():
            # Apply filters
            if metric_id and event.metric_id != metric_id:
                continue
                
            if severity and event.severity != severity:
                continue
                
            if start_time and event.timestamp < start_time:
                continue
                
            if end_time and event.timestamp > end_time:
                continue
                
            if not include_acknowledged and event.acknowledged:
                continue
            
            # Add to results
            result = event.to_dict()
            
            # Add metric information
            if event.metric_id in self.metric_definitions:
                metric = self.metric_definitions[event.metric_id]
                result["metric_name"] = metric.name
                result["metric_unit"] = metric.unit
            
            # Add anomaly information
            if event.anomaly_id in self.anomaly_definitions:
                anomaly = self.anomaly_definitions[event.anomaly_id]
                result["anomaly_name"] = anomaly.name
                result["detection_method"] = anomaly.detection_method
            
            results.append(result)
        
        # Sort by timestamp (newest first)
        results.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return results
    
    async def create_metrics_report(self,
                                 categories: Optional[List[MetricCategory]] = None,
                                 start_time: Optional[str] = None,
                                 end_time: Optional[str] = None,
                                 group_by: Optional[str] = None) -> Dict[str, Any]:
        """Create a comprehensive report of metrics."""
        # Query metrics
        query = MetricQuery(
            categories=[c for c in categories] if categories else None,
            start_time=start_time,
            end_time=end_time,
            group_by=group_by
        )
        
        query_result = await self.query_metrics(query)
        
        # Get anomalies in the same period
        anomalies = await self.get_anomalies(
            start_time=start_time,
            end_time=end_time
        )
        
        # Create summary statistics
        summary = {
            "total_metrics": len(query_result["results"]),
            "total_values": sum(len(r["values"]) for r in query_result["results"]),
            "anomalies": len(anomalies),
            "time_range": {
                "start": start_time or min((r["values"][0]["timestamp"] for r in query_result["results"] if r["values"]), default=None),
                "end": end_time or max((r["values"][-1]["timestamp"] for r in query_result["results"] if r["values"]), default=None)
            }
        }
        
        # Count metrics by category
        category_counts = defaultdict(int)
        for result in query_result["results"]:
            category_counts[result["category"]] += 1
            
        summary["categories"] = dict(category_counts)
        
        # Count anomalies by severity
        severity_counts = defaultdict(int)
        for anomaly in anomalies:
            severity_counts[anomaly["severity"]] += 1
            
        summary["anomalies_by_severity"] = dict(severity_counts)
        
        # Create visualizations
        visualizations = {}
        try:
            # Only create visualizations if we have data
            if query_result["results"] and any(r["values"] for r in query_result["results"]):
                # Create time series visualization for each metric
                for result in query_result["results"][:5]:  # Limit to 5 metrics
                    if result["values"]:
                        vis = await self._create_metric_visualization(result)
                        visualizations[result["metric_id"]] = vis
                
                # Create category distribution visualization
                vis = await self._create_category_visualization(query_result["results"])
                visualizations["category_distribution"] = vis
                
                # Create anomaly visualization if there are anomalies
                if anomalies:
                    vis = await self._create_anomaly_visualization(anomalies)
                    visualizations["anomalies"] = vis
        except Exception as e:
            logger.error(f"Error creating visualizations: {str(e)}")
            visualizations["error"] = str(e)
        
        # Build final report
        report = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "summary": summary,
            "visualizations": visualizations,
            "metrics": query_result["results"],
            "anomalies": anomalies
        }
        
        return report
    
    async def _create_metric_visualization(self, metric_result: Dict[str, Any]) -> Dict[str, Any]:
        """Create visualization for a single metric."""
        # Extract data
        metric_id = metric_result["metric_id"]
        metric_name = metric_result["name"]
        unit = metric_result["unit"]
        values = metric_result["values"]
        
        # Create time series plot
        plt.figure(figsize=(10, 5))
        
        # Group by component if multiple components
        components = {v.get("component", "") for v in values}
        
        if len(components) > 1:
            for component in components:
                component_values = [v for v in values if v.get("component", "") == component]
                if component_values:
                    timestamps = [datetime.fromisoformat(v["timestamp"]) for v in component_values]
                    data_values = [v["value"] for v in component_values]
                    plt.plot(timestamps, data_values, label=component or "unknown", marker='o' if len(timestamps) < 10 else None)
            
            plt.legend()
        else:
            timestamps = [datetime.fromisoformat(v["timestamp"]) for v in values]
            data_values = [v["value"] for v in values]
            plt.plot(timestamps, data_values, label=metric_name, marker='o' if len(timestamps) < 10 else None)
        
        plt.title(f"{metric_name} ({metric_id})")
        plt.xlabel("Time")
        plt.ylabel(unit)
        plt.grid(True)
        
        # Convert to base64
        buffer = BytesIO()
        plt.savefig(buffer, format="png")
        plt.close()
        
        image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        return {
            "type": "time_series",
            "image": f"data:image/png;base64,{image_base64}",
            "metric_id": metric_id,
            "metric_name": metric_name
        }
    
    async def _create_category_visualization(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create visualization of metric categories."""
        # Count metrics by category
        category_counts = defaultdict(int)
        for metric in metrics:
            category = metric["category"]
            category_counts[category] += 1
        
        # Create pie chart
        plt.figure(figsize=(8, 8))
        plt.pie(
            list(category_counts.values()),
            labels=list(category_counts.keys()),
            autopct='%1.1f%%',
            startangle=90,
            shadow=True
        )
        plt.axis('equal')
        plt.title('Metrics by Category')
        
        # Convert to base64
        buffer = BytesIO()
        plt.savefig(buffer, format="png")
        plt.close()
        
        image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        return {
            "type": "category_distribution",
            "image": f"data:image/png;base64,{image_base64}"
        }
    
    async def _create_anomaly_visualization(self, anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create visualization of anomalies."""
        # Group anomalies by metric
        metric_anomalies = defaultdict(list)
        for anomaly in anomalies:
            metric_id = anomaly["metric_id"]
            metric_name = anomaly.get("metric_name", metric_id)
            metric_anomalies[metric_name].append(anomaly)
        
        # Create bar chart
        plt.figure(figsize=(10, 6))
        metrics = list(metric_anomalies.keys())
        counts = [len(anomalies) for anomalies in metric_anomalies.values()]
        
        # Sort by count
        sorted_data = sorted(zip(metrics, counts), key=lambda x: x[1], reverse=True)
        metrics = [m for m, _ in sorted_data]
        counts = [c for _, c in sorted_data]
        
        # Limit to top 10
        if len(metrics) > 10:
            metrics = metrics[:10]
            counts = counts[:10]
        
        # Create plot
        bars = plt.bar(metrics, counts)
        
        # Color by count
        for i, bar in enumerate(bars):
            if counts[i] >= 5:
                bar.set_color('red')
            elif counts[i] >= 3:
                bar.set_color('orange')
            else:
                bar.set_color('blue')
        
        plt.title('Anomalies by Metric')
        plt.xlabel('Metric')
        plt.ylabel('Number of Anomalies')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        # Convert to base64
        buffer = BytesIO()
        plt.savefig(buffer, format="png")
        plt.close()
        
        image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        return {
            "type": "anomaly_distribution",
            "image": f"data:image/png;base64,{image_base64}"
        } 