"""
Tests for the MetricsCollector module.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import os
import tempfile
import json
import asyncio
from datetime import datetime, timedelta
import uuid

from src.server.observability.metrics_monitoring import (
    MetricType, MetricCategory, MetricPriority, MetricDefinition,
    MetricValue, MetricQuery, AnomalyDefinition, AnomalyEvent,
    MetricsCollector
)

@pytest.fixture
def metrics_collector():
    """Create MetricsCollector instance for testing."""
    # Use temp directory for storage
    temp_dir = tempfile.mkdtemp()
    
    return MetricsCollector(
        config={
            "storage_path": temp_dir,
            "default_retention_days": 30,
            "batch_size": 5,  # Small for testing
            "sampling_enabled": True,
            "anomaly_detection_enabled": True
        }
    )

class TestMetricsCollector:
    """Test suite for MetricsCollector."""
    
    @pytest.mark.asyncio
    async def test_register_metric(self, metrics_collector):
        """Test metric registration."""
        metric = await metrics_collector.register_metric(
            name="Test Metric",
            description="A test metric",
            type=MetricType.GAUGE,
            category=MetricCategory.PERFORMANCE,
            unit="ms",
            priority=MetricPriority.HIGH,
            tags=["test", "performance"]
        )
        
        assert metric.name == "Test Metric"
        assert metric.type == MetricType.GAUGE
        assert metric.category == MetricCategory.PERFORMANCE
        assert metric.unit == "ms"
        assert metric.priority == MetricPriority.HIGH
        assert "test" in metric.tags
        assert metric.id in metrics_collector.metric_definitions
    
    @pytest.mark.asyncio
    async def test_record_metric(self, metrics_collector):
        """Test recording metric values."""
        # Register metric
        metric = await metrics_collector.register_metric(
            name="Response Time",
            description="API response time",
            type=MetricType.HISTOGRAM,
            category=MetricCategory.PERFORMANCE,
            unit="ms"
        )
        
        # Record values
        value1 = await metrics_collector.record_metric(
            metric_id=metric.id,
            value=50.0,
            component="api",
            context={"endpoint": "/users"}
        )
        
        value2 = await metrics_collector.record_metric(
            metric_id=metric.id,
            value=75.0,
            component="api",
            context={"endpoint": "/orders"}
        )
        
        # Check values were recorded
        assert len(metrics_collector.metric_values[metric.id]) == 2
        assert metrics_collector.metric_values[metric.id][0].value == 50.0
        assert metrics_collector.metric_values[metric.id][1].value == 75.0
        assert metrics_collector.metric_values[metric.id][0].component == "api"
        assert metrics_collector.metric_values[metric.id][0].context["endpoint"] == "/users"
    
    @pytest.mark.asyncio
    async def test_query_metrics(self, metrics_collector):
        """Test querying metrics."""
        # Register metrics
        metric1 = await metrics_collector.register_metric(
            name="CPU Usage",
            description="CPU usage percentage",
            type=MetricType.GAUGE,
            category=MetricCategory.SYSTEM,
            unit="percent",
            tags=["system"]
        )
        
        metric2 = await metrics_collector.register_metric(
            name="Memory Usage",
            description="Memory usage percentage",
            type=MetricType.GAUGE,
            category=MetricCategory.SYSTEM,
            unit="percent",
            tags=["system"]
        )
        
        metric3 = await metrics_collector.register_metric(
            name="API Latency",
            description="API response latency",
            type=MetricType.HISTOGRAM,
            category=MetricCategory.PERFORMANCE,
            unit="ms",
            tags=["api"]
        )
        
        # Record values
        for i in range(5):
            await metrics_collector.record_metric(
                metric_id=metric1.id,
                value=40.0 + i * 5,
                component="system"
            )
            
            await metrics_collector.record_metric(
                metric_id=metric2.id,
                value=60.0 + i * 2,
                component="system"
            )
            
            await metrics_collector.record_metric(
                metric_id=metric3.id,
                value=100.0 + i * 20,
                component="api"
            )
        
        # Query all metrics
        query_all = MetricQuery()
        result_all = await metrics_collector.query_metrics(query_all)
        
        assert result_all["status"] == "success"
        # The test expected 3 metrics, but MetricsCollector also registers built-in metrics
        assert len(result_all["results"]) >= 3
        
        # Query by specific metric IDs
        query_specific = MetricQuery(
            metric_ids=[metric1.id, metric2.id, metric3.id]
        )
        result_specific = await metrics_collector.query_metrics(query_specific)
        assert len(result_specific["results"]) == 3
        
        # Query by category
        query_system = MetricQuery(
            categories=[MetricCategory.SYSTEM]
        )
        result_system = await metrics_collector.query_metrics(query_system)
        
        assert len(result_system["results"]) >= 2
        assert all(r["category"] == "system" for r in result_system["results"])
        
        # Query by tag
        query_api = MetricQuery(
            tags=["api"]
        )
        result_api = await metrics_collector.query_metrics(query_api)
        
        assert len(result_api["results"]) >= 1
        assert metric3.id in [r["metric_id"] for r in result_api["results"]]
        
        # Query with limit
        query_limit = MetricQuery(
            metric_ids=[metric1.id],
            limit=3
        )
        result_limit = await metrics_collector.query_metrics(query_limit)
        
        assert len(result_limit["results"]) == 1
        assert len(result_limit["results"][0]["values"]) == 3
        
        # Query with aggregation
        query_agg = MetricQuery(
            metric_ids=[metric1.id],
            aggregation="average"
        )
        result_agg = await metrics_collector.query_metrics(query_agg)
        
        assert "aggregated_value" in result_agg["results"][0]
        assert result_agg["results"][0]["aggregated_value"] == 50.0  # Average of 40, 45, 50, 55, 60
    
    @pytest.mark.asyncio
    async def test_anomaly_detection(self, metrics_collector):
        """Test anomaly detection."""
        # Register metric
        metric = await metrics_collector.register_metric(
            name="Request Duration",
            description="API request duration",
            type=MetricType.HISTOGRAM,
            category=MetricCategory.PERFORMANCE,
            unit="ms"
        )
        
        # Register anomaly definition with threshold
        anomaly = await metrics_collector.register_anomaly_definition(
            name="High Request Duration",
            description="Detects unusually high request durations",
            metric_id=metric.id,
            detection_method="threshold",
            parameters={"max": 200.0},
            severity="warning"
        )
        
        # Record normal values
        for i in range(5):
            await metrics_collector.record_metric(
                metric_id=metric.id,
                value=100.0 + i * 10,
                component="api"
            )
        
        # No anomalies yet
        anomalies = await metrics_collector.get_anomalies()
        assert len(anomalies) == 0
        
        # Record anomalous value
        await metrics_collector.record_metric(
            metric_id=metric.id,
            value=250.0,
            component="api"
        )
        
        # Should have detected anomaly
        anomalies = await metrics_collector.get_anomalies()
        assert len(anomalies) == 1
        assert anomalies[0]["metric_id"] == metric.id
        assert anomalies[0]["value"] == 250.0
        assert anomalies[0]["severity"] == "warning"
        
        # Acknowledge anomaly
        await metrics_collector.acknowledge_anomaly(anomalies[0]["id"])
        
        # Should not appear in unacknowledged anomalies
        unacked_anomalies = await metrics_collector.get_anomalies(include_acknowledged=False)
        assert len(unacked_anomalies) == 0
        
        # But should appear when including acknowledged
        all_anomalies = await metrics_collector.get_anomalies(include_acknowledged=True)
        assert len(all_anomalies) == 1
    
    @pytest.mark.asyncio
    async def test_zscore_anomaly_detection(self, metrics_collector):
        """Test Z-score anomaly detection."""
        # Register metric
        metric = await metrics_collector.register_metric(
            name="Page Load Time",
            description="Page load time",
            type=MetricType.HISTOGRAM,
            category=MetricCategory.PERFORMANCE,
            unit="ms"
        )
        
        # Register anomaly definition with z-score
        anomaly = await metrics_collector.register_anomaly_definition(
            name="Unusual Page Load Time",
            description="Detects statistically unusual page load times",
            metric_id=metric.id,
            detection_method="zscore",
            parameters={"threshold": 2.0},
            severity="warning"
        )
        
        # Record normal values with some variation
        values = [100, 105, 95, 110, 90, 105, 100]
        for value in values:
            await metrics_collector.record_metric(
                metric_id=metric.id,
                value=value,
                component="frontend"
            )
        
        # No anomalies yet (within 2 standard deviations)
        anomalies = await metrics_collector.get_anomalies()
        assert len(anomalies) == 0
        
        # Record anomalous value (much higher than others)
        await metrics_collector.record_metric(
            metric_id=metric.id,
            value=200.0,  # Well outside normal range
            component="frontend"
        )
        
        # Should have detected anomaly
        anomalies = await metrics_collector.get_anomalies()
        assert len(anomalies) == 1
        assert anomalies[0]["metric_id"] == metric.id
        assert anomalies[0]["value"] == 200.0
    
    @pytest.mark.asyncio
    async def test_collection_start_stop(self, metrics_collector):
        """Test starting and stopping metric collection."""
        # Start collection
        result = await metrics_collector.start_collection()
        assert result["status"] == "collection_started"
        assert metrics_collector.is_collecting
        
        # Wait briefly for samplers to start
        await asyncio.sleep(0.1)
        
        # Should have some system metric samplers
        assert len(metrics_collector.metric_samplers) > 0
        
        # Stop collection
        stop_result = await metrics_collector.stop_collection()
        assert stop_result["status"] == "collection_stopped"
        assert not metrics_collector.is_collecting
        assert len(metrics_collector.metric_samplers) == 0
    
    @pytest.mark.asyncio
    async def test_metrics_report(self, metrics_collector):
        """Test generating metrics report."""
        # Register metrics
        metric1 = await metrics_collector.register_metric(
            name="CPU Usage",
            description="CPU usage percentage",
            type=MetricType.GAUGE,
            category=MetricCategory.SYSTEM,
            unit="percent"
        )
        
        metric2 = await metrics_collector.register_metric(
            name="Memory Usage",
            description="Memory usage percentage",
            type=MetricType.GAUGE,
            category=MetricCategory.SYSTEM,
            unit="percent"
        )
        
        metric3 = await metrics_collector.register_metric(
            name="API Latency",
            description="API response latency",
            type=MetricType.HISTOGRAM,
            category=MetricCategory.PERFORMANCE,
            unit="ms"
        )
        
        # Record some values
        for i in range(5):
            await metrics_collector.record_metric(
                metric_id=metric1.id,
                value=40.0 + i * 5
            )
            
            await metrics_collector.record_metric(
                metric_id=metric2.id,
                value=60.0 + i * 2
            )
            
            await metrics_collector.record_metric(
                metric_id=metric3.id,
                value=100.0 + i * 20
            )
        
        # Create report
        report = await metrics_collector.create_metrics_report()
        
        assert report["status"] == "success"
        assert "summary" in report
        # The MetricsCollector also has built-in metrics, so the total count will be higher
        assert report["summary"]["total_metrics"] >= 3
        assert report["summary"]["total_values"] >= 15  # 3 metrics x 5 values each
        assert "visualizations" in report
        assert "metrics" in report
    
    @pytest.mark.asyncio
    async def test_mad_anomaly_detection(self, metrics_collector):
        """Test MAD anomaly detection."""
        # Register metric
        metric = await metrics_collector.register_metric(
            name="API Error Rate",
            description="Error rate percentage",
            type=MetricType.GAUGE,
            category=MetricCategory.RELIABILITY,
            unit="percent"
        )
        
        # Register anomaly definition with MAD method
        anomaly = await metrics_collector.register_anomaly_definition(
            name="Error Rate Spike",
            description="Detects unusual spikes in error rates",
            metric_id=metric.id,
            detection_method="mad",
            parameters={"threshold": 2.5},
            severity="critical"
        )
        
        # Record normal values
        values = [1.2, 1.5, 1.8, 1.3, 1.7, 1.6, 1.9]
        for value in values:
            await metrics_collector.record_metric(
                metric_id=metric.id,
                value=value,
                component="api_gateway"
            )
        
        # Record anomalous value
        await metrics_collector.record_metric(
            metric_id=metric.id,
            value=8.5,  # Major spike
            component="api_gateway"
        )
        
        # Should have detected anomaly
        anomalies = await metrics_collector.get_anomalies(severity="critical")
        assert len(anomalies) == 1
        assert anomalies[0]["metric_id"] == metric.id
        assert anomalies[0]["value"] == 8.5
        assert anomalies[0]["severity"] == "critical"
    
    @pytest.mark.asyncio
    async def test_iqr_anomaly_detection(self, metrics_collector):
        """Test IQR anomaly detection."""
        # Register metric
        metric = await metrics_collector.register_metric(
            name="Response Size",
            description="Response size in KB",
            type=MetricType.HISTOGRAM,
            category=MetricCategory.PERFORMANCE,
            unit="KB"
        )
        
        # Register anomaly definition with IQR method
        anomaly = await metrics_collector.register_anomaly_definition(
            name="Unusual Response Size",
            description="Detects unusually large or small responses",
            metric_id=metric.id,
            detection_method="iqr",
            parameters={"multiplier": 1.5},
            severity="warning"
        )
        
        # Record enough values for quartiles
        values = [10, 12, 15, 14, 13, 18, 16, 11, 19, 17]
        for value in values:
            await metrics_collector.record_metric(
                metric_id=metric.id,
                value=value,
                component="web_service"
            )
        
        # Record anomalous value (outlier)
        await metrics_collector.record_metric(
            metric_id=metric.id,
            value=35.0,  # Much larger than normal
            component="web_service"
        )
        
        # Should have detected anomaly
        anomalies = await metrics_collector.get_anomalies()
        assert len(anomalies) == 1
        assert anomalies[0]["metric_id"] == metric.id
        assert anomalies[0]["value"] == 35.0
    
    @pytest.mark.asyncio
    async def test_group_results(self, metrics_collector):
        """Test grouping query results."""
        # Register metrics
        metric1 = await metrics_collector.register_metric(
            name="Latency Service A",
            description="Service A latency",
            type=MetricType.HISTOGRAM,
            category=MetricCategory.PERFORMANCE,
            unit="ms"
        )
        
        metric2 = await metrics_collector.register_metric(
            name="Latency Service B",
            description="Service B latency",
            type=MetricType.HISTOGRAM,
            category=MetricCategory.PERFORMANCE,
            unit="ms"
        )
        
        # Record values for different components
        components = ["frontend", "backend", "database"]
        for component in components:
            for i in range(3):
                await metrics_collector.record_metric(
                    metric_id=metric1.id,
                    value=50.0 + i * 10,
                    component=component
                )
                
                await metrics_collector.record_metric(
                    metric_id=metric2.id,
                    value=30.0 + i * 5,
                    component=component
                )
        
        # Query with grouping by component
        query = MetricQuery(group_by="component")
        results = await metrics_collector.query_metrics(query)
        
        assert "grouped_results" in results
        assert set(results["grouped_results"].keys()) >= set(components)
        
        # Verify each component group has the right metrics
        for component in components:
            component_results = results["grouped_results"][component]
            assert len(component_results) >= 2  # Both metrics
            
            for result in component_results:
                assert all(v["component"] == component for v in result["values"])
                
        # Query with grouping by category and only our specific metrics
        query = MetricQuery(
            metric_ids=[metric1.id, metric2.id],
            group_by="category"
        )
        results = await metrics_collector.query_metrics(query)
        
        assert "grouped_results" in results
        assert "performance" in results["grouped_results"]
        assert len(results["grouped_results"]["performance"]) == 2  # Both metrics 