"""
Planning Engine Visualization.

This module provides visualization capabilities for planning components and outputs,
supporting both user-facing displays and machine-readable formats.
"""

from typing import Dict, List, Optional, Any, Union, Tuple
import logging
import json
import os
from enum import Enum
from datetime import datetime
import uuid

from src.server.planning.planning_engine import IntegratedPlan, PlanType
from src.server.planning.planning_metrics import MetricTrend, MetricType

logger = logging.getLogger(__name__)

class VisualizationType(Enum):
    """Types of visualizations supported by the system."""
    GOAL_HIERARCHY = "goal_hierarchy"
    DEPENDENCY_GRAPH = "dependency_graph"
    RESOURCE_ALLOCATION = "resource_allocation"
    TIMELINE = "timeline"
    METRICS_TREND = "metrics_trend"
    COMPARISON = "comparison"

class OutputFormat(Enum):
    """Output formats for visualizations."""
    JSON = "json"
    HTML = "html"
    MERMAID = "mermaid"
    D3 = "d3"
    PLOTLY = "plotly"

class PlanningVisualization:
    """
    Provides visualization capabilities for planning components.
    
    This class generates various visualizations for integrated plans,
    goals, implementations, resources, and metrics, supporting different
    output formats for both human and machine consumption.
    """
    
    def __init__(self, storage_path: str = "data/planning/visualizations"):
        """
        Initialize the Planning Visualization.
        
        Args:
            storage_path: Path to store visualization outputs
        """
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
    
    def visualize_integrated_plan(
        self,
        plan: IntegratedPlan,
        visualization_type: VisualizationType,
        output_format: OutputFormat,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a visualization for an integrated plan.
        
        Args:
            plan: The integrated plan to visualize
            visualization_type: Type of visualization to generate
            output_format: Output format for the visualization
            context: Additional context for the visualization
            
        Returns:
            Visualization result with content and metadata
        """
        context = context or {}
        
        # Generate unique ID for this visualization
        vis_id = str(uuid.uuid4())
        
        # Prepare result structure
        result = {
            "id": vis_id,
            "plan_id": plan.id,
            "type": visualization_type.value,
            "format": output_format.value,
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "plan_name": plan.name,
                "plan_type": plan.plan_type.value if plan.plan_type else None,
                "generation_context": context
            }
        }
        
        # Generate visualization based on type
        if visualization_type == VisualizationType.GOAL_HIERARCHY:
            result.update(self._generate_goal_hierarchy(plan, output_format, context))
        elif visualization_type == VisualizationType.DEPENDENCY_GRAPH:
            result.update(self._generate_dependency_graph(plan, output_format, context))
        elif visualization_type == VisualizationType.RESOURCE_ALLOCATION:
            result.update(self._generate_resource_allocation(plan, output_format, context))
        elif visualization_type == VisualizationType.TIMELINE:
            result.update(self._generate_timeline(plan, output_format, context))
        else:
            raise ValueError(f"Unsupported visualization type: {visualization_type}")
        
        # Save visualization if format supports persistence
        if output_format in [OutputFormat.JSON, OutputFormat.HTML, OutputFormat.MERMAID]:
            self._save_visualization(result, vis_id)
        
        return result
    
    def visualize_metrics_trend(
        self,
        trends: Dict[MetricType, MetricTrend],
        output_format: OutputFormat,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a visualization for metrics trends.
        
        Args:
            trends: Dictionary of metric trends
            output_format: Output format for the visualization
            context: Additional context for the visualization
            
        Returns:
            Visualization result with content and metadata
        """
        context = context or {}
        
        # Generate unique ID for this visualization
        vis_id = str(uuid.uuid4())
        
        # Prepare result structure
        result = {
            "id": vis_id,
            "type": VisualizationType.METRICS_TREND.value,
            "format": output_format.value,
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "metric_types": [t.value for t in trends.keys()],
                "generation_context": context
            }
        }
        
        # Generate trends visualization
        if output_format == OutputFormat.JSON:
            json_data = {}
            
            for metric_type, trend in trends.items():
                json_data[metric_type.value] = {
                    "data_points": trend.data_points,
                    "mean": trend.mean,
                    "median": trend.median,
                    "min": trend.min_value,
                    "max": trend.max_value,
                    "std_dev": trend.standard_deviation,
                    "trend_direction": trend.trend_direction,
                    "rate_of_change": trend.rate_of_change
                }
            
            result["content"] = json.dumps(json_data, indent=2)
            result["content_type"] = "application/json"
        
        elif output_format == OutputFormat.PLOTLY:
            # For Plotly, we provide the data structure that can be used to create a plot
            plotly_data = []
            
            for metric_type, trend in trends.items():
                trace = {
                    "type": "scatter",
                    "mode": "lines+markers",
                    "name": metric_type.value,
                    "x": [point[0] for point in trend.data_points],  # timestamps
                    "y": [point[1] for point in trend.data_points],  # values
                    "text": [f"Value: {point[1]}<br>Time: {point[0]}" for point in trend.data_points],
                    "hoverinfo": "text+name"
                }
                plotly_data.append(trace)
            
            layout = {
                "title": "Metrics Trend Analysis",
                "xaxis": {"title": "Time"},
                "yaxis": {"title": "Value"},
                "hovermode": "closest"
            }
            
            result["content"] = {
                "data": plotly_data,
                "layout": layout
            }
            result["content_type"] = "application/vnd.plotly.v1+json"
        
        elif output_format == OutputFormat.HTML:
            # For HTML, we generate a simple representation that can be displayed
            html_content = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Metrics Trend Visualization</title>
                <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
                <style>
                    .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
                    .plot { width: 100%; height: 500px; }
                    .stats { margin-top: 30px; }
                    table { border-collapse: collapse; width: 100%; }
                    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                    th { background-color: #f2f2f2; }
                    tr:nth-child(even) { background-color: #f9f9f9; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Metrics Trend Visualization</h1>
                    <div id="plotDiv" class="plot"></div>
                    
                    <div class="stats">
                        <h2>Trend Statistics</h2>
                        <table>
                            <tr>
                                <th>Metric</th>
                                <th>Mean</th>
                                <th>Median</th>
                                <th>Min</th>
                                <th>Max</th>
                                <th>Std Dev</th>
                                <th>Trend</th>
                                <th>Rate of Change</th>
                            </tr>
            """
            
            for metric_type, trend in trends.items():
                html_content += f"""
                <tr>
                    <td>{metric_type.value}</td>
                    <td>{trend.mean:.2f}</td>
                    <td>{trend.median:.2f}</td>
                    <td>{trend.min_value:.2f}</td>
                    <td>{trend.max_value:.2f}</td>
                    <td>{trend.standard_deviation:.2f}</td>
                    <td>{trend.trend_direction}</td>
                    <td>{trend.rate_of_change:.4f}</td>
                </tr>
                """
            
            html_content += """
                        </table>
                    </div>
                </div>
                
                <script>
                    const data = [];
            """
            
            for metric_type, trend in trends.items():
                x_values = [f"'{point[0]}'" for point in trend.data_points]
                y_values = [str(point[1]) for point in trend.data_points]
                
                html_content += f"""
                    data.push({{
                        x: [{', '.join(x_values)}],
                        y: [{', '.join(y_values)}],
                        type: 'scatter',
                        mode: 'lines+markers',
                        name: '{metric_type.value}'
                    }});
                """
            
            html_content += """
                    const layout = {
                        title: 'Metrics Trend Analysis',
                        xaxis: {
                            title: 'Time'
                        },
                        yaxis: {
                            title: 'Value'
                        }
                    };
                    
                    Plotly.newPlot('plotDiv', data, layout);
                </script>
            </body>
            </html>
            """
            
            result["content"] = html_content
            result["content_type"] = "text/html"
        
        else:
            raise ValueError(f"Unsupported output format for metrics trend: {output_format}")
        
        # Save visualization if format supports persistence
        if output_format in [OutputFormat.JSON, OutputFormat.HTML]:
            self._save_visualization(result, vis_id)
        
        return result
    
    def compare_plans(
        self,
        plans: List[IntegratedPlan],
        comparison_metrics: List[str],
        output_format: OutputFormat,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a comparison visualization for multiple plans.
        
        Args:
            plans: List of plans to compare
            comparison_metrics: Metrics to use for comparison
            output_format: Output format for the visualization
            context: Additional context for the visualization
            
        Returns:
            Visualization result with content and metadata
        """
        context = context or {}
        
        # Generate unique ID for this visualization
        vis_id = str(uuid.uuid4())
        
        # Prepare result structure
        result = {
            "id": vis_id,
            "type": VisualizationType.COMPARISON.value,
            "format": output_format.value,
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "plan_ids": [p.id for p in plans],
                "plan_names": [p.name for p in plans],
                "comparison_metrics": comparison_metrics,
                "generation_context": context
            }
        }
        
        # Extract data for comparison
        comparison_data = []
        
        for plan in plans:
            plan_data = {
                "id": plan.id,
                "name": plan.name,
                "type": plan.plan_type.value if plan.plan_type else None,
                "status": plan.status,
                "creation_time": plan.creation_time,
                "metrics": {}
            }
            
            # Extract metrics from plan metadata or versions
            for metric in comparison_metrics:
                if metric in plan.metadata:
                    plan_data["metrics"][metric] = plan.metadata[metric]
                elif hasattr(plan, "metrics") and plan.metrics and hasattr(plan.metrics, metric):
                    plan_data["metrics"][metric] = getattr(plan.metrics, metric)
                else:
                    plan_data["metrics"][metric] = None
            
            comparison_data.append(plan_data)
        
        # Generate comparison visualization
        if output_format == OutputFormat.JSON:
            result["content"] = json.dumps(comparison_data, indent=2)
            result["content_type"] = "application/json"
        
        elif output_format == OutputFormat.HTML:
            # For HTML, we generate a simple table for comparison
            html_content = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Plan Comparison</title>
                <style>
                    .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
                    table { border-collapse: collapse; width: 100%; }
                    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                    th { background-color: #f2f2f2; }
                    tr:nth-child(even) { background-color: #f9f9f9; }
                    .highlight { background-color: #e6f7ff; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Plan Comparison</h1>
                    <table>
                        <tr>
                            <th>Plan</th>
                            <th>Type</th>
                            <th>Status</th>
                            <th>Creation Time</th>
            """
            
            for metric in comparison_metrics:
                html_content += f"<th>{metric}</th>\n"
            
            html_content += """
                        </tr>
            """
            
            for plan_data in comparison_data:
                html_content += f"""
                <tr>
                    <td>{plan_data["name"]} ({plan_data["id"]})</td>
                    <td>{plan_data["type"] or "N/A"}</td>
                    <td>{plan_data["status"] or "N/A"}</td>
                    <td>{plan_data["creation_time"] or "N/A"}</td>
                """
                
                for metric in comparison_metrics:
                    value = plan_data["metrics"].get(metric, "N/A")
                    if value is None:
                        value = "N/A"
                    html_content += f"<td>{value}</td>\n"
                
                html_content += "</tr>\n"
            
            html_content += """
                    </table>
                </div>
            </body>
            </html>
            """
            
            result["content"] = html_content
            result["content_type"] = "text/html"
        
        elif output_format == OutputFormat.PLOTLY:
            # For Plotly, we provide data structure for comparison chart
            metrics = comparison_metrics.copy()
            
            # Prepare data for each metric
            plotly_data = []
            
            for metric in metrics:
                trace = {
                    "type": "bar",
                    "name": metric,
                    "x": [p["name"] for p in comparison_data],
                    "y": [p["metrics"].get(metric, 0) for p in comparison_data],
                    "text": [f"{p['name']}: {p['metrics'].get(metric, 'N/A')}" for p in comparison_data],
                    "hoverinfo": "text"
                }
                plotly_data.append(trace)
            
            layout = {
                "title": "Plan Comparison",
                "barmode": "group",
                "xaxis": {"title": "Plans"},
                "yaxis": {"title": "Value"}
            }
            
            result["content"] = {
                "data": plotly_data,
                "layout": layout
            }
            result["content_type"] = "application/vnd.plotly.v1+json"
        
        else:
            raise ValueError(f"Unsupported output format for plan comparison: {output_format}")
        
        # Save visualization if format supports persistence
        if output_format in [OutputFormat.JSON, OutputFormat.HTML]:
            self._save_visualization(result, vis_id)
        
        return result
    
    def _generate_goal_hierarchy(
        self,
        plan: IntegratedPlan,
        output_format: OutputFormat,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate goal hierarchy visualization."""
        # Placeholder implementation - in a real system, this would extract the goal
        # data from goal decomposition component and generate appropriate visualization
        
        result = {
            "content_type": "application/json",
            "title": f"Goal Hierarchy for {plan.name}"
        }
        
        if output_format == OutputFormat.JSON:
            result["content"] = json.dumps({
                "type": "goal_hierarchy",
                "plan_id": plan.id,
                "goal_decomposition_id": plan.goal_decomposition_id,
                "message": "Goal hierarchy visualization (placeholder implementation)"
            }, indent=2)
        
        elif output_format == OutputFormat.MERMAID:
            # Example Mermaid diagram for goal hierarchy
            mermaid_content = """
graph TD
    A[Main Goal] --> B[Subgoal 1]
    A --> C[Subgoal 2]
    A --> D[Subgoal 3]
    B --> E[Task 1.1]
    B --> F[Task 1.2]
    C --> G[Task 2.1]
    D --> H[Task 3.1]
    D --> I[Task 3.2]
            """
            
            result["content"] = mermaid_content.strip()
            result["content_type"] = "text/vnd.mermaid"
        
        elif output_format == OutputFormat.HTML:
            # Simple HTML visualization with embedded mermaid
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Goal Hierarchy for {plan.name}</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <style>
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .mermaid {{ text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Goal Hierarchy for {plan.name}</h1>
        <div class="mermaid">
graph TD
    A[Main Goal] --> B[Subgoal 1]
    A --> C[Subgoal 2]
    A --> D[Subgoal 3]
    B --> E[Task 1.1]
    B --> F[Task 1.2]
    C --> G[Task 2.1]
    D --> H[Task 3.1]
    D --> I[Task 3.2]
        </div>
    </div>
    <script>
        mermaid.initialize({{ startOnLoad: true }});
    </script>
</body>
</html>
            """
            
            result["content"] = html_content
            result["content_type"] = "text/html"
        
        else:
            raise ValueError(f"Unsupported output format for goal hierarchy: {output_format}")
        
        return result
    
    def _generate_dependency_graph(
        self,
        plan: IntegratedPlan,
        output_format: OutputFormat,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate dependency graph visualization."""
        # Placeholder implementation - in a real system, this would extract the
        # dependency data from implementation planner and generate appropriate visualization
        
        result = {
            "content_type": "application/json",
            "title": f"Dependency Graph for {plan.name}"
        }
        
        if output_format == OutputFormat.JSON:
            result["content"] = json.dumps({
                "type": "dependency_graph",
                "plan_id": plan.id,
                "implementation_plan_id": plan.implementation_plan_id,
                "message": "Dependency graph visualization (placeholder implementation)"
            }, indent=2)
        
        elif output_format == OutputFormat.MERMAID:
            # Example Mermaid diagram for dependency graph
            mermaid_content = """
graph LR
    A[Setup Environment] --> B[Initialize Components]
    A --> C[Configure Database]
    B --> D[Implement Core Logic]
    C --> D
    D --> E[Implement UI]
    D --> F[Implement API]
    E --> G[Testing]
    F --> G
    G --> H[Deployment]
            """
            
            result["content"] = mermaid_content.strip()
            result["content_type"] = "text/vnd.mermaid"
        
        elif output_format == OutputFormat.HTML:
            # Simple HTML visualization with embedded mermaid
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Dependency Graph for {plan.name}</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <style>
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .mermaid {{ text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Dependency Graph for {plan.name}</h1>
        <div class="mermaid">
graph LR
    A[Setup Environment] --> B[Initialize Components]
    A --> C[Configure Database]
    B --> D[Implement Core Logic]
    C --> D
    D --> E[Implement UI]
    D --> F[Implement API]
    E --> G[Testing]
    F --> G
    G --> H[Deployment]
        </div>
    </div>
    <script>
        mermaid.initialize({{ startOnLoad: true }});
    </script>
</body>
</html>
            """
            
            result["content"] = html_content
            result["content_type"] = "text/html"
        
        else:
            raise ValueError(f"Unsupported output format for dependency graph: {output_format}")
        
        return result
    
    def _generate_resource_allocation(
        self,
        plan: IntegratedPlan,
        output_format: OutputFormat,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate resource allocation visualization."""
        # Placeholder implementation - in a real system, this would extract the
        # resource data from allocation manager and generate appropriate visualization
        
        result = {
            "content_type": "application/json",
            "title": f"Resource Allocation for {plan.name}"
        }
        
        if output_format == OutputFormat.JSON:
            result["content"] = json.dumps({
                "type": "resource_allocation",
                "plan_id": plan.id,
                "resource_allocation_id": plan.resource_allocation_id,
                "message": "Resource allocation visualization (placeholder implementation)"
            }, indent=2)
        
        elif output_format == OutputFormat.PLOTLY:
            # Example Plotly data for resource allocation
            plotly_data = [
                {
                    "type": "bar",
                    "x": ["Task 1", "Task 2", "Task 3", "Task 4", "Task 5"],
                    "y": [5, 3, 8, 4, 6],
                    "name": "Compute"
                },
                {
                    "type": "bar",
                    "x": ["Task 1", "Task 2", "Task 3", "Task 4", "Task 5"],
                    "y": [2, 4, 3, 6, 2],
                    "name": "Memory"
                },
                {
                    "type": "bar",
                    "x": ["Task 1", "Task 2", "Task 3", "Task 4", "Task 5"],
                    "y": [1, 1, 2, 1, 3],
                    "name": "Storage"
                }
            ]
            
            layout = {
                "title": f"Resource Allocation for {plan.name}",
                "barmode": "stack",
                "xaxis": {"title": "Tasks"},
                "yaxis": {"title": "Resource Units"}
            }
            
            result["content"] = {
                "data": plotly_data,
                "layout": layout
            }
            result["content_type"] = "application/vnd.plotly.v1+json"
        
        elif output_format == OutputFormat.HTML:
            # Simple HTML visualization with embedded plotly
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Resource Allocation for {plan.name}</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .plot {{ width: 100%; height: 500px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Resource Allocation for {plan.name}</h1>
        <div id="plotDiv" class="plot"></div>
    </div>
    <script>
        const data = [
            {{
                type: 'bar',
                x: ['Task 1', 'Task 2', 'Task 3', 'Task 4', 'Task 5'],
                y: [5, 3, 8, 4, 6],
                name: 'Compute'
            }},
            {{
                type: 'bar',
                x: ['Task 1', 'Task 2', 'Task 3', 'Task 4', 'Task 5'],
                y: [2, 4, 3, 6, 2],
                name: 'Memory'
            }},
            {{
                type: 'bar',
                x: ['Task 1', 'Task 2', 'Task 3', 'Task 4', 'Task 5'],
                y: [1, 1, 2, 1, 3],
                name: 'Storage'
            }}
        ];
        
        const layout = {{
            title: 'Resource Allocation for {plan.name}',
            barmode: 'stack',
            xaxis: {{ title: 'Tasks' }},
            yaxis: {{ title: 'Resource Units' }}
        }};
        
        Plotly.newPlot('plotDiv', data, layout);
    </script>
</body>
</html>
            """
            
            result["content"] = html_content
            result["content_type"] = "text/html"
        
        else:
            raise ValueError(f"Unsupported output format for resource allocation: {output_format}")
        
        return result
    
    def _generate_timeline(
        self,
        plan: IntegratedPlan,
        output_format: OutputFormat,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate timeline visualization."""
        # Placeholder implementation - in a real system, this would extract the
        # timeline data from implementation planner and generate appropriate visualization
        
        result = {
            "content_type": "application/json",
            "title": f"Timeline for {plan.name}"
        }
        
        if output_format == OutputFormat.JSON:
            result["content"] = json.dumps({
                "type": "timeline",
                "plan_id": plan.id,
                "implementation_plan_id": plan.implementation_plan_id,
                "message": "Timeline visualization (placeholder implementation)"
            }, indent=2)
        
        elif output_format == OutputFormat.PLOTLY:
            # Example Plotly data for timeline (Gantt chart)
            tasks = [
                "Setup Environment", 
                "Initialize Components", 
                "Configure Database", 
                "Implement Core Logic",
                "Implement UI",
                "Implement API",
                "Testing",
                "Deployment"
            ]
            
            start_dates = [
                "2023-01-01", "2023-01-03", "2023-01-03", "2023-01-05",
                "2023-01-10", "2023-01-10", "2023-01-15", "2023-01-20"
            ]
            
            end_dates = [
                "2023-01-03", "2023-01-05", "2023-01-04", "2023-01-10",
                "2023-01-15", "2023-01-14", "2023-01-20", "2023-01-22"
            ]
            
            colors = [
                "#FF9900", "#FF9900", "#FF9900", "#3366CC",
                "#3366CC", "#3366CC", "#109618", "#109618"
            ]
            
            plotly_data = [{
                "type": "bar",
                "x": [end_dates[i] if end_dates[i] else start_dates[i] for i in range(len(tasks))],
                "y": tasks,
                "orientation": "h",
                "base": start_dates,
                "marker": {
                    "color": colors
                },
                "hoverinfo": "text",
                "text": [f"{tasks[i]}<br>Start: {start_dates[i]}<br>End: {end_dates[i]}" for i in range(len(tasks))]
            }]
            
            layout = {
                "title": f"Timeline for {plan.name}",
                "xaxis": {
                    "type": "date",
                    "title": "Date"
                },
                "yaxis": {
                    "title": "Task",
                    "autorange": "reversed"  # To have the first task at the top
                },
                "height": 600,
                "margin": {
                    "l": 150  # To accommodate long task names
                }
            }
            
            result["content"] = {
                "data": plotly_data,
                "layout": layout
            }
            result["content_type"] = "application/vnd.plotly.v1+json"
        
        elif output_format == OutputFormat.HTML:
            # Simple HTML visualization with embedded plotly for timeline
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Timeline for {plan.name}</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .plot {{ width: 100%; height: 600px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Timeline for {plan.name}</h1>
        <div id="plotDiv" class="plot"></div>
    </div>
    <script>
        const tasks = [
            "Setup Environment", 
            "Initialize Components", 
            "Configure Database", 
            "Implement Core Logic",
            "Implement UI",
            "Implement API",
            "Testing",
            "Deployment"
        ];
        
        const startDates = [
            "2023-01-01", "2023-01-03", "2023-01-03", "2023-01-05",
            "2023-01-10", "2023-01-10", "2023-01-15", "2023-01-20"
        ];
        
        const endDates = [
            "2023-01-03", "2023-01-05", "2023-01-04", "2023-01-10",
            "2023-01-15", "2023-01-14", "2023-01-20", "2023-01-22"
        ];
        
        const colors = [
            "#FF9900", "#FF9900", "#FF9900", "#3366CC",
            "#3366CC", "#3366CC", "#109618", "#109618"
        ];
        
        const data = [{{
            type: "bar",
            x: endDates.map((end, i) => end || startDates[i]),
            y: tasks,
            orientation: "h",
            base: startDates,
            marker: {{
                color: colors
            }},
            hoverinfo: "text",
            text: tasks.map((task, i) => `${{task}}<br>Start: ${{startDates[i]}}<br>End: ${{endDates[i]}}`)
        }}];
        
        const layout = {{
            title: 'Timeline for {plan.name}',
            xaxis: {{
                type: 'date',
                title: 'Date'
            }},
            yaxis: {{
                title: 'Task',
                autorange: 'reversed'  // To have the first task at the top
            }},
            height: 600,
            margin: {{
                l: 150  // To accommodate long task names
            }}
        }};
        
        Plotly.newPlot('plotDiv', data, layout);
    </script>
</body>
</html>
            """
            
            result["content"] = html_content
            result["content_type"] = "text/html"
        
        else:
            raise ValueError(f"Unsupported output format for timeline: {output_format}")
        
        return result
    
    def _save_visualization(self, visualization: Dict[str, Any], vis_id: str):
        """Save visualization to storage."""
        file_name = f"{vis_id}.json"
        file_path = os.path.join(self.storage_path, file_name)
        
        # Serialize the visualization data
        serialized = {
            "id": visualization["id"],
            "plan_id": visualization.get("plan_id"),
            "type": visualization["type"],
            "format": visualization["format"],
            "timestamp": visualization["timestamp"],
            "metadata": visualization["metadata"],
            "content_type": visualization["content_type"],
            "content": visualization["content"]
        }
        
        # Write to file
        with open(file_path, "w") as f:
            json.dump(serialized, f, indent=2)
        
        logger.info(f"Saved visualization {vis_id} to {file_path}")
    
    def load_visualization(self, vis_id: str) -> Optional[Dict[str, Any]]:
        """
        Load a previously saved visualization.
        
        Args:
            vis_id: ID of the visualization to load
            
        Returns:
            Visualization data or None if not found
        """
        file_path = os.path.join(self.storage_path, f"{vis_id}.json")
        
        if not os.path.exists(file_path):
            logger.warning(f"Visualization file not found: {file_path}")
            return None
        
        try:
            with open(file_path, "r") as f:
                visualization = json.load(f)
            
            return visualization
        except Exception as e:
            logger.error(f"Error loading visualization {vis_id}: {e}")
            return None
    
    def list_visualizations(
        self,
        plan_id: Optional[str] = None,
        visualization_type: Optional[VisualizationType] = None
    ) -> List[Dict[str, Any]]:
        """
        List available visualizations with optional filtering.
        
        Args:
            plan_id: Filter by plan ID
            visualization_type: Filter by visualization type
            
        Returns:
            List of visualization metadata
        """
        visualizations = []
        
        for file_name in os.listdir(self.storage_path):
            if not file_name.endswith(".json"):
                continue
                
            file_path = os.path.join(self.storage_path, file_name)
            
            try:
                with open(file_path, "r") as f:
                    vis_data = json.load(f)
                
                # Apply filters if specified
                if plan_id and vis_data.get("plan_id") != plan_id:
                    continue
                    
                if visualization_type and vis_data.get("type") != visualization_type.value:
                    continue
                
                # Add metadata to result
                visualizations.append({
                    "id": vis_data["id"],
                    "plan_id": vis_data.get("plan_id"),
                    "type": vis_data["type"],
                    "format": vis_data["format"],
                    "timestamp": vis_data["timestamp"],
                    "title": vis_data.get("metadata", {}).get("title", "Untitled")
                })
            except Exception as e:
                logger.error(f"Error reading visualization file {file_name}: {e}")
        
        # Sort by timestamp (newest first)
        visualizations.sort(key=lambda v: v["timestamp"], reverse=True)
        
        return visualizations 