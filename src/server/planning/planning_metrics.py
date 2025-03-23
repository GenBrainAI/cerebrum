"""
Planning Engine Metrics Collector.

This module provides functionality for collecting, analyzing, and reporting
metrics related to planning activities across different planning components.
"""

from typing import Dict, List, Optional, Any, Union, Tuple
import logging
from enum import Enum
from datetime import datetime, timedelta
import uuid
import json
import os
import statistics
from dataclasses import dataclass, field, asdict

from src.server.planning.planning_engine import (
    PlanningEngine,
    IntegratedPlan,
    PlanningMetrics,
    PlanType,
    PlanVersion
)

logger = logging.getLogger(__name__)

class MetricType(Enum):
    """Types of metrics that can be collected."""
    TIME = "time"
    COMPLEXITY = "complexity"
    CONFIDENCE = "confidence"
    RESOURCE_EFFICIENCY = "resource_efficiency"
    ADAPTABILITY = "adaptability"
    CUSTOM = "custom"

@dataclass
class MetricSnapshot:
    """Snapshot of a specific metric at a point in time."""
    plan_id: str
    metric_type: MetricType
    value: float
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MetricTrend:
    """Trend analysis for a specific metric over time."""
    metric_type: MetricType
    data_points: List[Tuple[str, float]]  # [(timestamp, value), ...]
    start_time: str
    end_time: str
    mean: float
    median: float
    min_value: float
    max_value: float
    standard_deviation: float
    trend_direction: str  # "increasing", "decreasing", "stable"
    rate_of_change: float
    metadata: Dict[str, Any] = field(default_factory=dict)

class PlanningMetricsCollector:
    """
    Collects, stores, and analyzes metrics related to planning activities.
    
    This class provides functionality for tracking the performance of the
    planning engine and its components over time, allowing for historical
    analysis and optimization.
    """
    
    def __init__(self, storage_path: str = "data/planning/metrics"):
        """
        Initialize the Planning Metrics Collector.
        
        Args:
            storage_path: Path to store metrics data
        """
        self.storage_path = storage_path
        self.metrics_path = os.path.join(storage_path, "snapshots")
        self.trends_path = os.path.join(storage_path, "trends")
        
        # Create directories if they don't exist
        os.makedirs(self.metrics_path, exist_ok=True)
        os.makedirs(self.trends_path, exist_ok=True)
        
        # In-memory cache of metrics
        self.metrics_cache: Dict[str, Dict[str, List[MetricSnapshot]]] = {}
        self.trends_cache: Dict[str, Dict[MetricType, MetricTrend]] = {}
        
        # Load existing metrics
        self._load_metrics()
    
    def _load_metrics(self):
        """Load existing metrics from storage."""
        # Load metrics snapshots
        try:
            if os.path.exists(os.path.join(self.metrics_path, "index.json")):
                with open(os.path.join(self.metrics_path, "index.json"), "r") as f:
                    metrics_index = json.load(f)
                    
                for plan_id, metrics_files in metrics_index.items():
                    self.metrics_cache[plan_id] = {}
                    
                    for metric_type, file_path in metrics_files.items():
                        try:
                            with open(os.path.join(self.metrics_path, file_path), "r") as mf:
                                snapshots_data = json.load(mf)
                                
                                # Convert to MetricSnapshot objects
                                snapshots = []
                                for data in snapshots_data:
                                    data["metric_type"] = MetricType(data["metric_type"])
                                    snapshots.append(MetricSnapshot(**data))
                                
                                # Group by metric type
                                metric_enum = MetricType(metric_type)
                                self.metrics_cache[plan_id][metric_enum] = snapshots
                        except Exception as e:
                            logger.error(f"Error loading metrics file {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error loading metrics index: {e}")
            self.metrics_cache = {}
        
        # Load trends
        try:
            if os.path.exists(os.path.join(self.trends_path, "index.json")):
                with open(os.path.join(self.trends_path, "index.json"), "r") as f:
                    trends_index = json.load(f)
                    
                for plan_id, trends_files in trends_index.items():
                    self.trends_cache[plan_id] = {}
                    
                    for metric_type, file_path in trends_files.items():
                        try:
                            with open(os.path.join(self.trends_path, file_path), "r") as tf:
                                trend_data = json.load(tf)
                                
                                # Convert to MetricTrend object
                                trend_data["metric_type"] = MetricType(trend_data["metric_type"])
                                self.trends_cache[plan_id][MetricType(metric_type)] = MetricTrend(**trend_data)
                        except Exception as e:
                            logger.error(f"Error loading trend file {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error loading trends index: {e}")
            self.trends_cache = {}
    
    def _save_metrics_index(self):
        """Save metrics index to storage."""
        metrics_index = {}
        
        for plan_id, metrics_by_type in self.metrics_cache.items():
            metrics_index[plan_id] = {}
            
            for metric_type, _ in metrics_by_type.items():
                file_name = f"{plan_id}_{metric_type.value}.json"
                metrics_index[plan_id][metric_type.value] = file_name
        
        with open(os.path.join(self.metrics_path, "index.json"), "w") as f:
            json.dump(metrics_index, f, indent=2)
    
    def _save_trends_index(self):
        """Save trends index to storage."""
        trends_index = {}
        
        for plan_id, trends_by_type in self.trends_cache.items():
            trends_index[plan_id] = {}
            
            for metric_type, _ in trends_by_type.items():
                file_name = f"{plan_id}_{metric_type.value}_trend.json"
                trends_index[plan_id][metric_type.value] = file_name
        
        with open(os.path.join(self.trends_path, "index.json"), "w") as f:
            json.dump(trends_index, f, indent=2)
    
    def _save_metric_snapshots(self, plan_id: str, metric_type: MetricType):
        """
        Save metric snapshots for a specific plan and metric type.
        
        Args:
            plan_id: ID of the plan
            metric_type: Type of metric
        """
        if plan_id not in self.metrics_cache or metric_type not in self.metrics_cache[plan_id]:
            return
        
        snapshots = self.metrics_cache[plan_id][metric_type]
        file_name = f"{plan_id}_{metric_type.value}.json"
        file_path = os.path.join(self.metrics_path, file_name)
        
        # Convert snapshots to dictionaries
        snapshots_dict = []
        for snapshot in snapshots:
            snapshot_dict = asdict(snapshot)
            snapshot_dict["metric_type"] = snapshot_dict["metric_type"].value
            snapshots_dict.append(snapshot_dict)
        
        with open(file_path, "w") as f:
            json.dump(snapshots_dict, f, indent=2)
    
    def _save_metric_trend(self, plan_id: str, metric_type: MetricType):
        """
        Save metric trend for a specific plan and metric type.
        
        Args:
            plan_id: ID of the plan
            metric_type: Type of metric
        """
        if plan_id not in self.trends_cache or metric_type not in self.trends_cache[plan_id]:
            return
        
        trend = self.trends_cache[plan_id][metric_type]
        file_name = f"{plan_id}_{metric_type.value}_trend.json"
        file_path = os.path.join(self.trends_path, file_name)
        
        # Convert trend to dictionary
        trend_dict = asdict(trend)
        trend_dict["metric_type"] = trend_dict["metric_type"].value
        
        with open(file_path, "w") as f:
            json.dump(trend_dict, f, indent=2)
    
    def collect_metrics(self, plan_id: str, metrics: PlanningMetrics, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Collect metrics for a plan and add to storage.
        
        Args:
            plan_id: ID of the plan
            metrics: Planning metrics to collect
            context: Additional context information
            
        Returns:
            Dictionary with snapshot IDs for each metric type
        """
        if not metrics:
            return {}
            
        context = context or {}
        timestamp = datetime.now().isoformat()
        
        # Initialize plan in cache if not present
        if plan_id not in self.metrics_cache:
            self.metrics_cache[plan_id] = {}
        
        # Create snapshots for each metric type
        snapshot_ids = {}
        
        # Planning time
        time_snapshot = MetricSnapshot(
            plan_id=plan_id,
            metric_type=MetricType.TIME,
            value=metrics.planning_time,
            timestamp=timestamp,
            context=context,
            metadata={"metric_source": "planning_metrics"}
        )
        if MetricType.TIME not in self.metrics_cache[plan_id]:
            self.metrics_cache[plan_id][MetricType.TIME] = []
        self.metrics_cache[plan_id][MetricType.TIME].append(time_snapshot)
        snapshot_ids["time"] = time_snapshot.id
        
        # Complexity score
        complexity_snapshot = MetricSnapshot(
            plan_id=plan_id,
            metric_type=MetricType.COMPLEXITY,
            value=metrics.complexity_score,
            timestamp=timestamp,
            context=context,
            metadata={"metric_source": "planning_metrics"}
        )
        if MetricType.COMPLEXITY not in self.metrics_cache[plan_id]:
            self.metrics_cache[plan_id][MetricType.COMPLEXITY] = []
        self.metrics_cache[plan_id][MetricType.COMPLEXITY].append(complexity_snapshot)
        snapshot_ids["complexity"] = complexity_snapshot.id
        
        # Confidence score
        confidence_snapshot = MetricSnapshot(
            plan_id=plan_id,
            metric_type=MetricType.CONFIDENCE,
            value=metrics.confidence_score,
            timestamp=timestamp,
            context=context,
            metadata={"metric_source": "planning_metrics"}
        )
        if MetricType.CONFIDENCE not in self.metrics_cache[plan_id]:
            self.metrics_cache[plan_id][MetricType.CONFIDENCE] = []
        self.metrics_cache[plan_id][MetricType.CONFIDENCE].append(confidence_snapshot)
        snapshot_ids["confidence"] = confidence_snapshot.id
        
        # Resource efficiency
        efficiency_snapshot = MetricSnapshot(
            plan_id=plan_id,
            metric_type=MetricType.RESOURCE_EFFICIENCY,
            value=metrics.resource_efficiency,
            timestamp=timestamp,
            context=context,
            metadata={"metric_source": "planning_metrics"}
        )
        if MetricType.RESOURCE_EFFICIENCY not in self.metrics_cache[plan_id]:
            self.metrics_cache[plan_id][MetricType.RESOURCE_EFFICIENCY] = []
        self.metrics_cache[plan_id][MetricType.RESOURCE_EFFICIENCY].append(efficiency_snapshot)
        snapshot_ids["resource_efficiency"] = efficiency_snapshot.id
        
        # Adaptability score
        adaptability_snapshot = MetricSnapshot(
            plan_id=plan_id,
            metric_type=MetricType.ADAPTABILITY,
            value=metrics.adaptability_score,
            timestamp=timestamp,
            context=context,
            metadata={"metric_source": "planning_metrics"}
        )
        if MetricType.ADAPTABILITY not in self.metrics_cache[plan_id]:
            self.metrics_cache[plan_id][MetricType.ADAPTABILITY] = []
        self.metrics_cache[plan_id][MetricType.ADAPTABILITY].append(adaptability_snapshot)
        snapshot_ids["adaptability"] = adaptability_snapshot.id
        
        # Save metrics to storage
        self._save_metrics_index()
        for metric_type in self.metrics_cache[plan_id].keys():
            self._save_metric_snapshots(plan_id, metric_type)
        
        # Update trends
        self.update_trends(plan_id)
        
        return snapshot_ids
    
    def collect_custom_metric(
        self,
        plan_id: str,
        metric_name: str,
        value: float,
        context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Collect a custom metric for a plan.
        
        Args:
            plan_id: ID of the plan
            metric_name: Name of the custom metric
            value: Value of the metric
            context: Additional context information
            metadata: Additional metadata
            
        Returns:
            Snapshot ID
        """
        context = context or {}
        metadata = metadata or {}
        metadata["metric_name"] = metric_name
        timestamp = datetime.now().isoformat()
        
        # Initialize plan in cache if not present
        if plan_id not in self.metrics_cache:
            self.metrics_cache[plan_id] = {}
        
        # Create snapshot for custom metric
        snapshot = MetricSnapshot(
            plan_id=plan_id,
            metric_type=MetricType.CUSTOM,
            value=value,
            timestamp=timestamp,
            context=context,
            metadata=metadata
        )
        
        if MetricType.CUSTOM not in self.metrics_cache[plan_id]:
            self.metrics_cache[plan_id][MetricType.CUSTOM] = []
        
        self.metrics_cache[plan_id][MetricType.CUSTOM].append(snapshot)
        
        # Save metrics to storage
        self._save_metrics_index()
        self._save_metric_snapshots(plan_id, MetricType.CUSTOM)
        
        return snapshot.id
    
    def update_trends(self, plan_id: str) -> Dict[MetricType, MetricTrend]:
        """
        Update trend analysis for all metrics of a plan.
        
        Args:
            plan_id: ID of the plan
            
        Returns:
            Dictionary of metric trends
        """
        if plan_id not in self.metrics_cache:
            return {}
        
        # Initialize trends cache if not present
        if plan_id not in self.trends_cache:
            self.trends_cache[plan_id] = {}
        
        trends = {}
        
        # Update trends for each metric type
        for metric_type, snapshots in self.metrics_cache[plan_id].items():
            if not snapshots:
                continue
            
            # Sort snapshots by timestamp
            sorted_snapshots = sorted(snapshots, key=lambda s: s.timestamp)
            
            # Extract timestamps and values
            data_points = [(s.timestamp, s.value) for s in sorted_snapshots]
            values = [s.value for s in sorted_snapshots]
            
            # Calculate statistics
            mean = statistics.mean(values)
            median = statistics.median(values)
            min_value = min(values)
            max_value = max(values)
            std_dev = statistics.stdev(values) if len(values) > 1 else 0.0
            
            # Determine trend direction and rate of change
            if len(values) < 2:
                trend_direction = "stable"
                rate_of_change = 0.0
            else:
                # Simple linear regression slope for rate of change
                n = len(values)
                indices = list(range(n))
                sum_xy = sum(i * values[i] for i in range(n))
                sum_x = sum(indices)
                sum_y = sum(values)
                sum_x2 = sum(i * i for i in range(n))
                
                # Calculate slope
                slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
                
                # Determine direction
                if abs(slope) < 0.001:
                    trend_direction = "stable"
                elif slope > 0:
                    trend_direction = "increasing"
                else:
                    trend_direction = "decreasing"
                
                rate_of_change = slope
            
            # Create trend object
            trend = MetricTrend(
                metric_type=metric_type,
                data_points=data_points,
                start_time=sorted_snapshots[0].timestamp,
                end_time=sorted_snapshots[-1].timestamp,
                mean=mean,
                median=median,
                min_value=min_value,
                max_value=max_value,
                standard_deviation=std_dev,
                trend_direction=trend_direction,
                rate_of_change=rate_of_change,
                metadata={
                    "snapshot_count": len(snapshots),
                    "last_updated": datetime.now().isoformat()
                }
            )
            
            # Update trends cache
            self.trends_cache[plan_id][metric_type] = trend
            trends[metric_type] = trend
            
            # Save trend to storage
            self._save_metric_trend(plan_id, metric_type)
        
        # Save trends index
        self._save_trends_index()
        
        return trends
    
    def get_metric_snapshots(
        self,
        plan_id: str,
        metric_type: MetricType,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100
    ) -> List[MetricSnapshot]:
        """
        Get metric snapshots for a plan.
        
        Args:
            plan_id: ID of the plan
            metric_type: Type of metric
            start_time: Start time for filtering (ISO format)
            end_time: End time for filtering (ISO format)
            limit: Maximum number of snapshots to return
            
        Returns:
            List of metric snapshots
        """
        if plan_id not in self.metrics_cache or metric_type not in self.metrics_cache[plan_id]:
            return []
        
        snapshots = self.metrics_cache[plan_id][metric_type]
        
        # Apply time filters if specified
        if start_time or end_time:
            filtered_snapshots = []
            
            for snapshot in snapshots:
                if start_time and snapshot.timestamp < start_time:
                    continue
                if end_time and snapshot.timestamp > end_time:
                    continue
                filtered_snapshots.append(snapshot)
            
            snapshots = filtered_snapshots
        
        # Sort by timestamp (newest first) and apply limit
        return sorted(snapshots, key=lambda s: s.timestamp, reverse=True)[:limit]
    
    def get_metric_trend(self, plan_id: str, metric_type: MetricType) -> Optional[MetricTrend]:
        """
        Get trend analysis for a specific metric of a plan.
        
        Args:
            plan_id: ID of the plan
            metric_type: Type of metric
            
        Returns:
            Metric trend or None if not found
        """
        if plan_id not in self.trends_cache or metric_type not in self.trends_cache[plan_id]:
            return None
        
        return self.trends_cache[plan_id][metric_type]
    
    def get_all_trends(self, plan_id: str) -> Dict[MetricType, MetricTrend]:
        """
        Get all trend analyses for a plan.
        
        Args:
            plan_id: ID of the plan
            
        Returns:
            Dictionary of metric trends
        """
        if plan_id not in self.trends_cache:
            return {}
        
        return self.trends_cache[plan_id]
    
    def get_cross_plan_metrics(
        self,
        metric_type: MetricType,
        plan_ids: Optional[List[str]] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> Dict[str, List[MetricSnapshot]]:
        """
        Get metrics of a specific type across multiple plans.
        
        Args:
            metric_type: Type of metric
            plan_ids: List of plan IDs (all plans if None)
            start_time: Start time for filtering (ISO format)
            end_time: End time for filtering (ISO format)
            
        Returns:
            Dictionary mapping plan IDs to lists of metric snapshots
        """
        result = {}
        
        # Determine which plans to include
        if plan_ids:
            target_plans = [p for p in plan_ids if p in self.metrics_cache]
        else:
            target_plans = list(self.metrics_cache.keys())
        
        # Collect metrics for each plan
        for plan_id in target_plans:
            if metric_type in self.metrics_cache[plan_id]:
                snapshots = self.metrics_cache[plan_id][metric_type]
                
                # Apply time filters if specified
                if start_time or end_time:
                    filtered_snapshots = []
                    
                    for snapshot in snapshots:
                        if start_time and snapshot.timestamp < start_time:
                            continue
                        if end_time and snapshot.timestamp > end_time:
                            continue
                        filtered_snapshots.append(snapshot)
                    
                    snapshots = filtered_snapshots
                
                if snapshots:
                    result[plan_id] = snapshots
        
        return result
    
    def generate_metrics_report(
        self,
        plan_id: str,
        include_trends: bool = True
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive report of metrics for a plan.
        
        Args:
            plan_id: ID of the plan
            include_trends: Whether to include trend analysis
            
        Returns:
            Report dictionary
        """
        if plan_id not in self.metrics_cache:
            return {"error": "Plan not found"}
        
        report = {
            "plan_id": plan_id,
            "report_time": datetime.now().isoformat(),
            "metrics": {},
            "trends": {} if include_trends else None
        }
        
        # Include latest snapshot for each metric type
        for metric_type, snapshots in self.metrics_cache[plan_id].items():
            if not snapshots:
                continue
                
            # Get latest snapshot
            latest = max(snapshots, key=lambda s: s.timestamp)
            
            # Add to report
            report["metrics"][metric_type.value] = {
                "latest_value": latest.value,
                "timestamp": latest.timestamp,
                "snapshot_count": len(snapshots)
            }
            
            # Include custom metric names if applicable
            if metric_type == MetricType.CUSTOM:
                custom_metrics = {}
                for snapshot in snapshots:
                    metric_name = snapshot.metadata.get("metric_name", "unknown")
                    if metric_name not in custom_metrics:
                        custom_metrics[metric_name] = []
                    custom_metrics[metric_name].append(snapshot.value)
                
                report["metrics"]["custom_metrics"] = {
                    name: {
                        "count": len(values),
                        "latest": values[-1] if values else None,
                        "average": sum(values) / len(values) if values else None
                    }
                    for name, values in custom_metrics.items()
                }
        
        # Include trends if requested
        if include_trends and plan_id in self.trends_cache:
            for metric_type, trend in self.trends_cache[plan_id].items():
                report["trends"][metric_type.value] = {
                    "mean": trend.mean,
                    "median": trend.median,
                    "min": trend.min_value,
                    "max": trend.max_value,
                    "std_dev": trend.standard_deviation,
                    "trend_direction": trend.trend_direction,
                    "rate_of_change": trend.rate_of_change,
                    "data_points": len(trend.data_points)
                }
        
        return report
    
    def compare_plans(
        self,
        plan_ids: List[str],
        metric_types: Optional[List[MetricType]] = None
    ) -> Dict[str, Any]:
        """
        Compare metrics across multiple plans.
        
        Args:
            plan_ids: List of plan IDs to compare
            metric_types: List of metric types to compare (all if None)
            
        Returns:
            Comparison report
        """
        if not plan_ids:
            return {"error": "No plans specified"}
        
        # Filter to existing plans
        existing_plans = [p for p in plan_ids if p in self.metrics_cache]
        if not existing_plans:
            return {"error": "None of the specified plans found"}
        
        # Determine metric types to include
        if not metric_types:
            # Find common metric types across all plans
            common_types = set()
            first = True
            
            for plan_id in existing_plans:
                if first:
                    common_types = set(self.metrics_cache[plan_id].keys())
                    first = False
                else:
                    common_types &= set(self.metrics_cache[plan_id].keys())
            
            metric_types = list(common_types)
        else:
            # Filter to existing metric types
            metric_types = [
                mt for mt in metric_types
                if any(mt in self.metrics_cache[p] for p in existing_plans)
            ]
        
        if not metric_types:
            return {"error": "No common metrics found"}
        
        # Create comparison report
        report = {
            "plans": existing_plans,
            "comparison_time": datetime.now().isoformat(),
            "metrics": {},
            "rankings": {}
        }
        
        # Collect latest metrics for each plan
        for metric_type in metric_types:
            report["metrics"][metric_type.value] = {}
            plan_values = []
            
            for plan_id in existing_plans:
                if metric_type in self.metrics_cache[plan_id] and self.metrics_cache[plan_id][metric_type]:
                    # Get latest snapshot
                    latest = max(self.metrics_cache[plan_id][metric_type], key=lambda s: s.timestamp)
                    
                    report["metrics"][metric_type.value][plan_id] = {
                        "value": latest.value,
                        "timestamp": latest.timestamp
                    }
                    
                    plan_values.append((plan_id, latest.value))
            
            # Create rankings for this metric
            if plan_values:
                # Sort by value (descending)
                sorted_values = sorted(plan_values, key=lambda x: x[1], reverse=True)
                report["rankings"][metric_type.value] = [
                    {"plan_id": pv[0], "value": pv[1], "rank": i + 1}
                    for i, pv in enumerate(sorted_values)
                ]
        
        # Calculate overall ranking
        overall_ranks = {plan_id: 0 for plan_id in existing_plans}
        rank_counts = {plan_id: 0 for plan_id in existing_plans}
        
        for metric_type in metric_types:
            if metric_type.value in report["rankings"]:
                for ranking in report["rankings"][metric_type.value]:
                    plan_id = ranking["plan_id"]
                    overall_ranks[plan_id] += ranking["rank"]
                    rank_counts[plan_id] += 1
        
        # Calculate average rank for each plan
        avg_ranks = []
        for plan_id in existing_plans:
            if rank_counts[plan_id] > 0:
                avg_rank = overall_ranks[plan_id] / rank_counts[plan_id]
                avg_ranks.append((plan_id, avg_rank))
        
        # Sort by average rank (ascending)
        sorted_ranks = sorted(avg_ranks, key=lambda x: x[1])
        report["overall_ranking"] = [
            {"plan_id": sr[0], "average_rank": sr[1], "rank": i + 1}
            for i, sr in enumerate(sorted_ranks)
        ]
        
        return report 